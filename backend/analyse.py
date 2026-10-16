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

from backend.llm import ask_augure, ask_compagnon, bloc_sources

SCHEMA_CONTRADICTIONS = """
Réponds par un objet JSON exact, sans texte autour :
{
  "contradictions": [
    {
      "id": "C1",
      "enonce": "les deux versions du même fait, en une phrase chacune",
      "element_a": "fait, pièce et référence précise",
      "element_b": "fait, pièce et référence précise",
      "gravite": "moyenne | forte | bloquante",
      "impact_notarial": "ce que l'acte perd en solidité si cette contradiction reste",
      "question_a_poser": "question à poser au client pour la lever",
      "resolution_proposee": "ce qu'il faudrait écrire si le client confirme"
    }
  ],
  "information_manquante": [
    {"manque": "ce qui manque", "enquete": "comment l'obtenir", "impact": "effet sur l'acte"}
  ],
  "questions_prioritaires": ["les questions à poser en premier, dans l'ordre"],
  "elements_a_verifier": [
    {"element": "phrase ou donnée du dossier", "raison": "pourquoi la source est incertaine"}
  ],
  "aucune_contradiction": false
}
Règles : une contradiction oppose deux affirmations du dossier, pas une qualité du texte ;
une seule entrée par paire d'éléments qui se contredisent, même si la conséquence est grave ;
cite la pièce (nom du document) pour chaque élément ; n'invente aucune pièce.
Si le dossier est cohérent, renvoie une liste "contradictions" vide, "aucune_contradiction": true,
et toutes les informations manquantes que tu as trouvées.
"""

SCHEMA_CONSEQUENCES = """
Réponds par un objet JSON exact, sans texte autour :
{
  "consequences": [
    {
      "id": "K1",
      "type": "un des types possibles, repris tel quel",
      "consequence": "ce qui arrive, concrètement, pour le client",
      "condition": "à quelles conditions cette conséquence s'applique",
      "effet_acte": "comment l'acte doit être rédigé dans ce cas",
      "recommandation": "ce que tu conseilles au notaire, sans le remplacer",
      "source": {"titre": "titre exact de la source fournie", "url": "url exacte fournie", "extrait": "passage qui fonde la conséquence"},
      "confiance": "elevee | moyenne | faible"
    }
  ],
  "recommandation_generale": "ce qu'il faut trancher en premier",
  "sources_non_found": ["questions sans passage dans les sources fournies"]
}
Règles : n'utilise que les sources fournies et n'écris jamais une url qui n'y figure pas ;
si aucun passage ne fonde une conséquence, laisse "url" vide et passe la question dans
"questions_prioritaires" ; distingue les conséquences certaines des conséquences possibles.
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


def _corps(synthese, elements_factuels, demandes_clients=None, commentaires=None):
    sections = ["SYNTHÈSE DU DOSSIER", (synthese or "").strip() or "(aucune synthèse fournie)"]
    faits = _liste_en_texte(elements_factuels, "\nÉLÉMENTS FACTUELS")
    if faits:
        sections.append(faits)
    demandes = _couple_en_texte(demandes_clients, commentaires)
    if demandes:
        sections.append("DEMANDES DU CLIENT ET COMMENTAIRES\n" + demandes)
    return "\n\n".join(sections)


def get_contradictions(demandes_clients, commentaires, synthese, elements_factuels,
                       utiliser_sources=False, model=None, dossier=None):
    """Cherche les contradictions du dossier et les informations qui manquent.

    Renvoie le rapport en JSON (une chaîne) : ``contradictions``,
    ``information_manquante``, ``questions_prioritaires``, ``elements_a_verifier``.

        rapport = json.loads(get_contradictions(demandes, commentaires, synthese, faits))
    """
    corps = _corps(synthese, elements_factuels, demandes_clients, commentaires)
    demande = (
        "Tu es l'assistant du notaire qui prépare un acte à partir d'un modèle du "
        "Répertoire de droit. Ton rôle est de critiquer le dossier, pas de rédiger l'acte. "
        "Cherche toutes les contradictions entre les pièces du dossier, entre les demandes du "
        "client et les pièces, ainsi que ce qui manque et doit être enquête avant de signer.\n\n"
        + corps
    )

    if utiliser_sources:
        sources = ask_compagnon(
            f"{synthese or ''} obligation de clarification notaire acte contradictoire "
            f"{' '.join(str(f)[:120] for f in (elements_factuels or [])[:3])}"[:900]
        )
        if sources.get("nb_sources"):
            demande += "\n\nSOURCES JURIDIQUES (Compagnon)\n" + bloc_sources(sources)

    reponse = ask_augure(demande, dossier=dossier, sortie_json=True,
                         consignes=SCHEMA_CONTRADICTIONS.strip(), model=model)
    return json.dumps(_normaliser_contradictions(reponse), ensure_ascii=False, indent=2)


def _normaliser_contradictions(reponse):
    if isinstance(reponse, list):
        reponse = {"contradictions": reponse}
    if not isinstance(reponse, dict):
        return {"contradictions": [], "information_manquante": [], "reponse_brute": reponse}
    rapport = dict(reponse)
    for cle in ("contradictions", "information_manquante", "questions_prioritaires",
                "elements_a_verifier"):
        rapport[cle] = rapport.get(cle) or []
    for rang, contradiction in enumerate(rapport["contradictions"], 1):
        if isinstance(contradiction, dict):
            contradiction.setdefault("id", f"C{rang}")
    rapport.setdefault("aucune_contradiction", not rapport["contradictions"])
    return rapport


def get_type_consequences(demandes_clients, commentaires, type_consequences_possibles,
                          synthese, elements_factuels, utiliser_sources=True, model=None):
    """Classe les conséquences possibles du dossier et renvoie la liste retenue.

    Les sources viennent du Compagnon : chaque conséquence doit citer un passage
    réel, avec son url, ou être signalée comme non étayée.
    """
    types = list(type_consequences_possibles or [])
    corps = _corps(synthese, elements_factuels, demandes_clients, commentaires)
    demande = (
        "Tu es l'assistant du notaire qui doit avertir le client des conséquences "
        "juridiques et pratiques de ce qu'il demande. Classe chaque conséquence possible "
        "dans une des catégories proposées, et n'invente jamais une autre catégorie.\n\n"
        + corps
        + "\n\nTYPES DE CONSÉQUENCES POSSIBLES\n"
        + "\n".join(f"- {t}" for t in types)
    )

    sources = {}
    if utiliser_sources and types:
        question = f"{synthese or ''} {' '.join(types)}".strip()
        sources = ask_compagnon(question[:900])
        if sources.get("nb_sources"):
            demande += "\n\nSOURCES JURIDIQUES (Compagnon)\n" + bloc_sources(sources)

    reponse = ask_augure(demande, sortie_json=True, consignes=SCHEMA_CONSEQUENCES.strip(),
                         model=model)
    consequences = reponse.get("consequences") if isinstance(reponse, dict) else reponse
    if not isinstance(consequences, list):
        consequences = []
    consequences = [c for c in consequences if isinstance(c, dict)]
    for rang, consequence in enumerate(consequences, 1):
        consequence.setdefault("id", f"K{rang}")
        if not isinstance(consequence.get("source"), dict):
            consequence["source"] = {}
        consequence["source"].setdefault("titre", "")
        consequence["source"].setdefault("url", "")
        consequence["source"].setdefault("extrait", "")
    return consequences