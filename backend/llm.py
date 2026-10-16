"""Un prompt, une sortie : les deux clients du hackathon derrière une seule interface.

    from backend.llm import ask_augure, ask_compagnon

    analyse = ask_augure("Quelles informations se contredisent ?", dossier="mandat_protection")
    sources = ask_compagnon("homologation du mandat de protection")

- ``ask_augure`` envoie les pièces du dossier (et, si demandé, le modèle PDF) à
  Augure, qui les lit et les analyse. La réponse est relue en JSON ; au besoin
  une seconde tentative est faite pour obtenir du JSON valide.
- ``ask_compagnon`` interroge les sources du CAIJ sans clé. Les passages sont
  renvoyés en entier, avec le titre et l'URL à citer.

Les clients de ``scripts/`` sont repris tels quels : ce module ne fait que les
appeler, formuler la demande, et nettoyer la réponse. Seule la lecture du flux
d'Augure est refaite ici (``_stream_chat``), pour mesurer chaque appel dans le journal.
Une source inventée disqualifie : rien n'est ajouté ici aux résultats du Compagnon.
"""

import importlib.util
import json
import re
import sys
import time
from pathlib import Path

from backend.clients import AugureError, lire_flux
from backend.config import (
    EFFORT_AUGURE,
    EXTRACT_COMPAGNON,
    MAX_TOKENS_AUGURE,
    REPETITIONS,
    PAUSE_REPETITION,
    TYPES_COMPAGNON,
    TOP_K_COMPAGNON,
    valeurs,
)
from backend.journal import SuiviAugure, chrono, journal, nombre

CONSIGNE_JSON = (
    "Réponds uniquement par un objet JSON valide, sans texte avant ni après, "
    "sans commentaire et sans bloc de code. Sois exhaustif : reprends tous les "
    "éléments pertinents du dossier, même les détails secondaires. "
    "N'invente aucun fait : si une information manque, inscris-la comme manquante "
    "au lieu de la combler."
)

CONSIGNE_JSON_RENOUVEL = (
    "Ta réponse précédente n'était pas du JSON valide. "
    "Réponds à nouveau, et uniquement par un objet JSON valide : "
    "il doit commencer par { et se terminer par }, "
    "sans texte avant ni après, sans commentaire et sans bloc de code."
)


class ErreurLLM(RuntimeError):
    """Échec d'appel à Augure ou au Compagnon."""


def _charger(nom):
    chemin = Path(__file__).resolve().parent.parent / "scripts" / f"{nom}.py"
    specification = importlib.util.spec_from_file_location(f"backend_{nom}", chemin)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


augure = _charger("augure")
compagnon = _charger("compagnon")

def _regler_clients(reglages=None):
    """Aligne les clients de ``scripts/`` sur la configuration, y compris après un .env créé tard."""
    reglages = reglages or valeurs()
    augure.BASE_URL = reglages["augure_base"]
    compagnon.URL = reglages["compagnon_url"]
    return reglages


_regler_clients()


def _appeler(fonction, *args, **kwargs):
    """Appelle un client de ``scripts/`` en transformant ses ``sys.exit`` en exception."""
    for essai in range(REPETITIONS):
        try:
            return fonction(*args, **kwargs)
        except SystemExit as arret:
            message = str(arret) or "échec sans message"
            if "429" in message and essai + 1 < REPETITIONS:
                journal.warning("429, trop de requêtes : nouvel essai dans %.0f s (%d/%d)",
                                PAUSE_REPETITION * (essai + 1), essai + 2, REPETITIONS)
                time.sleep(PAUSE_REPETITION * (essai + 1))
                continue
            raise ErreurLLM(message) from None
    raise ErreurLLM("échec après plusieurs tentatives")


def _taille_contenu(contenu):
    """« 9 parties, 84 512 car., 1 PDF (1.2 Mo en base64) » : ce qui part chez Augure, sans le texte."""
    textes = [p.get("text") or "" for p in contenu if p.get("type") == "text"]
    fichiers = [(p.get("file") or {}).get("file_data") or "" for p in contenu if p.get("type") == "file"]
    taille = f"{len(contenu)} partie{'s' if len(contenu) > 1 else ''}, {nombre(sum(map(len, textes)))} car."
    if fichiers:
        taille += f", {len(fichiers)} PDF ({sum(map(len, fichiers)) / 1e6:.1f} Mo en base64)"
    return taille


def _stream_chat(cle, charge):
    """``augure.stream_chat``, mesuré dans le journal ; une erreur reste un ``sys.exit`` pour ``_appeler``."""
    with SuiviAugure(charge, _taille_contenu(charge["messages"][-1]["content"])) as suivi:
        with augure.request("POST", "/chat/completions", cle, charge) as resp:
            suivi.entetes()
            try:
                texte = lire_flux(resp, suivi)
            except AugureError as erreur:
                sys.exit(f"Erreur Augure : {erreur}")
        suivi.recu(texte)
    return texte


def _sans_bloc(texte):
    correspondance = re.search(r"```(?:json)?\s*(.*?)\s*```", texte, re.S)
    return correspondance.group(1) if correspondance else None


def _accolades(texte):
    debut = texte.find("{")
    fin = texte.rfind("}")
    if debut == -1 or fin <= debut:
        debut = texte.find("[")
        fin = texte.rfind("]")
    return texte[debut:fin + 1] if 0 <= debut < fin else None


def _nettoyer(texte):
    sans_accolades_vides = re.sub(r",\s*([}\]])", r"\1", texte)
    return sans_accolades_vides.replace("“", '"').replace("”", '"')


def extraire_json(texte):
    """Relit une réponse en JSON, même entourée d'un bloc de code ou d'un commentaire."""
    texte = (texte or "").strip()
    candidats = [texte, _sans_bloc(texte), _accolades(texte)]
    for candidat in candidats:
        if not candidat:
            continue
        for version in (candidat, _nettoyer(candidat)):
            try:
                return json.loads(version)
            except (json.JSONDecodeError, ValueError):
                continue
    return None


def _charge(modele=None, effort=None):
    reglages = _regler_clients()
    if not reglages["augure_cle"]:
        raise ErreurLLM("AUGURE_API_KEY manquant (voir .env.example)")
    return {
        "model": modele or reglages["augure_modele"],
        "effort": effort or EFFORT_AUGURE,
        "cle": reglages["augure_cle"],
    }


def ask_augure(prompt, dossier=None, modele=False, fichiers=(), sortie_json=True,
               consignes=None, model=None, effort=None):
    """Pose une question à Augure en lui envoyant les pièces du dossier.

    ``dossier`` : nom d'un dossier de ``docs/dossiers_fictifs``.
    ``modele`` : joindre en plus le PDF du modèle d'acte du même nom.
    ``fichiers`` : autres pièces (``.txt``, ``.md``, ``.pdf``).
    ``sortie_json`` : reprendre la réponse en JSON détaillé.
    Renvoie le JSON décodé, ou ``{"reponse_brute": texte}`` si le modèle n'a
    pas pu produire de JSON valide.
    """
    reglages = _charge(model, effort)
    contenu = []
    if dossier:
        contenu += augure.dossier_parts(dossier)
        if modele:
            contenu += augure.modele_parts(dossier)
    contenu += [augure.file_part(Path(f).resolve()) for f in fichiers]

    demande = prompt
    if sortie_json:
        demande = f"{prompt}\n\n{consignes or CONSIGNE_JSON}"
    contenu.append({"type": "text", "text": demande})

    reponse = ""
    forcer_json = sortie_json
    for essai in range(2):
        charge = {
            "model": reglages["model"],
            "messages": [{"role": "user", "content": contenu}],
            "stream": True,
            # Jetons lus et produits dans le dernier événement, pour le journal.
            "stream_options": {"include_usage": True},
            "reasoning_effort": reglages["effort"],
            "max_tokens": MAX_TOKENS_AUGURE,
        }
        if forcer_json:
            charge["response_format"] = {"type": "json_object"}
        try:
            reponse = _appeler(_stream_chat, reglages["cle"], charge)
        except ErreurLLM as erreur:
            if forcer_json and essai == 0 and "response_format" in str(erreur):
                journal.warning("Augure refuse response_format : nouvel appel sans")
                forcer_json = False
                continue
            if "reasoning_cutoff" in str(erreur) and reglages["effort"] != "low":
                journal.warning("Augure a épuisé son budget de raisonnement (effort %s) : nouvel appel en effort low",
                                reglages["effort"])
                reglages["effort"] = "low"
                continue
            raise
        if not sortie_json:
            return reponse
        donnees = extraire_json(reponse)
        if donnees is not None:
            return donnees
        if essai == 0:
            journal.warning("réponse d'Augure illisible en JSON (%s car.) : second appel complet",
                            nombre(len(reponse)))
            contenu = contenu[:-1] + [{"type": "text", "text": f"{prompt}\n\n{CONSIGNE_JSON_RENOUVEL}"}]
    journal.warning("toujours pas de JSON après deux appels : la réponse brute est renvoyée")
    return {"reponse_brute": reponse, "json": False}


def ask_compagnon(prompt, types=None, top_k=None, resume=True, clarifications=None,
                  tous=True):
    """Cherche dans les sources du CAIJ. Pas de clé requise.

    Les extraits sont rendus en entier, avec le titre et l'URL à citer.
    """
    _regler_clients()
    types = list(types or TYPES_COMPAGNON)
    # resume=True fait aussi analyser et résumer par le Compagnon : plus lent.
    with chrono(f"Compagnon « {' '.join(prompt.split())[:60]} » ({', '.join(types)}, "
                f"résumé {'oui' if resume else 'non'})", service="Compagnon") as infos:
        resultat = _appeler(
            compagnon.search,
            prompt,
            types,
            int(top_k or TOP_K_COMPAGNON),
            resume,
            clarifications,
        )
        if not isinstance(resultat, dict):
            resultat = {"results": resultat or {}}
        infos["résultats"] = sum(len(v or []) for v in (resultat.get("results") or {}).values())

    documents = []
    for categorie, trouves in (resultat.get("results") or {}).items():
        for rang, document in enumerate(trouves if tous else trouves[:top_k or TOP_K_COMPAGNON]):
            if not isinstance(document, dict):
                continue
            documents.append({
                "type": categorie,
                "rang": rang + 1,
                "titre": document.get("title") or "",
                "url": document.get("original_url") or document.get("url") or "",
                "score": document.get("score"),
                "extrait": " ".join(str(document.get("content") or "").split()),
                "metadonnees": document.get("metadata") or {},
            })
    return {
        "query": prompt,
        "resume": resultat.get("textual_summary") or "",
        "suggestions": resultat.get("follow_up_suggestions") or [],
        "sources": documents,
        "par_type": {t: [d for d in documents if d["type"] == t] for t in (resultat.get("results") or {})},
        "nb_sources": len(documents),
    }


def bloc_sources(sources, extrait=EXTRACT_COMPAGNON):
    """Met en forme des sources pour les coller à une demande, en gardant l'URL."""
    lignes = []
    for source in sources.get("sources", []):
        passage = source["extrait"][:extrait] if extrait else source["extrait"]
        lignes.append(
            f"[{source['type']}] {source['titre']}\n{source['url']}\n{passage}"
        )
    if sources.get("resume"):
        lignes.insert(0, f"Résumé du Compagnon :\n{sources['resume']}")
    return "\n\n".join(lignes)