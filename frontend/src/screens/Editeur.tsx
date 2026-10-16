import { useRef, useState, type MouseEvent } from "react";
import { acteProduit } from "../api/backend";
import type { Source } from "../api/source";
import { BoutonPrincipal, BoutonSecondaire } from "../components/Base";
import { Arborescence, BarreSuperieure, RailAugure, titreMandat } from "../components/Espace";
import { Icon } from "../components/Icon";
import { PanneauAugure } from "../components/PanneauAugure";
import type { ActeProduit, Mandat } from "../data/types";

const STYLES_BLOC = [
  { libelle: "Paragraphe", balise: "p" },
  { libelle: "Intertitre", balise: "h4" },
];

/** Applique une commande de mise en forme à la sélection courante de la page éditable. */
function commande(nom: string, valeur?: string) {
  document.execCommand(nom, false, valeur);
}

/** « 2026-10-16T15:01:47 » → « 16 oct. 2026, 15 h 01 ». */
function dateCourte(iso: string) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString("fr-CA", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

/** Éditeur d'un acte produit à l'étape 8. Les modifications restent dans la page : elles ne sont pas renvoyées au .docx. */
export function Editeur({
  mandat,
  acte,
  source,
  onQuitter,
  onAjouterPieces,
}: {
  mandat: Mandat;
  acte: ActeProduit;
  source: Source;
  onQuitter: () => void;
  onAjouterPieces?: (fichiers: File[]) => Promise<void>;
}) {
  const [augure, setAugure] = useState(false);
  const [modifie, setModifie] = useState(false);
  const [version, setVersion] = useState(0);
  const [sauvegarde, setSauvegarde] = useState<string | null>(null);
  const [courant, setCourant] = useState(acte);
  const [erreur, setErreur] = useState("");
  const page = useRef<HTMLDivElement>(null);

  // Les actes du dossier, le plus récent d'abord ; à défaut, l'acte reçu.
  const actes = mandat.actes.length ? mandat.actes : [{ nom: acte.nom, creeLe: "", fichier: acte.fichier }];
  const documents = actes.map((a, i) => ({
    numero: `G${i + 1}`,
    titre: a.creeLe ? `Projet d’acte du ${dateCourte(a.creeLe)}` : "Projet d’acte",
  }));
  const selection = documents[Math.max(0, actes.findIndex((a) => a.nom === courant.nom))]?.numero;

  async function ouvrir(numero: string) {
    const choisi = actes[Number(numero.slice(1)) - 1];
    if (!choisi || choisi.nom === courant.nom || mandat.exemple) return;
    setErreur("");
    try {
      setCourant(await acteProduit(choisi.nom));
      setSauvegarde(null);
      setModifie(false);
      setVersion((v) => v + 1);
    } catch (e) {
      setErreur(`Impossible d’ouvrir cet acte : ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  function annuler() {
    if (sauvegarde !== null && page.current) {
      page.current.innerHTML = sauvegarde;
    } else {
      setVersion((v) => v + 1);
    }
    setModifie(false);
  }

  function enregistrer() {
    setSauvegarde(page.current?.innerHTML ?? null);
    setModifie(false);
  }

  function inserer(texte: string) {
    const el = page.current;
    if (!el) return;
    texte.split(/\n+/).forEach((ligne) => {
      const p = document.createElement("p");
      p.className = "page__texte";
      p.textContent = ligne.replace(/^•\s*/, "").replace(/\*\*/g, "");
      el.appendChild(p);
    });
    el.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "center" });
    setModifie(true);
  }

  // Les boutons de la barre d'outils ne doivent pas voler le focus de la page.
  const garderFocus = (e: MouseEvent) => e.preventDefault();

  return (
    <div className="espace">
      <BarreSuperieure titre={titreMandat(mandat)} onRetour={onQuitter} onBasculeAugure={() => setAugure(!augure)} />
      <div className="zones">
        <Arborescence
          mandat={mandat}
          generes={documents}
          selection={selection}
          onSelection={ouvrir}
          variante="editeur"
          onAjouterPieces={onAjouterPieces}
        />

        <section className="milieu">
          <div className="outils">
            <div className="outils__document">
              <Icon nom="file" />
              <span className="outils__nom">Projet d’acte</span>
              {modifie && <span className="pastille pastille--ambre pastille--ronde">Modifié</span>}
              {courant.fichier && (
                <a className="lien-accent" href={courant.fichier} download>
                  Télécharger le .docx
                </a>
              )}
            </div>
            <div className="outils__forme" onMouseDown={garderFocus}>
              <label className="outils__style">
                <select
                  defaultValue="p"
                  onChange={(e) => commande("formatBlock", e.target.value)}
                  aria-label="Style de paragraphe"
                >
                  {STYLES_BLOC.map((s) => (
                    <option key={s.balise} value={s.balise}>
                      {s.libelle}
                    </option>
                  ))}
                </select>
                <Icon nom="chev-d-outils" />
              </label>
              <span className="outils__trait" />
              <button type="button" className="outils__bouton outils__bouton--gras" onClick={() => commande("bold")} aria-label="Gras">
                B
              </button>
              <button type="button" className="outils__bouton outils__bouton--italique" onClick={() => commande("italic")} aria-label="Italique">
                I
              </button>
              <button type="button" className="outils__bouton outils__bouton--souligne" onClick={() => commande("underline")} aria-label="Souligné">
                U
              </button>
              <span className="outils__trait" />
              <button type="button" className="outils__bouton" onClick={() => commande("insertUnorderedList")} aria-label="Liste">
                <Icon nom="list" />
              </button>
              <button type="button" className="outils__bouton" onClick={() => setAugure(true)} aria-label="Commenter avec Augure">
                <Icon nom="comment" />
              </button>
              <button type="button" className="outils__bouton" onClick={() => commande("undo")} aria-label="Annuler la dernière action">
                <Icon nom="undo" />
              </button>
            </div>
          </div>

          <div className="canevas">
            {erreur && <p className="echec">{erreur}</p>}
            <div
              key={version}
              ref={page}
              className="page"
              contentEditable
              suppressContentEditableWarning
              spellCheck
              onInput={() => setModifie(true)}
            >
              {courant.blocs.map((b, i) =>
                b.type === "titre" ? (
                  <h4 key={i} className="page__intertitre">
                    {b.texte}
                  </h4>
                ) : b.type === "texte" ? (
                  <p key={i} className="page__texte">
                    {b.texte}
                  </p>
                ) : (
                  <div key={i} className="discuter" contentEditable={false}>
                    <span className="discuter__etiquette">
                      <Icon nom="sparkle-note" />À REVOIR
                    </span>
                    <p contentEditable suppressContentEditableWarning>
                      {b.texte}
                    </p>
                    <p className="discuter__note">{b.note}</p>
                  </div>
                ),
              )}
            </div>
          </div>

          <footer className="actions actions--debut">
            <BoutonSecondaire onClick={annuler}>{augure ? "Annuler" : "Annuler les modifications"}</BoutonSecondaire>
            <BoutonPrincipal onClick={enregistrer}>
              <Icon nom="save" />
              Enregistrer
            </BoutonPrincipal>
          </footer>
        </section>

        {augure ? (
          <PanneauAugure
            source={source}
            contexte={`Mandat : ${titreMandat(mandat)}. Document ouvert : projet d’acte.\n${page.current?.innerText ?? ""}`}
            onFermer={() => setAugure(false)}
            onInserer={inserer}
          />
        ) : (
          <RailAugure onOuvrir={() => setAugure(true)} />
        )}
      </div>
    </div>
  );
}
