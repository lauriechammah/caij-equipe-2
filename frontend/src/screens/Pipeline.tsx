import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import type { Source, Valide } from "../api/source";
import { Attente } from "../components/Attente";
import { BoutonRetour, BoutonSuivant } from "../components/Base";
import { Arborescence, BarreSuperieure, RailAugure, titreMandat } from "../components/Espace";
import { Icon } from "../components/Icon";
import { PanneauAugure } from "../components/PanneauAugure";
import { ANNEXES, ETAPES } from "../data/etapes";
import { CONVERSATION_DEMO } from "../data/exemple";
import { versParagraphes, versTexte } from "../data/texte";
import type { ActeProduit, Element, EtatCase, Mandat, Paragraphe } from "../data/types";

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
      <span className="etape__numero">{numero}</span>
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
            {i > 0 && (
              <span className={`stepper__fleche ${e.numero <= atteinte ? "stepper__fleche--vif" : ""}`} aria-hidden="true">
                →
              </span>
            )}
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

function ZoneTexte({
  initial,
  consigne,
  demander,
  titre,
  enTete,
  onTexte,
}: {
  initial: Paragraphe[];
  consigne: string;
  /** Pose une question à Augure (avec le dossier en contexte) et renvoie sa réponse. */
  demander: (question: string) => Promise<string>;
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
      const texte = await demander(
        `${consigne}\n\nVersion actuelle :\n${actuel}\n\n` +
          "Propose une nouvelle version. Un paragraphe par ligne ; si un paragraphe a une amorce, écris-la en **gras**.",
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
        <ElementACocher key={`${i}-${e.titre}`} element={e} onBascule={() => basculer(i)} />
      ))}
      {elements.length === 0 && <p className="liste__vide">Aucun élément proposé pour ce dossier.</p>}
    </div>
  );
}

// Étape 8 : projet d'acte

function ProjetActe({ acte, onAnnexe }: { acte: ActeProduit; onAnnexe: (etape: number) => void }) {
  const passages = acte.blocs.filter((b) => b.type === "revoir").length;
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
          {passages} passage{passages > 1 ? "s" : ""} à revoir
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
          {acte.fichier && (
            <>
              <a className="lien-accent lien-accent--moyen" href={acte.fichier} download>
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
        {acte.blocs.map((b, i) => {
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

        <h4 className="acte__intertitre">Documents de travail</h4>
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

// Appels au backend

/** `debut` : heure de lancement de l'appel en cours, pour afficher le temps écoulé. */
type Appel = { enCours: boolean; erreur: string; debut?: number };
const REPOS: Appel = { enCours: false, erreur: "" };
type CleAppel = "synthese" | "articles" | "faits" | "contradictions" | "consequences" | "acte";
const AUCUN_APPEL: Record<CleAppel, Appel> = {
  synthese: REPOS,
  articles: REPOS,
  faits: REPOS,
  contradictions: REPOS,
  consequences: REPOS,
  acte: REPOS,
};

/** Pendant l'appel, un message d'attente ; en cas d'échec, l'erreur et « Réessayer » ; sinon le contenu. */
function Chargement({
  appel,
  attente,
  onReessayer,
  children,
}: {
  appel: Appel;
  attente: string;
  onReessayer: () => void;
  children: ReactNode;
}) {
  if (appel.enCours) return <Attente message={attente} debut={appel.debut} />;
  return (
    <>
      {appel.erreur && (
        <div className="echec">
          <p>Le backend n’a pas pu générer cette étape : {appel.erreur}</p>
          <button type="button" className="lien-accent" onClick={onReessayer}>
            Réessayer
          </button>
        </div>
      )}
      {children}
    </>
  );
}

// Écran

export function Pipeline({
  mandat,
  source,
  onQuitter,
  onTerminer,
  onAjouterPieces,
}: {
  mandat: Mandat;
  source: Source;
  onQuitter: () => void;
  /** Téléverse des pièces dans le dossier (absent pour le mandat d'exemple). */
  onAjouterPieces?: (fichiers: File[]) => Promise<void>;
  /** « Enregistrer l'acte » : l'acte produit et les noms des clients trouvés à l'étape 1. */
  onTerminer: (acte: ActeProduit, titre: string) => void;
}) {
  const [actif, setActif] = useState(1);
  const [atteinte, setAtteinte] = useState(1);
  const [augure, setAugure] = useState(false);
  const [titre, setTitre] = useState(mandat.titre);
  const [syntdmd, setSyntdmd] = useState("");
  const [articles, setArticles] = useState<Element[]>([]);
  const [syntheseArticles, setSyntheseArticles] = useState<Paragraphe[]>([]);
  const [faits, setFaits] = useState<Element[]>([]);
  const [demandes, setDemandes] = useState<Element[]>([]);
  const [contradictions, setContradictions] = useState<Paragraphe[]>([]);
  const [contradictionsBrutes, setContradictionsBrutes] = useState<unknown[]>([]);
  const [consequences, setConsequences] = useState<Element[]>([]);
  const [risques, setRisques] = useState<Paragraphe[]>([]);
  const [acte, setActe] = useState<ActeProduit | null>(null);
  // Sens du dernier changement d'étape ; nul à l'arrivée, pour ne pas animer en plus de la transition d'écran.
  const [sens, setSens] = useState<"avant" | "arriere" | null>(null);
  const [appels, setAppels] = useState(AUCUN_APPEL);
  // Entrées du dernier appel réussi ou en cours : on ne relance pas un appel de plusieurs minutes pour rien.
  const derniers = useRef<Partial<Record<CleAppel, string>>>({});
  const contenu = useRef<HTMLDivElement>(null);

  const etape = ETAPES[actif - 1];
  const generes = ETAPES.slice(0, atteinte).map((e) => ({ numero: `G${e.numero}`, titre: e.document }));
  const mandatAffiche = { ...mandat, titre };
  // Les étapes 1, 3, 5 et 7 lancent un appel : pas de nouvel appel tant qu'un autre est en cours,
  // ce qui garantit aussi que chaque appel part des résultats de l'étape précédente.
  const bloque = [1, 3, 5, 7].includes(actif) && Object.values(appels).some((a) => a.enCours);
  const contexte = [`Mandat : ${titreMandat(mandatAffiche)}. Étape en cours : ${etape.titre}.`, syntdmd].join("\n");
  const demander = (question: string) => source.question(question, [], contexte);

  function aller(n: number) {
    setSens(n < actif ? "arriere" : "avant");
    setActif(n);
    setAtteinte((a) => Math.max(a, n));
    contenu.current?.scrollTo({ top: 0 });
  }

  async function lancer(cle: CleAppel, entrees: unknown, appel: () => Promise<void>, forcer = false) {
    const signature = JSON.stringify(entrees);
    if (!forcer && derniers.current[cle] === signature) return;
    derniers.current[cle] = signature;
    setAppels((a) => ({ ...a, [cle]: { enCours: true, erreur: "", debut: Date.now() } }));
    try {
      await appel();
      setAppels((a) => ({ ...a, [cle]: REPOS }));
    } catch (e) {
      delete derniers.current[cle];
      setAppels((a) => ({ ...a, [cle]: { enCours: false, erreur: e instanceof Error ? e.message : String(e) } }));
    }
  }

  /** Ce que le notaire a retenu aux étapes 1 à 5. */
  function valide(): Valide {
    return {
      dossier: mandat.dossier,
      syntdmd,
      articles: articles.filter((a) => a.etat === "coche"),
      synthese_droit: versTexte(syntheseArticles),
      faits: faits.filter((f) => f.etat === "coche"),
      demandes: demandes.filter((d) => d.etat !== "decoche"),
    };
  }

  const appelsEtapes = {
    synthese: (forcer = false) =>
      lancer(
        "synthese",
        mandat.dossier,
        async () => {
          const r = await source.syntheseDemande();
          setSyntdmd(r.synthese);
          if (r.titre) setTitre(r.titre);
        },
        forcer,
      ),
    articles: (forcer = false) =>
      lancer(
        "articles",
        syntdmd,
        async () => {
          const r = await source.articles(syntdmd);
          setArticles(r.articles);
          setSyntheseArticles(versParagraphes(r.synthese));
        },
        forcer,
      ),
    faits: (forcer = false) => {
      const retenus = articles.filter((a) => a.etat === "coche");
      return lancer(
        "faits",
        [syntdmd, retenus],
        async () => {
          const r = await source.faitsEtDemandes(syntdmd, retenus);
          setFaits(r.faits);
          setDemandes(r.demandes);
        },
        forcer,
      );
    },
    // Contradictions et conséquences ne dépendent que des étapes 1 à 5 : en parallèle.
    contradictions: (forcer = false) => {
      const v = valide();
      return lancer(
        "contradictions",
        v,
        async () => {
          const r = await source.contradictions(v);
          setContradictions(r.paragraphes);
          setContradictionsBrutes(r.brutes);
        },
        forcer,
      );
    },
    consequences: (forcer = false) => {
      const v = valide();
      return lancer(
        "consequences",
        v,
        async () => {
          const r = await source.consequences(v);
          setConsequences(r.consequences);
          setRisques(r.risques);
        },
        forcer,
      );
    },
    acte: (forcer = false) => {
      const v = {
        ...valide(),
        contradictions: contradictionsBrutes,
        consequences: consequences.filter((c) => c.etat === "coche"),
      };
      return lancer("acte", v, async () => setActe(await source.acte(v)), forcer);
    },
  };

  // Étape 1 : la synthèse de la demande est générée à l'arrivée.
  useEffect(() => {
    appelsEtapes.synthese();
    // Un seul appel par dossier ; `lancer` ignore le second montage du mode strict.
  }, [mandat.dossier]);

  function confirmer() {
    if (actif === 1) appelsEtapes.articles();
    if (actif === 3) appelsEtapes.faits();
    if (actif === 5) {
      appelsEtapes.contradictions();
      appelsEtapes.consequences();
    }
    if (actif === 7) appelsEtapes.acte();
    aller(actif + 1);
  }

  const reessayer = (cle: CleAppel) => () => appelsEtapes[cle](true);

  return (
    <div className="espace">
      <BarreSuperieure titre={titreMandat(mandatAffiche)} onRetour={onQuitter} onBasculeAugure={() => setAugure(!augure)} />
      <div className="zones">
        <Arborescence
          mandat={mandat}
          generes={generes}
          selection={`G${actif}`}
          onSelection={(numero) => aller(Number(numero.slice(1)))}
          onAjouterPieces={onAjouterPieces}
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
              <Chargement
                appel={appels.synthese}
                attente="Augure lit les pièces du dossier et résume la demande (quelques minutes)…"
                onReessayer={reessayer("synthese")}
              >
                <ZoneTexte
                  initial={versParagraphes(syntdmd)}
                  consigne="Rédige la synthèse de la demande des clients, à partir des pièces du dossier."
                  demander={demander}
                  onTexte={setSyntdmd}
                />
              </Chargement>
            )}
            {actif === 2 && (
              <Chargement
                appel={appels.articles}
                attente="Le Compagnon cherche les articles, puis Augure retient ceux qui s’appliquent (quelques minutes)…"
                onReessayer={reessayer("articles")}
              >
                <ListeACocher elements={articles} onChange={setArticles} />
              </Chargement>
            )}
            {actif === 3 && (
              <Chargement
                appel={appels.articles}
                attente="Augure rédige la synthèse des articles (quelques minutes)…"
                onReessayer={reessayer("articles")}
              >
                <ZoneTexte
                  initial={syntheseArticles}
                  consigne="Rédige la synthèse juridique des articles retenus et de leurs effets pour les clients."
                  demander={demander}
                  onTexte={(t) => setSyntheseArticles(versParagraphes(t))}
                />
              </Chargement>
            )}
            {actif === 4 && (
              <Chargement
                appel={appels.faits}
                attente="Augure relève les éléments factuels du dossier (quelques minutes)…"
                onReessayer={reessayer("faits")}
              >
                <ListeACocher elements={faits} onChange={setFaits} />
              </Chargement>
            )}
            {actif === 5 && (
              <Chargement
                appel={appels.faits}
                attente="Augure dresse la liste des demandes des clients (quelques minutes)…"
                onReessayer={reessayer("faits")}
              >
                <ListeACocher elements={demandes} onChange={setDemandes} troisEtats />
              </Chargement>
            )}
            {actif === 6 && (
              <Chargement
                appel={appels.contradictions}
                attente="Augure relève les contradictions (quelques minutes)…"
                onReessayer={reessayer("contradictions")}
              >
                <ZoneTexte
                  initial={contradictions}
                  consigne="Relève les contradictions entre les pièces du dossier, en citant chaque pièce."
                  demander={demander}
                />
              </Chargement>
            )}
            {actif === 7 && (
              <Chargement
                appel={appels.consequences}
                attente="Augure relève les conséquences possibles (quelques minutes)…"
                onReessayer={reessayer("consequences")}
              >
                <div className="pile">
                  <ListeACocher elements={consequences} onChange={setConsequences} />
                  <ZoneTexte
                    initial={risques}
                    titre="Synthèse des risques"
                    enTete="crayon"
                    consigne="Rédige la synthèse des risques juridiques et relationnels de ce mandat."
                    demander={demander}
                  />
                </div>
              </Chargement>
            )}
            {actif === 8 && (
              <Chargement
                appel={appels.acte}
                attente="Augure complète le modèle d’acte, puis le backend produit le Word annoté (quelques minutes)…"
                onReessayer={reessayer("acte")}
              >
                {acte && <ProjetActe acte={acte} onAnnexe={aller} />}
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
              <BoutonSuivant libelle="Enregistrer l’acte" onClick={() => acte && onTerminer(acte, titre)} disabled={!acte} />
            )}
          </footer>
        </section>

        {augure ? (
          <PanneauAugure
            source={source}
            contexte={contexte}
            initiale={mandat.exemple ? CONVERSATION_DEMO : []}
            onFermer={() => setAugure(false)}
          />
        ) : (
          <RailAugure onOuvrir={() => setAugure(true)} />
        )}
      </div>
    </div>
  );
}
