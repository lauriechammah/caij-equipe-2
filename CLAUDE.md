# Règles pour Claude

- Ne jamais lire ni analyser soi-même les fichiers de `docs/dossiers_fictifs/` ou `docs/modeles/` (ni avec Read, ni avec `cat`, `type`, `Get-Content`, etc.).
- Pour toute question sur un dossier ou un modèle, passer par Augure : `python scripts/augure.py --dossier <nom> [--modele] "<question>"`.
- Le backend fait de même : c'est Augure qui lit les pièces. Ne pas lire ces fichiers pour écrire ou déboguer `backend/`, et ne pas coller leur contenu dans un test. `python -m backend.essais` vérifie le backend sans clé et sans les lire.
- `python-docx` est requis : utiliser `.venv/bin/python` (`.venv/bin/pip install -r backend/requirements.txt`).
- La clé est dans `.env` (`AUGURE_API_KEY`). Ne jamais l'afficher ni la commit.
