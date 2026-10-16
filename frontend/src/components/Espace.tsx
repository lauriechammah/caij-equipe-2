import { useState, type ReactNode } from "react";
import type { Fichier, Mandat } from "../data/types";
import { Badge } from "./Base";
import { Icon, type NomIcone } from "./Icon";
import { useAjoutPieces } from "./Televersement";

/** « Benoit / Morin, charte de vie commune » ; le type d'acte seul tant que les clients sont inconnus. */
export function titreMandat(mandat: Mandat) {
  return mandat.titre && mandat.titre !== mandat.typeActe
    ? `${mandat.titre}, ${mandat.typeActe.charAt(0).toLowerCase()}${mandat.typeActe.slice(1)}`
    : mandat.typeActe;
}

/** Barre supérieure de l'espace de travail. */
export function BarreSuperieure({
  titre,
  onRetour,
  onBasculeAugure,
}: {
  titre: string;
  onRetour: () => void;
  onBasculeAugure: () => void;
}) {
  return (
    <header className="barre">
      <div className="barre__gauche">
        <button type="button" className="barre__retour" onClick={onRetour}>
          <Icon nom="chev-l-barre" />
          Mandats
        </button>
        <span className="barre__separateur" />
        <h1 className="barre__titre">{titre}</h1>
      </div>
      <button type="button" className="bascule-augure" onClick={onBasculeAugure}>
        <Icon nom="sparkle-bascule" />
        Demander à Augure AI
      </button>
    </header>
  );
}

export function ElementFichier({
  fichier,
  selectionne,
  onClick,
}: {
  fichier: Fichier;
  selectionne?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      className={`fichier ${selectionne ? "fichier--selectionne" : ""} ${onClick ? "" : "fichier--statique"}`}
      onClick={onClick}
      aria-current={selectionne || undefined}
    >
      <Badge numero={fichier.numero} actif={selectionne} />
      <span className="fichier__titre">{fichier.titre}</span>
    </button>
  );
}

function Groupe({
  libelle,
  icone,
  accent,
  nombre,
  children,
}: {
  libelle: string;
  icone: NomIcone;
  accent?: boolean;
  nombre: number;
  children: ReactNode;
}) {
  const [ouvert, setOuvert] = useState(true);
  return (
    <section className="groupe">
      <button type="button" className="groupe__entete" onClick={() => setOuvert(!ouvert)} aria-expanded={ouvert}>
        <Icon nom="chev-d-arbo" className={ouvert ? "" : "icone--fermee"} />
        <Icon nom={icone} />
        <span className={`groupe__libelle ${accent ? "groupe__libelle--accent" : ""}`}>{libelle}</span>
        <span className="groupe__nombre">{nombre}</span>
      </button>
      {ouvert && <div className="groupe__liste">{children}</div>}
    </section>
  );
}

/** Zone gauche : arborescence du dossier. */
export function Arborescence({
  generes,
  selection,
  onSelection,
  variante = "pipeline",
  mandat,
  onAjouterPieces,
}: {
  mandat: Mandat;
  generes: Fichier[];
  selection?: string;
  onSelection?: (numero: string) => void;
  variante?: "pipeline" | "editeur";
  /** Téléverse des pièces dans le dossier (absent pour le mandat d'exemple). */
  onAjouterPieces?: (fichiers: File[]) => Promise<void>;
}) {
  const ajout = useAjoutPieces(onAjouterPieces);
  return (
    <aside className="arbo">
      <div className="arbo__entete">
        <h2>Dossier</h2>
        {variante === "pipeline" ? (
          ajout.bouton("lien-accent", "+ Ajouter")
        ) : (
          <button type="button" className="arbo__plus" aria-label="Plus d’options">
            <Icon nom="more" />
          </button>
        )}
      </div>
      {ajout.message}

      <Groupe libelle="PIÈCES DU DOSSIER" icone="folder-arbo" nombre={mandat.pieces.length}>
        {mandat.pieces.map((p) => (
          <ElementFichier key={`${p.numero}-${p.titre}`} fichier={p} />
        ))}
      </Groupe>

      <Groupe libelle="MODÈLE" icone="folder-arbo" nombre={mandat.modele ? 1 : 0}>
        {mandat.modele && <ElementFichier fichier={mandat.modele} />}
      </Groupe>

      <div className="arbo__trait" />

      <Groupe libelle="DOCUMENTS GÉNÉRÉS" icone="sparkle-arbo" accent nombre={generes.length}>
        {generes.map((g) => (
          <ElementFichier
            key={g.numero}
            fichier={g}
            selectionne={g.numero === selection}
            onClick={onSelection ? () => onSelection(g.numero) : undefined}
          />
        ))}
      </Groupe>

      {variante === "editeur" && onAjouterPieces && (
        <>
          <div className="arbo__espace" />
          {ajout.bouton(
            "arbo__ajouter",
            <>
              <Icon nom="plus" />
              Ajouter des pièces
            </>,
          )}
        </>
      )}
    </aside>
  );
}

/** Zone droite fermée : bouton d'ouverture d'Augure. */
export function RailAugure({ onOuvrir }: { onOuvrir: () => void }) {
  return (
    <aside className="rail">
      <button type="button" className="rail__bouton" onClick={onOuvrir} aria-label="Ouvrir Augure AI">
        <Icon nom="sparkle-rail" />
      </button>
      <span className="rail__libelle">Augure</span>
    </aside>
  );
}
