# Backend

Le même backend que les scripts de `scripts/`, mais en fonctions : on donne un prompt à
Augure ou au Compagnon, on reçoit du JSON ; on donne un dossier, on reçoit l'acte.

```bash
python -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
cp .env.example .env          # puis AUGURE_API_KEY
.venv/bin/python -m backend.essais      # 41 vérifications, sans clé ni appel réseau
```

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

Comme l'exige le prompt : le texte du modèle n'est jamais supprimé ni reformulé.

- chaque **ajout** est **rouge** et en révision suivie : Word l'affiche comme une insertion,
  avec l'auteur « Assistant CAIJ — équipe 2 » ;
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

`db.py` est un squelette : le document de départ est cherché dans `docs/modeles/<dossier>/`
et les actes écrits dans `out/actes_modifies/`. Quand la base existera, il n'y aura qu'à
réécrire `get_acte_source` et `lister_dossiers` ; le reste du backend n'appelle que ces deux
fonctions.

## Essayer de bout en bout

```bash
.venv/bin/python -m backend.cli acte --dossier mandat_protection --types nullité inaptitude
.venv/bin/python -m backend.cli contradictions --dossier mandat_protection
.venv/bin/python -m backend.cli consequences --dossier mandat_protection --types nullité inaptitude
.venv/bin/python -m backend.cli sources "homologation du mandat de protection"
```

Les sorties sont déposées dans `out/demo/`. Les pièces du dossier ne sont jamais lues ici :
c'est Augure qui les lit.