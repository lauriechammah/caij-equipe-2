# Backend

Le même backend que les scripts de `scripts/`, mais en fonctions : on donne un prompt à
Augure ou au Compagnon, on reçoit du JSON ; on donne un dossier, on reçoit l'acte.

```bash
python -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
cp .env.example .env          # puis AUGURE_API_KEY
.venv/bin/python -m backend.essais      # 29 vérifications, sans clé ni appel réseau
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

```python
from backend import get_contradictions, get_type_consequences, create_acte_modifie

rapport = get_contradictions(demandes_clients, commentaires, synthese, elements_factuels)
consequences = get_type_consequences(
    demandes_clients, commentaires, types_possibles, synthese, elements_factuels)
chemin = create_acte_modifie(
    synthese, demandes_clients, commentaires, elements_factuels, consequences, commentaires)
```

| Méthode | Renvoie |
| --- | --- |
| `get_contradictions` | le rapport en JSON, **une chaîne** : `contradictions`, `information_manquante`, `questions_prioritaires`, `elements_a_verifier` |
| `get_type_consequences` | la **liste** des conséquences retenues, chacune avec sa source et son url |
| `create_acte_modifie` | le **chemin** du fichier Word produit |

`get_type_consequences` interroge le Compagnon avant Augure : une conséquence sans passage
dans les sources revient avec une url vide plutôt qu'avec une référence inventée.

## Le document produit

`create_acte_modifie` fait proposer à Augure un plan (`annotation`, `ajout`, `remplacement`,
`suppression`, chacun avec son ancre citation exacte du modèle), puis **le code** l'applique.
Rien n'est jamais modifié en silence.

- les **ajouts** sont des révisions suivies : Word les affiche comme des insertions, avec
  l'auteur « Assistant CAIJ — équipe 2 » ; les suppressions et remplacements aussi ;
- les passages à vérifier sont **surlignés** (jaune, vert, cyan, rose ou rouge) et portent un
  **commentaire Word** ;
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
.venv/bin/python -m backend.cli contradictions --dossier mandat_protection
.venv/bin/python -m backend.cli consequences --dossier mandat_protection --types nullité inaptitude
.venv/bin/python -m backend.cli acte --dossier mandat_protection
.venv/bin/python -m backend.cli sources "homologation du mandat de protection"
```

Les sorties sont déposées dans `out/demo/`. Les pièces du dossier ne sont jamais lues ici :
c'est Augure qui les lit.