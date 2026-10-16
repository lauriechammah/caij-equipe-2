"""Interroger Augure (API compatible OpenAI) en lui envoyant les pièces d'un dossier.

Les documents sont lus localement et envoyés à Augure : c'est Augure qui les
analyse, pas Claude. Seule la réponse d'Augure est imprimée.

Exemples :
    python scripts/augure.py --dossier mandat_protection "Liste les faits contradictoires."
    python scripts/augure.py --dossier servitude_enclave --modele "Quelles options du modèle retenir ?"
    python scripts/augure.py --file notes.txt --out sortie.md "Résume."
    python scripts/augure.py --list-models
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOSSIERS = ROOT / "docs" / "dossiers_fictifs"
MODELES = ROOT / "docs" / "modeles"
BASE_URL = "https://api.augureai.ca/v1"


def load_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def text_part(path):
    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    body = path.read_text(encoding="utf-8")
    return {"type": "text", "text": f"--- Document : {rel} ---\n{body}"}


def pdf_part(path):
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "file",
        "file": {"filename": path.name, "file_data": f"data:application/pdf;base64,{data}"},
    }


def file_part(path):
    if path.suffix.lower() == ".pdf":
        return pdf_part(path)
    if path.suffix.lower() in (".docx", ".doc"):
        sys.exit(f"Format non supporté par Augure : {path.name} (utiliser la version .txt ou .pdf)")
    return text_part(path)


def dossier_parts(name):
    folder = DOSSIERS / name / "txt"
    if not folder.is_dir():
        sys.exit(f"Dossier introuvable : {folder}")
    return [text_part(p) for p in sorted(folder.glob("*.txt"))]


def modele_parts(name):
    pdfs = sorted((MODELES / name).glob("*.pdf"))
    if not pdfs:
        sys.exit(f"Aucun modèle PDF dans {MODELES / name}")
    return [pdf_part(p) for p in pdfs]


def request(method, path, api_key, payload=None):
    req = urllib.request.Request(
        BASE_URL + path,
        method=method,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        return urllib.request.urlopen(req, timeout=600)
    except urllib.error.HTTPError as e:
        sys.exit(f"Erreur Augure {e.code} : {e.read().decode('utf-8', 'replace')}")


def stream_chat(api_key, payload):
    """Streaming SSE : évite le délai de 240 s des requêtes non streamées."""
    chunks = []
    with request("POST", "/chat/completions", api_key, payload) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            event = json.loads(data)
            if "error" in event:
                sys.exit(f"Erreur Augure : {event['error']}")
            for choice in event.get("choices", []):
                delta = choice.get("delta", {}).get("content")
                if delta:
                    chunks.append(delta)
    return "".join(chunks)


def main():
    parser = argparse.ArgumentParser(description="Envoyer un dossier et une question à Augure.")
    parser.add_argument("prompt", nargs="?", help="La question (sinon lue sur stdin)")
    parser.add_argument("--dossier", help="Nom du dossier fictif (ex. mandat_protection)")
    parser.add_argument("--modele", action="store_true", help="Joindre le modèle d'acte PDF du même nom")
    parser.add_argument("--file", action="append", default=[], help="Fichier supplémentaire (.txt, .md, .pdf)")
    parser.add_argument("--system", help="Message système")
    parser.add_argument("--model", help="Modèle Augure (défaut : AUGURE_MODEL ou rosedale-1)")
    parser.add_argument("--effort", choices=["none", "low", "medium", "high"], help="reasoning_effort")
    parser.add_argument("--out", help="Écrire la réponse dans ce fichier")
    parser.add_argument("--list-models", action="store_true", help="Lister les modèles disponibles")
    args = parser.parse_args()

    load_env()
    api_key = os.environ.get("AUGURE_API_KEY")
    if not api_key:
        sys.exit("AUGURE_API_KEY manquant (voir .env.example)")

    if args.list_models:
        with request("GET", "/models", api_key) as resp:
            for m in json.load(resp).get("data", []):
                print(m.get("id"))
        return

    prompt = args.prompt or sys.stdin.read()
    if not prompt.strip():
        sys.exit("Aucune question fournie")

    content = []
    if args.dossier:
        content += dossier_parts(args.dossier)
        if args.modele:
            content += modele_parts(args.dossier)
    content += [file_part(Path(f).resolve()) for f in args.file]
    content.append({"type": "text", "text": prompt})

    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": content})

    payload = {
        "model": args.model or os.environ.get("AUGURE_MODEL", "rosedale-1"),
        "messages": messages,
        "stream": True,
    }
    if args.effort:
        payload["reasoning_effort"] = args.effort

    answer = stream_chat(api_key, payload)
    if args.out:
        Path(args.out).write_text(answer, encoding="utf-8")
        print(f"Réponse écrite dans {args.out}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(answer)


if __name__ == "__main__":
    main()
