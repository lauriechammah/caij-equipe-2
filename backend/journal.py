"""Journal du backend : ce que fait chaque étape, et combien de temps prend chaque appel.

Le serveur l'affiche dans son terminal et l'écrit dans ``out/logs/backend.log`` :

    14:02:11.204 INFO    [synthese-demande-clients #3] début : choix des articles (prompt 2)
    14:02:11.205 INFO    [synthese-demande-clients #3] Augure envoi : rosedale-1, effort medium, 52 340 car.
    14:03:02.410 INFO    [synthese-demande-clients #3] Augure 51.2 s : 1er mot à 44.0 s, 3 210 car. reçus, fin stop
    14:03:02.411 INFO    [synthese-demande-clients #3] fin : choix des articles (prompt 2) en 51.2 s
    14:03:40.022 INFO    [synthese-demande-clients #3] POST 200 en 98.7 s · Augure 3 appels 90.1 s · Compagnon 3 appels 8.2 s

Chaque ligne porte l'étape du frontend et le numéro de la requête : deux étapes lancées en
même temps restent lisibles. Jamais le texte des pièces ni la clé : des tailles, des durées
et des compteurs. ``CAIJ_LOG=DEBUG`` (variable d'environnement ou ``.env``) ajoute le premier
octet de chaque réponse et les lignes HTTP brutes du serveur.
"""

import contextvars
import itertools
import logging
import os
import sys
import threading
import time
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler

from backend.config import ROOT

FICHIER = ROOT / "out" / "logs" / "backend.log"

journal = logging.getLogger("caij")

_requete = contextvars.ContextVar("requete", default=None)
_numeros = itertools.count(1)


def nombre(n):
    """52340 → « 52 340 »."""
    return f"{n:,}".replace(",", " ")


class Requete:
    """Une requête du frontend : son étiquette, et le temps passé chez Augure et le Compagnon."""

    def __init__(self, route):
        self.etiquette = f"{route} #{next(_numeros)}"
        self.debut = time.perf_counter()
        self._verrou = threading.Lock()
        self.appels = {}

    def duree(self):
        return time.perf_counter() - self.debut

    def compter(self, service, duree):
        with self._verrou:
            n, total = self.appels.get(service, (0, 0.0))
            self.appels[service] = (n + 1, total + duree)

    def bilan(self):
        """« Augure 3 appels 90.1 s · Compagnon 3 appels 8.2 s » (temps cumulé, parallèle compris)."""
        return " · ".join(f"{service} {n} appel{'s' if n > 1 else ''} {total:.1f} s"
                          for service, (n, total) in self.appels.items())


class _Etiquette(logging.Filter):
    def filter(self, record):
        requete = _requete.get()
        record.etiquette = requete.etiquette if requete else "-"
        return True


journal.addFilter(_Etiquette())


def configurer():
    """Affiche le journal dans le terminal et l'écrit dans out/logs/backend.log (une seule fois)."""
    if journal.handlers:
        return
    niveau = getattr(logging, (os.environ.get("CAIJ_LOG") or "INFO").strip().upper(), None)
    journal.setLevel(niveau if isinstance(niveau, int) else logging.INFO)
    journal.propagate = False
    try:
        sys.stderr.reconfigure(errors="replace")  # un caractère hors de la page de code ne bloque rien
    except (AttributeError, ValueError):
        pass
    format_ = "%(asctime)s.%(msecs)03d %(levelname)-7s [%(etiquette)s] %(message)s"
    terminal = logging.StreamHandler()
    terminal.setFormatter(logging.Formatter(format_, "%H:%M:%S"))
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    fichier = RotatingFileHandler(FICHIER, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    fichier.setFormatter(logging.Formatter(format_, "%Y-%m-%d %H:%M:%S"))
    journal.addHandler(terminal)
    journal.addHandler(fichier)


@contextmanager
def requete(route):
    """Toutes les lignes écrites pendant la requête portent son étape et son numéro."""
    courante = Requete(route)
    jeton = _requete.set(courante)
    try:
        yield courante
    finally:
        _requete.reset(jeton)


def propager(fonction):
    """La même étiquette dans un thread de ThreadPoolExecutor, qui ne copie pas le contexte."""
    courante = _requete.get()

    def appel(*args, **kwargs):
        jeton = _requete.set(courante)
        try:
            return fonction(*args, **kwargs)
        finally:
            _requete.reset(jeton)

    return appel


def compter(service, duree):
    if (courante := _requete.get()) is not None:
        courante.compter(service, duree)


def _court(erreur, longueur=300):
    texte = " ".join(str(erreur).split()) or type(erreur).__name__
    return texte if len(texte) <= longueur else texte[:longueur] + "…"


@contextmanager
def chrono(libelle, service=None):
    """Début, fin et durée d'une sous-étape ; s'utilise aussi en décorateur.

    En ``with``, le dictionnaire renvoyé complète la ligne de fin (``infos["résultats"] = 30``).
    ``service`` (« Compagnon ») ajoute la durée au bilan de la requête.
    """
    infos = {}
    debut = time.perf_counter()
    journal.info("début : %s", libelle)
    try:
        yield infos
    except BaseException as erreur:
        duree = time.perf_counter() - debut
        journal.warning("échec : %s après %.1f s (%s : %s)", libelle, duree, type(erreur).__name__, _court(erreur))
        raise
    else:
        duree = time.perf_counter() - debut
        details = "".join(f", {cle} {valeur}" for cle, valeur in infos.items())
        journal.info("fin : %s en %.1f s%s", libelle, duree, details)
    finally:
        if service:
            compter(service, time.perf_counter() - debut)


class SuiviAugure:
    """Mesure un appel à Augure en streaming : envoi, premier octet, premier mot, fin.

        with SuiviAugure(charge, "52 340 car.") as suivi:
            with urlopen(...) as resp:
                suivi.entetes()
                texte = lire_flux(resp, suivi)      # appelle suivi.evenement(event)
            suivi.recu(texte)

    Le temps entre le premier octet et le premier mot est celui du raisonnement du modèle.
    """

    def __init__(self, charge, taille):
        self.modele = charge.get("model")
        self.effort = charge.get("reasoning_effort") or "par défaut"
        self.taille = taille
        self.premier_octet = self.premier_mot = None
        self.raisonnement = 0  # caractères de raisonnement, si l'API les diffuse
        self.evenements = 0
        self.fin = None
        self.usage = None
        self.texte = ""

    def __enter__(self):
        self.debut = time.perf_counter()
        journal.info("Augure envoi : %s, effort %s, %s", self.modele, self.effort, self.taille)
        return self

    def _ecoule(self):
        return time.perf_counter() - self.debut

    def entetes(self):
        self.premier_octet = self._ecoule()
        journal.debug("Augure : en-têtes reçus après %.1f s", self.premier_octet)

    def evenement(self, event):
        self.evenements += 1
        if event.get("usage"):
            self.usage = event["usage"]
        for choix in event.get("choices") or []:
            delta = choix.get("delta") or {}
            if delta.get("content") and self.premier_mot is None:
                self.premier_mot = self._ecoule()
                journal.debug("Augure : premier mot après %.1f s", self.premier_mot)
            self.raisonnement += len(delta.get("reasoning_content") or delta.get("reasoning") or "")
            self.fin = choix.get("finish_reason") or self.fin

    def recu(self, texte):
        self.texte = texte or ""

    def _jetons(self, duree):
        """Jetons lus et produits (stream_options.include_usage), et vitesse de production."""
        usage = self.usage or {}
        if not isinstance(usage, dict) or not usage.get("completion_tokens"):
            return ""
        produits = usage["completion_tokens"]
        raisonnement = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
        generation = duree - (self.premier_octet or 0)
        return (f"jetons {nombre(usage.get('prompt_tokens') or 0)} lus, {nombre(produits)} produits"
                + (f" dont {nombre(raisonnement)} de raisonnement" if raisonnement else "")
                + (f" ({produits / generation:.0f} jetons/s)" if generation > 0.5 else ""))

    def __exit__(self, type_erreur, erreur, trace):
        duree = self._ecoule()
        compter("Augure", duree)
        if erreur is not None:
            journal.warning("Augure échec après %.1f s (%s) : %s", duree, type_erreur.__name__, _court(erreur))
            return False
        details = [
            f"1er octet à {self.premier_octet:.1f} s" if self.premier_octet is not None else "",
            f"1er mot à {self.premier_mot:.1f} s" if self.premier_mot is not None else "aucun mot",
            f"{nombre(len(self.texte))} car. reçus",
            f"raisonnement {nombre(self.raisonnement)} car." if self.raisonnement else "",
            f"fin {self.fin}" if self.fin else "",
            self._jetons(duree),
        ]
        niveau = logging.WARNING if self.fin == "length" or not self.texte else logging.INFO
        journal.log(niveau, "Augure %.1f s : %s", duree, ", ".join(d for d in details if d))
        return False
