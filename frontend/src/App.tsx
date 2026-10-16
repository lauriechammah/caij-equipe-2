import { useState } from "react";
import { flushSync } from "react-dom";
import { Ouverture } from "./components/Ouverture";
import { Accueil } from "./screens/Accueil";
import { Editeur } from "./screens/Editeur";
import { Pipeline } from "./screens/Pipeline";

type Ecran = "accueil" | "pipeline" | "editeur";

/** Phase de l'écran d'ouverture affiché au chargement. */
export type PhaseOuverture = "logo" | "sortie" | "finie";

/** Ordre des écrans : décide du sens du glissement (vers l'avant ou vers l'arrière). */
const ORDRE: Record<Ecran, number> = { accueil: 0, pipeline: 1, editeur: 2 };

export function App() {
  const [ecran, setEcran] = useState<Ecran>("accueil");
  const [ouverture, setOuverture] = useState<PhaseOuverture>("logo");

  /** Change d'écran avec une transition animée quand le navigateur prend en charge les View Transitions. */
  function naviguer(suivant: Ecran) {
    if (!document.startViewTransition || document.hidden) {
      setEcran(suivant);
      return;
    }
    const racine = document.documentElement;
    racine.dataset.sens = ORDRE[suivant] < ORDRE[ecran] ? "arriere" : "avant";
    const transition = document.startViewTransition(() => flushSync(() => setEcran(suivant)));
    // Une transition sautée (onglet masqué, clic rapide) rejette `ready` : l'écran change quand même.
    transition.ready.catch(() => {});
    transition.finished.finally(() => delete racine.dataset.sens);
  }

  const accueil = () => naviguer("accueil");

  return (
    <>
      {ecran === "pipeline" && <Pipeline onQuitter={accueil} onTerminer={() => naviguer("editeur")} />}
      {ecran === "editeur" && <Editeur onQuitter={accueil} />}
      {ecran === "accueil" && (
        <Accueil ouverture={ouverture} onDemarrer={() => naviguer("pipeline")} onOuvrir={() => naviguer("editeur")} />
      )}
      {ouverture !== "finie" && (
        <Ouverture onSortie={() => setOuverture("sortie")} onFin={() => setOuverture("finie")} />
      )}
    </>
  );
}
