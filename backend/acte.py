"""Écrire l'acte : modifier le modèle Word en annotant et en traçant les changements.

    chemin = create_acte_modifie(synthese, demandes_clients, commentaires,
                                 elements_factuels, consequences, commentaires_consequences)

Le modèle propose un plan de modifications ; c'est le code qui l'applique, pour
que le résultat soit reproductible et que rien ne soit appliqué en silence.

Dans le document produit, le modèle est respecté à la lettre :

- les 3 pages liminaires du modèle (mise en garde, droits d'auteur…) sont retirées
  et ne sont jamais envoyées à Augure ;
- le texte du modèle n'est jamais modifié ni supprimé ; un remplacement ou une
  suppression proposés deviennent un passage surligné avec une note ;
- les ajouts sont des révisions suivies (Word les affiche comme des insertions,
  avec leur auteur), en rouge, dans la police et la taille du modèle ;
- les passages à vérifier sont surlignés et portent un commentaire Word ;
- une annexe reprend les questions à trancher, les conséquences et leurs urls,
  et tout ce qui n'a pas pu être appliqué.

Deux points d'entrée : ``create_acte_modifie`` (plan par Augure) et
``appliquer_plan`` (plan fourni), qui rejoue un plan déjà calculé sans appeler Augure.
"""

import json
import re
import unicodedata
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from difflib import SequenceMatcher

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import RGBColor
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from backend import db
from backend.analyse import corps_demande
from backend.llm import ask_augure

AUTEUR = "Assistant CAIJ — équipe 2"
INITIALES = "CAIJ"
LONGUEUR_NOTE = 220
COULEUR_AJOUT = RGBColor(0xC0, 0x00, 0x00)
COULEURS = {
    "jaune": WD_COLOR_INDEX.YELLOW,
    "vert": WD_COLOR_INDEX.BRIGHT_GREEN,
    "cyan": WD_COLOR_INDEX.TURQUOISE,
    "rose": WD_COLOR_INDEX.PINK,
    "rouge": WD_COLOR_INDEX.RED,
}
SEUIL_SIMILARITE = 0.82
# Pages liminaires du Répertoire (mise en garde, droits d'auteur, citation…) : jamais lues,
# jamais modifiées, absentes de l'acte produit.
PAGES_LIMINAIRES = 3
_dernier_id = [1000]


def _prochain_id():
    """Identifiant unique de révision suivie, exigé par Word."""
    _dernier_id[0] += 1
    return _dernier_id[0]


PROMPT_ACTE = """
Complète le modèle d'acte pour ce dossier à partir de toute la documentation fournie : la liste des faits, le résumé et la liste des articles du droit applicable, la liste exhaustive des demandes, les contradictions et les conséquences.
Remplis chaque section du modèle avec les informations exactes tirées des faits et des demandes. Ajoute les clauses nécessaires pour couvrir toutes les demandes du client, en respectant le droit applicable et le style du modèle. Ne modifie pas le texte existant du modèle, sauf pour le compléter. Si une clause du modèle ne semble pas s'appliquer au dossier, ne la supprime pas : signale-la.
Mets en rouge tout le texte que tu ajoutes au modèle. Surligne les passages touchés par une contradiction ou une conséquence relevée aux étapes précédentes, et ajoute à côté une courte note qui explique le problème.
N'invente aucune information. Si un renseignement nécessaire est absent ou incertain, laisse un espace à compléter, mets-le en rouge et ajoute une note. Ne règle pas les contradictions toi-même : présente-les au notaire.
"""

SCHEMA_PLAN = """
Réponds par un objet JSON exact, sans texte autour, sans commentaire :
{
  "ajouts": [
    {"apres": "phrase exacte du modèle après laquelle insérer, 10 mots ou plus",
     "texte": "la clause rédigée dans le style du modèle. Si une information manque, écris [À COMPLÉTER : ce qu'il manque] à sa place, jamais une invention.",
     "note": "d'où vient la clause, ou ce qu'il faut confirmer"}
  ],
  "surlignages": [
    {"ancre": "phrase exacte du modèle touchée par une contradiction ou une conséquence",
     "note": "courte note expliquant le problème, en une phrase",
     "origine": "contradiction | consequence", "couleur": "jaune"}
  ],
  "signalees": [
    {"clause": "citation exacte de la clause du modèle qui ne s'applique pas au dossier",
     "raison": "pourquoi elle ne s'applique pas"}
  ],
  "questions_au_client": ["les questions à poser avant de signer, dans l'ordre"],
  "resume_modifications": "en trois phrases, ce que tu as complété et pourquoi"
}
Règles : n'utilise que les faits, les demandes, le droit applicable, les contradictions et les
conséquences fournis ; les ancres sont des citations exactes du modèle, jamais des reformulations ;
une opération par point à corriger, sans doublon ; aucune suppression, aucune reformulation du
texte du modèle. "signalees" sert pour les clauses qui ne s'appliquent pas : on les signale,
on ne les retire pas.
"""


def _normaliser(texte):
    sans_accent = "".join(
        c for c in unicodedata.normalize("NFD", texte or "")
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sans_accent.lower()).strip()


def _paragraphes(document):
    """Tous les paragraphes, dans l'ordre du document, tableaux compris."""
    yield from _blocs(document.element.body, document, "corps")


def _blocs(parent, document, prefixe):
    for enfant in parent:
        balise = enfant.tag.rsplit("}", 1)[-1]
        if balise == "p":
            yield Paragraph(enfant, parent), prefixe
        elif balise == "tbl":
            table = Table(enfant, document)
            for ligne, rangee in enumerate(table.rows, 1):
                for colonne, cellule in enumerate(rangee.cells, 1):
                    yield from _blocs(cellule._tc, cellule,
                                      f"{prefixe}, tableau, ligne {ligne}, colonne {colonne}")


def _trouver(document, ancre, seuil=SEUIL_SIMILARITE):
    """Retrouve un passage : d'abord exactement, puis au plus proche."""
    cible = _normaliser(ancre)
    if not cible:
        return None, None, 0.0
    passages = list(_paragraphes(document))
    for paragraphe, ou in passages:
        texte = _normaliser(_texte(paragraphe))
        if cible and cible in texte:
            return paragraphe, ou, 1.0
    meilleur, score = None, 0.0
    for paragraphe, ou in passages:
        ratio = SequenceMatcher(None, cible, _normaliser(_texte(paragraphe))).ratio()
        if ratio > score:
            meilleur, score = (paragraphe, ou), ratio
    if meilleur and score >= seuil:
        return meilleur[0], meilleur[1], round(score, 3)
    return None, None, round(score, 3)


def _texte_run(element):
    """Texte d'un run, suppressions (w:delText) et insertions comprises."""
    morceaux = []
    for enfant in element.iterchildren():
        balise = enfant.tag.rsplit("}", 1)[-1]
        if balise in ("t", "delText"):
            morceaux.append(enfant.text or "")
        elif balise == "tab":
            morceaux.append("\t")
        elif balise in ("br", "cr"):
            morceaux.append("\n")
    return "".join(morceaux)


def _runs(paragraphe):
    """Tous les runs, y compris ceux enveloppés dans une révision suivie.

    ``paragraph.runs`` de python-docx ignore les runs placés dans un ``w:ins`` ou
    un ``w:del`` : le texte qu'on vient d'ajouter serait alors invisible à la
    recherche d'ancres comme à la relecture du document.
    """
    return [Run(r, paragraphe) for r in paragraphe._p.findall(".//" + qn("w:r"))]


def _texte(paragraphe):
    return "".join(_texte_run(run._r) for run in _runs(paragraphe))


def _enveloppe(run):
    parent = run._r.getparent()
    return parent is not None and parent.tag.rsplit("}", 1)[-1] in ("ins", "del")


def _decouper(run, debut, fin):
    """Coupe un run pour isoler ``[debut, fin)``. Ne renvoie que la partie isolée."""
    texte = _texte_run(run._r)
    supprime = run._r.getparent().tag.rsplit("}", 1)[-1] == "del"
    morceaux = [texte[:debut], texte[debut:fin], texte[fin:]]
    isole = []
    for position, morceau in enumerate(morceaux):
        if not morceau:
            continue
        element = OxmlElement("w:r")
        if run._r.rPr is not None:
            element.append(deepcopy(run._r.rPr))
        contenu = OxmlElement("w:delText" if supprime else "w:t")
        contenu.set(qn("xml:space"), "preserve")
        contenu.text = morceau
        element.append(contenu)
        run._r.addprevious(element)
        if position == 1:
            isole.append(Run(element, run._parent))
    run._r.getparent().remove(run._r)
    return isole


def _isoler(paragraphe, debut, fin):
    """Runs couvrant exactement ``[debut, fin)`` du paragraphe."""
    choisis, parcouru = [], 0
    for run in _runs(paragraphe):
        longueur = len(_texte_run(run._r))
        suivant = parcouru + longueur
        if parcouru >= debut and suivant <= fin:
            choisis.append(run)
        elif parcouru < fin and suivant > debut:
            choisis.extend(_decouper(run, debut - parcouru, min(fin, suivant) - parcouru))
        parcouru = suivant
    return choisis


def _baliser(runs, element):
    """Enveloppe des runs dans ``w:ins`` ou ``w:del`` : Word verra un changement suivi."""
    if not runs:
        return None
    restants = [r for r in runs if not _enveloppe(r)]
    if not restants:
        return None
    if element == "del":
        for run in restants:
            for texte in run._r.findall(qn("w:t")):
                supprime = OxmlElement("w:delText")
                supprime.set(qn("xml:space"), "preserve")
                supprime.text = texte.text
                run._r.replace(texte, supprime)
    enveloppe = OxmlElement("w:ins" if element == "ins" else "w:del")
    enveloppe.set(qn("w:id"), str(_prochain_id()))
    enveloppe.set(qn("w:author"), AUTEUR)
    enveloppe.set(qn("w:date"), datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    restants[-1]._r.addnext(enveloppe)
    for run in restants:
        enveloppe.append(run._r)
    return enveloppe


# --- Pages liminaires --------------------------------------------------------

def _finit_la_page(element):
    """Saut de page explicite, ou fin de section, dans cet élément du corps."""
    sauts = [b for b in element.iter(qn("w:br")) if b.get(qn("w:type")) == "page"]
    return bool(sauts) or element.find(qn("w:pPr") + "/" + qn("w:sectPr")) is not None


def _debut_de_page(elements, numero):
    """Indice du premier élément de la page ``numero`` (1 = première page), ou None.

    Les débuts de page sont ceux que Word a mémorisés au dernier enregistrement
    (w:lastRenderedPageBreak) ; à défaut, les sauts de page et de section explicites.
    """
    rendus = [i for i, el in enumerate(elements)
              if el.find(".//" + qn("w:lastRenderedPageBreak")) is not None]
    if len(rendus) >= numero - 1:
        return rendus[numero - 2]
    debuts = [i for i, el in enumerate(elements) if i and (
        el.find(".//" + qn("w:pageBreakBefore")) is not None or _finit_la_page(elements[i - 1]))]
    return debuts[numero - 2] if len(debuts) >= numero - 1 else None


def retirer_pages_liminaires(document, pages=PAGES_LIMINAIRES):
    """Retire les ``pages`` premières pages du modèle. Renvoie le nombre d'éléments retirés."""
    corps = document.element.body
    elements = [el for el in corps if el.tag != qn("w:sectPr")]
    debut = _debut_de_page(elements, pages + 1)
    for element in elements[:debut or 0]:
        corps.remove(element)
    return debut or 0


# --- Mise en forme du modèle ---------------------------------------------------

def _run_modele(paragraphe):
    """Le premier run de texte du paragraphe (élément w:r), ou None."""
    for run in paragraphe._p.iter(qn("w:r")):
        if _texte_run(run).strip():
            return run
    return None


def _est_titre(paragraphe):
    style = paragraphe._p.pPr.pStyle if paragraphe._p.pPr is not None else None
    nom = (style.val if style is not None else "").lower()
    texte = _texte(paragraphe).strip()
    return any(m in nom for m in ("titre", "title", "heading")) or (texte.isupper() and len(texte) < 90)


def reference(document):
    """Le paragraphe courant du modèle : style et format de texte les plus fréquents."""
    formats, exemples = Counter(), {}
    for paragraphe, _ in _paragraphes(document):
        run = _run_modele(paragraphe)
        if run is None or _est_titre(paragraphe):
            continue
        rpr = run.find(qn("w:rPr"))
        police = rpr.find(qn("w:rFonts")) if rpr is not None else None
        taille = rpr.find(qn("w:sz")) if rpr is not None else None
        style = paragraphe._p.pPr.pStyle if paragraphe._p.pPr is not None else None
        cle = (style.val if style is not None else "",
               police.get(qn("w:ascii")) if police is not None else "",
               taille.get(qn("w:val")) if taille is not None else "")
        formats[cle] += 1
        exemples.setdefault(cle, paragraphe)
    return exemples[formats.most_common(1)[0][0]] if formats else None


def _paragraphe_comme(document, gabarit):
    """Nouveau paragraphe (hors du corps) avec la mise en page de ``gabarit``.

    Ni saut de section, ni numérotation, ni saut de page : la structure du modèle
    ne change pas.
    """
    paragraphe = document.add_paragraph()
    paragraphe._p.getparent().remove(paragraphe._p)
    if gabarit is not None and gabarit._p.pPr is not None:
        ppr = deepcopy(gabarit._p.pPr)
        for balise in ("w:sectPr", "w:numPr", "w:pageBreakBefore"):
            for element in ppr.findall(qn(balise)):
                ppr.remove(element)
        paragraphe._p.insert(0, ppr)
    return paragraphe


def _ecrire(paragraphe, texte, gabarit=None):
    """Ajoute du texte en rouge, avec la police et la taille du run ``gabarit`` du modèle."""
    run = paragraphe.add_run(texte)
    origine = gabarit.find(qn("w:rPr")) if gabarit is not None else None
    if origine is not None:
        rpr = OxmlElement("w:rPr")
        for balise in ("w:rFonts", "w:sz", "w:szCs", "w:lang"):
            element = origine.find(qn(balise))
            if element is not None:
                rpr.append(deepcopy(element))
        run._r.insert(0, rpr)
    run.font.color.rgb = COULEUR_AJOUT
    return run


def _inserer(document, apres, texte, note=None, modele=None):
    """Ajoute une clause après le paragraphe ``apres``, en rouge et en révision suivie.

    La clause prend la mise en forme du paragraphe d'ancrage, ou celle du paragraphe
    courant du modèle (``modele``) si l'ancre est un titre.
    """
    ancre, _, _ = _trouver(document, apres)
    if ancre is None:
        return None
    gabarit = modele if _est_titre(ancre) and modele is not None else ancre
    paragraphe = _paragraphe_comme(document, gabarit)
    ancre._p.addnext(paragraphe._p)
    run = _ecrire(paragraphe, texte.strip(), _run_modele(gabarit))
    _baliser([run], "ins")
    if note:
        _commenter(document, [run], note)
        _note_en_marge(paragraphe, run, note)
    return paragraphe


def _note_en_marge(paragraphe, apres, note):
    """La courte note demandée à côté du passage, en rouge, dans la police du passage."""
    texte = " ".join(str(note).split())
    if len(texte) > LONGUEUR_NOTE:
        texte = texte[:LONGUEUR_NOTE - 1].rstrip() + "…"
    if not texte:
        return None
    run = _ecrire(paragraphe, "  [Note : " + texte + "]", apres._r if apres is not None else None)
    run.italic = True
    return run


def _commenter(document, runs, texte, suffixe=""):
    """Commentaire Word, ou simple note en rouge quand il n'y a pas de passage à ancrer."""
    if not runs or not texte:
        return None
    return document.add_comment(runs=runs, text=str(texte) + suffixe, author=AUTEUR,
                               initials=INITIALES)


def _surligner(document, ancre, note=None, couleur="jaune", signaler=False):
    """Surligne le passage et pose la note à côté. Rien n'est retiré du modèle."""
    paragraphe, _, score = _trouver(document, ancre)
    if paragraphe is None:
        return None, score
    texte = _texte(paragraphe)
    if _normaliser(ancre) in _normaliser(texte):
        debut, fin = _position_reelle(texte, ancre)
    else:
        debut, fin = 0, len(texte)
    runs = _isoler(paragraphe, debut, fin)
    if not runs:
        return None, score
    teinte = COULEURS.get("rouge" if signaler else str(couleur).lower(), WD_COLOR_INDEX.YELLOW)
    for run in runs:
        run.font.highlight_color = teinte
    if note:
        _commenter(document, runs, note, " — clause qui ne s'applique pas au dossier" if signaler else "")
        _note_en_marge(paragraphe, runs[-1], ("Ne s'applique pas : " if signaler else "") + note)
    return runs, score


def _position_reelle(texte, ancre):
    """Position du passage dans le texte d'origine, accents et espaces compris."""
    correspondance = re.search(re.escape(ancre), texte, re.I)
    if correspondance:
        return correspondance.start(), correspondance.end()
    normalise = _normaliser(ancre)
    debut = _normaliser(texte).find(normalise)
    if debut < 0:
        return 0, min(len(texte), len(ancre))
    return debut, debut + len(normalise)


def _a_la_fin(document, paragraphe):
    """Place le paragraphe à la fin du corps, avant les propriétés de la dernière section."""
    corps = document.element.body
    section = corps.find(qn("w:sectPr"))
    if section is not None:
        section.addprevious(paragraphe._p)
    else:
        corps.append(paragraphe._p)


def _annexe(document, questions, consequences, rapporter, modele=None):
    """Annexe : questions à trancher, conséquences sourcées, et ce qui n'a pas été appliqué.

    Écrite en rouge, dans la mise en forme du paragraphe courant du modèle.
    """
    corps = []
    for question in questions or []:
        corps.append(f"• {question}")
    for consequence in consequences or []:
        if not isinstance(consequence, dict):
            continue
        source = consequence.get("source") or {}
        reference = source.get("url") or "source non trouvée"
        corps.append(
            f"• [{consequence.get('type') or 'conséquence'}] {consequence.get('consequence') or ''} "
            f"— {source.get('titre') or ''} {reference}".strip()
        )
    for introuvable in rapporter.get("introuvables", []):
        corps.append(f"• [Non appliqué] {introuvable.get('type')}: « {introuvable.get('ancre') or ''} »")

    run_modele = _run_modele(modele) if modele is not None else None
    titre = _paragraphe_comme(document, modele)
    _a_la_fin(document, titre)
    run_titre = _ecrire(titre, "Annexe — points à trancher avant la signature (assisté)", run_modele)
    run_titre.bold = True
    _baliser([run_titre], "ins")
    for ligne in corps or ["• Aucune question à trancher pour l'instant."]:
        paragraphe = _paragraphe_comme(document, modele)
        _a_la_fin(document, paragraphe)
        _baliser([_ecrire(paragraphe, ligne, run_modele)], "ins")


def _operations(plan):
    """Les opérations du plan, quelle que soit sa forme.

    Le plan produit par Augure a trois clés (``ajouts``, ``surlignages``, ``signalees``) ;
    un plan écrit à la main peut aussi donner une liste ``operations`` d'objets
    ``{"type": …}``, les deux formes sont acceptées.
    """
    plan = plan or {}
    operations = []
    for surlignage in plan.get("surlignages") or []:
        operations.append({"type": "annotation", **surlignage})
    for signalee in plan.get("signalees") or []:
        operations.append({"type": "signalement", **signalee})
    for ajout in plan.get("ajouts") or []:
        operations.append({"type": "ajout", **ajout})
    for operation in plan.get("operations") or []:
        operations.append({"type": str(operation.get("type", "")).lower(), **operation})
    return operations


def appliquer_plan(document, plan):
    """Applique un plan de modifications à un document ouvert. Retourne un rapport.

    Le modèle ne propose que d'annoter, de compléter et de signaler : le texte du
    modèle n'est ni supprimé ni reformulé.
    """
    rapport = {"appliquees": [], "introuvables": [], "compteurs": {}}
    modele = reference(document)
    for operation in _operations(plan):
        genre = str(operation.get("type", "")).lower()
        ancre = operation.get("ancre") or operation.get("apres") or operation.get("cible") or ""
        detail = {"type": genre, "ancre": ancre,
                  "note": operation.get("note") or operation.get("raison") or "",
                  "origine": operation.get("origine", "")}

        if genre == "annotation":
            resultat, detail["score"] = _surligner(document, ancre, detail["note"],
                                                   operation.get("couleur", "jaune"))
        elif genre == "signalement":
            detail["ancre"] = operation.get("clause") or ancre
            resultat, detail["score"] = _surligner(document, detail["ancre"], detail["note"],
                                                   signaler=True)
        elif genre == "ajout":
            detail["score"] = 1.0
            resultat = _inserer(document, ancre, operation.get("texte", ""), detail["note"], modele)
        elif genre in ("remplacement", "suppression"):
            # Le texte du modèle n'est jamais modifié : la proposition devient une note.
            proposition = operation.get("texte", "").strip()
            suite = f" Proposition : {proposition}" if genre == "remplacement" and proposition else (
                " Suppression proposée." if genre == "suppression" else "")
            detail["note"] = (detail["note"] + suite).strip()
            resultat, detail["score"] = _surligner(document, ancre, detail["note"], "rose")
        else:
            detail["type"] = genre or "inconnue"
            rapport["introuvables"].append(detail)
            continue

        if resultat:
            rapport["appliquees"].append(detail)
        else:
            rapport["introuvables"].append(detail)

    _annexe(document, (plan or {}).get("questions_au_client"),
            (plan or {}).get("consequences_a_rappeler") or [], rapport, modele)
    rapport["compteurs"] = {
        "appliquees": len(rapport["appliquees"]),
        "introuvables": len(rapport["introuvables"]),
        "questions": len((plan or {}).get("questions_au_client") or []),
    }
    rapport["resume_modifications"] = (plan or {}).get("resume_modifications", "")
    return rapport


def _consequences_en_texte(consequences):
    if not consequences:
        return ""
    lignes = []
    for consequence in consequences:
        if isinstance(consequence, dict):
            lignes.append(
                f"- [{consequence.get('type') or ''}] {consequence.get('consequence') or ''} "
                f"(certitude : {consequence.get('certitude') or 'possible'} ; "
                f"{(consequence.get('source') or {}).get('url') or 'source à confirmer'})")
        else:
            lignes.append(f"- {consequence}")
    return "CONSÉQUENCES RELEVÉES\n" + "\n".join(lignes)


def _contradictions_en_texte(contradictions):
    if isinstance(contradictions, str):
        try:
            contradictions = json.loads(contradictions).get("contradictions", [])
        except (json.JSONDecodeError, AttributeError):
            return "CONTRADICTIONS RELEVÉES\n" + contradictions
    if not contradictions:
        return ""
    lignes = []
    for contradiction in contradictions:
        if isinstance(contradiction, dict):
            demandes = ", ".join(str(d) for d in contradiction.get("demandes_concernees") or [])
            lignes.append(
                f"- {demandes} : {contradiction.get('probleme') or ''} "
                f"(articles : {', '.join(str(a) for a in contradiction.get('articles') or []) or '—'} ; "
                f"{contradiction.get('certitude') or 'possible'})")
        else:
            lignes.append(f"- {contradiction}")
    return "CONTRADICTIONS RELEVÉES\n" + "\n".join(lignes)


def _planifier(synthese, demandes_clients, commentaires, elements_factuels,
               contradictions, consequences, commentaires_consequences,
               droit_applicable, texte_modele, model=None):
    """Demande à Augure le plan de complétion du modèle, selon le prompt de l'étape 8.

    Augure reçoit le texte du modèle Word sans ses pages liminaires : ses ancres
    sont des citations exactes du document qui sera complété.
    """
    corps = [PROMPT_ACTE.strip(),
             corps_demande(synthese, elements_factuels, demandes_clients, commentaires,
                           droit_applicable),
             _contradictions_en_texte(contradictions),
             _consequences_en_texte(consequences)]
    if commentaires_consequences:
        corps.append("COMMENTAIRES SUR LES CONSÉQUENCES\n"
                     + "\n".join(f"- {c}" for c in commentaires_consequences))
    demande = "\n\n".join(section for section in corps if section)

    demande += "\n\nTEXTE DU MODÈLE D'ACTE\n" + texte_modele[:200000]
    plan = ask_augure(demande, sortie_json=True, consignes=SCHEMA_PLAN.strip(), model=model)
    if not isinstance(plan, dict):
        plan = {"reponse_brute": plan}
    plan.setdefault("ajouts", [])
    plan.setdefault("surlignages", [])
    plan.setdefault("signalees", [])
    plan["consequences_a_rappeler"] = consequences or []
    return plan


def create_acte_modifie(synthese, demandes_clients, commentaires, elements_factuels,
                        consequences, commentaires_consequences=(), contradictions=None,
                        droit_applicable=None, dossier=None, acte_id=None,
                        sortie=None, model=None, plan=None):
    """Complète le modèle d'acte pour ce dossier. Renvoie le chemin du fichier Word.

    Les pages liminaires du modèle (``PAGES_LIMINAIRES``) ne sont ni lues ni
    reprises. Le texte du modèle n'est jamais modifié : tout ce qui est ajouté est en
    rouge, en révision suivie, dans la police et la taille du modèle ; les passages
    touchés par une contradiction ou une conséquence sont surlignés, avec une note à
    côté ; les clauses qui ne s'appliquent pas sont signalées, jamais retirées.
    Un rapport des modifications est écrit à côté, en ``.rapport.json``.

    ``plan`` : rejouer un plan déjà calculé au lieu d'en demander un nouveau.
    """
    chemin_source = db.get_acte_source(dossier, acte_id)
    document = Document(str(chemin_source))
    retirer_pages_liminaires(document)
    if plan is None:
        plan = _planifier(synthese, demandes_clients, commentaires, elements_factuels,
                          contradictions, consequences, commentaires_consequences,
                          droit_applicable, _texte_du_document(document), model)

    rapport = appliquer_plan(document, plan)
    rapport.update({
        "source": str(chemin_source),
        "cree_le": datetime.now().isoformat(timespec="seconds"),
        "auteur": AUTEUR,
        "resume_modifications": (plan or {}).get("resume_modifications", ""),
    })

    chemin = sortie or db.chemin_sortie(dossier)
    db.enregistrer(document, chemin)
    rapport["fichier"] = str(chemin)
    rapport["plan"] = plan
    chemin.with_suffix(".rapport.json").write_text(
        json.dumps(rapport, ensure_ascii=False, indent=2), encoding="utf-8")
    db.archiver_acte(chemin, dossier, rapport)
    return str(chemin)


def _texte_du_document(document):
    morceaux = [texte for paragraphe, _ in _paragraphes(document)
               if (texte := _texte(paragraphe)).strip()]
    return "\n".join(morceaux)


def texte_document(chemin):
    """Texte d'un Word, pour comparer au plan ou l'afficher."""
    return _texte_du_document(Document(str(chemin)))