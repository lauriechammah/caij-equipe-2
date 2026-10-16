# CAIJ Hackathon 2026, équipe 2, défi 2 (notarial)

L'assistant de rédaction d'actes aide le notaire à passer d'un modèle du Répertoire de droit à un projet d'acte adapté à son dossier client.

Le thème du hackathon est l'IA qui critique, pas l'IA qui fait tout. L'assistant ne livre pas un acte fini : il relève les contradictions, les informations manquantes et les conséquences à discuter, puis il pose les questions. Le notaire valide chaque étape et décide.

## Le pipeline en 8 étapes

1. Synthèse de la demande des clients (prompt 1).
2. Articles applicables du Code civil et du Code de procédure civile : Augure formule des requêtes, le Compagnon cherche les articles en vigueur, Augure retient ceux qui s'appliquent (prompt 2).
3. Synthèse du droit applicable (prompt 3).
4. Éléments factuels du dossier (prompt 4).
5. Demandes des clients, avec celles à confirmer (prompt 5).
6. Contradictions entre les demandes et avec le droit (prompt 6).
7. Conséquences possibles, choisies dans `backend/consequences_possibles.txt` selon le type d'acte (prompt 7).
8. Projet d'acte Word (prompt 8).

À chaque étape, le notaire coche ou décoche ce qu'Augure propose. Seul ce qui est retenu passe à l'étape suivante.

Le projet d'acte respecte le modèle à la lettre. Les 3 premières pages du modèle (mise en garde, droits d'auteur) sont ignorées. Le texte du modèle n'est jamais modifié. Les ajouts sont en rouge, en révision suivie, dans la police et la taille du modèle. Les passages touchés par une contradiction ou une conséquence sont surlignés avec une note, et une annexe reprend les questions à poser au client. Le fichier .docx se télécharge depuis l'application.

Une source inventée disqualifie : chaque article cité vient du Compagnon, avec son URL CAIJ.

## Organisation du repo

- `frontend/` : application React et Vite. Mandats, téléversement des pièces (.txt, .md, .docx), pipeline en 8 étapes, panneau de discussion avec Augure.
- `backend/` : serveur Python appelé par le frontend (proxy Vite `/api/pipeline`, port 8000).
  - `serveur.py` : les routes HTTP de chaque étape et le téléchargement des actes.
  - `fonctions.py` : étapes 1 à 5. `analyse.py` : étapes 6 et 7. `acte.py` : étape 8.
  - `prompts.py` et `consequences_possibles.txt` : les prompts et la liste des conséquences.
  - `clients.py` et `llm.py` : appels à Augure et au Compagnon, avec reprise automatique si Augure coupe ou dépasse son délai.
  - `db.py` : base SQLite `data/documents.db` avec les pièces, les modèles, les actes produits et le cache des réponses. Une étape déjà calculée revient du cache.
  - `pieces.py` : lecture des pièces téléversées. `journal.py` : journal des étapes dans `out/logs/backend.log`.
  - `essais.py` : tests hors ligne. `bout_en_bout.py` : les 8 étapes par HTTP sur les dossiers fictifs.
- `docs/` : les six dossiers fictifs et les six modèles d'actes. Seul Augure les lit, jamais Claude (voir `CLAUDE.md`).
- `scripts/` : `augure.py` et `compagnon.py`, les clients en ligne de commande d'origine.

## Installation et lancement

Il faut Python 3.9 ou plus récent, Node.js et la clé Augure dans `.env` (copier `.env.example`, puis remplir `AUGURE_API_KEY`). Sous macOS ou Linux, remplacer `.venv/Scripts` par `.venv/bin`.

```bash
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements.txt
.venv/Scripts/python -m backend.serveur
cd frontend && npm install && npm run dev
```

Autres commandes utiles, à lancer avec le Python du `.venv` :

- `python -m backend.essais` vérifie le backend sans clé ni réseau.
- `python -m backend.bout_en_bout` lance les 8 étapes sur les dossiers fictifs (le serveur doit tourner).
- `python -m backend.db` réimporte `docs/` dans la base, et `python -m backend.db --vider-cache` oublie les réponses en cache.

## À savoir

- Le pipeline complet prend environ 20 minutes, surtout à cause d'Augure. Grâce au cache, une relance reprend où l'on s'était arrêté.
- Les modèles de la vente et de la convention d'indivision sont en .doc (Word 97-2003). Il faut les convertir en .docx avec LibreOffice (`soffice --headless --convert-to docx`) pour produire leur acte.
- Augure : API compatible OpenAI (`https://api.augureai.ca/v1`), modèle `rosedale-1` par défaut, 60 requêtes par minute.
- Compagnon : recherche dans les sources du CAIJ, sans clé (`https://hackathon.caij.qc.ca/docs`).

## Critères du jury

Pertinence et utilité, valeur ajoutée, faisabilité, prise en compte des risques, présentation et démo.
