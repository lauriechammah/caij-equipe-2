"""Les deux premières étapes de l'assistant : les contradictions, puis les conséquences.

    from backend.analyse import get_contradictions, get_type_consequences

    rapport = get_contradictions(demandes_clients, commentaires, synthese, elements_factuels)
    consequences = get_type_consequences(
        demandes_clients, commentaires, types_possibles, synthese, elements_factuels)

Le thème du hackathon tient dans ces deux fonctions : l'IA ne rédige pas à la
place du notaire, elle signale ce qui ne colle pas et ce qui engage le client.
Augure lit les pièces, le Compagnon ramène les sources réelles à citer.
"""

import json
import re
import unicodedata

from backend.config import EXTRACT_COMPAGNON
from backend.journal import chrono
from backend.llm import ask_augure, ask_compagnon, bloc_sources

PROMPT_CONTRADICTIONS = """
À partir de la liste exhaustive des demandes, du résumé du droit applicable et de la liste des articles, relève toutes les contradictions possibles.
Compare d'abord les demandes entre elles. Relève celles qui s'opposent, s'excluent ou ne peuvent pas être réalisées ensemble. Compare ensuite chaque demande au droit applicable. Relève celles que la loi interdit, celles qui exigent une condition ou une formalité non remplie, et celles dont l'effet recherché va à l'encontre de ce que prévoit la loi.
Pour chaque contradiction, indique les demandes concernées, explique brièvement le problème et donne les numéros des articles en cause. Précise si la contradiction est certaine ou seulement possible selon des faits à confirmer.
Signale même les contradictions incertaines, puisque le notaire tranchera. Ne modifie pas les demandes.
"""

PROMPT_CONSEQUENCES = """
À partir de la liste des conséquences possibles fournie, de la liste exhaustive des demandes et du résumé du droit applicable, relève les conséquences que les demandes du client pourraient entraîner et dont le notaire devra discuter avec lui.
Pour chaque demande, parcours la liste des conséquences et retiens celles qui pourraient s'appliquer à la situation. Porte une attention particulière aux conséquences moins évidentes, dans d'autres domaines du droit, que le client ou le notaire pourrait ne pas avoir envisagées.
Pour chaque conséquence retenue, indique la ou les demandes qui la déclenchent et explique brièvement en quoi elle pourrait toucher le client. Précise les faits ou les articles sur lesquels tu t'appuies, et indique si la conséquence est certaine ou seulement possible.
Retiens seulement les conséquences qui ont un lien réel avec le dossier. Si une conséquence importante te semble absente de la liste fournie, tu peux l'ajouter en précisant qu'elle ne provient pas de la liste.
"""

SCHEMA_CONTRADICTIONS = """
Réponds par un objet JSON exact, sans texte autour, sans commentaire :
{
  "contradictions": [
    {
      "id": "C1",
      "demandes_concernees": ["demande visée, citée mot pour mot"],
      "probleme": "explication brève de la contradiction",
      "articles": ["numéro d'article en cause, cité tel quel dans le droit applicable"],
      "certitude": "certaine | possible",
      "faits_a_confirmer": ["ce qui reste à vérifier pour trancher"]
    }
  ],
  "questions_au_notaire": ["ce qu'il faut trancher, dans l'ordre"],
  "aucune_contradiction": false
}
Une entrée par contradiction, jamais deux fois la même. Un article qui ne figure pas dans le
droit applicable fourni ne doit pas être cité : laisse-le vide plutôt que de l'inventer.
Si le dossier est cohérent, renvoie "contradictions": [] et "aucune_contradiction": true.
"""

SCHEMA_CONSEQUENCES = """
Réponds par un objet JSON exact, sans texte autour, sans commentaire :
{
  "consequences": [
    {
      "id": "K1",
      "type": "le type repris tel quel dans la liste fournie",
      "consequence": "ce qui pourrait arriver, concrètement",
      "demandes_declencheuses": ["demande visée, citée mot pour mot"],
      "effet_sur_le_client": "en quoi cela le touche",
      "faits": ["fait du dossier sur lequel tu t'appuies"],
      "articles": ["numéro d'article, cité tel quel dans le droit applicable"],
      "certitude": "certaine | possible",
      "hors_liste": false
    }
  ],
  "questions_au_notaire": ["ce qu'il faut trancher avec le client, dans l'ordre"]
}
Reprends les types de la liste fournie sans les renommer. "hors_liste" passe à true seulement
pour une conséquence que tu ajoutes et qui n'y figure pas. Un article absent du droit
applicable fourni ne doit pas être cité : laisse la liste vide plutôt que de l'inventer.
"""


def _liste_en_texte(valeur, titre=None):
    if not valeur:
        return ""
    morceaux = []
    for index, item in enumerate(valeur, 1):
        if isinstance(item, str):
            morceaux.append(f"{index}. {item.strip()}")
        elif isinstance(item, dict):
            morceaux.append(f"{index}. {json.dumps(item, ensure_ascii=False)}")
        else:
            morceaux.append(f"{index}. {item}")
    entete = f"{titre}\n" if titre else ""
    return entete + "\n".join(morceaux)


def _couple_en_texte(demandes_clients, commentaires=None):
    if isinstance(demandes_clients, (list, tuple)) and commentaires is None:
        demandes_clients, commentaires = demandes_clients, []
    lignes = []
    for index, demande in enumerate(demandes_clients or [], 1):
        if isinstance(demande, dict):
            lignes.append(f"{index}. " + json.dumps(demande, ensure_ascii=False))
        else:
            lignes.append(f"{index}. {demande}")
        if index <= len(commentaires or []):
            lignes.append(f"   commentaire : {commentaires[index - 1]}")
    return "\n".join(lignes)


def corps_demande(synthese, elements_factuels, demandes_clients=None, commentaires=None,
           droit_applicable=None):
    sections = ["SYNTHÈSE DU DOSSIER", (synthese or "").strip() or "(aucune synthèse fournie)"]
    faits = _liste_en_texte(elements_factuels, "\nÉLÉMENTS FACTUELS")
    if faits:
        sections.append(faits)
    demandes = _couple_en_texte(demandes_clients, commentaires)
    if demandes:
        sections.append("LISTE EXHAUSTIVE DES DEMANDES\n" + demandes)
    droit = droit_en_texte(droit_applicable)
    if droit:
        sections.append(droit)
    return "\n\n".join(sections)


def droit_en_texte(droit_applicable):
    """Le droit applicable tel qu'il est fourni, ou tel que le Compagnon l'a trouvé."""
    if not droit_applicable:
        return ""
    if isinstance(droit_applicable, str):
        return "RÉSUMÉ DU DROIT APPLICABLE ET LISTE DES ARTICLES\n" + droit_applicable.strip()
    corps = ["RÉSUMÉ DU DROIT APPLICABLE", droit_applicable.get("resume") or "(aucun)"]
    sources = droit_applicable.get("sources") or []
    if sources:
        corps.append("LISTE DES ARTICLES\n" + bloc_sources(droit_applicable))
    return "\n".join(corps)


def resume_droit_applicable(synthese, elements_factuels=None, demandes_clients=None,
                            types=None, question=None):
    """Cherche le droit applicable dans les sources du CAIJ.

    Renvoie ``{"resume", "sources", "nb_sources"}``, à passer ensuite à
    ``get_contradictions``, ``get_type_consequences`` et ``create_acte_modifie``.
    """
    if question is None:
        question = f"{synthese or ''} {' '.join(str(t) for t in (types or []))}".strip()
    return ask_compagnon(question[:900])


@chrono("contradictions (prompt 6)")
def get_contradictions(demandes_clients, commentaires, synthese, elements_factuels,
                       droit_applicable=None, model=None, dossier=None):
    """Relève toutes les contradictions possibles du dossier.

    Renvoie le rapport en JSON, une chaîne :
    ``contradictions`` (demandes concernées, problème, articles, certitude),
    ``questions_au_notaire``, ``aucune_contradiction``.

        rapport = json.loads(get_contradictions(demandes, commentaires, synthese, faits, droit))
    """
    demande = (PROMPT_CONTRADICTIONS.strip() + "\n\n"
               + corps_demande(synthese, elements_factuels, demandes_clients, commentaires,
                        droit_applicable))
    reponse = ask_augure(demande, dossier=dossier, sortie_json=True,
                         consignes=SCHEMA_CONTRADICTIONS.strip(), model=model)
    return json.dumps(_normaliser_contradictions(reponse), ensure_ascii=False, indent=2)


def _normaliser_contradictions(reponse):
    if isinstance(reponse, list):
        reponse = {"contradictions": reponse}
    if not isinstance(reponse, dict):
        return {"contradictions": [], "questions_au_notaire": [], "reponse_brute": reponse}
    rapport = dict(reponse)
    for cle in ("contradictions", "questions_au_notaire"):
        rapport[cle] = rapport.get(cle) or []
    for rang, contradiction in enumerate(rapport["contradictions"], 1):
        if isinstance(contradiction, dict):
            contradiction.setdefault("id", f"C{rang}")
            contradiction.setdefault("certitude", "possible")
    rapport.setdefault("aucune_contradiction", not rapport["contradictions"])
    return rapport


def _attacher_sources(consequences, sources):
    """Aligne chaque article cité sur une source réelle du Compagnon.

    Une conséquence dont aucun article ne se retrouve dans les sources fournies
    revient avec une url vide : mieux vaut rien qu'une référence inventée.
    """
    disponibles = sources.get("sources") or []
    for consequence in consequences:
        cites = consequence.get("articles") or []
        trouvee = None
        for article in cites:
            for source in disponibles:
                if _normaliser(article) in _normaliser(source["titre"] + " " + source["extrait"]):
                    trouvee = source
                    break
            if trouvee:
                break
        if trouvee:
            consequence["source"] = {"titre": trouvee["titre"], "url": trouvee["url"],
                                     "extrait": trouvee["extrait"][:EXTRACT_COMPAGNON]}
        else:
            consequence["source"] = {"titre": "", "url": "", "extrait": ""}
    return consequences


def _normaliser(texte):
    sans_accent = "".join(
        c for c in unicodedata.normalize("NFD", str(texte or ""))
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sans_accent.lower()).strip()


@chrono("conséquences (prompt 7)")
def get_type_consequences(demandes_clients, commentaires, type_consequences_possibles,
                          synthese, elements_factuels, droit_applicable=None, model=None):
    """Relève les conséquences que les demandes pourraient entraîner.

    Si le droit applicable n'est pas fourni, il est cherché dans les sources du
    CAIJ. Chaque conséquence retenue revient avec les demandes qui la déclenchent,
    les faits et articles invoqués, la certitude, et l'url de la source lorsque
    l'article cité se retrouve dans les sources fournies.
    """
    types = [str(t) for t in (type_consequences_possibles or [])]
    demande = (PROMPT_CONSEQUENCES.strip() + "\n\n"
               + corps_demande(synthese, elements_factuels, demandes_clients, commentaires,
                        droit_applicable)
               + "\n\nLISTE DES CONSÉQUENCES POSSIBLES\n"
               + "\n".join(f"- {t}" for t in types))

    sources = droit_applicable if isinstance(droit_applicable, dict) else {}
    if not sources:
        question = f"{synthese or ''} {' '.join(types)}".strip()
        sources = ask_compagnon(question[:900])
        if sources.get("nb_sources"):
            demande += "\n\n" + droit_en_texte(sources)

    reponse = ask_augure(demande, sortie_json=True, consignes=SCHEMA_CONSEQUENCES.strip(),
                         model=model)
    consequences = reponse.get("consequences") if isinstance(reponse, dict) else reponse
    if not isinstance(consequences, list):
        consequences = []
    consequences = [c for c in consequences if isinstance(c, dict)]
    for rang, consequence in enumerate(consequences, 1):
        consequence.setdefault("id", f"K{rang}")
        consequence.setdefault("certitude", "possible")
        consequence.setdefault("type", next((t for t in types if t.lower() in
                                             str(consequence.get("type", "")).lower()), ""))
        consequence.setdefault("hors_liste", False)
    return _attacher_sources(consequences, sources)
