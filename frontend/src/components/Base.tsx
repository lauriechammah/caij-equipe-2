import type { ReactNode } from "react";
import logo from "../assets/logo-anglesvivants.png";
import type { Statut } from "../data/mandat";
import { Icon } from "./Icon";

/** Logo AnglesVivants, recadré dans l'image fournie comme dans Figma. */
export function Logo() {
  return (
    <span className="logo" role="img" aria-label="AnglesVivants">
      <img src={logo} alt="" />
    </span>
  );
}

export function Pastille({ statut }: { statut: Statut }) {
  return <span className={`pastille ${statut === "Terminé" ? "pastille--vert" : "pastille--ambre"}`}>{statut}</span>;
}

export function Badge({ numero, actif }: { numero: string; actif?: boolean }) {
  return <span className={`badge ${actif ? "badge--actif" : ""}`}>{numero}</span>;
}

type BoutonProps = {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
};

/** Bouton plein (fond accent). */
export function BoutonPrincipal({ children, onClick, disabled, type = "button" }: BoutonProps) {
  return (
    <button type={type} className="bouton bouton--principal" onClick={onClick} disabled={disabled}>
      {children}
    </button>
  );
}

/** Bouton contour (fond blanc). */
export function BoutonSecondaire({ children, onClick, type = "button" }: BoutonProps) {
  return (
    <button type={type} className="bouton bouton--secondaire" onClick={onClick}>
      {children}
    </button>
  );
}

export function BoutonRetour({ libelle, onClick }: { libelle: string; onClick: () => void }) {
  return (
    <BoutonSecondaire onClick={onClick}>
      <Icon nom="chev-l-bouton" />
      {libelle}
    </BoutonSecondaire>
  );
}

export function BoutonSuivant({ libelle, onClick }: { libelle: string; onClick: () => void }) {
  return (
    <BoutonPrincipal onClick={onClick}>
      {libelle}
      <Icon nom="arrow-r-blanc" />
    </BoutonPrincipal>
  );
}
