"""Essayer le backend de bout en bout sur un dossier fictif.

    python -m backend.cli acte --dossier mandat_protection --types nullité inaptitude
    python -m backend.cli contradictions --dossier mandat_protection
    python -m backend.cli consequences --dossier mandat_protection --types nullité inaptitude
    python -m backend.cli sources "homologation du mandat de protection"

``acte`` enchaîne les trois étapes : droit applicable, contradictions, conséquences,
puis l'acte. Les sorties intermédiaires sont dans ``out/demo/``.

Le dossier n'est jamais lu ici : Augure lit les pièces et renvoie la synthèse,
les demandes du client et les éléments factuels.
"""

import argparse
import json
import sys
from pathlib import Path

from backend.acte import create_acte_modifie
from backend.analyse import get_contradictions, get_type_consequences, resume_droit_applicable
from backend.config import SORTIE
from backend.journal import configurer
from backend.llm import ErreurLLM, ask_augure, ask_compagnon

ETATRE = """
On te donne toutes les pièces txt d'un dossier client, dans l'ordre. En français, renvoie
un objet JSON : {"synthese": "résumé factuel du dossier, en 5 à 10 phrases, sans interprétation",
"demandes_clients": [{"demande": "ce que le client demande", "piece": "pièce d'où elle vient"}],
"commentaires": ["commentaire ou réserve de la notaire, pièce par pièce"],
"elements_factuels": ["un fait vérifiable et sa pièce, un par entrée"]}.
N'invente aucun fait et ne cite que des pièces reçues.
"""


def _sortie(dossier, nom, donnees):
    chemin = SORTIE.parent / "demo" / f"{dossier}-{nom}.json"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(donnees, str):
        chemin = chemin.with_suffix(".txt")
        chemin.write_text(donnees, encoding="utf-8")
    else:
        chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(chemin)
    return donnees


def _pieces(dossier):
    return ask_augure(f"Voici le dossier {dossier}.\n\n" + ETATRE, dossier=dossier)


def main():
    configurer()
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sous = parseur.add_subparsers(dest="commande", required=True)

    contradictions = sous.add_parser("contradictions", help="signaler les contradictions d'un dossier")
    contradictions.add_argument("--dossier", required=True)

    consequences = sous.add_parser("consequences", help="classer les conséquences possibles")
    consequences.add_argument("--dossier", required=True)
    consequences.add_argument("--types", nargs="+", required=True)

    acte = sous.add_parser("acte", help="enchaîner les trois étapes et produire l'acte Word")
    acte.add_argument("--dossier", required=True)
    acte.add_argument("--types", nargs="+", default=[],
                      help="liste des conséquences possibles")
    acte.add_argument("--plan", help="rejouer un plan JSON au lieu de le calculer")

    sources = sous.add_parser("sources", help="chercher dans les sources du CAIJ")
    sources.add_argument("question")

    args = parseur.parse_args()
    try:
        if args.commande == "sources":
            _sortie("recherche", "sources", ask_compagnon(args.question))
            return

        if getattr(args, "plan", None):
            plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
            _sortie(args.dossier, "acte", create_acte_modifie(
                "", [], [], [], [], dossier=args.dossier, plan=plan))
            return

        pieces = _pieces(args.dossier)
        synthese = pieces.get("synthese", "")
        demandes = pieces.get("demandes_clients", [])
        commentaires = pieces.get("commentaires", [])
        faits = pieces.get("elements_factuels", [])
        droit = resume_droit_applicable(synthese, faits, demandes, getattr(args, "types", None))

        if args.commande == "contradictions":
            _sortie(args.dossier, "contradictions", get_contradictions(
                demandes, commentaires, synthese, faits, droit_applicable=droit,
                dossier=args.dossier))
        elif args.commande == "consequences":
            _sortie(args.dossier, "consequences", get_type_consequences(
                demandes, commentaires, args.types, synthese, faits, droit_applicable=droit))
        else:
            contradictions = json.loads(get_contradictions(
                demandes, commentaires, synthese, faits, droit_applicable=droit,
                dossier=args.dossier))
            consequences = get_type_consequences(
                demandes, commentaires, args.types, synthese, faits, droit_applicable=droit)
            chemin = create_acte_modifie(
                synthese, demandes, commentaires, faits, consequences,
                contradictions=contradictions, droit_applicable=droit, dossier=args.dossier)
            print(f"{len(contradictions['contradictions'])} contradictions, "
                  f"{len(consequences)} conséquences, acte : {chemin}")
    except ErreurLLM as erreur:
        sys.exit(f"Erreur : {erreur}")


if __name__ == "__main__":
    main()