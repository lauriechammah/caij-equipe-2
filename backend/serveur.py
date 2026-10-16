"""Serveur HTTP du backend, appelé par le frontend via le proxy Vite /api/pipeline.

    .venv/Scripts/python -m backend.serveur      # http://localhost:8000 (Windows)
    .venv/bin/python -m backend.serveur          # idem (macOS, Linux)

Le navigateur n'envoie que le nom du dossier et ce que le notaire a validé :
le serveur lit les pièces txt et les transmet à Augure, comme scripts/augure.py.

    Étapes 2-3  POST synthese-demande-clients   synthesedemandeclients
    Étapes 4-5  POST demandes-et-faits          getdemandeclientsetelementsfactuels
    Étape 6     POST contradictions             get_contradictions
    Étape 7     POST consequences               get_type_consequences
    Étape 8     POST acte                       create_acte_modifie
                GET  fichier/<nom>              le .docx produit
"""

import json
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
from backend.config import SORTIE
from backend.db import ErreurDocument
from backend.fonctions import getdemandeclientsetelementsfactuels, synthesedemandeclients
from backend.llm import ErreurLLM

PORT = 8000

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
    return db.get_pieces(verifier_dossier(nom))


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
    types = TYPES_ACTE.get(dossier)
    retenues = [l for l in lignes if l.split(" – ", 1)[0] in types] if types else []
    return retenues or lignes


def _liste(libelle, valeurs):
    valeurs = [str(v) for v in valeurs or [] if v]
    return f"{libelle} : {' ; '.join(valeurs)}." if valeurs else ""


# --- Routes ------------------------------------------------------------------

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
        "fichier": f"/api/pipeline/fichier/{quote(chemin.name)}",
        "blocs": blocs_acte(chemin),
        "questions": (rapport.get("plan") or {}).get("questions_au_client") or [],
        "resume": rapport.get("resume_modifications") or "",
        "compteurs": rapport.get("compteurs") or {},
    }


def blocs_acte(chemin):
    """Le projet d'acte, paragraphe par paragraphe, au format de l'écran de l'étape 8.

    Un passage annoté porte sa note « [Note : …] » ; un paragraphe ajouté est une
    révision suivie (w:ins). Après le titre de l'annexe, tout est du texte simple.
    """
    blocs, annexe = [], False
    for paragraphe, _ in _paragraphes(Document(str(chemin))):
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
    "/api/pipeline/synthese-demande-clients": synthese_demande_clients,
    "/api/pipeline/demandes-et-faits": demandes_et_faits,
    "/api/pipeline/contradictions": contradictions,
    "/api/pipeline/consequences": consequences,
    "/api/pipeline/acte": acte,
}
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class Gestionnaire(BaseHTTPRequestHandler):
    def do_POST(self):
        route = ROUTES.get(self.path)
        if route is None:
            return self._repondre(404, {"erreur": f"Route inconnue : {self.path}"})
        try:
            corps = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            self._repondre(200, route(corps))
        except KeyError as e:
            self._repondre(400, {"erreur": f"Champ manquant : {e.args[0]}"})
        except (ValueError, ErreurDocument) as e:
            self._repondre(400, {"erreur": str(e)})
        except (AugureError, CompagnonError, ErreurLLM) as e:
            self._repondre(502, {"erreur": str(e)})
        except Exception as e:
            self._repondre(500, {"erreur": f"{type(e).__name__} : {e}"})

    def do_GET(self):
        """Télécharge un acte produit : depuis la base, à défaut depuis out/actes_modifies/."""
        prefixe = "/api/pipeline/fichier/"
        nom = unquote(self.path[len(prefixe):]) if self.path.startswith(prefixe) else ""
        if not nom.endswith(".docx") or "/" in nom or "\\" in nom or ".." in nom:
            return self._repondre(404, {"erreur": "Fichier introuvable"})
        contenu = db.get_acte(nom) or ((SORTIE / nom).read_bytes() if (SORTIE / nom).is_file() else None)
        if contenu is None:
            return self._repondre(404, {"erreur": "Fichier introuvable"})
        self.send_response(200)
        self.send_header("Content-Type", DOCX)
        self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(nom)}")
        self.send_header("Content-Length", str(len(contenu)))
        self.end_headers()
        self.wfile.write(contenu)

    def _repondre(self, code, donnees):
        corps = json.dumps(donnees, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)


if __name__ == "__main__":
    print(f"Backend sur http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Gestionnaire).serve_forever()
