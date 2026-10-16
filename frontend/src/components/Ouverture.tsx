import { useEffect, useRef, useState, type CSSProperties } from "react";
import logo from "../assets/logo-anglesvivants.png";

/** Durée pendant laquelle le logo reste en gros plan. */
const DUREE_GROS_PLAN = 3000;
/** Vol du logo jusqu'à la barre de l'accueil. */
const DUREE_VOL = 800;
/** Laisse aussi le temps à l'entrée en cascade de l'accueil de se terminer. */
const DUREE_SORTIE = 1300;

/**
 * Écran d'ouverture : le logo en gros plan pendant 3 secondes, puis il rejoint
 * sa place dans la barre de l'accueil pendant que le fond s'efface.
 */
export function Ouverture({ onSortie, onFin }: { onSortie: () => void; onFin: () => void }) {
  const [sortie, setSortie] = useState(false);
  const marque = useRef<HTMLDivElement>(null);
  // Les rappels changent à chaque rendu de l'App : on les lit par référence
  // pour que l'effet ne soit pas relancé (ce qui annulerait l'animation).
  const rappels = useRef({ onSortie, onFin });
  rappels.current = { onSortie, onFin };

  useEffect(() => {
    let vol: Animation | undefined;
    let fin: number | undefined;

    const debutSortie = window.setTimeout(() => {
      setSortie(true);
      rappels.current.onSortie();

      const el = marque.current;
      const cible = document.querySelector(".accueil__barre .logo")?.getBoundingClientRect();
      const reduit = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (el && cible && !reduit) {
        // Si l'apparition n'est pas terminée (onglet ralenti, par exemple), on la termine pour mesurer le bon point de départ.
        el.getAnimations().forEach((a) => a.finish());
        const depart = el.getBoundingClientRect();
        const dx = cible.left - depart.left;
        const dy = cible.top - depart.top;
        vol = el.animate(
          [
            { transformOrigin: "0 0", transform: "none" },
            { transformOrigin: "0 0", transform: `translate(${dx}px, ${dy}px) scale(${cible.width / depart.width})` },
          ],
          { duration: DUREE_VOL, easing: "cubic-bezier(0.65, 0, 0.35, 1)", fill: "forwards" },
        );
      } else if (el) {
        vol = el.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 400, fill: "forwards" });
      }

      fin = window.setTimeout(() => rappels.current.onFin(), DUREE_SORTIE);
    }, DUREE_GROS_PLAN);

    return () => {
      window.clearTimeout(debutSortie);
      window.clearTimeout(fin);
      vol?.cancel();
    };
  }, []);

  return (
    <div className={`ouverture ${sortie ? "ouverture--sortie" : ""}`} aria-hidden="true">
      <div className="ouverture__fond" />
      <div className="ouverture__centre">
        <div
          ref={marque}
          className="logo ouverture__logo"
          style={{ "--logo-image": `url(${logo})` } as CSSProperties}
        >
          <img src={logo} alt="" />
        </div>
        <div className="ouverture__progression" />
      </div>
    </div>
  );
}
