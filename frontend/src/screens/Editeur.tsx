import { useRef, useState, type MouseEvent } from "react";
import { BoutonPrincipal, BoutonSecondaire } from "../components/Base";
import { Arborescence, BarreSuperieure, RailAugure } from "../components/Espace";
import { Icon } from "../components/Icon";
import { PanneauAugure } from "../components/PanneauAugure";
import { CHARTE_V1, DOCUMENTS_EDITEUR, TITRE_MANDAT } from "../data/mandat";

const STYLES_BLOC = [
  { libelle: "Paragraphe", balise: "p" },
  { libelle: "Intertitre", balise: "h4" },
];

/** Applique une commande de mise en forme à la sélection courante de la page éditable. */
function commande(nom: string, valeur?: string) {
  document.execCommand(nom, false, valeur);
}

export function Editeur({ onQuitter }: { onQuitter: () => void }) {
  const [augure, setAugure] = useState(false);
  const [modifie, setModifie] = useState(false);
  const [version, setVersion] = useState(0);
  const [sauvegarde, setSauvegarde] = useState<string | null>(null);
  const [selection, setSelection] = useState("G1");
  const page = useRef<HTMLDivElement>(null);

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
      <BarreSuperieure onRetour={onQuitter} onBasculeAugure={() => setAugure(!augure)} />
      <div className="zones">
        <Arborescence generes={DOCUMENTS_EDITEUR} selection={selection} onSelection={setSelection} variante="editeur" />

        <section className="milieu">
          <div className="outils">
            <div className="outils__document">
              <Icon nom="file" />
              <span className="outils__nom">Projet de charte v1</span>
              {modifie && <span className="pastille pastille--ambre pastille--ronde">Modifié</span>}
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
            <div
              key={version}
              ref={page}
              className="page"
              contentEditable
              suppressContentEditableWarning
              spellCheck
              onInput={() => setModifie(true)}
            >
              <h3 className="page__titre">CHARTE DE VIE COMMUNE</h3>
              <p className="page__parties">Sarah Benoit et David Morin</p>
              <p className="page__meta">Projet pour la rencontre du 2 novembre 2026</p>
              <div className="page__filet" contentEditable={false} />
              {CHARTE_V1.map((b, i) =>
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
                      <Icon nom="sparkle-note" />À DISCUTER
                    </span>
                    <p contentEditable suppressContentEditableWarning>
                      {b.texte}
                    </p>
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
            contexte={`Mandat : ${TITRE_MANDAT}. Document ouvert : projet de charte v1.\n${page.current?.innerText ?? ""}`}
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
