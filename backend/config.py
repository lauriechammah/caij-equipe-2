"""Réglages du backend : variables d'environnement, clés et valeurs par défaut.

Le ``.env`` de la racine est chargé au premier accès à ``valeurs()``. Rien n'est
écrit sur le disque et la clé n'est jamais journalisée.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOSSIERS = ROOT / "docs" / "dossiers_fictifs"
MODELES = ROOT / "docs" / "modeles"
SORTIE = ROOT / "out" / "actes_modifies"

MODELE_AUGURE = "rosedale-1"
EFFORT_AUGURE = "high"
TYPES_COMPAGNON = ["legislation", "jurisprudence", "doctrine"]
TOP_K_COMPAGNON = 10
EXTRACT_COMPAGNON = 1500
REPETITIONS = 3
PAUSE_REPETITION = 5.0


def _charger_env():
    fichier = ROOT / ".env"
    if not fichier.exists():
        return
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.startswith("#") and "=" in ligne:
            cle, valeur = ligne.split("=", 1)
            os.environ.setdefault(cle.strip(), valeur.strip().strip('"').strip("'"))


def _url_compagnon(base):
    """Adresse complète de l'endpoint, que la variable soit donnée avec ou sans le chemin.

    L'équipe peut remettre ``https://…/semantic-search`` ou seulement la racine de
    l'instance ; les deux écritures doivent aboutir au même appel.
    """
    base = base.strip().rstrip("/")
    if "://" not in base:
        base = f"https://{base}"
    return base if base.endswith("/semantic-search") else f"{base}/semantic-search"


def valeurs():
    """Retourne la configuration effective, en rechargeant le ``.env`` si besoin.

    Une variable présente mais vide — ce que donne ``.env.example`` une fois copié —
    est traitée comme absente, sinon l'URL de base finirait vide.
    """

    def lire(nom, defaut):
        return (os.environ.get(nom) or "").strip() or defaut

    _charger_env()
    return {
        "augure_cle": lire("AUGURE_API_KEY", ""),
        "augure_modele": lire("AUGURE_MODEL", MODELE_AUGURE),
        "augure_base": lire("AUGURE_BASE_URL", "https://api.augureai.ca/v1"),
        "compagnon_url": _url_compagnon(
            lire("COMPAGNON_API_URL", "https://hackathon.caij.qc.ca")),
        "racine": ROOT,
        "dossiers": DOSSIERS,
        "modeles": MODELES,
        "sortie": SORTIE,
    }