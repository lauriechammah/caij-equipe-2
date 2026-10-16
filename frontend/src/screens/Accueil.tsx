import { useEffect, useMemo, useRef, useState } from "react";
import type { PhaseOuverture } from "../App";
import { Logo, Pastille, BoutonRetour, BoutonSuivant, Badge, BoutonPrincipal } from "../components/Base";
import { Icon } from "../components/Icon";
import { CHEMIN_DOSSIER, MANDATS, PIECES, TYPES_ACTE, type Mandat } from "../data/mandat";

type Filtre = "Tous" | "En cours" | "Terminés";

function CarteMandat({ mandat, onOuvrir }: { mandat: Mandat; onOuvrir: () => void }) {
  return (
    <button type="button" className="carte" onClick={onOuvrir}>
      <div className="carte__entete">
        <span className="carte__dossier">{mandat.dossier}</span>
        <Pastille statut={mandat.statut} />
      </div>
      <span className="carte__client">{mandat.client}</span>
      <span className="carte__type">{mandat.type}</span>
      <span className="carte__separateur" />
      <span className="carte__pied">
        <Icon nom="clock-carte" />
        {mandat.meta}
      </span>
    </button>
  );
}

function DialogueNouveauMandat({ onFermer, onDemarrer }: { onFermer: () => void; onDemarrer: () => void }) {
  const [type, setType] = useState(TYPES_ACTE[0]);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ref.current?.focus();
    const echap = (e: KeyboardEvent) => e.key === "Escape" && onFermer();
    window.addEventListener("keydown", echap);
    return () => window.removeEventListener("keydown", echap);
  }, [onFermer]);

  return (
    <div className="voile">
      <div className="dialogue" role="dialog" aria-modal="true" aria-labelledby="titre-dialogue" tabIndex={-1} ref={ref}>
        <div className="dialogue__entete">
          <h2 id="titre-dialogue">Nouveau mandat</h2>
          <button type="button" className="dialogue__fermer" onClick={onFermer} aria-label="Fermer">
            <Icon nom="x-dialogue" />
          </button>
        </div>

        <div className="champ">
          <span className="champ__etiquette">DOSSIER</span>
          <div className="champ__dossier">
            <Icon nom="folder-champ" />
            <span className="champ__chemin">{CHEMIN_DOSSIER}</span>
            <button type="button" className="lien-accent">
              Changer
            </button>
          </div>
        </div>

        <div className="champ champ--serre">
          <span className="champ__etiquette">FICHIERS</span>
          <div className="champ__fichiers">
            {PIECES.map((p) => (
              <div key={p.numero} className="fichier fichier--statique">
                <Badge numero={p.numero} />
                <span className="fichier__titre">{p.titre}</span>
              </div>
            ))}
          </div>
        </div>

        <label className="champ">
          <span className="champ__etiquette">TYPE D’ACTE</span>
          <span className="champ__select">
            <select value={type} onChange={(e) => setType(e.target.value)}>
              {TYPES_ACTE.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
            <Icon nom="chev-d-champ" />
          </span>
        </label>

        <div className="dialogue__actions">
          <BoutonRetour libelle="Retour" onClick={onFermer} />
          <BoutonSuivant libelle="Démarrer la synthèse" onClick={onDemarrer} />
        </div>
      </div>
    </div>
  );
}

export function Accueil({
  ouverture,
  onDemarrer,
  onOuvrir,
}: {
  ouverture: PhaseOuverture;
  onDemarrer: () => void;
  onOuvrir: (m: Mandat) => void;
}) {
  const [filtre, setFiltre] = useState<Filtre>("Tous");
  const [recherche, setRecherche] = useState("");
  const [dialogue, setDialogue] = useState(false);

  const visibles = useMemo(() => {
    const q = recherche.trim().toLowerCase();
    return MANDATS.filter(
      (m) =>
        (filtre === "Tous" || (filtre === "En cours" ? m.statut === "En cours" : m.statut === "Terminé")) &&
        (!q || [m.client, m.type, m.dossier].some((v) => v.toLowerCase().includes(q))),
    );
  }, [filtre, recherche]);

  // Pendant l'ouverture, le logo de la barre est masqué (le logo en gros plan vient s'y poser),
  // puis le contenu entre en cascade quand le fond de l'ouverture s'efface.
  const classes = [
    "accueil",
    ouverture !== "finie" && "accueil--ouverture",
    ouverture === "sortie" && "accueil--entree",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes} inert={ouverture === "logo"}>
      <header className="accueil__barre">
        <Logo />
      </header>

      <main className="accueil__contenu">
        <div className="accueil__entete">
          <h1>Mes mandats</h1>
          <label className="recherche">
            <Icon nom="search" />
            <input
              type="search"
              placeholder="Rechercher"
              value={recherche}
              onChange={(e) => setRecherche(e.target.value)}
              aria-label="Rechercher un mandat"
            />
          </label>
        </div>

        <div className="nouveau" onClick={() => setDialogue(true)}>
          <span className="nouveau__icone">
            <Icon nom="folder-plus" />
          </span>
          <span className="nouveau__titre">Nouveau mandat</span>
          <BoutonPrincipal>
            <Icon nom="folder-blanc" />
            Choisir un dossier
          </BoutonPrincipal>
        </div>

        <div className="accueil__section">
          <h2>Historique des mandats</h2>
          <div className="filtres" role="tablist">
            {(["Tous", "En cours", "Terminés"] as Filtre[]).map((f) => (
              <button
                key={f}
                type="button"
                role="tab"
                aria-selected={filtre === f}
                className={`filtres__onglet ${filtre === f ? "filtres__onglet--actif" : ""}`}
                onClick={() => setFiltre(f)}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div className="grille">
          {visibles.map((m) => (
            <CarteMandat key={m.dossier} mandat={m} onOuvrir={() => onOuvrir(m)} />
          ))}
          {visibles.length === 0 && <p className="grille__vide">Aucun mandat ne correspond.</p>}
        </div>
      </main>

      {dialogue && <DialogueNouveauMandat onFermer={() => setDialogue(false)} onDemarrer={onDemarrer} />}
    </div>
  );
}
