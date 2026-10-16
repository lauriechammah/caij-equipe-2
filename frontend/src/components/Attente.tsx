import { useEffect, useState } from "react";
import logo from "../assets/logo-anglesvivants.png";

/** « 75 » → « 1 min 15 s ». */
function duree(secondes: number) {
  const min = Math.floor(secondes / 60);
  const s = secondes % 60;
  return min ? `${min} min ${String(s).padStart(2, "0")} s` : `${s} s`;
}

/**
 * Écran de chargement d'une étape : le symbole AnglesVivants dans un anneau qui tourne,
 * le message de l'étape et le temps écoulé (les étapes durent plusieurs minutes).
 */
export function Attente({ message, debut }: { message: string; debut?: number }) {
  const [maintenant, setMaintenant] = useState(() => Date.now());

  useEffect(() => {
    const minuterie = window.setInterval(() => setMaintenant(Date.now()), 1000);
    return () => window.clearInterval(minuterie);
  }, []);

  const ecoule = debut ? Math.max(0, Math.floor((maintenant - debut) / 1000)) : 0;

  return (
    <div className="attente" role="status" aria-live="polite">
      <div className="attente__cercle">
        <svg className="attente__anneau" viewBox="0 0 120 120" aria-hidden="true">
          <circle className="attente__piste" cx="60" cy="60" r="56" />
          <circle className="attente__arc" cx="60" cy="60" r="56" />
        </svg>
        <span className="attente__symbole" aria-hidden="true">
          <img src={logo} alt="" />
        </span>
      </div>
      <p className="attente__message">{message}</p>
      {debut !== undefined && <p className="attente__duree">{duree(ecoule)}</p>}
    </div>
  );
}
