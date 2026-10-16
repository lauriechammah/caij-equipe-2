"""Clients minimaux pour Compagnon (recherche CAIJ) et Augure (LLM compatible OpenAI).

Même logique que scripts/compagnon.py et scripts/augure.py, mais les erreurs
lèvent des exceptions au lieu d'appeler sys.exit (utilisable dans un serveur).
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from backend.journal import SuiviAugure, chrono, journal, nombre

ROOT = Path(__file__).resolve().parent.parent


class CompagnonError(RuntimeError):
    pass


class AugureError(RuntimeError):
    pass


def load_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()


def compagnon_search(query, types=("legislation",), top_k=10, clarifications=None):
    """Recherche sémantique Compagnon. Renvoie le JSON décodé de l'événement « done »."""
    base_url = os.environ.get("COMPAGNON_API_URL") or "https://hackathon.caij.qc.ca"
    payload = {
        "query": query,
        "search_types": list(types),
        "top_k": top_k,
        "semantic_analysis": False,
        "summarization": False,
    }
    if clarifications:
        payload["clarifications"] = clarifications
    req = urllib.request.Request(
        base_url.rstrip("/") + "/semantic-search",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
    )
    event = None
    with chrono(f"Compagnon « {' '.join(query.split())[:60]} » ({', '.join(types)}, top_k {top_k})",
                service="Compagnon") as infos:
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                for raw in resp:
                    line = raw.decode("utf-8").strip()
                    if line.startswith("event:"):
                        event = line[6:].strip()
                    elif line.startswith("data:") and event in ("done", "error"):
                        data = json.loads(line[5:].strip())
                        if event == "error":
                            raise CompagnonError(data)
                        resultat = json.loads(data["message"])
                        infos["résultats"] = sum(len(v or []) for v in (resultat.get("results") or {}).values())
                        return resultat
        except urllib.error.HTTPError as e:
            raise CompagnonError(f"{e.code} : {e.read().decode('utf-8', 'replace')}") from e
        raise CompagnonError("Aucun résultat reçu du Compagnon")


def augure_chat(prompt, system=None, model=None, effort="low", max_tokens=64000):
    """Envoie un prompt texte à Augure (streaming SSE) et renvoie la réponse complète.

    Si le modèle épuise son budget en raisonnement sans répondre (reasoning_cutoff),
    l'appel est refait une fois sans raisonnement.
    """
    try:
        return _augure_chat(prompt, system, model, effort, max_tokens)
    except AugureError as e:
        if "reasoning_cutoff" not in str(e) or effort == "none":
            raise
        journal.warning("Augure a épuisé son budget de raisonnement (effort %s) : nouvel appel sans raisonnement", effort)
        return _augure_chat(prompt, system, model, "none", max_tokens)


def _augure_chat(prompt, system, model, effort, max_tokens):
    api_key = os.environ.get("AUGURE_API_KEY")
    if not api_key:
        raise AugureError("AUGURE_API_KEY manquant (voir .env.example)")
    base_url = os.environ.get("AUGURE_BASE_URL") or "https://api.augureai.ca/v1"

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model or os.environ.get("AUGURE_MODEL") or "rosedale-1",
        "messages": messages,
        "stream": True,
        # Jetons lus et produits dans le dernier événement, pour le journal.
        "stream_options": {"include_usage": True},
        "max_tokens": max_tokens,
    }
    if effort:
        payload["reasoning_effort"] = effort

    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    taille = f"{nombre(len(prompt))} car." + (f" + consigne {nombre(len(system))} car." if system else "")
    try:
        with SuiviAugure(payload, taille) as suivi:
            with urllib.request.urlopen(req, timeout=600) as resp:
                suivi.entetes()
                texte = lire_flux(resp, suivi)
            suivi.recu(texte)
    except urllib.error.HTTPError as e:
        raise AugureError(f"{e.code} : {e.read().decode('utf-8', 'replace')}") from e
    return texte


def lire_flux(resp, suivi=None):
    """Lit la réponse SSE d'Augure jusqu'à [DONE] ; ``suivi`` (journal.SuiviAugure) voit chaque événement."""
    chunks = []
    for raw in resp:
        line = raw.decode("utf-8").strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        event = json.loads(data)
        if "error" in event:
            raise AugureError(event["error"])
        if suivi:
            suivi.evenement(event)
        for choice in event.get("choices", []):
            delta = choice.get("delta", {}).get("content")
            if delta:
                chunks.append(delta)
    return "".join(chunks)
