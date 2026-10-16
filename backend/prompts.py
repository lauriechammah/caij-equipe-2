"""Prompts des sous-fonctions (document « Prompts for code »).

Les prompts sont recopiés tels quels. Les données (documents, résumé, faits,
articles) sont ajoutées à la suite par backend/fonctions.py, chacune sous son titre.
"""

# --- synthesedemandeclients ---

# Prompt 2 – droit applicable (sous-fonction 1 : Compagnon cherche, Augure applique ce prompt).
PROMPT_DROIT_APPLICABLE = """À partir du résumé des demandes et des documents fournis, trouve tous les articles du Code civil du Québec et du Code de procédure civile du Québec qui s'appliquent à ce dossier.
Pour chaque demande, principale ou accessoire, relève les articles qui la régissent. Tiens compte aussi des faits déterminants mentionnés dans le résumé. Quand un article applicable renvoie à d'autres articles du Code civil ou du Code de procédure civile, ajoute aussi ces articles de renvoi, à condition qu'ils soient pertinents pour le dossier.
Pour chaque article, donne son numéro, le code dont il provient et son texte intégral. Regroupe les articles par demande. Si un article s'applique à plusieurs demandes, indique-le plutôt que de le répéter.
Va chercher le texte de chaque article dans la source officielle mise à ta disposition et reproduis-le mot pour mot, dans sa version en vigueur. Ne rédige jamais le texte d'un article de mémoire. Si tu ne parviens pas à obtenir le texte d'un article, donne seulement son numéro et indique que le texte n'a pas pu être récupéré.
Limite-toi aux articles qui s'appliquent réellement à la situation décrite et ne fais pas d'analyse juridique à cette étape."""

# Avant le prompt 2 : requêtes courtes pour le Compagnon. Un récit détaillé (noms, montants)
# donne une mauvaise recherche sémantique ; une notion juridique par requête en donne une bonne.
PROMPT_REQUETES_COMPAGNON = """À partir du résumé des demandes ci-dessous, formule de 3 à 5 requêtes courtes pour chercher, dans le Code civil du Québec et le Code de procédure civile, les articles qui régissent ces demandes.
Une notion juridique par requête, en quelques mots (par exemple : « union parentale patrimoine d'union parentale », « protection de la résidence familiale »), sans noms, montants ni dates."""

FORMAT_REQUETES = "Réponds uniquement avec un tableau JSON de chaînes de caractères, sans texte avant ni après."

# Message système du prompt 2 : une liste d'articles vérifiables, affichée à cocher par le frontend.
FORMAT_ARTICLES = (
    "La source officielle est la liste d'extraits du Compagnon du CAIJ fournie à la fin. "
    "Le notaire validera ta liste article par article : en cas de doute, retiens l'article. "
    "Ne renvoie un tableau vide que si aucun extrait ne concerne le dossier. "
    "Réponds uniquement avec un tableau JSON, sans texte avant ni après. Une entrée par article retenu : "
    '{"titre": ce que l\'article régit, en quelques mots, '
    '"source": "Article <numéro> C.c.Q." ou "Article <numéro> C.p.c.", '
    '"demande": la ou les demandes qu\'il régit, '
    '"texte": son texte intégral tel qu\'il figure dans la source, ou "Texte non récupéré", '
    '"url": son URL telle qu\'elle figure dans la source, ou ""}.'
)

# Prompt 3 – synthèse droit applicable (sous-fonction 2, Augure).
PROMPT_SYNTHESE_DROIT_APPLICABLE = """À partir de la liste validée des articles du Code civil du Québec et du Code de procédure civile du Québec, rédige un résumé général du droit applicable à ce dossier.
Organise le résumé par demande. Pour chacune, explique en termes clairs les règles qui s'appliquent : les conditions à respecter, les formalités exigées, les droits et obligations des parties et les exceptions pertinentes. Indique entre parenthèses les numéros des articles sur lesquels repose chaque règle, pour que le notaire puisse s'y référer.
Ce résumé servira de référence au notaire et à la rédaction finale de l'acte. Il doit donc rester fidèle au texte des articles. Base-toi uniquement sur les articles fournis et n'ajoute aucune règle qui n'y figure pas. Si l'application d'un article au dossier est incertaine, signale-le."""

# --- getdemandeclientsetelementsfactuels ---

# Prompt 4 – éléments factuels (sous-fonction 1, Augure).
PROMPT_ELEMENTS_FACTUELS = """À partir des documents fournis et du contexte du dossier, dresse une liste exhaustive de tous les faits qui pourraient être pertinents pour la rédaction de l'acte.
Cette liste doit être la plus complète possible, car un fait oublié peut compromettre l'acte. Inclus notamment l'identité, l'état civil et la capacité des parties, leur régime matrimonial, la description des biens, les titres de propriété, les droits réels et les charges, les montants, les dates, les conditions, les délais et toute autre information présente dans les documents. Dans le doute, inclus le fait.
Regroupe les faits par catégorie et indique pour chacun le document dont il provient. Reproduis fidèlement les noms, numéros, montants et dates. Base-toi uniquement sur les documents, sans rien inventer. Si des documents se contredisent sur un fait, présente les deux versions et signale la contradiction. Si une information habituellement nécessaire pour ce type d'acte est absente, signale-la à la fin de la liste."""

# Prompt 5 – demandes clients (sous-fonction 2, Augure).
PROMPT_DEMANDES_CLIENTS = """À partir des documents fournis, du résumé initial des demandes, de la liste des faits et de la liste des articles applicables, dresse une liste exhaustive des demandes du client.
Contrairement au premier résumé, cette liste doit être détaillée et complète, puisqu'elle servira à la rédaction de l'acte. Décompose la demande principale et chaque demande accessoire en toutes leurs composantes : les obligations de chaque partie, les conditions, les modalités, les garanties, les déclarations, les délais et toute autre stipulation que le client souhaite voir dans l'acte. Inclus les détails précis tirés des documents, comme les montants, les dates et les désignations.
À côté de chaque demande, indique entre parenthèses les numéros des articles qui s'y appliquent, sans leur texte. Si aucun article de la liste ne s'applique à une demande, indique-le.
Distingue les demandes formulées explicitement par le client de celles qui découlent nécessairement du dossier. N'invente aucune demande. Si une demande est incomplète ou ambiguë, signale-le."""

# Messages système des prompts 4 et 5 : des listes affichées à cocher par le frontend.
FORMAT_FAITS = (
    "Réponds uniquement avec un tableau JSON, sans texte avant ni après. Une entrée par fait : "
    '{"categorie": sa catégorie, "titre": le fait, '
    '"source": le ou les documents dont il provient}. '
    "Les contradictions et les informations manquantes sont aussi des entrées, "
    'avec "Contradiction" ou "Information manquante" comme catégorie.'
)

FORMAT_DEMANDES = (
    "Réponds uniquement avec un tableau JSON, sans texte avant ni après. Une entrée par demande : "
    '{"titre": la demande, suivie des numéros d\'articles entre parenthèses, '
    '"source": le document d\'où elle vient, et si elle est formulée par le client ou découle du dossier, '
    '"a_confirmer": true si elle est incomplète, ambiguë ou contredite, sinon false}.'
)
