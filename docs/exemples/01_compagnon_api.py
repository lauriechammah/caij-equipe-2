# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx", "python-dotenv"]
# ///
"""Exemple 1 : interroger l'API de Compagnon (recherche sémantique du CAIJ).

    uv run 01_compagnon_api.py "Quels sont les critères de l'outrage au tribunal ?"
    uv run 01_compagnon_api.py --complet "..."    # passages entiers, non tronqués

L'endpoint `/semantic-search` répond en Server-Sent Events : une suite
d'événements `status` (progression), puis un seul événement `done` qui porte
la réponse complète, ou un événement `error`.

L'analyse des résultats et le résumé sont désactivés sur l'instance du
hackathon : l'API renvoie les documents trouvés et, dans `content`, le texte
des passages repérés. À vous d'en faire quelque chose.
"""

import argparse
import json
import os
import sys
from typing import Iterable, Iterator

import httpx
from dotenv import load_dotenv

# Une variable déjà présente dans l'environnement l'emporte sur `.env`.
URL_FROM_ENVIRONMENT = bool(os.environ.get("COMPAGNON_API_URL", "").strip())
load_dotenv()

# URL de l'instance déployée pour le hackathon, sans le chemin (voir .env.example).
DEFAULT_API_URL = "http://localhost:8000"
CONFIGURED_API_URL = os.environ.get("COMPAGNON_API_URL", "").strip()
API_URL = (CONFIGURED_API_URL or DEFAULT_API_URL).rstrip("/")
if "://" not in API_URL:  # adresse donnée sans protocole
    API_URL = f"https://{API_URL}"

# Sources interrogeables : "jurisprudence", "doctrine", "legislation", "topo".
SEARCH_TYPES = ["jurisprudence", "doctrine", "legislation"]

# Longueur de l'extrait affiché par document, sauf avec --complet.
EXCERPT_CHARS = 600


def iter_sse(lines: Iterable[str]) -> Iterator[tuple[str, dict]]:
    """Découpe un flux SSE en couples (nom de l'événement, données JSON)."""
    event, data = "message", []
    for line in lines:
        if line.startswith("event:"):
            event = line[len("event:") :].strip()
        elif line.startswith("data:"):
            data.append(line[len("data:") :].strip())
        elif not line and data:  # une ligne vide termine l'événement
            yield event, json.loads("\n".join(data))
            event, data = "message", []


def search(query: str) -> dict:
    """Lance une recherche et renvoie la réponse complète de Compagnon."""
    payload = {
        "query": query,
        "search_types": SEARCH_TYPES,
    }
    # Pas de limite de lecture : le flux reste ouvert le temps du traitement.
    timeout = httpx.Timeout(10.0, read=None)
    with httpx.stream(
        "POST", f"{API_URL}/semantic-search", json=payload, timeout=timeout
    ) as response:
        if response.is_error:
            response.read()
            sys.exit(f"HTTP {response.status_code} : {response.text}")

        for event, data in iter_sse(response.iter_lines()):
            if event == "status":
                print(f"  … {data.get('stage')}", file=sys.stderr)
            elif event == "error":
                sys.exit(f"Erreur {data.get('code')} : {data.get('message')}")
            elif event == "done":
                # `message` contient la réponse complète, encodée en JSON.
                return json.loads(data["message"])

    sys.exit("Le flux s'est terminé sans événement « done ».")


def connection_help(error: Exception) -> str:
    """Message à afficher quand Compagnon est injoignable."""
    if CONFIGURED_API_URL:
        source = "l'environnement" if URL_FROM_ENVIRONMENT else ".env"
        advice = (
            f"Vérifier COMPAGNON_API_URL, lu dans {source} (adresse sans chemin "
            "ni barre finale), et que l'instance est bien démarrée."
        )
    else:
        advice = (
            f"COMPAGNON_API_URL n'est pas défini : le script vise {DEFAULT_API_URL} "
            "par défaut.\nDonner l'URL remise par l'équipe, dans .env ou en "
            "variable d'environnement, ou démarrer Compagnon en local."
        )
    return f"Impossible de joindre Compagnon à {API_URL}.\n{advice}\n({error})"


def excerpt(document: dict, complet: bool) -> str:
    """Texte des passages repérés dans le document.

    Quand plusieurs passages d'un même document ressortent, `content` les
    enchaîne, chacun précédé de « CHUNK INDEX: n ».
    """
    text = (document.get("content") or "").strip()
    if not complet and len(text) > EXCERPT_CHARS:
        text = text[:EXCERPT_CHARS].rstrip() + " […]"
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("query", help="question juridique en langage naturel")
    parser.add_argument(
        "--complet", action="store_true", help="afficher les passages en entier"
    )
    args = parser.parse_args()

    try:
        result = search(args.query)
    except (httpx.TransportError, httpx.InvalidURL) as error:
        sys.exit(connection_help(error))

    for source, documents in result["results"].items():
        print(f"\n== {source} ({len(documents)}) ==")
        for document in documents:
            print(f"\n- {document.get('title')}\n  {document.get('url')}")
            for line in excerpt(document, args.complet).splitlines():
                print(f"    {line}")


if __name__ == "__main__":
    main()
