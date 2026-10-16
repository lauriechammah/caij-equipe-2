"""Pièces téléversées depuis le frontend : le texte en est extrait pour Augure.

Augure lit du texte : un .txt ou un .md est décodé, un .docx est lu avec python-docx
(paragraphes et tableaux, dans l'ordre). Les autres formats sont refusés avec un message
clair plutôt que transmis tels quels.
"""

import base64
import binascii
import io
import re
import unicodedata
from pathlib import Path

from docx import Document

from backend.acte import _paragraphes, _texte

FORMATS = (".txt", ".md", ".docx")
TAILLE_MAX = 15 * 1024 * 1024  # par pièce


def texte_de_fichier(nom, octets):
    """Texte d'une pièce selon son extension ; ValueError si le format n'est pas pris en charge."""
    suffixe = Path(nom).suffix.lower()
    if suffixe in (".txt", ".md"):
        for codage in ("utf-8-sig", "cp1252"):
            try:
                return octets.decode(codage)
            except UnicodeDecodeError:
                continue
    if suffixe == ".docx":
        try:
            document = Document(io.BytesIO(octets))
        except Exception as e:
            raise ValueError(f"{nom} : document Word illisible ({e})") from e
        return "\n".join(t for paragraphe, _ in _paragraphes(document) if (t := _texte(paragraphe).strip()))
    raise ValueError(f"{nom} : format non pris en charge ({suffixe or 'sans extension'}). "
                     f"Formats acceptés : {', '.join(FORMATS)}.")


def lire_pieces(liste):
    """[{nom, contenu (base64)}] reçu du frontend → [(nom sans extension, texte)]."""
    pieces = []
    for piece in liste or []:
        nom = Path(str(piece.get("nom") or "")).name
        try:
            octets = base64.b64decode(piece.get("contenu") or "", validate=True)
        except (binascii.Error, ValueError) as e:
            raise ValueError(f"{nom or 'pièce'} : contenu mal encodé") from e
        if len(octets) > TAILLE_MAX:
            raise ValueError(f"{nom} : fichier trop lourd (plus de {TAILLE_MAX // 1024 // 1024} Mo)")
        texte = texte_de_fichier(nom, octets).strip()
        if not texte:
            raise ValueError(f"{nom} : aucun texte à lire")
        pieces.append((Path(nom).stem, texte))
    return pieces


def identifiant(titre, existants):
    """Nom de dossier tiré du titre (« Tremblay / Roy » → tremblay_roy), unique parmi `existants`."""
    base = unicodedata.normalize("NFKD", titre).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]+", "_", base).strip("_")[:40] or "mandat"
    nom, rang = base, 2
    while nom in existants:
        nom, rang = f"{base}_{rang}", rang + 1
    return nom
