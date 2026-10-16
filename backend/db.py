"""Source de l'acte à modifier — squelette, la base de données arrive plus tard.

Pour l'instant le document de départ est cherché sur le disque :

- ``docs/modeles/<dossier>/*_not.docx`` : le modèle d'acte Word, version annotée
  des auteurs du Répertoire ;
- à défaut, le seul ``.docx`` du dossier ;
- à défaut d'argument, l'unique modèle disponible dans ``docs/modeles``.

Le jour où la base existe, seules ``get_acte_source`` et ``lister_dossiers`` sont
à réécrire : le reste du backend n'appelle que ces deux fonctions.
Les actes produits sont déposés dans ``out/actes_modifies/`` et retournés en
chemin : le frontend s'en sert pour proposer le téléchargement.
"""

import shutil
from pathlib import Path

from backend.config import MODELES, valeurs


class ErreurDocument(RuntimeError):
    """Aucun document de départ ne correspond à la demande."""


def _modeles(dossier=None):
    dossiers = [MODELES / dossier] if dossier else sorted(p for p in MODELES.iterdir() if p.is_dir())
    return dossiers


def lister_dossiers():
    """Noms des dossiers pour lesquels un modèle Word est disponible."""
    noms = []
    for dossier in _modeles():
        if list(dossier.glob("*.docx")):
            noms.append(dossier.name)
    return noms


def get_acte_source(dossier=None, acte_id=None):
    """Renvoie le chemin du document Word à modifier.

    ``dossier`` : nom du dossier fictif (``mandat_protection``, …).
    ``acte_id`` : identifiant de l'acte dans la base ; pour l'instant traité
    comme un nom de dossier.
    """
    if dossier is None and acte_id:
        dossier = acte_id
    if dossier is None:
        disponibles = lister_dossiers()
        if len(disponibles) == 1:
            dossier = disponibles[0]
        else:
            raise ErreurDocument(
                "Préciser le dossier : " + ", ".join(disponibles or ["aucun modèle disponible"])
            )

    dossier = MODELES / dossier
    if not dossier.is_dir():
        raise ErreurDocument(f"Dossier introuvable : {dossier}")

    annotes = sorted(dossier.glob("*_not.docx")) + sorted(dossier.glob("*_not.doc"))
    autres = [p for p in sorted(dossier.glob("*.docx")) if p not in annotes]
    documents = annotes or autres
    if not documents:
        anciens = sorted(dossier.glob("*.doc"))
        if anciens:
            raise ErreurDocument(
                f"{dossier.name} : le modèle est en .doc (Word 97-2003), que python-docx ne lit "
                f"pas. Le convertir d'abord en .docx :\n"
                f"    soffice --headless --convert-to docx \"{anciens[0]}\""
            )
        raise ErreurDocument(f"Aucun modèle Word dans {dossier}")
    return documents[0]


def chemin_sortie(dossier=None, suffixe="docx"):
    """Chemin d'écriture d'un acte modifié, daté pour ne rien écraser."""
    from datetime import datetime

    sortie = valeurs()["sortie"]
    sortie.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.now().strftime("%Y%m%d-%H%M%S")
    prefixe = f"{dossier or 'acte'}-{horodatage}"
    return sortie / f"{prefixe}.{suffixe}"


def enregistrer(contenu, chemin):
    """Écrit un acte modifié (octets ou document Word) et renvoie son chemin."""
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(contenu, (bytes, bytearray)):
        chemin.write_bytes(contenu)
    elif isinstance(contenu, Path):
        shutil.copyfile(contenu, chemin)
    else:
        contenu.save(str(chemin))
    return chemin