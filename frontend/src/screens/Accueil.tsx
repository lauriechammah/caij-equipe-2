import { useEffect, useMemo, useRef, useState } from "react";
import type { PhaseOuverture } from "../App";
import * as backend from "../api/backend";
import { Badge, BoutonPrincipal, BoutonRetour, BoutonSuivant, Logo, Pastille, type Statut } from "../components/Base";
import { Icon } from "../components/Icon";
import { useAjoutPieces, ZoneDepot } from "../components/Televersement";
import type { Mandat } from "../data/types";

type Filtre = "Tous" | "À traiter" | "Terminés";

export type ChargementDossiers = { enCours: boolean; erreur: string };

function statut(mandat: Mandat): Statut {
  return mandat.exemple ? "Exemple" : mandat.actes.length ? "Terminé" : "À traiter";
}

/** « 2026-10-16T15:01:47 » → « 16 oct. 2026, 15 h 01 ». */
function dateCourte(iso: string) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString("fr-CA", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

/** Libellé d'un dossier dans la liste du dialogue. */
function libelle(mandat: Mandat) {
  if (mandat.exemple) return `Exemple — ${mandat.titre}, ${mandat.typeActe.toLowerCase()}`;
  return `${mandat.typeActe} — docs › dossiers_fictifs › ${mandat.dossier}`;
}

function AvertissementDoc() {
  return (
    <p className="champ__avertissement">
      Ce modèle est en .doc (Word 97-2003) : les étapes 1 à 7 fonctionnent, mais l’étape 8 ne pourra pas produire
      l’acte tant qu’il n’est pas converti en .docx.
    </p>
  );
}

function CarteMandat({ mandat, onOuvrir }: { mandat: Mandat; onOuvrir: () => void }) {
  const dernier = mandat.actes[0];
  return (
    <button type="button" className="carte" onClick={onOuvrir}>
      <div className="carte__entete">
        <span className="carte__dossier">{mandat.exemple ? "exemple" : mandat.dossier}</span>
        <Pastille statut={statut(mandat)} />
      </div>
      <span className="carte__client">{mandat.titre}</span>
      <span className="carte__type">
        {mandat.exemple ? mandat.typeActe : `${mandat.pieces.length} pièces · modèle ${mandat.reference}`}
      </span>
      <span className="carte__separateur" />
      <span className="carte__pied">
        <Icon nom="clock-carte" />
        {dernier
          ? `Acte produit le ${dateCourte(dernier.creeLe)}`
          : mandat.exemple
            ? "Contenu de démonstration, sans backend"
            : "Aucun acte produit"}
      </span>
    </button>
  );
}

/** Valeur du sélecteur de dossier pour « nouveau dossier, pièces téléversées ». */
const NOUVEAU = "__nouveau__";

function DialogueNouveauMandat({
  mandats,
  initial,
  onFermer,
  onDemarrer,
  onMisAJour,
}: {
  mandats: Mandat[];
  /** Dossier présélectionné ; null pour un nouveau dossier. */
  initial: Mandat | null;
  onFermer: () => void;
  onDemarrer: (mandat: Mandat) => void;
  /** Un dossier a été créé ou a reçu des pièces : la liste de l'accueil se met à jour. */
  onMisAJour: (mandat: Mandat) => void;
}) {
  const [choisi, setChoisi] = useState<Mandat | null>(initial);
  // Modèles d'acte proposés pour un nouveau dossier : ceux des dossiers fictifs du backend.
  const modeles = mandats.filter((m) => !m.exemple && m.modeleActe === m.dossier && m.modele);
  const [titre, setTitre] = useState("");
  const [modele, setModele] = useState(modeles[0]?.dossier ?? "");
  const [fichiers, setFichiers] = useState<File[]>([]);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState("");
  const ajout = useAjoutPieces(
    choisi && !choisi.exemple
      ? async (liste) => {
          const misAJour = await backend.ajouterPieces(choisi.dossier, liste);
          setChoisi(misAJour);
          onMisAJour(misAJour);
        }
      : undefined,
  );
  const ref = useRef<HTMLDivElement>(null);
  const modeleChoisi = modeles.find((m) => m.dossier === modele);

  async function demarrer() {
    if (choisi) return onDemarrer(choisi);
    setEnvoi(true);
    setErreur("");
    try {
      const cree = await backend.creerMandat(titre.trim(), modele, fichiers);
      onMisAJour(cree);
      onDemarrer(cree);
    } catch (e) {
      setErreur(e instanceof Error ? e.message : String(e));
      setEnvoi(false);
    }
  }

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

        <label className="champ">
          <span className="champ__etiquette">DOSSIER</span>
          <span className="champ__select champ__select--icone">
            <Icon nom="folder-champ" />
            <select
              value={choisi?.dossier ?? NOUVEAU}
              onChange={(e) => setChoisi(mandats.find((m) => m.dossier === e.target.value) ?? null)}
            >
              <option value={NOUVEAU} disabled={!modeles.length}>
                + Nouveau dossier — téléverser des pièces
              </option>
              {mandats.map((m) => (
                <option key={m.dossier} value={m.dossier}>
                  {libelle(m)}
                </option>
              ))}
            </select>
            <Icon nom="chev-d-champ" />
          </span>
        </label>

        {choisi ? (
          <>
            <div className="champ champ--serre">
              <span className="champ__etiquette champ__etiquette--action">
                FICHIERS
                {ajout.bouton("lien-accent lien-accent--petit", "+ Ajouter des pièces")}
              </span>
              <div className="champ__fichiers">
                {choisi.pieces.map((p) => (
                  <div key={`${p.numero}-${p.titre}`} className="fichier fichier--statique">
                    <Badge numero={p.numero} />
                    <span className="fichier__titre">{p.titre}</span>
                  </div>
                ))}
              </div>
              {ajout.message}
            </div>

            <div className="champ">
              <span className="champ__etiquette">TYPE D’ACTE</span>
              <div className="champ__valeur">
                {choisi.typeActe}
                {choisi.reference && <span className="champ__reference"> · modèle {choisi.reference}</span>}
              </div>
              {!choisi.modeleWord && <AvertissementDoc />}
            </div>
          </>
        ) : (
          <>
            <label className="champ">
              <span className="champ__etiquette">NOM DU MANDAT</span>
              <input
                className="champ__saisie"
                value={titre}
                onChange={(e) => setTitre(e.target.value)}
                placeholder="Ex. : Tremblay / Roy"
              />
            </label>

            <label className="champ">
              <span className="champ__etiquette">TYPE D’ACTE</span>
              <span className="champ__select">
                <select value={modele} onChange={(e) => setModele(e.target.value)}>
                  {modeles.map((m) => (
                    <option key={m.dossier} value={m.dossier}>
                      {m.typeActe} · modèle {m.reference}
                    </option>
                  ))}
                </select>
                <Icon nom="chev-d-champ" />
              </span>
              {modeleChoisi && !modeleChoisi.modeleWord && <AvertissementDoc />}
            </label>

            <div className="champ champ--serre">
              <span className="champ__etiquette">PIÈCES DU DOSSIER</span>
              <ZoneDepot fichiers={fichiers} onChange={setFichiers} />
            </div>
          </>
        )}

        {erreur && <p className="echec">{erreur}</p>}

        <div className="dialogue__actions">
          <BoutonRetour libelle="Retour" onClick={onFermer} />
          <BoutonSuivant
            libelle={choisi ? "Démarrer la synthèse" : envoi ? "Envoi des pièces…" : "Créer et démarrer la synthèse"}
            onClick={demarrer}
            disabled={!choisi && (envoi || !fichiers.length || !modele)}
          />
        </div>
      </div>
    </div>
  );
}

export function Accueil({
  ouverture,
  mandats,
  chargement,
  onRecharger,
  onDemarrer,
  onOuvrirActe,
  onMisAJour,
}: {
  ouverture: PhaseOuverture;
  /** Le mandat d'exemple, puis les dossiers du backend. */
  mandats: Mandat[];
  chargement: ChargementDossiers;
  onRecharger: () => void;
  onDemarrer: (mandat: Mandat) => void;
  /** Mandat terminé : ouvrir son dernier acte dans l'éditeur. */
  onOuvrirActe: (mandat: Mandat) => void;
  /** Un dossier a été créé ou a reçu des pièces. */
  onMisAJour: (mandat: Mandat) => void;
}) {
  const [filtre, setFiltre] = useState<Filtre>("Tous");
  const [recherche, setRecherche] = useState("");
  const [dialogue, setDialogue] = useState<Mandat | null>(null);

  const visibles = useMemo(() => {
    const q = recherche.trim().toLowerCase();
    return mandats.filter(
      (m) =>
        (filtre === "Tous" || (filtre === "Terminés" ? statut(m) === "Terminé" : statut(m) !== "Terminé")) &&
        (!q || [m.titre, m.typeActe, m.dossier].some((v) => v.toLowerCase().includes(q))),
    );
  }, [mandats, filtre, recherche]);

  // Pendant l'ouverture, le logo de la barre est masqué (le logo en gros plan vient s'y poser),
  // puis le contenu entre en cascade quand le fond de l'ouverture s'efface.
  const classes = [
    "accueil",
    ouverture !== "finie" && "accueil--ouverture",
    ouverture === "sortie" && "accueil--entree",
  ]
    .filter(Boolean)
    .join(" ");

  // Par défaut, le dialogue propose le premier vrai dossier ; l'exemple s'il n'y en a pas.
  const parDefaut = mandats.find((m) => !m.exemple) ?? mandats[0];

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

        <div className="nouveau" onClick={() => parDefaut && setDialogue(parDefaut)}>
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
            {(["Tous", "À traiter", "Terminés"] as Filtre[]).map((f) => (
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

        {chargement.erreur && (
          <div className="echec">
            <p>
              Backend injoignable ({chargement.erreur}) : seuls les dossiers déjà chargés et l’exemple sont affichés.
              Lancer <code>.venv\Scripts\python -m backend.serveur</code>, puis réessayer.
            </p>
            <button type="button" className="lien-accent" onClick={onRecharger}>
              Réessayer
            </button>
          </div>
        )}

        <div className="grille">
          {visibles.map((m) => (
            <CarteMandat
              key={m.dossier}
              mandat={m}
              onOuvrir={() => (m.actes.length ? onOuvrirActe(m) : setDialogue(m))}
            />
          ))}
          {chargement.enCours && <p className="grille__vide">Chargement des dossiers…</p>}
          {!chargement.enCours && visibles.length === 0 && <p className="grille__vide">Aucun mandat ne correspond.</p>}
        </div>
      </main>

      {dialogue && (
        <DialogueNouveauMandat
          mandats={mandats}
          initial={dialogue}
          onFermer={() => setDialogue(null)}
          onDemarrer={(m) => {
            setDialogue(null);
            onDemarrer(m);
          }}
          onMisAJour={onMisAJour}
        />
      )}
    </div>
  );
}
