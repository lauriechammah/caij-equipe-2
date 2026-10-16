"""Essai de bout en bout : les 8 étapes du frontend, pour chaque dossier, par HTTP.

    python -m backend.serveur                                   # dans un autre terminal
    python -m backend.bout_en_bout                              # tous les dossiers, sur :8000
    python -m backend.bout_en_bout --base http://localhost:5173 # en passant par le proxy Vite
    python -m backend.bout_en_bout --dossiers mandat_protection

Chaque dossier suit le parcours du frontend (screens/Pipeline.tsx) avec les mêmes
corps de requête : ce que le notaire « coche » est tout ce que le backend propose,
comme à l'écran par défaut. Appels réels à Augure et au Compagnon : compter
plusieurs minutes par étape. Deux dossiers à la fois par défaut (--paralleles) : à six
requêtes lourdes simultanées, Augure a déjà coupé tous les flux (« upstream_stream_idle »).
Une étape déjà calculée revient du cache du serveur : relancer reprend où l'on s'était arrêté.

Seules des mesures sont affichées (statuts, durées, nombres d'éléments), jamais le
contenu : les réponses complètes sont écrites dans out/tests/bout_en_bout/<date>/.
"""

import argparse
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from backend.config import ROOT

DELAI = 1800  # secondes : une étape peut prendre plusieurs minutes
_verrou = threading.Lock()
_bilan = []  # (dossier, vérification, réussie, détail)


def _ecrire(ligne):
    with _verrou:
        print(ligne, flush=True)


def verifier(dossier, libelle, condition, detail=""):
    with _verrou:
        _bilan.append((dossier, libelle, bool(condition), detail))
    _ecrire(f"  {'ok   ' if condition else 'ÉCHEC'} [{dossier}] {libelle}{f' ({detail})' if detail else ''}")
    return condition


class Client:
    def __init__(self, base, sortie):
        self.base = base.rstrip("/")
        self.sortie = sortie

    def appeler(self, methode, route, corps=None):
        """Renvoie (statut, en-têtes, octets, durée en s)."""
        donnees = json.dumps(corps).encode("utf-8") if corps is not None else None
        requete = urllib.request.Request(
            f"{self.base}/api/pipeline/{route}", data=donnees, method=methode,
            headers={"Content-Type": "application/json"} if donnees else {})
        debut = time.monotonic()
        try:
            with urllib.request.urlopen(requete, timeout=DELAI) as reponse:
                return reponse.status, dict(reponse.headers), reponse.read(), time.monotonic() - debut
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read(), time.monotonic() - debut

    def json(self, methode, route, corps=None, dossier=None, nom=None):
        statut, _, octets, duree = self.appeler(methode, route, corps)
        try:
            donnees = json.loads(octets or b"{}")
        except json.JSONDecodeError:
            donnees = {"non_json": octets[:200].decode("utf-8", "replace")}
        if dossier and nom:
            chemin = self.sortie / dossier / f"{nom}.json"
            chemin.parent.mkdir(parents=True, exist_ok=True)
            chemin.write_text(json.dumps({"statut": statut, "duree_s": round(duree, 1), "reponse": donnees},
                                         ensure_ascii=False, indent=2), encoding="utf-8")
        return statut, donnees, duree


def vers_elements(liste):
    """Comme versElements (frontend/src/api/backend.ts) : l'état coché que l'écran ajoute."""
    return [{**e, "etat": "attente" if e.get("a_confirmer") else "coche"} for e in liste]


def vers_texte_affiche(texte):
    """Comme versTexte(versParagraphes(texte)) (frontend/src/data/texte.ts) : le texte tel que l'écran le renvoie."""
    lignes = []
    for ligne in re.split(r"\n+", texte):
        ligne = ligne.strip()
        if not ligne:
            continue
        m = re.match(r"^\*\*(.+?)\*\*\s*(.*)$", ligne)
        lignes.append(f"**{m.group(1)}** {m.group(2)}" if m else ligne.replace("**", ""))
    return "\n".join(lignes)


def _elements_valides(liste):
    return isinstance(liste, list) and all(
        isinstance(e, dict) and isinstance(e.get("titre"), str) and isinstance(e.get("source"), str) for e in liste)


def _paragraphes_valides(liste):
    return isinstance(liste, list) and all(isinstance(p, dict) and isinstance(p.get("texte"), str) for p in liste)


def parcours(client, info):
    """Le parcours du frontend pour un dossier. Renvoie la durée totale."""
    dossier = info["dossier"]
    debut = time.monotonic()
    _ecrire(f"\n▶ {dossier} : {len(info['pieces'])} pièces, modèle Word : {'oui' if info['modele_word'] else 'non'}")

    # Étape 1 : synthèse de la demande
    statut, r, duree = client.json("POST", "synthese-demande", {"dossier": dossier}, dossier, "1-synthese-demande")
    if not verifier(dossier, f"étape 1 synthèse de la demande : HTTP {statut} en {duree:.0f} s",
                    statut == 200 and str(r.get("synthese") or "").strip(), r.get("erreur", "")):
        return time.monotonic() - debut
    syntdmd = r["synthese"]
    verifier(dossier, "étape 1 : titre (noms des clients) renvoyé", bool(str(r.get("titre") or "").strip()))
    verifier(dossier, "étape 1 : synthèse substantielle", len(syntdmd) > 300, f"{len(syntdmd)} caractères")

    # Étapes 2-3 : articles et synthèse du droit applicable
    statut, r, duree = client.json("POST", "synthese-demande-clients", {"dossier": dossier, "syntdmd": syntdmd},
                                   dossier, "2-3-articles")
    if not verifier(dossier, f"étapes 2-3 articles : HTTP {statut} en {duree:.0f} s", statut == 200, r.get("erreur", "")):
        return time.monotonic() - debut
    articles = r.get("articles") or []
    verifier(dossier, "étape 2 : liste d'articles au format du frontend", _elements_valides(articles))
    verifier(dossier, "étape 2 : au moins un article applicable", articles, f"{len(articles)} articles")
    avec_url = sum(1 for a in articles if str(a.get("url") or "").startswith("http"))
    sans_texte = sum(1 for a in articles if "non récupéré" in str(a.get("texte") or "").lower())
    verifier(dossier, "étape 2 : chaque article a une URL du Compagnon", avec_url == len(articles),
             f"{avec_url}/{len(articles)} avec URL, {sans_texte} sans texte")
    synthese_droit = r.get("synthese") or ""
    verifier(dossier, "étape 3 : synthèse du droit applicable", len(synthese_droit) > 200,
             f"{len(synthese_droit)} caractères")

    # Étapes 4-5 : faits et demandes, à partir des articles cochés (comme Pipeline.tsx)
    articles = [a for a in vers_elements(articles) if a["etat"] == "coche"]
    statut, r, duree = client.json("POST", "demandes-et-faits",
                                   {"dossier": dossier, "syntdmd": syntdmd, "articles": articles},
                                   dossier, "4-5-faits-demandes")
    if not verifier(dossier, f"étapes 4-5 faits et demandes : HTTP {statut} en {duree:.0f} s",
                    statut == 200, r.get("erreur", "")):
        return time.monotonic() - debut
    faits, demandes = r.get("faits") or [], r.get("demandes") or []
    verifier(dossier, "étape 4 : faits au format du frontend", _elements_valides(faits) and faits, f"{len(faits)} faits")
    verifier(dossier, "étape 4 : chaque fait cite sa pièce", all(f["source"].strip() for f in faits),
             f"{sum(1 for f in faits if not f['source'].strip())} sans source")
    verifier(dossier, "étape 5 : demandes au format du frontend", _elements_valides(demandes) and demandes,
             f"{len(demandes)} demandes, {sum(1 for d in demandes if d.get('a_confirmer'))} à confirmer")

    # Ce que le frontend envoie ensuite (Pipeline.valide), au caractère près, pour que ce
    # parcours remplisse aussi le cache du serveur pour une démonstration à l'écran.
    valide = {
        "dossier": dossier, "syntdmd": syntdmd, "articles": articles,
        "synthese_droit": vers_texte_affiche(synthese_droit),
        "faits": [f for f in vers_elements(faits) if f["etat"] == "coche"],
        "demandes": [d for d in vers_elements(demandes) if d["etat"] != "decoche"],
    }

    # Étapes 6 et 7 en parallèle, comme le frontend
    with ThreadPoolExecutor(max_workers=2) as pool:
        f6 = pool.submit(client.json, "POST", "contradictions", valide, dossier, "6-contradictions")
        f7 = pool.submit(client.json, "POST", "consequences", valide, dossier, "7-consequences")
        (s6, r6, d6), (s7, r7, d7) = f6.result(), f7.result()

    brutes = []
    if verifier(dossier, f"étape 6 contradictions : HTTP {s6} en {d6:.0f} s", s6 == 200, r6.get("erreur", "")):
        brutes = r6.get("contradictions") or []
        verifier(dossier, "étape 6 : paragraphes affichables", _paragraphes_valides(r6.get("paragraphes")) and r6["paragraphes"],
                 f"{len(brutes)} contradictions, {len(r6.get('paragraphes') or [])} paragraphes")
    consequences = []
    if verifier(dossier, f"étape 7 conséquences : HTTP {s7} en {d7:.0f} s", s7 == 200, r7.get("erreur", "")):
        consequences = r7.get("consequences") or []
        verifier(dossier, "étape 7 : conséquences au format du frontend", _elements_valides(consequences) and consequences,
                 f"{len(consequences)} conséquences")
        sourcees = sum(1 for c in consequences if ((c.get("consequence") or {}).get("source") or {}).get("url"))
        verifier(dossier, "étape 7 : conséquences rattachées à une source", sourcees > 0,
                 f"{sourcees}/{len(consequences)} avec URL")
        verifier(dossier, "étape 7 : synthèse des risques", _paragraphes_valides(r7.get("risques")) and r7["risques"],
                 f"{len(r7.get('risques') or [])} risques")

    # Étape 8 : projet d'acte, avec les conséquences cochées
    retenues = [c for c in vers_elements(consequences) if c["etat"] == "coche"]
    statut, r, duree = client.json("POST", "acte", {**valide, "contradictions": brutes, "consequences": retenues},
                                   dossier, "8-acte")
    if not info["modele_word"]:
        verifier(dossier, f"étape 8 sans modèle .docx : refus explicite (HTTP {statut})",
                 statut == 400 and ".doc" in str(r.get("erreur", "")), str(r.get("erreur", ""))[:90])
        return time.monotonic() - debut
    if not verifier(dossier, f"étape 8 acte : HTTP {statut} en {duree:.0f} s", statut == 200, r.get("erreur", "")):
        return time.monotonic() - debut
    blocs = r.get("blocs") or []
    revoir = [b for b in blocs if b.get("type") == "revoir"]
    compteurs = r.get("compteurs") or {}
    verifier(dossier, "étape 8 : blocs affichables", blocs and all(b.get("type") in ("titre", "texte", "revoir") for b in blocs),
             f"{len(blocs)} blocs, {len(revoir)} à revoir")
    verifier(dossier, "étape 8 : modifications appliquées au modèle", compteurs.get("appliquees", 0) > 0,
             f"{compteurs}")
    verifier(dossier, "étape 8 : questions au client", isinstance(r.get("questions"), list),
             f"{len(r.get('questions') or [])} questions")

    # Téléchargement du .docx et réouverture dans l'éditeur
    route = r["fichier"].split("/api/pipeline/", 1)[1]
    statut, entetes, octets, _ = client.appeler("GET", route)
    verifier(dossier, "téléchargement du .docx", statut == 200 and octets[:2] == b"PK"
             and "wordprocessingml" in entetes.get("Content-Type", ""), f"{len(octets)} octets")
    statut, rouvert, _ = client.json("GET", f"actes/{route.split('/', 1)[1]}")
    verifier(dossier, "réouverture de l'acte dans l'éditeur", statut == 200 and len(rouvert.get("blocs") or []) == len(blocs))

    # Cache : la même étape 1, redemandée, revient du cache sans rappeler Augure
    statut, entetes, _, duree = client.appeler("POST", "synthese-demande", {"dossier": dossier})
    verifier(dossier, "cache : étape 1 redemandée servie depuis le cache",
             statut == 200 and entetes.get("X-Cache") == "HIT" and duree < 5,
             f"X-Cache {entetes.get('X-Cache')}, {duree:.1f} s")

    # Panneau Augure : une question avec le dossier en contexte
    statut, r, duree = client.json("POST", "question", {
        "dossier": dossier, "question": "Quelles informations manquent encore pour finaliser l'acte ?",
        "historique": [], "contexte": "Étape 8, projet d'acte produit."}, dossier, "question")
    verifier(dossier, f"panneau Augure : HTTP {statut} en {duree:.0f} s", statut == 200 and str(r.get("reponse") or "").strip(),
             r.get("erreur", ""))
    return time.monotonic() - debut


def essais_generaux(client, attendus):
    _ecrire("\nRoutes générales")
    statut, r, _ = client.json("GET", "dossiers")
    liste = r.get("dossiers") or []
    verifier("général", f"GET dossiers : HTTP {statut}", statut == 200, f"{len(liste)} dossiers")
    noms = {d["dossier"] for d in liste}
    verifier("général", "les six dossiers fictifs sont proposés", attendus <= noms, ", ".join(sorted(attendus - noms)))
    statut, r, _ = client.json("POST", "synthese-demande", {"dossier": "inexistant"})
    verifier("général", "dossier inconnu : 400", statut == 400, r.get("erreur", ""))
    statut, r, _ = client.json("POST", "synthese-demande-clients", {"dossier": "mandat_protection"})
    verifier("général", "champ manquant : 400", statut == 400, r.get("erreur", ""))
    statut, _, _ = client.json("POST", "inconnue", {})
    verifier("général", "route inconnue : 404", statut == 404)
    statut, _, _, _ = client.appeler("GET", "fichier/..%2F..%2F.env")
    verifier("général", "chemin hors des actes refusé : 404", statut == 404)
    return liste


def main():
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("--base", default="http://localhost:8000")
    parseur.add_argument("--dossiers", nargs="*")
    parseur.add_argument("--paralleles", type=int, default=2,
                         help="dossiers traités en même temps (Augure décroche quand on lui en envoie trop)")
    args = parseur.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    sortie = ROOT / "out" / "tests" / "bout_en_bout" / datetime.now().strftime("%Y%m%d-%H%M%S")
    client = Client(args.base, sortie)
    attendus = {"charte_vie_commune", "convention_indivision", "mandat_protection",
                "servitude_enclave", "testament_simple_fiducie", "vente_immeuble_comptant"}
    try:
        liste = essais_generaux(client, attendus)
    except urllib.error.URLError as e:
        sys.exit(f"Backend injoignable sur {args.base} ({e.reason}) : lancer python -m backend.serveur")

    choisis = [d for d in liste if not args.dossiers or d["dossier"] in args.dossiers]
    debut = time.monotonic()
    with ThreadPoolExecutor(max_workers=max(1, min(args.paralleles, len(choisis)))) as pool:
        durees = dict(zip([d["dossier"] for d in choisis], pool.map(lambda d: parcours(client, d), choisis)))

    print(f"\n=== Bilan ({(time.monotonic() - debut) / 60:.1f} min, réponses dans {sortie}) ===")
    for dossier in ["général"] + [d["dossier"] for d in choisis]:
        lignes = [b for b in _bilan if b[0] == dossier]
        echecs = [b for b in lignes if not b[2]]
        duree = f", {durees[dossier] / 60:.1f} min" if dossier in durees else ""
        print(f"{dossier:28} {len(lignes) - len(echecs):3}/{len(lignes):<3} réussies{duree}")
        for _, libelle, _, detail in echecs:
            print(f"    ÉCHEC {libelle}{f' — {detail}' if detail else ''}")
    total_echecs = sum(1 for b in _bilan if not b[2])
    print(f"\n{len(_bilan) - total_echecs} vérifications réussies, {total_echecs} échecs")
    return 1 if total_echecs else 0


if __name__ == "__main__":
    sys.exit(main())
