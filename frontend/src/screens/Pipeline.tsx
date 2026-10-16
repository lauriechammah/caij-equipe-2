import { Fragment, useRef, useState, type ReactNode } from "react";
import { demanderAugure } from "../api/augure";
import * as api from "../api/backend";
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
  DOSSIER_FICTIF,
  ETAPES,
  FAITS,
  SYNTHESE_ARTICLES,
  SYNTHESE_DEMANDE,
  SYNTHESE_RISQUES,
  TITRE_MANDAT,
  type BlocActe,
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

function versTexte(paragraphes: Paragraphe[]): string {
  return paragraphes.map((p) => (p.amorce ? `**${p.amorce}** ${p.texte}` : p.texte)).join("\n");
}

function ZoneTexte({
  initial,
  consigne,
  titre,
  enTete,
  onTexte,
}: {
  initial: Paragraphe[];
  consigne: string;
  titre?: string;
  enTete?: "crayon";
  /** Reçoit le texte à chaque modification ou régénération. */
  onTexte?: (texte: string) => void;
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
        onTexte?.(texte);
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
        onInput={(e) => onTexte?.(e.currentTarget.innerText)}
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

function ProjetActe({
  blocs,
  fichier,
  onAnnexe,
}: {
  blocs: BlocActe[];
  /** URL de téléchargement du .docx produit par le backend. */
  fichier: string;
  onAnnexe: (etape: number) => void;
}) {
  const passages = blocs.filter((b) => b.type === "revoir").length;
  const [courant, setCourant] = useState(0);
  const refs = useRef<(HTMLDivElement | null)[]>([]);
  const annexes = useRef<HTMLDivElement>(null);

  function aller(i: number) {
    if (!passages) return;
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
            {passages ? courant + 1 : 0} / {passages}
          </span>
          <button type="button" className="passages__fleche" onClick={() => aller(courant - 1)} aria-label="Passage précédent">
            <Icon nom="chev-u-nav" />
          </button>
          <button type="button" className="passages__fleche" onClick={() => aller(courant + 1)} aria-label="Passage suivant">
            <Icon nom="chev-d-nav" />
          </button>
          <span className="passages__trait" />
          {fichier && (
            <>
              <a className="lien-accent lien-accent--moyen" href={fichier} download>
                Télécharger le .docx
              </a>
              <span className="passages__trait" />
            </>
          )}
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

        {blocs.map((b, i) => {
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

// Appels au backend (étapes 2 à 8)

type Appel = { enCours: boolean; erreur: string };
const REPOS: Appel = { enCours: false, erreur: "" };
type CleAppel = "articles" | "faits" | "contradictions" | "consequences" | "acte";
const AUCUN_APPEL: Record<CleAppel, Appel> = {
  articles: REPOS,
  faits: REPOS,
  contradictions: REPOS,
  consequences: REPOS,
  acte: REPOS,
};

function versElements(liste: api.ElementBackend[]): Element[] {
  return liste.map((e): Element => ({ ...e, etat: e.a_confirmer ? "attente" : "coche" }));
}

/** Pendant l'appel, un message d'attente ; ensuite le contenu, précédé de l'erreur s'il y en a une. */
function Chargement({ appel, attente, children }: { appel: Appel; attente: string; children: ReactNode }) {
  if (appel.enCours) return <p className="grille__vide">{attente}</p>;
  return (
    <>
      {appel.erreur && (
        <p className="zone-texte__erreur">
          Le backend n’a pas pu générer cette étape ({appel.erreur}). Contenu de démonstration affiché.
        </p>
      )}
      {children}
    </>
  );
}

// Écran

export function Pipeline({ onQuitter, onTerminer }: { onQuitter: () => void; onTerminer: () => void }) {
  const [actif, setActif] = useState(1);
  const [atteinte, setAtteinte] = useState(1);
  const [augure, setAugure] = useState(false);
  const [syntdmd, setSyntdmd] = useState(() => versTexte(SYNTHESE_DEMANDE));
  const [articles, setArticles] = useState(ARTICLES);
  const [syntheseArticles, setSyntheseArticles] = useState(SYNTHESE_ARTICLES);
  const [faits, setFaits] = useState(FAITS);
  const [demandes, setDemandes] = useState(DEMANDES);
  const [consequences, setConsequences] = useState(CONSEQUENCES);
  // Sens du dernier changement d'étape ; nul à l'arrivée, pour ne pas animer en plus de la transition d'écran.
  const [sens, setSens] = useState<"avant" | "arriere" | null>(null);
  const [contradictions, setContradictions] = useState(CONTRADICTIONS);
  const [contradictionsBrutes, setContradictionsBrutes] = useState<unknown[]>([]);
  const [risques, setRisques] = useState(SYNTHESE_RISQUES);
  const [blocsActe, setBlocsActe] = useState<BlocActe[]>(ACTE);
  const [fichierActe, setFichierActe] = useState("");
  const [appels, setAppels] = useState(AUCUN_APPEL);
  // Entrées du dernier appel réussi : on ne relance pas un appel de plusieurs minutes pour rien.
  const derniers = useRef<Partial<Record<CleAppel, string>>>({});
  const contenu = useRef<HTMLDivElement>(null);

  const etape = ETAPES[actif - 1];
  const generes = ETAPES.slice(0, atteinte).map((e) => ({ numero: `G${e.numero}`, titre: e.document }));
  // Les étapes 1, 3, 5 et 7 lancent un appel : pas de nouvel appel tant qu'un autre est en cours,
  // ce qui garantit aussi que chaque appel part des résultats de l'étape précédente.
  const bloque = [1, 3, 5, 7].includes(actif) && Object.values(appels).some((a) => a.enCours);

  function aller(n: number) {
    setSens(n < actif ? "arriere" : "avant");
    setActif(n);
    setAtteinte((a) => Math.max(a, n));
    contenu.current?.scrollTo({ top: 0 });
  }

  async function lancer(cle: CleAppel, entrees: unknown, appel: () => Promise<void>) {
    const signature = JSON.stringify(entrees);
    if (derniers.current[cle] === signature) return;
    setAppels((a) => ({ ...a, [cle]: { enCours: true, erreur: "" } }));
    try {
      await appel();
      derniers.current[cle] = signature;
      setAppels((a) => ({ ...a, [cle]: REPOS }));
    } catch (e) {
      setAppels((a) => ({ ...a, [cle]: { enCours: false, erreur: e instanceof Error ? e.message : String(e) } }));
    }
  }

  /** Ce que le notaire a retenu aux étapes 1 à 5. */
  function valide(): api.Valide {
    return {
      dossier: DOSSIER_FICTIF,
      syntdmd,
      articles: articles.filter((a) => a.etat === "coche"),
      synthese_droit: versTexte(syntheseArticles),
      faits: faits.filter((f) => f.etat === "coche"),
      demandes: demandes.filter((d) => d.etat !== "decoche"),
    };
  }

  function confirmer() {
    if (actif === 1)
      lancer("articles", syntdmd, async () => {
        const r = await api.syntheseDemandeClients(DOSSIER_FICTIF, syntdmd);
        setArticles(versElements(r.articles));
        setSyntheseArticles(versParagraphes(r.synthese));
      });
    if (actif === 3) {
      const retenus = articles.filter((a) => a.etat === "coche");
      lancer("faits", [syntdmd, retenus], async () => {
        const r = await api.demandesEtFaits(DOSSIER_FICTIF, syntdmd, retenus);
        setFaits(versElements(r.faits));
        setDemandes(versElements(r.demandes));
      });
    }
    if (actif === 5) {
      // Contradictions et conséquences ne dépendent que des étapes 1 à 5 : en parallèle.
      const v = valide();
      lancer("contradictions", v, async () => {
        const r = await api.contradictions(v);
        setContradictions(r.paragraphes);
        setContradictionsBrutes(r.contradictions);
      });
      lancer("consequences", v, async () => {
        const r = await api.consequences(v);
        setConsequences(versElements(r.consequences));
        setRisques(r.risques);
      });
    }
    if (actif === 7) {
      const v = {
        ...valide(),
        contradictions: contradictionsBrutes,
        consequences: consequences.filter((c) => c.etat === "coche"),
      };
      lancer("acte", v, async () => {
        const r = await api.acte(v);
        setBlocsActe(r.blocs);
        setFichierActe(r.fichier);
      });
    }
    aller(actif + 1);
  }

  const contexte = [`Mandat : ${TITRE_MANDAT}. Étape en cours : ${etape.titre}.`, syntdmd].join("\n");

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
                initial={versParagraphes(syntdmd)}
                consigne="Rédige la synthèse de la demande des clients, à partir des pièces du dossier."
                onTexte={setSyntdmd}
              />
            )}
            {actif === 2 && (
              <Chargement appel={appels.articles} attente="Le Compagnon cherche les articles, puis Augure retient ceux qui s’appliquent (quelques minutes)…">
                <ListeACocher elements={articles} onChange={setArticles} />
              </Chargement>
            )}
            {actif === 3 && (
              <Chargement appel={appels.articles} attente="Augure rédige la synthèse des articles (quelques minutes)…">
                <ZoneTexte
                  initial={syntheseArticles}
                  consigne="Rédige la synthèse juridique des articles retenus et de leurs effets pour ce couple."
                  onTexte={(t) => setSyntheseArticles(versParagraphes(t))}
                />
              </Chargement>
            )}
            {actif === 4 && (
              <Chargement appel={appels.faits} attente="Augure relève les éléments factuels du dossier (quelques minutes)…">
                <ListeACocher elements={faits} onChange={setFaits} />
              </Chargement>
            )}
            {actif === 5 && (
              <Chargement appel={appels.faits} attente="Augure dresse la liste des demandes des clients (quelques minutes)…">
                <ListeACocher elements={demandes} onChange={setDemandes} troisEtats />
              </Chargement>
            )}
            {actif === 6 && (
              <Chargement appel={appels.contradictions} attente="Augure relève les contradictions (quelques minutes)…">
                <ZoneTexte
                  initial={contradictions}
                  consigne="Relève les contradictions entre les pièces du dossier, en citant chaque pièce."
                />
              </Chargement>
            )}
            {actif === 7 && (
              <Chargement appel={appels.consequences} attente="Augure relève les conséquences possibles (quelques minutes)…">
                <div className="pile">
                  <ListeACocher elements={consequences} onChange={setConsequences} />
                  <ZoneTexte
                    initial={risques}
                    titre="Synthèse des risques"
                    enTete="crayon"
                    consigne="Rédige la synthèse des risques juridiques et relationnels de ce mandat."
                  />
                </div>
              </Chargement>
            )}
            {actif === 8 && (
              <Chargement appel={appels.acte} attente="Augure complète le modèle d’acte, puis le backend produit le Word annoté (quelques minutes)…">
                <ProjetActe blocs={blocsActe} fichier={fichierActe} onAnnexe={aller} />
              </Chargement>
            )}
          </div>

          <footer className="actions">
            {actif === 1 ? (
              <BoutonRetour libelle="Retour" onClick={onQuitter} />
            ) : (
              <BoutonRetour libelle="Étape précédente" onClick={() => aller(actif - 1)} />
            )}
            {actif < 8 ? (
              <BoutonSuivant libelle={`Confirmer et passer à l’étape ${actif + 1}`} onClick={confirmer} disabled={bloque} />
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
