# Argumentation — exemples d'appel

Deux scripts de départ pour le hackathon :

| Fichier | Ce qu'il montre |
|---|---|
| `01_compagnon_api.py` | Chercher dans les sources du CAIJ avec l'API de Compagnon |
| `02_augure_api.py` | Faire générer du texte par un modèle d'Augure |

Le premier trouve les documents et leur texte, le second raisonne dessus : à vous de les assembler.

## Mise en place

1. Installer [uv](https://docs.astral.sh/uv/getting-started/installation/). Chaque script déclare ses dépendances en tête de fichier, `uv run` les installe tout seul.
2. Copier `.env.example` en `.env` et y inscrire les valeurs remises par l'équipe :

   | Variable | Rôle |
   |---|---|
   | `COMPAGNON_API_URL` | Adresse de l'instance Compagnon du hackathon, sans chemin ni barre finale |
   | `AUGURE_API_KEY` | Votre clé Augure |
   | `AUGURE_MODEL` | Identifiant du modèle à utiliser |

Ne versionnez pas `.env` : il contient votre clé.

## 1. Chercher avec Compagnon

```bash
uv run 01_compagnon_api.py "Quels sont les critères de l'outrage au tribunal ?"
uv run 01_compagnon_api.py --complet "..."    # passages entiers, non tronqués
```

Le script envoie la question à `POST /semantic-search`. Aucun jeton n'est requis sur l'instance du hackathon.

### Requête

```json
{
  "query": "Quels sont les critères de l'outrage au tribunal ?",
  "search_types": ["jurisprudence", "doctrine", "legislation"]
}
```

- `query` : la question, en langage naturel. C'est le seul champ obligatoire.
- `search_types` : les sources à interroger, parmi `jurisprudence`, `doctrine`, `legislation` et `topo`.

### Réponse

La réponse arrive en Server-Sent Events, pas en JSON simple :

| Événement | Contenu |
|---|---|
| `status` | Progression (`stage` : `init`, `filter_detect`, `search`…). Plusieurs par requête. |
| `done` | Un seul, à la fin. Son champ `message` est la réponse complète, **encodée en JSON dans une chaîne** : il faut la décoder une seconde fois. |
| `error` | `code` et `message` décrivent l'échec. |

La fonction `iter_sse` du script fait ce découpage ; reprenez-la telle quelle.

Dans la réponse décodée, `results` regroupe les documents par source. Les champs utiles de chaque document :

| Champ | Contenu |
|---|---|
| `title` | Titre du document |
| `url` | Lien vers le document sur le site du CAIJ |
| `content` | Texte des passages repérés |
| `score` | Score de pertinence |
| `metadata` | Le reste : tribunal, date, numéro d'article, etc., selon la source |

Quand plusieurs passages d'un même document ressortent, `content` les enchaîne, chacun précédé d'une ligne `CHUNK INDEX: n`.

L'analyse des résultats et le résumé sont désactivés sur cette instance : la réponse ne contient ni `semantic_analysis` ni `textual_summary`. C'est justement la partie à construire.

## 2. Appeler un modèle d'Augure

```bash
uv run 02_augure_api.py --modeles        # lister les modèles accessibles avec votre clé
uv run 02_augure_api.py "Résume l'arrêt Vavilov en trois phrases."
uv run 02_augure_api.py --modele <id> "..."   # choisir un autre modèle que AUGURE_MODEL
```

L'API d'Augure est compatible avec celle d'OpenAI. On utilise donc le SDK `openai`, en changeant seulement l'adresse et la clé :

```python
from openai import OpenAI

client = OpenAI(api_key="...", base_url="https://api.augureai.ca/v1")
reponse = client.chat.completions.create(
    model="...",
    messages=[{"role": "user", "content": "Bonjour"}],
)
print(reponse.choices[0].message.content)
```

Tout outil qui accepte une adresse de base OpenAI peut être branché sur Augure de la même façon. Le script affiche la réponse au fil de sa génération (`stream=True`).

## Pour aller plus loin

L'enchaînement naturel : chercher avec Compagnon, puis passer les `content` au modèle comme contexte, en lui demandant de citer le titre et l'URL de ce qu'il utilise. Un modèle qui cite de mémoire invente des références ; un modèle qui cite les passages qu'on lui a fournis peut être vérifié.

## En cas de pépin

| Symptôme | Cause probable |
|---|---|
| `KeyError: 'AUGURE_API_KEY'` | `.env` absent, ou script lancé depuis un autre dossier |
| `Préciser le modèle` | `AUGURE_MODEL` vide : lancer `--modeles` pour voir les identifiants |
| Erreur de connexion sur l'exemple 1 | `COMPAGNON_API_URL` vide (le script vise alors `localhost:8000`) ou erroné |
| Titres et URL, mais pas de texte | L'instance ne renvoie pas `content` : prévenir l'équipe |
