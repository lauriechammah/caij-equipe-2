import { useCallback, useEffect, useState } from "react";
import { flushSync } from "react-dom";
import * as backend from "./api/backend";
import { sourceExemple } from "./api/exemple";
import type { Source } from "./api/source";
import { Ouverture } from "./components/Ouverture";
import { EXEMPLE } from "./data/exemple";
import type { ActeProduit, Mandat } from "./data/types";
import { Accueil, type ChargementDossiers } from "./screens/Accueil";
import { Editeur } from "./screens/Editeur";
import { Pipeline } from "./screens/Pipeline";

type Ecran =
  | { nom: "accueil" }
  | { nom: "pipeline"; mandat: Mandat }
  | { nom: "editeur"; mandat: Mandat; acte: ActeProduit };

/** Phase de l'écran d'ouverture affiché au chargement. */
export type PhaseOuverture = "logo" | "sortie" | "finie";

/** Ordre des écrans : décide du sens du glissement (vers l'avant ou vers l'arrière). */
const ORDRE: Record<Ecran["nom"], number> = { accueil: 0, pipeline: 1, editeur: 2 };

/** Le mandat d'exemple a du contenu fixe ; les autres passent par le backend. */
function sourcePour(mandat: Mandat): Source {
  return mandat.exemple ? sourceExemple : backend.sourceBackend(mandat.dossier);
}

export function App() {
  const [ecran, setEcran] = useState<Ecran>({ nom: "accueil" });
  const [ouverture, setOuverture] = useState<PhaseOuverture>("logo");
  const [dossiers, setDossiers] = useState<Mandat[]>([]);
  const [chargement, setChargement] = useState<ChargementDossiers>({ enCours: true, erreur: "" });

  const recharger = useCallback(async () => {
    setChargement({ enCours: true, erreur: "" });
    try {
      setDossiers(await backend.dossiers());
      setChargement({ enCours: false, erreur: "" });
    } catch (e) {
      setChargement({ enCours: false, erreur: e instanceof Error ? e.message : String(e) });
    }
  }, []);

  useEffect(() => {
    recharger();
  }, [recharger]);

  /** Change d'écran avec une transition animée quand le navigateur prend en charge les View Transitions. */
  function naviguer(suivant: Ecran) {
    if (!document.startViewTransition || document.hidden) {
      setEcran(suivant);
      return;
    }
    const racine = document.documentElement;
    racine.dataset.sens = ORDRE[suivant.nom] < ORDRE[ecran.nom] ? "arriere" : "avant";
    const transition = document.startViewTransition(() => flushSync(() => setEcran(suivant)));
    // Une transition sautée (onglet masqué, clic rapide) rejette `ready` : l'écran change quand même.
    transition.ready.catch(() => {});
    transition.finished.finally(() => delete racine.dataset.sens);
  }

  const accueil = () => {
    naviguer({ nom: "accueil" });
    recharger();
  };

  /** Un dossier créé ou complété : il remplace l'ancien dans la liste (ou s'y ajoute). */
  function mettreAJour(mandat: Mandat) {
    setDossiers((liste) =>
      liste.some((d) => d.dossier === mandat.dossier)
        ? liste.map((d) => (d.dossier === mandat.dossier ? mandat : d))
        : [...liste, mandat],
    );
  }

  /** Le dossier tel que le backend le décrit maintenant (pièces ajoutées, actes produits). */
  const aJour = (mandat: Mandat) => dossiers.find((d) => d.dossier === mandat.dossier) ?? mandat;

  /** Téléversement depuis l'espace de travail ; pas de pièces pour le mandat d'exemple. */
  const ajoutPieces = (mandat: Mandat) =>
    mandat.exemple
      ? undefined
      : async (fichiers: File[]) => mettreAJour(await backend.ajouterPieces(mandat.dossier, fichiers));

  /** Mandat terminé : son dernier acte, dans l'éditeur. */
  async function ouvrirActe(mandat: Mandat) {
    try {
      naviguer({ nom: "editeur", mandat, acte: await backend.acteProduit(mandat.actes[0].nom) });
    } catch (e) {
      setChargement({ enCours: false, erreur: e instanceof Error ? e.message : String(e) });
    }
  }

  return (
    <>
      {ecran.nom === "pipeline" && (
        <Pipeline
          key={ecran.mandat.dossier}
          mandat={aJour(ecran.mandat)}
          source={sourcePour(ecran.mandat)}
          onQuitter={accueil}
          onAjouterPieces={ajoutPieces(ecran.mandat)}
          onTerminer={(acte, titre) => {
            naviguer({ nom: "editeur", mandat: { ...ecran.mandat, titre }, acte });
            if (!ecran.mandat.exemple) recharger();
          }}
        />
      )}
      {ecran.nom === "editeur" && (
        <Editeur
          key={`${ecran.mandat.dossier}-${ecran.acte.nom}`}
          // Liste des actes à jour (rechargée après l'étape 8), noms des clients trouvés à l'étape 1.
          mandat={{ ...aJour(ecran.mandat), titre: ecran.mandat.titre }}
          acte={ecran.acte}
          source={sourcePour(ecran.mandat)}
          onQuitter={accueil}
          onAjouterPieces={ajoutPieces(ecran.mandat)}
        />
      )}
      {ecran.nom === "accueil" && (
        <Accueil
          ouverture={ouverture}
          mandats={[EXEMPLE, ...dossiers]}
          chargement={chargement}
          onRecharger={recharger}
          onDemarrer={(mandat) => naviguer({ nom: "pipeline", mandat })}
          onOuvrirActe={ouvrirActe}
          onMisAJour={mettreAJour}
        />
      )}
      {ouverture !== "finie" && (
        <Ouverture onSortie={() => setOuverture("sortie")} onFin={() => setOuverture("finie")} />
      )}
    </>
  );
}
