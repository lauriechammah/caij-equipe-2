# Backend

Le même backend que les scripts de `scripts/`, mais en fonctions : on donne un prompt à
Augure ou au Compagnon, on reçoit du JSON ; on donne un dossier, on reçoit l'acte.

```bash
python -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
cp .env.example .env          # puis AUGURE_API_KEY
.venv/bin/python -m backend.essais      # 41 vérifications, sans clé ni appel réseau
```

## Lancer l'application (backend + frontend)

```bash
.venv/bin/python -m backend.serveur     # Windows : .venv\Scripts\python -m backend.serveur
cd frontend && npm install && npm run dev
```

Le serveur écoute sur `http://localhost:8000` ; le proxy Vite lui envoie `/api/pipeline/*`.
Chaque étape du pipeline du frontend appelle une route :

| Étapes | Route (`POST /api/pipeline/…`) | Fonction |
| --- | --- | --- |
| 2-3 | `synthese-demande-clients` | `synthesedemandeclients` (`fonctions.py`, prompts 2-3) |
| 4-5 | `demandes-et-faits` | `getdemandeclientsetelementsfactuels` (`fonctions.py`, prompts 4-5) |
| 6 | `contradictions` | `get_contradictions` (`analyse.py`, prompt 6) |
| 7 | `consequences` | `get_type_consequences` (`analyse.py`, prompt 7) |
| 8 | `acte` | `create_acte_modifie` (`acte.py`, prompt 8) ; `GET fichier/<nom>` télécharge le `.docx` |

Les étapes 6 à 8 ne reçoivent que ce que le notaire a coché aux étapes précédentes. La liste
des conséquences possibles du prompt 7 est `consequences_possibles.txt` (une par ligne, préfixée
par le type d'acte) : seules celles du type d'acte du dossier sont envoyées (`TYPES_ACTE`, `serveur.py`).

## Les deux appels, un prompt chacun

```python
from backend import ask_augure, ask_compagnon

analyse = ask_augure("Quelles informations se contredisent ?", dossier="mandat_protection")
sources = ask_compagnon("homologation du mandat de protection")
```

- `ask_augure(prompt, dossier=…, modele=True, fichiers=[…])` envoie les pièces du dossier
  et, si demandé, le PDF du modèle. Le `reasoning_effort` est mis à `high` par défaut pour
  une réponse détaillée. La réponse est relue en JSON ; si le modèle n'en renvoie pas, une
  seconde tentative est faite, et au pire `{"reponse_brute": …}` est renvoyé.
- `ask_compagnon(prompt, types=[…], top_k=…)` rend `{resume, sources[], nb_sources}`, chaque
  source avec `type`, `titre`, `url`, `extrait` entier, `score`. Rien n'y est inventé : une
  citation sans url n'est pas une source.

## Les trois méthodes

Les trois prompts sont dans `analyse.py` (`PROMPT_CONTRADICTIONS`, `PROMPT_CONSEQUENCES`)
et `acte.py` (`PROMPT_ACTE`), repris tels quels ; la sortie attendue de chacune est dans le
`SCHEMA_…` qui suit.

```python
from backend import get_contradictions, get_type_consequences, create_acte_modifie
from backend import resume_droit_applicable

droit = resume_droit_applicable(synthese, elements_factuels)      # résumé + liste des articles
rapport = get_contradictions(demandes_clients, commentaires, synthese,
                            elements_factuels, droit_applicable=droit)
consequences = get_type_consequences(
    demandes_clients, commentaires, types_possibles, synthese, elements_factuels,
    droit_applicable=droit)
chemin = create_acte_modifie(
    synthese, demandes_clients, commentaires, elements_factuels, consequences,
    contradictions=json.loads(rapport), droit_applicable=droit)
```

| Méthode | Renvoie |
| --- | --- |
| `get_contradictions` | le rapport en JSON, **une chaîne** : `contradictions` (demandes concernées, problème, articles, certitude), `questions_au_notaire` |
| `get_type_consequences` | la **liste** des conséquences retenues : demandes déclencheuses, effets, faits, articles, certitude, `hors_liste`, et la source |
| `create_acte_modifie` | le **chemin** du fichier Word produit |

Le droit applicable se cherche une fois avec `resume_droit_applicable` et se passe aux trois
étapes ; si on ne le fournit pas, chaque étape le cherche elle-même. Un article cité par le
modèle est rapproché des passages du Compagnon : s'il ne s'y retrouve pas, la conséquence
revient avec une url vide plutôt qu'avec une référence inventée.

## Le document produit

`create_acte_modifie` fait proposer à Augure un plan — `ajouts`, `surlignages`, `signalees`,
chacun avec une ancre citant le modèle mot pour mot — puis **le code** l'applique.

Le modèle est respecté à la lettre : son texte n'est jamais supprimé ni reformulé (un
remplacement ou une suppression proposés deviennent un passage surligné avec une note).

- les **3 pages liminaires** du modèle (mise en garde, droits d'auteur…) sont retirées dès le
  chargement : Augure ne les reçoit pas, aucune ancre n'y tombe, l'acte commence à la page 4.
  Augure reçoit le texte du `.docx` (et non le PDF) : ses ancres citent le document complété ;
- chaque **ajout** est **rouge** et en révision suivie : Word l'affiche comme une insertion,
  avec l'auteur « Assistant CAIJ — équipe 2 ». Il prend la **police et la taille** du
  paragraphe d'ancrage (ou du paragraphe courant du modèle si l'ancre est un titre), comme
  les notes et l'annexe ;
- un **[À COMPLÉTER : …]** reste en rouge quand une information manque, avec sa note ;
- les passages touchés par une contradiction ou une conséquence sont **surlignés** (jaune,
  vert, cyan, rose), portent un **commentaire Word** et une **note courte à côté** ;
- une clause qui ne s'applique pas est **signalée** en rouge, jamais retirée ;
- une **annexe** reprend les questions à trancher, les conséquences et leurs urls, et ce qui
  n'a pas pu être appliqué ;
- à côté du `.docx`, un `.rapport.json` liste les opérations appliquées, les ancres introuvables
  et le plan lui-même.

Une ancre est retrouvée d'abord mot pour mot (accents et espaces insensibles), puis au plus
proche : en dessous de 0,82 de ressemblance, l'opération est signalée dans le rapport plutôt
que appliquée au hasard. `appliquer_plan(document, plan)` rejoue un plan déjà calculé, sans
appel à Augure.

Quatre des six modèles sont en `.docx` (`charte_vie_commune`, `mandat_protection`,
`servitude_enclave`, `testament_simple_fiducie`). Les deux autres — `convention_indivision`
et `vente_immeuble_comptant` — sont en `.doc` de Word 97-2003, que `python-docx` ne lit pas :
il faut les convertir une fois avec `soffice --headless --convert-to docx`. Tant qu'ils ne le
sont pas, `db.get_acte_source` le dit explicitement.

## La base de données

`db.py` tient une base SQLite, `data/documents.db` (ignorée par git), créée et remplie au
premier accès à partir de `docs/` :

| Table | Contenu |
| --- | --- |
| `pieces` | les pièces txt de chaque dossier (`docs/dossiers_fictifs/<dossier>/txt/`) |
| `modeles` | les modèles d'actes `.docx`, `.doc` et `.pdf` (`docs/modeles/<dossier>/`) |
| `actes` | chaque acte produit par `create_acte_modifie`, avec son rapport JSON |

```bash
.venv/bin/python -m backend.db     # réimporte docs/ et affiche le contenu de la base
```

`get_pieces(dossier)` alimente le serveur ; `get_acte_source(dossier)` extrait le modèle Word
(et ses PDF annotés) dans `data/cache/` pour python-docx et Augure ; `archiver_acte` garde
chaque acte produit, que le serveur sert ensuite au téléchargement. Les actes sont aussi
écrits dans `out/actes_modifies/`, comme avant.

## Essayer de bout en bout

```bash
.venv/bin/python -m backend.cli acte --dossier mandat_protection --types nullité inaptitude
.venv/bin/python -m backend.cli contradictions --dossier mandat_protection
.venv/bin/python -m backend.cli consequences --dossier mandat_protection --types nullité inaptitude
.venv/bin/python -m backend.cli sources "homologation du mandat de protection"
```

Les sorties sont déposées dans `out/demo/`. Les pièces du dossier ne sont jamais lues ici :
c'est Augure qui les lit.