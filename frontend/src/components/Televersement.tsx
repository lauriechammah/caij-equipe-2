import { useRef, useState, type DragEvent, type ReactNode } from "react";
import { FORMATS_PIECES } from "../api/backend";
import { Icon } from "./Icon";

const extensions = FORMATS_PIECES.split(",");
const accepte = (f: File) => extensions.some((e) => f.name.toLowerCase().endsWith(e));

/** Zone où déposer (ou choisir) les pièces d'un nouveau mandat ; les fichiers restent modifiables avant l'envoi. */
export function ZoneDepot({ fichiers, onChange }: { fichiers: File[]; onChange: (f: File[]) => void }) {
  const entree = useRef<HTMLInputElement>(null);
  const [survol, setSurvol] = useState(false);
  const [refuses, setRefuses] = useState<string[]>([]);

  function ajouter(liste: FileList | null) {
    const nouveaux = [...(liste ?? [])];
    setRefuses(nouveaux.filter((f) => !accepte(f)).map((f) => f.name));
    const noms = new Set(fichiers.map((f) => f.name));
    onChange([...fichiers, ...nouveaux.filter((f) => accepte(f) && !noms.has(f.name))]);
  }

  function deposer(e: DragEvent) {
    e.preventDefault();
    setSurvol(false);
    ajouter(e.dataTransfer.files);
  }

  return (
    <div className="depot-bloc">
      <div
        className={`depot ${survol ? "depot--survol" : ""}`}
        role="button"
        tabIndex={0}
        onClick={() => entree.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && entree.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setSurvol(true);
        }}
        onDragLeave={() => setSurvol(false)}
        onDrop={deposer}
      >
        <Icon nom="folder-plus" />
        <span className="depot__texte">
          Déposer les pièces du dossier ici, ou <span className="lien-accent">choisir des fichiers</span>
        </span>
        <span className="depot__formats">.txt, .md ou .docx (le texte est extrait pour Augure)</span>
        <input
          ref={entree}
          type="file"
          multiple
          accept={FORMATS_PIECES}
          hidden
          onChange={(e) => {
            ajouter(e.target.files);
            e.target.value = "";
          }}
        />
      </div>
      {refuses.length > 0 && <p className="champ__avertissement">Format non pris en charge : {refuses.join(", ")}</p>}
      {fichiers.length > 0 && (
        <ul className="depot__liste">
          {fichiers.map((f, i) => (
            <li key={f.name}>
              <span className="badge">{i}</span>
              <span className="fichier__titre">{f.name}</span>
              <button
                type="button"
                className="depot__retirer"
                onClick={() => onChange(fichiers.filter((x) => x !== f))}
                aria-label={`Retirer ${f.name}`}
              >
                <Icon nom="x-panneau" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * Ajout de pièces à un dossier existant : `bouton` ouvre le choix de fichiers et envoie aussitôt
 * les pièces au backend ; `message` dit le résultat (à placer où l'écran a la place).
 */
export function useAjoutPieces(onAjouter?: (fichiers: File[]) => Promise<void>) {
  const entree = useRef<HTMLInputElement>(null);
  const [etat, setEtat] = useState({ envoi: false, message: "", erreur: false });

  async function envoyer(liste: FileList | null) {
    const fichiers = [...(liste ?? [])];
    if (!fichiers.length || !onAjouter) return;
    setEtat({ envoi: true, message: "", erreur: false });
    try {
      await onAjouter(fichiers);
      setEtat({
        envoi: false,
        erreur: false,
        message: `${fichiers.length} pièce${fichiers.length > 1 ? "s ajoutées" : " ajoutée"} : les prochaines étapes en tiendront compte.`,
      });
    } catch (e) {
      setEtat({ envoi: false, erreur: true, message: e instanceof Error ? e.message : String(e) });
    }
  }

  const bouton = (className: string, contenu: ReactNode) =>
    onAjouter ? (
      <>
        <button type="button" className={className} onClick={() => entree.current?.click()} disabled={etat.envoi}>
          {etat.envoi ? "Envoi…" : contenu}
        </button>
        <input
          ref={entree}
          type="file"
          multiple
          accept={FORMATS_PIECES}
          hidden
          onChange={(e) => {
            envoyer(e.target.files);
            e.target.value = "";
          }}
        />
      </>
    ) : null;

  const message = etat.message ? (
    <p className={`televersement__message ${etat.erreur ? "televersement__message--erreur" : ""}`} role="status">
      {etat.message}
    </p>
  ) : null;

  return { bouton, message };
}
