"""Interroger le Compagnon du CAIJ (recherche dans jurisprudence, doctrine, législation).

Pas de clé requise. La réponse arrive en SSE ; le résultat final est dans
l'événement « done ».

Exemples :
    python scripts/compagnon.py "servitude de passage enclave"
    python scripts/compagnon.py --types legislation jurisprudence --top-k 5 "mandat de protection homologation"
    python scripts/compagnon.py --summary "indivision convention durée maximale"
    python scripts/compagnon.py --json --out out/resultats.json "testament fiducie enfants mineurs"
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://hackathon.caij.qc.ca/semantic-search"
TYPES = ["topo", "doctrine", "legislation", "jurisprudence"]


def search(query, types, top_k, summary, clarifications=None):
    payload = {
        "query": query,
        "search_types": types,
        "top_k": top_k,
        "semantic_analysis": summary,
        "summarization": summary,
    }
    if clarifications:
        payload["clarifications"] = clarifications
    req = urllib.request.Request(
        URL,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
    )
    event = None
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            for raw in resp:
                line = raw.decode("utf-8").strip()
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:") and event in ("done", "error"):
                    data = json.loads(line[5:].strip())
                    if event == "error":
                        sys.exit(f"Erreur Compagnon : {data}")
                    return json.loads(data["message"])
    except urllib.error.HTTPError as e:
        sys.exit(f"Erreur Compagnon {e.code} : {e.read().decode('utf-8', 'replace')}")
    sys.exit("Aucun résultat reçu du Compagnon")


def format_results(result, types, top_k, summary):
    lines = []
    if summary and result.get("textual_summary"):
        lines += ["## Résumé", str(result["textual_summary"]), ""]
    for kind, docs in result.get("results", {}).items():
        if kind not in types or not docs:
            continue
        lines.append(f"## {kind} ({len(docs)})")
        for doc in docs[:top_k]:
            snippet = " ".join(str(doc.get("content", "")).split())[:300]
            lines.append(f"- {doc.get('title')}\n  {doc.get('original_url') or doc.get('url')}\n  {snippet}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Recherche dans les sources du CAIJ.")
    parser.add_argument("query", help="La recherche en langage naturel")
    parser.add_argument("--types", nargs="+", choices=TYPES, default=["legislation", "jurisprudence", "doctrine"])
    parser.add_argument("--top-k", type=int, default=5, help="Résultats par type (1 à 100)")
    parser.add_argument("--summary", action="store_true", help="Demander l'analyse et le résumé du Compagnon (plus lent)")
    parser.add_argument("--clarifications", help="Précisions pour reformuler la requête")
    parser.add_argument("--json", action="store_true", help="Sortie JSON brute")
    parser.add_argument("--out", help="Écrire la sortie dans ce fichier")
    args = parser.parse_args()

    result = search(args.query, args.types, args.top_k, args.summary, args.clarifications)
    if args.json:
        output = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        output = format_results(result, args.types, args.top_k, args.summary)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Résultats écrits dans {args.out}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(output)


if __name__ == "__main__":
    main()
