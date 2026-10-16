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

`POST https://hackathon.caij.qc.ca/semantic-search` (réponse en SSE). [Swagger](https://hackathon.caij.qc.ca/docs)

```json
{
  "query": "servitude de passage enclave article 997 C.c.Q.",
  "search_types": ["legislation", "jurisprudence", "doctrine"],
  "top_k": 10
}
```

`search_types` accepte `topo`, `doctrine`, `legislation` et `jurisprudence`. **Une source inventée disqualifie** : toute citation doit venir du Compagnon.

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
.env.example          variables d'environnement à copier dans .env
```
