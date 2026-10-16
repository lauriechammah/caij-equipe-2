"""Fonctions du backend.

Chaque grosse fonction appelle deux sous-fonctions et renvoie leurs résultats
sous forme de tuple. Ordre d'appel :

    articles, synthese = synthesedemandeclients(docs, syntdmd)
    faits, demandes = getdemandeclientsetelementsfactuels(docs, syntdmd, articles)

`docs` : un texte, une liste de textes ou un dict {nom du document: texte}.
`syntdmd` : le résumé général des demandes du client (prompt 1).
Les listes (articles, faits, demandes) contiennent des objets {titre, source, ...},
le format des listes à cocher du frontend.
"""

import json
from concurrent.futures import ThreadPoolExecutor

from .clients import AugureError, CompagnonError, augure_chat, compagnon_search
from .config import ARTICLES_MAX
from .journal import chrono, journal, nombre, propager
from .llm import extraire_json

# Démo (ARTICLES_MAX) : nombre d'articles candidats soumis à Augure pour n'en garder qu'un.
CANDIDATS_DEMO = 5
from .prompts import (
    CONSIGNE_QUESTION,
    FORMAT_ARTICLES,
    FORMAT_DEMANDES,
    FORMAT_FAITS,
    FORMAT_REQUETES,
    FORMAT_SYNTHESE_DEMANDE,
    PROMPT_DEMANDES_CLIENTS,
    PROMPT_DROIT_APPLICABLE,
    PROMPT_ELEMENTS_FACTUELS,
    PROMPT_REQUETES_COMPAGNON,
    PROMPT_SYNTHESE_DEMANDE,
    PROMPT_SYNTHESE_DROIT_APPLICABLE,
)


def _texte_docs(docs):
    """Met les documents bout à bout, chacun précédé de son nom."""
    if isinstance(docs, str):
        return docs
    if isinstance(docs, dict):
        items = docs.items()
    else:
        items = ((f"Document {i}", texte) for i, texte in enumerate(docs, 1))
    return "\n\n".join(f"--- Document : {nom} ---\n{texte}" for nom, texte in items)


def _texte_liste(elements):
    """Remet en texte une liste d'objets {titre, source, ...} pour la donner à Augure."""
    lignes = []
    for e in elements:
        details = [f"{cle} : {val}" for cle, val in e.items() if cle not in ("titre", "etat") and val not in ("", None)]
        lignes.append(f"- {e.get('titre', '')}" + "".join(f"\n  {d}" for d in details))
    return "\n".join(lignes)


def _message(prompt, *sections):
    """Le prompt, suivi des données, chacune sous son titre."""
    return "\n\n".join([prompt] + [f"## {titre}\n\n{contenu}" for titre, contenu in sections])


def _est_article_en_vigueur(doc):
    """Code civil du Québec (CCQ-1991) ou Code de procédure civile (C-25.01).

    Exclut les codes remplacés que le Compagnon renvoie aussi (Code civil du
    Bas Canada, ancien Code de procédure civile C-25) et les règlements pris
    sous ces codes (« RLRQ c C-25.01, r 6 »).
    """
    titre = (doc.get("title") or "").lower()
    texte = f"{titre} {doc.get('original_url') or doc.get('url') or ''}".lower()
    return (("ccq-1991" in texte or "c-25.01" in texte)
            and "remplac" not in titre and not titre.startswith("règlement"))


def _augure_liste(prompt, format_json, effort="low"):
    """Appelle Augure et décode sa réponse en liste d'objets {titre, source, ...}.

    Si le tableau JSON est illisible, chaque ligne de la réponse devient un élément.
    """
    reponse = augure_chat(prompt, system=format_json, effort=effort)
    debut, fin = reponse.find("["), reponse.rfind("]")
    try:
        elements = json.loads(reponse[debut:fin + 1]) if debut != -1 and fin > debut else None
    except json.JSONDecodeError:
        elements = None
    if not isinstance(elements, list):
        lignes = (ligne.strip(" -*•\t") for ligne in reponse.splitlines())
        elements = [ligne for ligne in lignes if ligne and not ligne.startswith("```")]
    return [
        {**e, "titre": str(e.get("titre", "")), "source": str(e.get("source", ""))}
        if isinstance(e, dict) else {"titre": str(e), "source": ""}
        for e in elements
    ]


# --- synthese_demande (étape 1) ----------------------------------------------

@chrono("synthèse de la demande (prompt 1)")
def synthese_demande(docs):
    """Étape 1 : Augure résume la demande du client (prompt 1).

    Renvoie (titre, synthèse) : le titre donne les noms des clients pour l'affichage.
    """
    reponse = augure_chat(
        _message(PROMPT_SYNTHESE_DEMANDE, ("Documents du dossier", _texte_docs(docs))),
        system=FORMAT_SYNTHESE_DEMANDE,
        effort="medium",
    )
    donnees = extraire_json(reponse)
    if isinstance(donnees, dict) and str(donnees.get("synthese") or "").strip():
        return str(donnees.get("titre") or "").strip(), str(donnees["synthese"]).strip()
    # Pas de JSON lisible : la réponse entière sert de synthèse.
    return "", reponse.strip()


@chrono("question du panneau Augure")
def repondre_question(docs, question, historique=(), contexte=""):
    """Panneau Augure : répond à une question du notaire, pièces du dossier à l'appui.

    `historique` : les échanges précédents, [{role: "user" | "assistant", texte}].
    """
    echanges = "\n\n".join(
        f"{'Notaire' if e.get('role') == 'user' else 'Augure'} : {e.get('texte', '')}" for e in historique
    )
    sections = [("Documents du dossier", _texte_docs(docs))]
    if contexte:
        sections.append(("Où en est le notaire", contexte))
    if echanges:
        sections.append(("Échanges précédents", echanges))
    sections.append(("Question", question))
    return augure_chat(_message(CONSIGNE_QUESTION, *sections), effort="low").strip()


# --- synthesedemandeclients --------------------------------------------------

@chrono("requêtes courtes pour le Compagnon (Augure)")
def _requetes_compagnon(syntdmd):
    """Le résumé des demandes, plus des requêtes courtes qu'Augure en tire (une notion juridique chacune)."""
    try:
        requetes = [e["titre"] for e in _augure_liste(
            _message(PROMPT_REQUETES_COMPAGNON, ("Résumé des demandes", syntdmd)), FORMAT_REQUETES)]
    except AugureError:
        requetes = []
    return [syntdmd] + [r for r in requetes if r.strip()][:5]


@chrono("recherche des articles (Compagnon, en parallèle)")
def _articles_compagnon(requetes):
    """Cherche chaque requête dans le Compagnon et fusionne les articles en vigueur, sans doublon."""
    def chercher(requete):
        try:
            return compagnon_search(requete, types=["legislation"], top_k=30), None
        except CompagnonError as e:
            return None, e

    with ThreadPoolExecutor(max_workers=3) as pool:
        reponses = list(pool.map(propager(chercher), requetes))
    if all(resultat is None for resultat, _ in reponses):
        raise reponses[0][1]
    # Fusion rang par rang (1er résultat de chaque requête, puis 2e…) : les premiers articles
    # de la liste couvrent toutes les requêtes, ce qui compte quand on n'en garde que quelques-uns.
    listes = [[doc for doc in (resultat or {}).get("results", {}).get("legislation") or []
               if _est_article_en_vigueur(doc)] for resultat, _ in reponses]
    vus, sources = set(), []
    for rang in range(max((len(l) for l in listes), default=0)):
        for liste in listes:
            if rang < len(liste):
                doc = liste[rang]
                cle = doc.get("title") or doc.get("original_url") or doc.get("url")
                if cle not in vus:
                    vus.add(cle)
                    sources.append(doc)
    return sources


def articles_pertinents(docs, syntdmd, maximum=ARTICLES_MAX):
    """Sous-fonction 1 : articles du C.c.Q. et du C.p.c. applicables au dossier (prompt 2).

    Le Compagnon du hackathon est un moteur de recherche (son analyse est
    désactivée) : il cherche les articles à partir du résumé des demandes et de
    requêtes ciblées, puis Augure applique le prompt 2 en ne s'appuyant que sur ces extraits.
    Renvoie [{titre, source, demande, texte, url}], vide si le Compagnon ne trouve rien.

    ``maximum`` (``ARTICLES_MAX``, démo) : trois requêtes ciblées, quelques candidats envoyés à
    Augure (un appel court) et au plus ``maximum`` articles renvoyés. Si Augure n'en retient
    aucun, le premier candidat du Compagnon est renvoyé : l'étape n'est jamais vide.
    """
    requetes = _requetes_compagnon(syntdmd)
    if maximum:
        requetes = requetes[1:4] or requetes[:1]
    sources = _articles_compagnon(requetes)
    if maximum:
        sources = sources[:max(maximum, CANDIDATS_DEMO)]
    if not sources:
        return []
    extraits = "\n\n".join(
        f"### {doc.get('title')}\nURL : {doc.get('original_url') or doc.get('url')}\n{(doc.get('content') or '')[:2000]}"
        for doc in sources
    )
    journal.info("choix des articles (prompt 2) : %d candidats du Compagnon, %s car. d'extraits",
                 len(sources), nombre(len(extraits)))
    articles = _augure_liste(
        _message(
            PROMPT_DROIT_APPLICABLE,
            ("Résumé des demandes", syntdmd),
            ("Documents du dossier", _texte_docs(docs)),
            ("Source officielle : articles trouvés par le Compagnon du CAIJ", extraits),
        ),
        FORMAT_ARTICLES,
    )
    if not maximum:
        return articles
    # Le prompt 2 demande aussi les articles de renvoi : en démo, on s'en tient au maximum.
    if articles := [a for a in articles if a["titre"].strip()][:maximum]:
        return articles
    premier = sources[0]
    return [{
        "titre": premier.get("title") or "Article trouvé par le Compagnon",
        "source": premier.get("title") or "",
        "demande": "",
        "texte": premier.get("content") or "Texte non récupéré",
        "url": premier.get("original_url") or premier.get("url") or "",
    }]


@chrono("synthèse du droit applicable (prompt 3)")
def synthese_droit_applicable(articles):
    """Sous-fonction 2 : Augure résume le droit applicable à partir des articles (prompt 3)."""
    if not articles:
        return "Le Compagnon n'a trouvé aucun article applicable : pas de synthèse du droit applicable."
    return augure_chat(
        _message(PROMPT_SYNTHESE_DROIT_APPLICABLE, ("Liste des articles applicables", _texte_liste(articles)))
    )


def synthesedemandeclients(docs, syntdmd):

    """Renvoie (articles applicables, synthèse du droit applicable)."""
    articles = articles_pertinents(docs, syntdmd)
    synthese = synthese_droit_applicable(articles)
    return articles, synthese


# --- getdemandeclientsetelementsfactuels -------------------------------------

@chrono("éléments factuels (prompt 4)")
def elements_factuels(docs):
    """Sous-fonction 1 : Augure dresse la liste des faits du dossier (prompt 4)."""
    return _augure_liste(
        _message(PROMPT_ELEMENTS_FACTUELS, ("Documents du dossier", _texte_docs(docs))),
        FORMAT_FAITS,
    )


@chrono("demandes du client (prompt 5)")
def demandes_clients(docs, syntdmd, faits, articles):
    """Sous-fonction 2 : Augure dresse la liste détaillée des demandes du client (prompt 5)."""
    return _augure_liste(
        _message(
            PROMPT_DEMANDES_CLIENTS,
            ("Documents du dossier", _texte_docs(docs)),
            ("Résumé initial des demandes", syntdmd),
            ("Liste des faits", _texte_liste(faits)),
            ("Liste des articles applicables", _texte_liste(articles)),
        ),
        FORMAT_DEMANDES,
    )


def getdemandeclientsetelementsfactuels(docs, syntdmd, articles):
    """Renvoie (éléments factuels, demandes du client).

    `articles` : la liste renvoyée par synthesedemandeclients, ou seulement les
    articles cochés par le notaire.
    """
    faits = elements_factuels(docs)
    demandes = demandes_clients(docs, syntdmd, faits, articles)
    return faits, demandes
