"""Backend du défi 2 : de la pièce du dossier au projet d'acte annoté.

    from backend import get_contradictions, get_type_consequences, create_acte_modifie

- ``get_contradictions`` : ce qui se contredit dans le dossier, ce qui manque.
- ``get_type_consequences`` : les conséquences discutables, ancrées dans les sources du CAIJ.
- ``create_acte_modifie`` : le projet d'acte Word, surligné, commenté, avec les
  ajouts en révision suivie.
"""

from backend.acte import appliquer_plan, create_acte_modifie, texte_document
from backend.analyse import (
    get_contradictions,
    get_type_consequences,
    resume_droit_applicable,
)
from backend.llm import ErreurLLM, ask_augure, ask_compagnon

__all__ = [
    "get_contradictions",
    "get_type_consequences",
    "resume_droit_applicable",
    "create_acte_modifie",
    "appliquer_plan",
    "texte_document",
    "ask_augure",
    "ask_compagnon",
    "ErreurLLM",
]