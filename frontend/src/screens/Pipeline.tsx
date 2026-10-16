import { Fragment, useRef, useState } from "react";
import { demanderAugure } from "../api/augure";
import { BoutonRetour, BoutonSuivant } from "../components/Base";
import { Arborescence, BarreSuperieure, RailAugure } from "../components/Espace";
import { Icon } from "../components/Icon";
import { PanneauAugure } from "../components/PanneauAugure";
import {
  ACTE,
  ANNEXES,
  ARTICLES,
  CONSEQUENCES,
  CONTRADICTIONS,
  DEMANDES,
  ETAPES,
  FAITS,
  SYNTHESE_ARTICLES,
  SYNTHESE_DEMANDE,
  SYNTHESE_RISQUES,
  TITRE_MANDAT,
  type Element,
  type EtatCase,
  type Paragraphe,
} from "../data/mandat";

// Stepper

type EtatEtape = "termine" | "actif" | "avenir";

function EtapePipeline({
  numero,
  libelle,
  etat,
  onClick,
}: {
  numero: number;
  libelle: string;
  etat: EtatEtape;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      className={`etape etape--${etat}`}
      onClick={onClick}
      disabled={!onClick}
      aria-current={etat === "actif" ? "step" : undefined}
    >
      <span className="etape__pastille">{etat === "termine" ? <Icon nom="check-etape" /> : numero}</span>
      <span className="etape__libelle">{libelle}</span>
    </button>
  );
}

function Stepper({ actif, atteinte, onAller }: { actif: number; atteinte: number; onAller: (n: number) => void }) {
  return (
    <nav className="stepper" aria-label="Étapes du pipeline">
      {ETAPES.map((e, i) => {
        const etat: EtatEtape = e.numero === actif ? "actif" : e.numero <= atteinte ? "termine" : "avenir";
        return (
          <Fragment key={e.numero}>
            {i > 0 && <span className={`stepper__lien ${e.numero <= atteinte ? "stepper__lien--vif" : ""}`} />}
            <EtapePipeline
              numero={e.numero}
              libelle={e.libelle}
              etat={etat}
              onClick={e.numero <= atteinte && e.numero !== actif ? () => onAller(e.numero) : undefined}
            />
          </Fragment>
        );
      })}
    </nav>
  );
}

// Zone de texte modifiable (avec « Régénérer »)

function versParagraphes(texte: string): Paragraphe[] {
  return texte
    .split(/\n+/)
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => {
      const m = l.match(/^\*\*(.+?)\*\*\s*(.*)$/);
      return m ? { amorce: m[1], texte: m[2] } : { texte: l.replace(/\*\*/g, "") };
    });
}

function ZoneTexte({
  initial,
  consigne,
  titre,
  enTete,
}: {
  initial: Paragraphe[];
  consigne: string;
  titre?: string;
  enTete?: "crayon";
}) {
  const [paragraphes, setParagraphes] = useState(initial);
  const [version, setVersion] = useState(0);
  const [occupe, setOccupe] = useState(false);
  const [erreur, setErreur] = useState("");
  const corps = useRef<HTMLDivElement>(null);

  async function regenerer() {
    if (occupe) return;
    setOccupe(true);
    setErreur("");
    const actuel = corps.current?.innerText ?? "";
    try {
      const texte = await demanderAugure(
        [
          {
            role: "user",
            content:
              `${consigne}\n\nVersion actuelle :\n${actuel}\n\n` +
              "Propose une nouvelle version. Un paragraphe par ligne ; si un paragraphe a une amorce, écris-la en **gras**.",
          },
        ],
        TITRE_MANDAT,
        () => {},
      );
      if (texte.trim()) {
        setParagraphes(versParagraphes(texte));
        setVersion((v) => v + 1);
      }
    } catch {
      setErreur("Augure est injoignable : le texte actuel est conservé.");
    } finally {
      setOccupe(false);
    }
  }

  const boutonRegenerer = (
    <button type="button" className="lien-accent lien-accent--icone" onClick={regenerer} disabled={occupe}>
      <Icon nom="sparkle-petit" />
      {occupe ? "Régénération…" : "Régénérer"}
    </button>
  );

  return (
    <div className={`zone-texte ${occupe ? "zone-texte--occupe" : ""}`}>
      <div className="zone-texte__entete">
        {enTete === "crayon" ? (
          <>
            <span className="zone-texte__titre">
              <Icon nom="pencil" />
              {titre}
            </span>
            {boutonRegenerer}
          </>
        ) : (
          boutonRegenerer
        )}
      </div>
      <div
        key={version}
        ref={corps}
        className={`zone-texte__corps ${enTete === "crayon" ? "zone-texte__corps--serre" : ""}`}
        contentEditable={!occupe}
        suppressContentEditableWarning
        spellCheck
      >
        {paragraphes.map((p, i) => (
          <p key={i}>
            {p.amorce && <strong>{p.amorce} </strong>}
            {p.texte}
          </p>
        ))}
      </div>
      {erreur && <p className="zone-texte__erreur">{erreur}</p>}
    </div>
  );
}

// Listes à cocher

function Case({ etat, petite }: { etat: EtatCase; petite?: boolean }) {
  return (
    <span className={`case case--${etat} ${petite ? "case--petite" : ""}`}>
      {etat === "coche" && <Icon nom={petite ? "check-legende" : "check-case"} />}
      {etat === "attente" && <Icon nom={petite ? "clock-legende" : "clock-case"} />}
    </span>
  );
}

function ElementACocher({ element, onBascule }: { element: Element; onBascule: () => void }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={element.etat === "coche" ? true : element.etat === "attente" ? "mixed" : false}
      className={`element element--${element.etat}`}
      onClick={onBascule}
    >
      <Case etat={element.etat} />
      <span className="element__texte">
        <span className="element__titre">{element.titre}</span>
        <span className="element__source">{element.source}</span>
      </span>
      {element.etat === "attente" && <span className="pastille pastille--ambre pastille--ronde">À confirmer avec le client</span>}
    </button>
  );
}

const CYCLE: Record<EtatCase, EtatCase> = { coche: "decoche", decoche: "attente", attente: "coche" };

function ListeACocher({
  elements,
  onChange,
  troisEtats,
}: {
  elements: Element[];
  onChange: (e: Element[]) => void;
  troisEtats?: boolean;
}) {
  const tous = (etat: EtatCase) => onChange(elements.map((e) => ({ ...e, etat })));
  const basculer = (i: number) =>
    onChange(
      elements.map((e, j) =>
        j === i ? { ...e, etat: troisEtats ? CYCLE[e.etat] : e.etat === "coche" ? "decoche" : "coche" } : e,
      ),
    );

  return (
    <div className="liste">
      <div className="liste__entete">
        {troisEtats ? (
          <div className="legende">
            <span className="legende__item">
              <Case etat="coche" petite />
              Retenue
            </span>
            <Icon nom="arrow-r-legende" />
            <span className="legende__item">
              <Case etat="decoche" petite />
              Exclue
            </span>
            <Icon nom="arrow-r-legende" />
            <span className="legende__item">
              <Case etat="attente" petite />À confirmer avec le client
            </span>
          </div>
        ) : (
          <div className="liste__actions">
            <button type="button" className="lien-accent lien-accent--petit" onClick={() => tous("coche")}>
              Tout cocher
            </button>
            <button type="button" className="lien-accent lien-accent--petit" onClick={() => tous("decoche")}>
              Tout décocher
            </button>
          </div>
        )}
      </div>
      {elements.map((e, i) => (
        <ElementACocher key={e.titre} element={e} onBascule={() => basculer(i)} />
      ))}
    </div>
  );
}

// Étape 8 : projet d'acte

function ProjetActe({ onAnnexe }: { onAnnexe: (etape: number) => void }) {
  const passages = ACTE.filter((b) => b.type === "revoir").length;
  const [courant, setCourant] = useState(0);
  const refs = useRef<(HTMLDivElement | null)[]>([]);
  const annexes = useRef<HTMLDivElement>(null);

  function aller(i: number) {
    const n = (i + passages) % passages;
    setCourant(n);
    refs.current[n]?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  let indexRevoir = -1;

  return (
    <div className="acte-corps">
      <div className="passages">
        <span className="passages__compte">
          <span className="passages__pastille" />
          {passages} passages à revoir
        </span>
        <span className="passages__nav">
          <span className="passages__position">
            {courant + 1} / {passages}
          </span>
          <button type="button" className="passages__fleche" onClick={() => aller(courant - 1)} aria-label="Passage précédent">
            <Icon nom="chev-u-nav" />
          </button>
          <button type="button" className="passages__fleche" onClick={() => aller(courant + 1)} aria-label="Passage suivant">
            <Icon nom="chev-d-nav" />
          </button>
          <span className="passages__trait" />
          <button
            type="button"
            className="lien-accent lien-accent--moyen"
            onClick={() => annexes.current?.scrollIntoView({ behavior: "smooth", block: "start" })}
          >
            Annexes
          </button>
        </span>
      </div>

      <article className="acte">
        <h3 className="acte__titre">CHARTE DE VIE COMMUNE</h3>
        <p className="acte__parties">Sarah Benoit et David Morin</p>
        <p className="acte__meta">Projet du 16 octobre 2026, dossier 2026-0644</p>

        {ACTE.map((b, i) => {
          if (b.type === "titre") return <h4 key={i} className="acte__intertitre">{b.texte}</h4>;
          if (b.type === "texte")
            return (
              <p key={i} className="acte__texte" contentEditable suppressContentEditableWarning>
                {b.texte}
              </p>
            );
          const k = ++indexRevoir;
          return (
            <div
              key={i}
              ref={(el) => {
                refs.current[k] = el;
              }}
              className={`revoir ${k === courant ? "revoir--courant" : ""}`}
              onClick={() => setCourant(k)}
            >
              <p className="acte__texte" contentEditable suppressContentEditableWarning>
                {b.texte}
              </p>
              <p className="revoir__note">{b.note}</p>
            </div>
          );
        })}

        <h4 className="acte__intertitre">Annexes</h4>
        <div className="annexes" ref={annexes}>
          {ANNEXES.map((a) => (
            <button key={a.libelle} type="button" className="annexes__ligne" onClick={() => onAnnexe(a.etape)}>
              <Icon nom="chev-r-annexe" />
              {a.libelle}
            </button>
          ))}
        </div>
      </article>
    </div>
  );
}

// Écran

export function Pipeline({ onQuitter, onTerminer }: { onQuitter: () => void; onTerminer: () => void }) {
  const [actif, setActif] = useState(1);
  const [atteinte, setAtteinte] = useState(1);
  const [augure, setAugure] = useState(false);
  const [articles, setArticles] = useState(ARTICLES);
  const [faits, setFaits] = useState(FAITS);
  const [demandes, setDemandes] = useState(DEMANDES);
  const [consequences, setConsequences] = useState(CONSEQUENCES);
  // Sens du dernier changement d'étape ; nul à l'arrivée, pour ne pas animer en plus de la transition d'écran.
  const [sens, setSens] = useState<"avant" | "arriere" | null>(null);
  const contenu = useRef<HTMLDivElement>(null);

  const etape = ETAPES[actif - 1];
  const generes = ETAPES.slice(0, atteinte).map((e) => ({ numero: `G${e.numero}`, titre: e.document }));

  function aller(n: number) {
    setSens(n < actif ? "arriere" : "avant");
    setActif(n);
    setAtteinte((a) => Math.max(a, n));
    contenu.current?.scrollTo({ top: 0 });
  }

  const contexte = [
    `Mandat : ${TITRE_MANDAT}. Étape en cours : ${etape.titre}.`,
    SYNTHESE_DEMANDE.map((p) => p.texte).join("\n"),
  ].join("\n");

  return (
    <div className="espace">
      <BarreSuperieure onRetour={onQuitter} onBasculeAugure={() => setAugure(!augure)} />
      <div className="zones">
        <Arborescence
          generes={generes}
          selection={`G${actif}`}
          onSelection={(numero) => aller(Number(numero.slice(1)))}
        />

        <section className="milieu">
          <Stepper actif={actif} atteinte={atteinte} onAller={aller} />

          <div
            key={actif}
            className={`milieu__contenu ${sens ? `milieu__contenu--${sens}` : ""}`}
            ref={contenu}
          >
            <h2 className="milieu__titre">{etape.titre}</h2>

            {actif === 1 && (
              <ZoneTexte
                initial={SYNTHESE_DEMANDE}
                consigne="Rédige la synthèse de la demande des clients, à partir des pièces du dossier."
              />
            )}
            {actif === 2 && <ListeACocher elements={articles} onChange={setArticles} />}
            {actif === 3 && (
              <ZoneTexte
                initial={SYNTHESE_ARTICLES}
                consigne="Rédige la synthèse juridique des articles retenus et de leurs effets pour ce couple."
              />
            )}
            {actif === 4 && <ListeACocher elements={faits} onChange={setFaits} />}
            {actif === 5 && <ListeACocher elements={demandes} onChange={setDemandes} troisEtats />}
            {actif === 6 && (
              <ZoneTexte
                initial={CONTRADICTIONS}
                consigne="Relève les contradictions entre les pièces du dossier, en citant chaque pièce."
              />
            )}
            {actif === 7 && (
              <div className="pile">
                <ListeACocher elements={consequences} onChange={setConsequences} />
                <ZoneTexte
                  initial={SYNTHESE_RISQUES}
                  titre="Synthèse des risques"
                  enTete="crayon"
                  consigne="Rédige la synthèse des risques juridiques et relationnels de ce mandat."
                />
              </div>
            )}
            {actif === 8 && <ProjetActe onAnnexe={aller} />}
          </div>

          <footer className="actions">
            {actif === 1 ? (
              <BoutonRetour libelle="Retour" onClick={onQuitter} />
            ) : (
              <BoutonRetour libelle="Étape précédente" onClick={() => aller(actif - 1)} />
            )}
            {actif < 8 ? (
              <BoutonSuivant libelle={`Confirmer et passer à l’étape ${actif + 1}`} onClick={() => aller(actif + 1)} />
            ) : (
              <BoutonSuivant libelle="Enregistrer l’acte" onClick={onTerminer} />
            )}
          </footer>
        </section>

        {augure ? (
          <PanneauAugure contexte={contexte} onFermer={() => setAugure(false)} />
        ) : (
          <RailAugure onOuvrir={() => setAugure(true)} />
        )}
      </div>
    </div>
  );
}
