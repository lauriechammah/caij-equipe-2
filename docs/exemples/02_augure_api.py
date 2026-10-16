# /// script
# requires-python = ">=3.10"
# dependencies = ["openai", "python-dotenv"]
# ///
"""Exemple 2 : appeler un modèle d'Augure par son API.

    uv run 02_augure_api.py --modeles      # lister les modèles accessibles avec la clé
    uv run 02_augure_api.py "Résume l'arrêt Vavilov en trois phrases."

L'API d'Augure est compatible avec celle d'OpenAI : on utilise le SDK `openai`
en changeant seulement `base_url` et la clé.
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ["AUGURE_API_KEY"],
    base_url=os.environ.get("AUGURE_BASE_URL", "https://api.augureai.ca/v1"),
    timeout=60.0,
)

SYSTEM_PROMPT = (
    "Tu es un assistant juridique québécois. Tu réponds en français, "
    "de façon concise, et tu signales ce dont tu n'es pas certain."
)


def list_models() -> None:
    for model in client.models.list():
        print(model.id)


def ask(question: str, model: str) -> None:
    """Pose une question et affiche la réponse au fil de sa génération."""
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("question", nargs="?", help="question à poser au modèle")
    parser.add_argument("--modeles", action="store_true", help="lister les modèles")
    parser.add_argument("--modele", default=os.environ.get("AUGURE_MODEL"))
    args = parser.parse_args()

    if args.modeles:
        list_models()
    elif not args.question:
        parser.error("donner une question, ou --modeles")
    elif not args.modele:
        sys.exit("Préciser le modèle : --modele <id> ou AUGURE_MODEL dans .env")
    else:
        ask(args.question, args.modele)


if __name__ == "__main__":
    main()
