"""Base SQLite des documents : pièces des dossiers, modèles d'actes et actes produits.

    python -m backend.db          # (ré)importe docs/ dans la base et affiche ce qu'elle contient
    python -m backend.db --vider-cache [dossier]   # oublie les réponses en cache du serveur

La base (``data/documents.db``) est créée et remplie au premier accès, à partir de :

- ``docs/dossiers_fictifs/<dossier>/txt/*.txt`` : les pièces des dossiers clients ;
- ``docs/modeles/<dossier>/`` : les modèles d'actes (.docx, .doc et .pdf annoté).

Les actes produits y sont archivés avec leur rapport (``archiver_acte``).

python-docx et Augure veulent des fichiers : ``get_acte_source`` extrait le modèle
Word et ses PDF dans ``data/cache/<dossier>/`` et renvoie ce chemin. Les actes sont
aussi écrits dans ``out/actes_modifies/``, comme avant.
"""

import json
import shutil
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from backend.config import DOSSIERS, MODELES, ROOT, valeurs

BASE = ROOT / "data" / "documents.db"
CACHE = ROOT / "data" / "cache"

SCHEMA = """
CREATE TABLE IF NOT EXISTS pieces (
    id      INTEGER PRIMARY KEY,
    dossier TEXT NOT NULL,              -- charte_vie_commune, mandat_protection, …
    nom     TEXT NOT NULL,              -- « 0 - Mise en contexte et mandat »
    texte   TEXT NOT NULL,
    UNIQUE (dossier, nom)
);
CREATE TABLE IF NOT EXISTS modeles (
    id      INTEGER PRIMARY KEY,
    dossier TEXT NOT NULL,
    nom     TEXT NOT NULL,              -- nom du fichier d'origine
    format  TEXT NOT NULL,              -- docx, doc ou pdf
    annote  INTEGER NOT NULL,           -- 1 : version annotée des auteurs (_not)
    contenu BLOB NOT NULL,
    UNIQUE (dossier, nom)
);
CREATE TABLE IF NOT EXISTS actes (
    id      INTEGER PRIMARY KEY,
    dossier TEXT NOT NULL,
    nom     TEXT NOT NULL UNIQUE,       -- nom du .docx produit
    cree_le TEXT NOT NULL,
    contenu BLOB NOT NULL,
    rapport TEXT                        -- rapport des modifications, en JSON
);
CREATE TABLE IF NOT EXISTS mandats (
    dossier TEXT PRIMARY KEY,           -- dossier créé depuis le frontend, pièces téléversées
    modele  TEXT NOT NULL,              -- dossier fictif dont il reprend le modèle d'acte
    titre   TEXT NOT NULL,              -- « Tremblay / Roy »
    cree_le TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reponses (
    cle     TEXT PRIMARY KEY,           -- empreinte de la route et du corps de la requête
    route   TEXT NOT NULL,
    dossier TEXT NOT NULL,
    cree_le TEXT NOT NULL,
    reponse TEXT NOT NULL               -- réponse du serveur, en JSON
);
"""


class ErreurDocument(RuntimeError):
    """Aucun document de départ ne correspond à la demande."""


@contextmanager
def _base():
    """Connexion à la base, créée et remplie à partir de docs/ si elle est vide."""
    BASE.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(BASE)
    try:
        with con:
            con.executescript(SCHEMA)
            if not con.execute("SELECT 1 FROM pieces UNION ALL SELECT 1 FROM modeles LIMIT 1").fetchone():
                _importer(con)
            yield con
    finally:
        con.close()


def _importer(con):
    for dossier in sorted(p for p in DOSSIERS.iterdir() if p.is_dir()) if DOSSIERS.is_dir() else []:
        for piece in sorted((dossier / "txt").glob("*.txt")):
            con.execute(
                "INSERT INTO pieces (dossier, nom, texte) VALUES (?, ?, ?)"
                " ON CONFLICT (dossier, nom) DO UPDATE SET texte = excluded.texte",
                (dossier.name, piece.stem, piece.read_text(encoding="utf-8")),
            )
    for dossier in sorted(p for p in MODELES.iterdir() if p.is_dir()) if MODELES.is_dir() else []:
        for fichier in sorted(dossier.iterdir()):
            if fichier.suffix.lower() in (".docx", ".doc", ".pdf"):
                con.execute(
                    "INSERT INTO modeles (dossier, nom, format, annote, contenu) VALUES (?, ?, ?, ?, ?)"
                    " ON CONFLICT (dossier, nom) DO UPDATE SET contenu = excluded.contenu",
                    (dossier.name, fichier.name, fichier.suffix[1:].lower(),
                     int("_not" in fichier.stem), fichier.read_bytes()),
                )


def importer():
    """(Ré)importe les pièces et les modèles de docs/ dans la base."""
    with _base() as con:
        _importer(con)


def lister_dossiers():
    """Noms des dossiers pour lesquels un modèle Word est disponible."""
    with _base() as con:
        return [nom for (nom,) in con.execute(
            "SELECT DISTINCT dossier FROM modeles WHERE format = 'docx' ORDER BY dossier")]


def dossiers_clients():
    """Noms des dossiers qui ont des pièces."""
    with _base() as con:
        return [nom for (nom,) in con.execute("SELECT DISTINCT dossier FROM pieces ORDER BY dossier")]


def inventaire():
    """Pour chaque dossier client : noms des pièces, modèles et actes produits (le plus récent d'abord).

    Un mandat créé depuis le frontend reprend les modèles du dossier fictif choisi (``modele``)
    et porte le titre saisi. Seuls des noms et des dates sortent d'ici : le texte des pièces
    reste dans la base.
    """
    with _base() as con:
        pieces = con.execute("SELECT dossier, nom FROM pieces ORDER BY dossier, nom").fetchall()
        modeles = con.execute(
            "SELECT dossier, nom, format, annote FROM modeles ORDER BY dossier, annote DESC, nom").fetchall()
        actes = con.execute("SELECT dossier, nom, cree_le FROM actes ORDER BY cree_le DESC, id DESC").fetchall()
        mandats = {d: (m, t) for d, m, t in con.execute("SELECT dossier, modele, titre FROM mandats")}
    par_modele = {}
    for dossier, nom, format_, annote in modeles:
        par_modele.setdefault(dossier, []).append({"nom": nom, "format": format_, "annote": bool(annote)})
    dossiers = {}
    for dossier, nom in pieces:
        if dossier not in dossiers:
            modele, titre = mandats.get(dossier, (dossier, ""))
            dossiers[dossier] = {"pieces": [], "modele": modele, "titre": titre,
                                 "modeles": par_modele.get(modele, []), "actes": []}
        dossiers[dossier]["pieces"].append(nom)
    for dossier, nom, cree_le in actes:
        if dossier in dossiers:
            dossiers[dossier]["actes"].append({"nom": nom, "cree_le": cree_le})
    return dossiers


def modele_de(dossier):
    """Dossier fictif dont ce dossier reprend le modèle d'acte (lui-même pour un dossier fictif)."""
    with _base() as con:
        ligne = con.execute("SELECT modele FROM mandats WHERE dossier = ?", (dossier,)).fetchone()
    return ligne[0] if ligne else dossier


def creer_mandat(dossier, modele, titre):
    """Enregistre un mandat créé depuis le frontend ; ses pièces s'ajoutent avec ajouter_pieces."""
    with _base() as con:
        con.execute("INSERT INTO mandats (dossier, modele, titre, cree_le) VALUES (?, ?, ?, ?)",
                    (dossier, modele, titre, datetime.now().isoformat(timespec="seconds")))


def ajouter_pieces(dossier, pieces):
    """Ajoute des pièces [(nom, texte)] au dossier, numérotées à la suite : « 5 - Courriel du client »."""
    with _base() as con:
        rang = con.execute("SELECT COUNT(*) FROM pieces WHERE dossier = ?", (dossier,)).fetchone()[0]
        noms = []
        for nom, texte in pieces:
            noms.append(f"{rang} - {nom}")
            con.execute(
                "INSERT INTO pieces (dossier, nom, texte) VALUES (?, ?, ?)"
                " ON CONFLICT (dossier, nom) DO UPDATE SET texte = excluded.texte",
                (dossier, noms[-1], texte))
            rang += 1
    return noms


def get_pieces(dossier):
    """Pièces txt du dossier, dans l'ordre : {nom de la pièce: texte}."""
    with _base() as con:
        pieces = dict(con.execute("SELECT nom, texte FROM pieces WHERE dossier = ? ORDER BY nom", (dossier,)))
    if not pieces:
        raise ErreurDocument(f"Dossier inconnu : {dossier}")
    return pieces


def get_acte_source(dossier=None, acte_id=None):
    """Renvoie le chemin du document Word à modifier, extrait de la base.

    ``dossier`` : nom du dossier fictif (``mandat_protection``, …).
    ``acte_id`` : identifiant d'un acte déjà produit (table ``actes``) pour le
    reprendre ; un nom de dossier est aussi accepté, comme avant la base.
    """
    if acte_id is not None and str(acte_id).isdigit():
        with _base() as con:
            ligne = con.execute("SELECT dossier, nom, contenu FROM actes WHERE id = ?", (int(acte_id),)).fetchone()
        if ligne is None:
            raise ErreurDocument(f"Acte introuvable : {acte_id}")
        return _extraire(ligne[0], ligne[1], ligne[2])
    if dossier is None and acte_id:
        dossier = acte_id
    if dossier is None:
        disponibles = lister_dossiers()
        if len(disponibles) != 1:
            raise ErreurDocument(
                "Préciser le dossier : " + ", ".join(disponibles or ["aucun modèle disponible"]))
        dossier = disponibles[0]

    # Un mandat créé depuis le frontend reprend le modèle du dossier fictif choisi.
    dossier = modele_de(dossier)
    with _base() as con:
        modeles = con.execute(
            "SELECT nom, format, annote, contenu FROM modeles WHERE dossier = ? ORDER BY annote DESC, nom",
            (dossier,)).fetchall()
    if not modeles:
        raise ErreurDocument(f"Dossier introuvable : {dossier}")
    word = [m for m in modeles if m[1] == "docx"]
    if not word:
        anciens = [m[0] for m in modeles if m[1] == "doc"]
        if anciens:
            raise ErreurDocument(
                f"{dossier} : le modèle est en .doc (Word 97-2003), que python-docx ne lit "
                f"pas. Le convertir d'abord en .docx, puis relancer python -m backend.db :\n"
                f"    soffice --headless --convert-to docx \"{MODELES / dossier / anciens[0]}\"")
        raise ErreurDocument(f"Aucun modèle Word pour {dossier}")
    # Les PDF annotés accompagnent le Word : acte.py les cherche à côté de lui.
    for nom, format_, _, contenu in modeles:
        if format_ == "pdf":
            _extraire(dossier, nom, contenu)
    return _extraire(dossier, word[0][0], word[0][3])


def _extraire(dossier, nom, contenu):
    chemin = CACHE / dossier / nom
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if not chemin.exists() or chemin.stat().st_size != len(contenu):
        chemin.write_bytes(contenu)
    return chemin


def chemin_sortie(dossier=None, suffixe="docx"):
    """Chemin d'écriture d'un acte modifié, daté pour ne rien écraser."""
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


def archiver_acte(chemin, dossier=None, rapport=None):
    """Archive un acte produit et son rapport dans la base ; renvoie son identifiant."""
    chemin = Path(chemin)
    with _base() as con:
        con.execute(
            "INSERT INTO actes (dossier, nom, cree_le, contenu, rapport) VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT (nom) DO UPDATE SET contenu = excluded.contenu, rapport = excluded.rapport",
            (dossier or "", chemin.name, datetime.now().isoformat(timespec="seconds"), chemin.read_bytes(),
             json.dumps(rapport, ensure_ascii=False, default=str) if rapport is not None else None),
        )
        return con.execute("SELECT id FROM actes WHERE nom = ?", (chemin.name,)).fetchone()[0]


def get_acte(nom):
    """Contenu (octets) d'un acte archivé, ou None."""
    with _base() as con:
        ligne = con.execute("SELECT contenu FROM actes WHERE nom = ?", (nom,)).fetchone()
    return ligne[0] if ligne else None


def reponse_en_cache(cle):
    """Réponse déjà calculée pour cette requête (dict), ou None."""
    with _base() as con:
        ligne = con.execute("SELECT reponse FROM reponses WHERE cle = ?", (cle,)).fetchone()
    return json.loads(ligne[0]) if ligne else None


def derniere_reponse(route, dossier):
    """Dernière réponse en cache pour cette étape de ce dossier (mode démo), ou None."""
    with _base() as con:
        ligne = con.execute(
            "SELECT reponse FROM reponses WHERE route = ? AND dossier = ? ORDER BY cree_le DESC LIMIT 1",
            (route, dossier or "")).fetchone()
    return json.loads(ligne[0]) if ligne else None


def mettre_en_cache(cle, route, dossier, reponse):
    with _base() as con:
        con.execute(
            "INSERT INTO reponses (cle, route, dossier, cree_le, reponse) VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT (cle) DO UPDATE SET reponse = excluded.reponse, cree_le = excluded.cree_le",
            (cle, route, dossier or "", datetime.now().isoformat(timespec="seconds"),
             json.dumps(reponse, ensure_ascii=False)),
        )


def vider_cache(dossier=None):
    """Oublie les réponses en cache (d'un dossier, ou toutes) ; renvoie leur nombre."""
    with _base() as con:
        if dossier:
            return con.execute("DELETE FROM reponses WHERE dossier = ?", (dossier,)).rowcount
        return con.execute("DELETE FROM reponses").rowcount


def main():
    if "--vider-cache" in sys.argv:
        dossier = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
        print(f"{vider_cache(dossier)} réponses retirées du cache")
        return
    importer()
    with _base() as con:
        print(f"Base : {BASE}")
        for table, requete in (
            ("pieces", "SELECT dossier, COUNT(*) FROM pieces GROUP BY dossier"),
            ("modeles", "SELECT dossier, GROUP_CONCAT(format, ', ') FROM modeles GROUP BY dossier"),
            ("actes", "SELECT dossier, COUNT(*) FROM actes GROUP BY dossier"),
            ("reponses (cache)", "SELECT dossier, COUNT(*) FROM reponses GROUP BY dossier"),
        ):
            print(f"\n{table}")
            for dossier, valeur in con.execute(requete):
                print(f"  {dossier or '(sans dossier)'} : {valeur}")


if __name__ == "__main__":
    main()
