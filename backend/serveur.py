"""Serveur HTTP du backend, appelé par le frontend via le proxy Vite /api/pipeline.

    .venv/Scripts/python -m backend.serveur      # http://localhost:8000 (Windows)
    .venv/bin/python -m backend.serveur          # idem (macOS, Linux)

Le navigateur n'envoie que le nom du dossier et ce que le notaire a validé :
le serveur lit les pièces txt et les transmet à Augure, comme scripts/augure.py.

    Accueil     GET  dossiers                   les dossiers, leurs pièces, modèles et actes
                POST mandats                    nouveau mandat à partir de pièces téléversées
                POST pieces                     ajouter des pièces téléversées à un dossier
    Étape 1     POST synthese-demande           synthese_demande
    Étapes 2-3  POST synthese-demande-clients   synthesedemandeclients
    Étapes 4-5  POST demandes-et-faits          getdemandeclientsetelementsfactuels
    Étape 6     POST contradictions             get_contradictions
    Étape 7     POST consequences               get_type_consequences
    Étape 8     POST acte                       create_acte_modifie
                GET  fichier/<nom>              le .docx produit
    Éditeur     GET  actes/<nom>                un acte produit, en blocs
    Augure      POST question                   repondre_question
"""

import hashlib
import io
import json
import logging
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote

from docx import Document
from docx.oxml.ns import qn

from backend import db
from backend.acte import _paragraphes, _texte, create_acte_modifie
from backend.analyse import get_contradictions, get_type_consequences
from backend.clients import AugureError, CompagnonError
from backend.config import ARTICLES_MAX, CACHE_DEMO, CACHE_REPONSES, ROOT, SORTIE
from backend.db import ErreurDocument
from backend.fonctions import (
    getdemandeclientsetelementsfactuels,
    repondre_question,
    synthese_demande,
    synthesedemandeclients,
)
from backend.journal import FICHIER, configurer, journal, nombre, requete
from backend.llm import ErreurLLM
from backend.pieces import identifiant, lire_pieces

PORT = 8000

# Type d'acte et modèle de chaque dossier (tableau du README de la racine).
LIBELLES = {
    "charte_vie_commune": ("Charte de vie commune", "Famille, Doc. 11.1"),
    "convention_indivision": ("Convention d’indivision", "Biens, Doc. 2"),
    "mandat_protection": ("Mandat de protection", "Mandat, Doc. 2"),
    "servitude_enclave": ("Servitude de passage en cas d’enclave", "Biens, Doc. 3.2"),
    "testament_simple_fiducie": ("Testament simple avec fiducie pour enfants", "Libéralités, Doc. 3.7"),
    "vente_immeuble_comptant": ("Vente d’un immeuble au comptant", "Vente, Doc. 2.1"),
}

# Liste des conséquences possibles du prompt 7, une par ligne, préfixée par le type d'acte.
CONSEQUENCES_POSSIBLES = Path(__file__).with_name("consequences_possibles.txt")
# Types d'acte de la liste qui concernent chaque dossier.
TYPES_ACTE = {
    "charte_vie_commune": ("Convention de vie commune",),
    "convention_indivision": ("Convention d’indivision",),
    "mandat_protection": ("Mandat de protection",),
    "servitude_enclave": ("Servitude",),
    "testament_simple_fiducie": ("Testament", "Fiducie"),
    "vente_immeuble_comptant": ("Vente au comptant",),
}

NOTE = re.compile(r"\s*\[Note : (.*?)\]\s*$", re.S)


def verifier_dossier(nom):
    if nom not in db.dossiers_clients():
        raise ValueError(f"Dossier inconnu : {nom}")
    return nom


def charger_dossier(nom):
    """Pièces txt du dossier, lues dans la base : {nom de la pièce: texte}."""
    pieces = db.get_pieces(verifier_dossier(nom))
    journal.info("dossier %s : %d pièces, %s car. joints à chaque appel Augure",
                 nom, len(pieces), nombre(sum(map(len, pieces.values()))))
    return pieces


def contexte(corps):
    """Ce que le notaire a validé, au format des fonctions de backend/analyse.py et acte.py."""
    demandes = corps.get("demandes") or []
    articles = corps.get("articles") or []
    return {
        "synthese": corps["syntdmd"],
        "faits": [f"{f['titre']} ({f['source']})" if f.get("source") else f["titre"]
                  for f in corps.get("faits") or []],
        "demandes": [d["titre"] for d in demandes],
        "commentaires": ["À confirmer avec le client" if d.get("etat") == "attente" else "Retenue par le notaire"
                         for d in demandes],
        "droit": {
            "resume": corps.get("synthese_droit") or "",
            "sources": [{"type": "legislation", "titre": f"{a['source']} — {a['titre']}",
                         "url": a.get("url") or "", "extrait": a.get("texte") or ""} for a in articles],
            "nb_sources": len(articles),
        },
    }


def consequences_possibles(dossier):
    """Les conséquences de la liste qui concernent le type d'acte du dossier (toutes, à défaut)."""
    lignes = [l.strip() for l in CONSEQUENCES_POSSIBLES.read_text(encoding="utf-8").splitlines() if l.strip()]
    types = TYPES_ACTE.get(db.modele_de(dossier))
    retenues = [l for l in lignes if l.split(" – ", 1)[0] in types] if types else []
    return retenues or lignes


def _liste(libelle, valeurs):
    valeurs = [str(v) for v in valeurs or [] if v]
    return f"{libelle} : {' ; '.join(valeurs)}." if valeurs else ""


# --- Routes ------------------------------------------------------------------

def entree_dossier(nom, contenu):
    """Un dossier tel que le frontend l'affiche : type d'acte, pièces, modèles, actes produits."""
    type_acte, reference = LIBELLES.get(contenu["modele"], (contenu["modele"].replace("_", " ").capitalize(), ""))
    return {
        "dossier": nom,
        "titre": contenu["titre"],
        "modele": contenu["modele"],
        "type_acte": type_acte,
        "reference": reference,
        "pieces": contenu["pieces"],
        "modeles": contenu["modeles"],
        # Sans modèle .docx, l'étape 8 ne peut pas produire l'acte (voir db.get_acte_source).
        "modele_word": any(m["format"] == "docx" for m in contenu["modeles"]),
        "actes": [{**a, "fichier": f"/api/pipeline/fichier/{quote(a['nom'])}"} for a in contenu["actes"]],
    }


def dossiers():
    """Les dossiers clients pour l'accueil : noms des pièces, modèles, actes déjà produits."""
    return {"dossiers": [entree_dossier(nom, contenu) for nom, contenu in db.inventaire().items()]}


def nouveau_mandat(corps):
    """Crée un dossier à partir de pièces téléversées, sur le modèle d'acte d'un dossier fictif."""
    modele = corps["modele"]
    if modele not in LIBELLES:
        raise ValueError(f"Type d'acte inconnu : {modele}")
    pieces = lire_pieces(corps.get("pieces"))
    if not pieces:
        raise ValueError("Ajouter au moins une pièce au nouveau mandat.")
    titre = str(corps.get("titre") or "").strip() or LIBELLES[modele][0]
    nom = identifiant(titre, set(db.dossiers_clients()) | set(LIBELLES))
    db.creer_mandat(nom, modele, titre)
    db.ajouter_pieces(nom, pieces)
    return {"dossier": entree_dossier(nom, db.inventaire()[nom])}


def ajouter_des_pieces(corps):
    """Ajoute des pièces téléversées à un dossier ; ses réponses en cache ne valent plus."""
    nom = verifier_dossier(corps["dossier"])
    pieces = lire_pieces(corps.get("pieces"))
    if not pieces:
        raise ValueError("Aucune pièce reçue.")
    db.ajouter_pieces(nom, pieces)
    db.vider_cache(nom)
    return {"dossier": entree_dossier(nom, db.inventaire()[nom])}


def etape_synthese_demande(corps):
    titre, synthese = synthese_demande(charger_dossier(corps["dossier"]))
    return {"titre": titre, "synthese": synthese}


def question(corps):
    reponse = repondre_question(charger_dossier(corps["dossier"]), corps["question"],
                                corps.get("historique") or [], corps.get("contexte") or "")
    return {"reponse": reponse}


def synthese_demande_clients(corps):
    articles, synthese = synthesedemandeclients(charger_dossier(corps["dossier"]), corps["syntdmd"])
    return {"articles": articles, "synthese": synthese}


def demandes_et_faits(corps):
    faits, demandes = getdemandeclientsetelementsfactuels(
        charger_dossier(corps["dossier"]), corps["syntdmd"], corps["articles"]
    )
    return {"faits": faits, "demandes": demandes}


def contradictions(corps):
    c = contexte(corps)
    rapport = json.loads(get_contradictions(c["demandes"], c["commentaires"], c["synthese"], c["faits"],
                                            droit_applicable=c["droit"]))
    liste = [x for x in rapport["contradictions"] if isinstance(x, dict)]
    paragraphes = [
        {"amorce": f"{x.get('id')} ({x.get('certitude', 'possible')}) :",
         "texte": " ".join(filter(None, [str(x.get("probleme") or ""),
                                         _liste("Demandes", x.get("demandes_concernees")),
                                         _liste("Articles", x.get("articles")),
                                         _liste("À confirmer", x.get("faits_a_confirmer"))]))}
        for x in liste
    ]
    paragraphes += [{"amorce": "Question :", "texte": str(q)} for q in rapport.get("questions_au_notaire") or []]
    if not paragraphes:
        brute = rapport.get("reponse_brute")
        paragraphes = [{"texte": str(brute) if brute else "Augure n'a relevé aucune contradiction."}]
    return {"contradictions": liste, "paragraphes": paragraphes}


def consequences(corps):
    c = contexte(corps)
    types = corps.get("types") or consequences_possibles(verifier_dossier(corps["dossier"]))
    liste = get_type_consequences(c["demandes"], c["commentaires"], types,
                                  c["synthese"], c["faits"], droit_applicable=c["droit"])
    elements = []
    for k in liste:
        source = " · ".join(filter(None, [
            str(k.get("type") or ""),
            str(k.get("certitude") or ""),
            "art. " + ", ".join(str(a) for a in k["articles"]) if k.get("articles") else "",
            "" if (k.get("source") or {}).get("url") else "source à confirmer",
            "hors liste" if k.get("hors_liste") else "",
        ]))
        elements.append({"titre": str(k.get("consequence") or ""), "source": source, "consequence": k})
    risques = [{"amorce": f"{k.get('type') or 'Conséquence'} :", "texte": str(k.get("effet_sur_le_client") or "")}
               for k in liste if k.get("effet_sur_le_client")]
    return {"consequences": elements, "risques": risques}


def acte(corps):
    c = contexte(corps)
    chemin = Path(create_acte_modifie(
        c["synthese"], c["demandes"], c["commentaires"], c["faits"],
        [e.get("consequence") or e for e in corps.get("consequences") or []],
        contradictions=corps.get("contradictions") or [],
        droit_applicable=c["droit"],
        dossier=verifier_dossier(corps["dossier"]),
    ))
    rapport = json.loads(chemin.with_suffix(".rapport.json").read_text(encoding="utf-8"))
    return {
        "nom": chemin.name,
        "fichier": f"/api/pipeline/fichier/{quote(chemin.name)}",
        "blocs": blocs_acte(Document(str(chemin))),
        "questions": (rapport.get("plan") or {}).get("questions_au_client") or [],
        "resume": rapport.get("resume_modifications") or "",
        "compteurs": rapport.get("compteurs") or {},
    }


def blocs_acte(document):
    """Le projet d'acte (document Word), paragraphe par paragraphe, au format de l'écran de l'étape 8.

    Un passage annoté porte sa note « [Note : …] » ; un paragraphe ajouté est une
    révision suivie (w:ins). Après le titre de l'annexe, tout est du texte simple.
    """
    blocs, annexe = [], False
    for paragraphe, _ in _paragraphes(document):
        texte = _texte(paragraphe).strip()
        if not texte:
            continue
        style = (paragraphe._p.style or "").lower()
        note = NOTE.search(texte)
        if texte.startswith("Annexe — "):
            annexe = True
            blocs.append({"type": "titre", "texte": texte})
        elif note and not annexe:
            blocs.append({"type": "revoir", "texte": texte[:note.start()].strip(), "note": note.group(1)})
        elif paragraphe._p.find(".//" + qn("w:ins")) is not None and not annexe:
            blocs.append({"type": "revoir", "texte": texte, "note": "Ajouté au modèle"})
        elif style.startswith(("title", "titre", "heading")) or (texte.isupper() and len(texte) < 90):
            blocs.append({"type": "titre", "texte": texte})
        else:
            blocs.append({"type": "texte", "texte": texte})
    return blocs


ROUTES = {
    "/api/pipeline/mandats": nouveau_mandat,
    "/api/pipeline/pieces": ajouter_des_pieces,
    "/api/pipeline/synthese-demande": etape_synthese_demande,
    "/api/pipeline/question": question,
    "/api/pipeline/synthese-demande-clients": synthese_demande_clients,
    "/api/pipeline/demandes-et-faits": demandes_et_faits,
    "/api/pipeline/contradictions": contradictions,
    "/api/pipeline/consequences": consequences,
    "/api/pipeline/acte": acte,
}
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
# Jamais en cache : le panneau Augure et « Régénérer » doivent donner une nouvelle réponse,
# et un téléversement doit vraiment enregistrer les pièces.
SANS_CACHE = {"/api/pipeline/question", "/api/pipeline/mandats", "/api/pipeline/pieces"}


def cle_cache(chemin, corps):
    """Empreinte de la requête : route, corps (JSON canonique) et réglages qui changent la réponse."""
    texte = json.dumps({"route": chemin, "corps": corps, "articles_max": ARTICLES_MAX},
                       sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()


class Gestionnaire(BaseHTTPRequestHandler):
    # Ce que la requête a répondu, pour sa ligne de bilan dans le journal.
    _code = _cache = _erreur = None

    def do_POST(self):
        self._journaliser("POST", self._post)

    def do_GET(self):
        self._journaliser("GET", self._get)

    def _journaliser(self, methode, traiter):
        """Une ligne de bilan par requête : code, durée, cache, temps passé chez Augure et le Compagnon."""
        with requete(self.path.removeprefix("/api/pipeline/").split("/")[0] or self.path) as courante:
            try:
                traiter()
            finally:
                details = [f"cache {self._cache}"] if self._cache else []
                if courante.appels:
                    details.append(courante.bilan())
                if self._erreur:
                    details.append(f"erreur : {self._erreur}")
                journal.log(logging.INFO if (self._code or 500) < 400 else logging.WARNING, "%s %s en %.1f s%s",
                            methode, self._code or "sans réponse", courante.duree(),
                            "".join(f" · {d}" for d in details))

    def _post(self):
        route = ROUTES.get(self.path)
        if route is None:
            return self._repondre(404, {"erreur": f"Route inconnue : {self.path}"})
        try:
            taille = int(self.headers.get("Content-Length", 0))
            corps = json.loads(self.rfile.read(taille) or b"{}")
            journal.info("POST reçu : dossier %s, %s octets", corps.get("dossier") or "-", nombre(taille))
            cle = cle_cache(self.path, corps) if CACHE_REPONSES and self.path not in SANS_CACHE else None
            if cle and (reponse := db.reponse_en_cache(cle)) is not None:
                return self._repondre(200, reponse, cache="HIT")
            if cle and CACHE_DEMO and (reponse := db.derniere_reponse(self.path, corps.get("dossier"))) is not None:
                return self._repondre(200, reponse, cache="DEMO")
            if cle:
                journal.info("pas en cache (%s) : calcul complet", cle[:10])
            reponse = route(corps)
            if cle:
                db.mettre_en_cache(cle, self.path, corps.get("dossier"), reponse)
            self._repondre(200, reponse, cache="MISS" if cle else None)
        except KeyError as e:
            self._repondre(400, {"erreur": f"Champ manquant : {e.args[0]}"})
        except (ValueError, ErreurDocument) as e:
            self._repondre(400, {"erreur": str(e)})
        except (AugureError, CompagnonError, ErreurLLM) as e:
            self._repondre(502, {"erreur": str(e)})
        except Exception as e:
            journal.exception("erreur inattendue")
            self._repondre(500, {"erreur": f"{type(e).__name__} : {e}"})

    def _get(self):
        """Liste des dossiers, acte produit en blocs (éditeur) ou téléchargement du .docx."""
        try:
            if self.path == "/api/pipeline/dossiers":
                return self._repondre(200, dossiers())
            for prefixe, envoyer in (("/api/pipeline/fichier/", self._envoyer_docx),
                                     ("/api/pipeline/actes/", self._envoyer_blocs)):
                if self.path.startswith(prefixe):
                    nom = unquote(self.path[len(prefixe):])
                    contenu = self._acte(nom)
                    if contenu is None:
                        return self._repondre(404, {"erreur": "Fichier introuvable"})
                    return envoyer(nom, contenu)
            self._repondre(404, {"erreur": f"Route inconnue : {self.path}"})
        except Exception as e:
            journal.exception("erreur inattendue")
            self._repondre(500, {"erreur": f"{type(e).__name__} : {e}"})

    def log_message(self, format, *args):
        """La ligne HTTP brute de http.server : dans le journal, en DEBUG (le bilan suffit d'ordinaire)."""
        journal.debug(format, *args)

    def log_error(self, format, *args):
        journal.warning(format, *args)

    @staticmethod
    def _acte(nom):
        """Un acte produit : depuis la base, à défaut depuis out/actes_modifies/."""
        if not nom.endswith(".docx") or "/" in nom or "\\" in nom or ".." in nom:
            return None
        return db.get_acte(nom) or ((SORTIE / nom).read_bytes() if (SORTIE / nom).is_file() else None)

    def _envoyer_blocs(self, nom, contenu):
        self._repondre(200, {"nom": nom, "fichier": f"/api/pipeline/fichier/{quote(nom)}",
                             "blocs": blocs_acte(Document(io.BytesIO(contenu)))})

    def _envoyer_docx(self, nom, contenu):
        self._code = 200
        self.send_response(200)
        self.send_header("Content-Type", DOCX)
        self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(nom)}")
        self.send_header("Content-Length", str(len(contenu)))
        self.end_headers()
        self.wfile.write(contenu)

    def _repondre(self, code, donnees, cache=None):
        self._code, self._cache = code, cache
        if code >= 400:
            self._erreur = donnees.get("erreur")
        corps = json.dumps(donnees, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if cache:
            self.send_header("X-Cache", cache)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)


if __name__ == "__main__":
    configurer()
    print(f"Backend sur http://localhost:{PORT}"
          f" (cache : {'oui' if CACHE_REPONSES else 'non'}{', mode démo' if CACHE_DEMO else ''},"
          f" articles : {ARTICLES_MAX or 'tous'})")
    print(f"Journal : {FICHIER.relative_to(ROOT)} (CAIJ_LOG=DEBUG pour le détail)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Gestionnaire).serve_forever()
