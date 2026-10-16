# CAIJ Hackathon 2026 — Équipe 2 · Défi 2 (Notarial)

**L'assistant de rédaction d'actes** : aider le notaire à passer d'un modèle d'acte du Répertoire de droit / Nouvelle série à un projet d'acte adapté à son dossier client.

> « Ce document ne doit pas être utilisé dans son intégralité, mais plutôt refléter avec précision la situation et les volontés réelles du mandant. »

Le thème du hackathon, c'est **l'IA qui critique, pas l'IA qui fait tout**. L'assistant ne livre pas un acte fini : il signale les contradictions du dossier, les informations manquantes et les options du modèle à trancher, puis il pose les questions. Le notaire décide et sait pourquoi.

## Les six dossiers

| Dossier (`docs/dossiers_fictifs/`) | Modèle d'acte (`docs/modeles/`) |
| --- | --- |
| `vente_immeuble_comptant` | Vente d'un immeuble au comptant (Vente, Doc. 2.1) |
| `servitude_enclave` | Servitude de passage en cas d'enclave (Biens, Doc. 3.2) |
| `convention_indivision` | Convention d'indivision (Biens, Doc. 2) |
| `mandat_protection` | Mandat de protection (Mandat, Doc. 2) |
| `testament_simple_fiducie` | Testament simple avec fiducie pour enfants (Libéralités, Doc. 3.7) |
| `charte_vie_commune` | Charte de vie commune (Famille, Doc. 11.1) |

Chaque dossier contient ses pièces en `word/` et en `txt/`. On commence par « 0 - Mise en contexte et mandat ». Les modèles sont fournis en PDF annoté (avec les notes des auteurs) et en Word.

## Architecture

```
Dossier client (txt) + modèle (PDF) ──► Augure ──► analyse, objections, questions
                                          ▲
              Compagnon (sources CAIJ) ───┘   jurisprudence, doctrine, législation
```

- **Augure** raisonne sur les documents. C'est lui, et **pas Claude**, qui lit et analyse les dossiers.
- **Compagnon** trouve les passages réels et vérifiables dans les sources du CAIJ.

## Installation

```bash
cp .env.example .env      # puis coller la clé dans AUGURE_API_KEY
python scripts/augure.py --list-models
```

Python 3.9 ou plus récent suffit, sans dépendances.

## Utiliser Augure

```bash
# Toutes les pièces txt d'un dossier + une question
python scripts/augure.py --dossier mandat_protection "Quelles informations se contredisent ?"

# Joindre aussi le modèle PDF annoté
python scripts/augure.py --dossier servitude_enclave --modele "Quelles options du modèle faut-il trancher, et sur quels faits ?"

# Autres options : --model, --effort none|low|medium|high, --system, --file, --out
python scripts/augure.py --dossier testament_simple_fiducie --out out/testament.md "Liste les questions à poser au client."
```

- API : `https://api.augureai.ca/v1`, compatible OpenAI ([docs](https://augureai.ca/docs/api)).
- Modèles : `rosedale-1` (défaut, contexte de 1M), `ossington-5`, `ossington-4-1` (fort en FR/EN), `tofino-3` (léger).
- Les PDF sont envoyés en base64 (25 Mo et 200 pages max.). Les `.docx` ne sont pas acceptés : on utilise les `.txt`.
- Limite de 60 requêtes par minute. Le script utilise le streaming pour éviter le délai de 240 s.

### Pourquoi pas Claude pour lire les dossiers ?

Les documents passent par Augure. Pour éviter que Claude Code les lise par accident :

- `.claude/settings.json` interdit à l'outil `Read` d'accéder à `docs/dossiers_fictifs/*/` et `docs/modeles/`.
- `CLAUDE.md` demande à Claude de passer par `scripts/augure.py`.

**Variante MCP (optionnelle)** : Augure offre aussi un serveur MCP (`ask_augure`, `list_models`, `get_limits`), mais il faut une clé MCP distincte (`aug_mcp_live_…`) à activer dans le tableau de bord développeur :

```bash
claude mcp add --transport http augure https://mcp.augureai.ca/mcp \
  --header "Authorization: Bearer aug_mcp_live_…"
```

## Compagnon (recherche CAIJ)

Aucune clé requise. [Swagger](https://hackathon.caij.qc.ca/docs)

```bash
python scripts/compagnon.py "servitude de passage enclave"
python scripts/compagnon.py --types legislation jurisprudence --top-k 5 "homologation mandat de protection"
python scripts/compagnon.py --summary "durée maximale convention d'indivision"   # + résumé par le Compagnon (plus lent)
python scripts/compagnon.py --json --out out/resultats.json "fiducie enfants mineurs testament"
```

Ou directement avec curl :

```bash
curl -N -X POST https://hackathon.caij.qc.ca/semantic-search \
  -H "Content-Type: application/json" \
  -d '{"query": "servitude de passage enclave", "search_types": ["legislation"], "top_k": 5,
       "semantic_analysis": false, "summarization": false}'
```

- La réponse arrive en **SSE** : des événements `status` (progression), puis un événement `done` dont le champ `data.message` est une **chaîne JSON** à décoder une deuxième fois.
- Dans ce JSON, `results` contient un tableau par type (`legislation`, `jurisprudence`, `doctrine`, `topo`). Chaque document a `title`, `content` (l'extrait), `original_url` (le lien CAIJ à citer) et `score`. Les champs `textual_summary` et `follow_up_suggestions` sont remplis si `summarization` est à `true`.
- Paramètres utiles : `search_types`, `top_k` (1 à 100), `clarifications`, `search_filters` (date, juridiction, tribunal).
- Le Compagnon peut renvoyer plus de résultats que `top_k` et des types non demandés. Le script les filtre.

**Une source inventée disqualifie** : toute citation doit venir du Compagnon, avec son `original_url`.

## Backend

`backend/` reprend les deux clients ci-dessus en fonctions : un prompt, du JSON en sortie.

```bash
python -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
.venv/bin/python -m backend.essais     # vérifications hors ligne, sans clé
```

```python
from backend import ask_augure, ask_compagnon, get_contradictions, get_type_consequences, create_acte_modifie

ask_augure("Quelles informations se contredisent ?", dossier="mandat_protection")
ask_compagnon("homologation du mandat de protection")
get_contradictions(demandes_clients, commentaires, synthese, elements_factuels)      # -> JSON
get_type_consequences(demandes_clients, commentaires, types, synthese, faits)        # -> liste
create_acte_modifie(synthese, demandes_clients, commentaires, faits, consequences, cmts)  # -> chemin du .docx
```

L'acte produit porte les ajouts en révision suivie, les passages à vérifier surlignés et
commentés, et une annexe de questions à trancher avec les urls des sources. Détail et
démarches : [`backend/README.md`](backend/README.md).

## Critères du jury

1. Pertinence et utilité · 2. Valeur ajoutée · 3. Faisabilité · 4. Prise en compte des risques · 5. Présentation et démo

Horaire : développement jusqu'à 16 h 15, puis présentations à 16 h 30.

## Arborescence

```
docs/
  dossiers_fictifs/   six dossiers clients fictifs (word/ + txt/)
  modeles/            six modèles d'actes (PDF annoté + Word)
  Hackathon CAIJ — Les deux défis.pdf
scripts/
  augure.py           client Augure : envoie dossier/modèle, renvoie la réponse
  compagnon.py        client Compagnon : recherche dans les sources du CAIJ
backend/
  llm.py              ask_augure / ask_compagnon : un prompt, du JSON
  analyse.py          get_contradictions, get_type_consequences
  acte.py             create_acte_modifie : l'acte Word annoté
  db.py               squelette : où trouver le document de départ
  essais.py, cli.py   vérifications hors ligne, essai de bout en bout
.env.example          variables d'environnement à copier dans .env
```
