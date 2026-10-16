# Règles pour Claude

- Ne jamais lire ni analyser soi-même les fichiers de `docs/dossiers_fictifs/` ou `docs/modeles/` (ni avec Read, ni avec `cat`, `type`, `Get-Content`, etc.).
- Pour toute question sur un dossier ou un modèle, passer par Augure : `python scripts/augure.py --dossier <nom> [--modele] "<question>"`.
- La clé est dans `.env` (`AUGURE_API_KEY`). Ne jamais l'afficher ni la commit.
