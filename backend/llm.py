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
appeler, formuler la demande, et nettoyer la réponse. Une source inventée
disqualifie : rien n'est ajouté ici aux résultats du Compagnon.
"""

import importlib.util
import json
import re
import time
from pathlib import Path

from backend.config import (
    EFFORT_AUGURE,
    EXTRACT_COMPAGNON,
    REPETITIONS,
    PAUSE_REPETITION,
    TYPES_COMPAGNON,
    TOP_K_COMPAGNON,
    valeurs,
)

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
                time.sleep(PAUSE_REPETITION * (essai + 1))
                continue
            raise ErreurLLM(message) from None
    raise ErreurLLM("échec après plusieurs tentatives")


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
            "reasoning_effort": reglages["effort"],
        }
        if forcer_json:
            charge["response_format"] = {"type": "json_object"}
        try:
            reponse = _appeler(augure.stream_chat, reglages["cle"], charge)
        except ErreurLLM as erreur:
            if forcer_json and essai == 0 and "response_format" in str(erreur):
                forcer_json = False
                continue
            raise
        if not sortie_json:
            return reponse
        donnees = extraire_json(reponse)
        if donnees is not None:
            return donnees
        if essai == 0:
            contenu = contenu[:-1] + [{"type": "text", "text": f"{prompt}\n\n{CONSIGNE_JSON_RENOUVEL}"}]
    return {"reponse_brute": reponse, "json": False}


def ask_compagnon(prompt, types=None, top_k=None, resume=True, clarifications=None,
                  tous=True):
    """Cherche dans les sources du CAIJ. Pas de clé requise.

    Les extraits sont rendus en entier, avec le titre et l'URL à citer.
    """
    _regler_clients()
    resultat = _appeler(
        compagnon.search,
        prompt,
        list(types or TYPES_COMPAGNON),
        int(top_k or TOP_K_COMPAGNON),
        resume,
        clarifications,
    )
    if not isinstance(resultat, dict):
        resultat = {"results": resultat or {}}

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