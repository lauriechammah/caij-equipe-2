import type { ActeProduit, BlocActe, Element, Fichier, Mandat, Message, Paragraphe } from "../data/types";
import type { Source, Valide, ValideActe } from "./source";

/** Élément de liste renvoyé par le backend : article, fait, demande ou conséquence. */
type ElementBackend = {
  titre: string;
  source: string;
  url?: string;
  texte?: string;
  a_confirmer?: boolean;
  consequence?: unknown;
};

type DossierBackend = {
  dossier: string;
  /** Titre saisi pour un mandat créé depuis l'écran ; vide pour un dossier fictif. */
  titre: string;
  /** Dossier fictif dont le mandat reprend le modèle d'acte. */
  modele: string;
  type_acte: string;
  reference: string;
  pieces: string[];
  modeles: { nom: string; format: string; annote: boolean }[];
  modele_word: boolean;
  actes: { nom: string; cree_le: string; fichier: string }[];
};

/**
 * Appelle le backend Python via le proxy /api/pipeline de Vite.
 * Les étapes interrogent le Compagnon et Augure : compter quelques minutes.
 */
async function appeler<T>(route: string, corps?: unknown): Promise<T> {
  // Durée de chaque appel dans la console ; le détail (Augure, Compagnon) est dans out/logs/backend.log.
  const debut = performance.now();
  console.info(`[backend] ${route} : envoi`);
  const reponse = await fetch(
    `/api/pipeline/${route}`,
    corps === undefined
      ? undefined
      : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps) },
  );
  const donnees = await reponse.json().catch(() => ({}));
  const cache = reponse.headers.get("X-Cache");
  console.info(
    `[backend] ${route} : ${reponse.status} en ${((performance.now() - debut) / 1000).toFixed(1)} s` +
      (cache ? ` (cache ${cache})` : ""),
  );
  if (!reponse.ok) throw new Error(donnees.erreur ?? `Le backend a répondu ${reponse.status}`);
  return donnees as T;
}

function versElements(liste: ElementBackend[]): Element[] {
  return liste.map((e) => ({ ...e, etat: e.a_confirmer ? "attente" : "coche" }));
}

/** « 0 - Mise en contexte et mandat » → { numero: "0", titre: "Mise en contexte et mandat" }. */
function versFichier(nom: string): Fichier {
  const m = nom.match(/^(\w+)\s*-\s*(.+)$/);
  return m ? { numero: m[1], titre: m[2] } : { numero: "•", titre: nom };
}

function versMandat(d: DossierBackend): Mandat {
  return {
    dossier: d.dossier,
    titre: d.titre || d.type_acte,
    typeActe: d.type_acte,
    reference: d.reference,
    modeleActe: d.modele,
    pieces: d.pieces.map(versFichier),
    modele: d.modeles.length ? { numero: "M", titre: `Modèle ${d.reference || d.type_acte}` } : null,
    modeleWord: d.modele_word,
    actes: d.actes.map((a) => ({ nom: a.nom, creeLe: a.cree_le, fichier: a.fichier })),
  };
}

/** Les dossiers proposés par le backend, avec leurs pièces et les actes déjà produits. */
export async function dossiers(): Promise<Mandat[]> {
  const r = await appeler<{ dossiers: DossierBackend[] }>("dossiers");
  return r.dossiers.map(versMandat);
}

/** Formats que le backend sait lire (il en extrait le texte pour Augure). */
export const FORMATS_PIECES = ".txt,.md,.docx";

/** Fichier choisi dans le navigateur → { nom, contenu en base64 }. */
function lireFichier(fichier: File): Promise<{ nom: string; contenu: string }> {
  return new Promise((resolve, reject) => {
    const lecteur = new FileReader();
    lecteur.onload = () => resolve({ nom: fichier.name, contenu: String(lecteur.result).split(",", 2)[1] ?? "" });
    lecteur.onerror = () => reject(new Error(`${fichier.name} : lecture impossible`));
    lecteur.readAsDataURL(fichier);
  });
}

/** Nouveau mandat à partir de pièces téléversées, sur le modèle d'acte d'un dossier fictif. */
export async function creerMandat(titre: string, modele: string, fichiers: File[]): Promise<Mandat> {
  const pieces = await Promise.all(fichiers.map(lireFichier));
  const r = await appeler<{ dossier: DossierBackend }>("mandats", { titre, modele, pieces });
  return versMandat(r.dossier);
}

/** Ajoute des pièces téléversées à un dossier ; renvoie le dossier à jour. */
export async function ajouterPieces(dossier: string, fichiers: File[]): Promise<Mandat> {
  const pieces = await Promise.all(fichiers.map(lireFichier));
  const r = await appeler<{ dossier: DossierBackend }>("pieces", { dossier, pieces });
  return versMandat(r.dossier);
}

/** Un acte déjà produit, pour l'éditeur. */
export function acteProduit(nom: string) {
  return appeler<ActeProduit>(`actes/${encodeURIComponent(nom)}`);
}

/** Les étapes du parcours pour un dossier du backend. */
export function sourceBackend(dossier: string): Source {
  return {
    syntheseDemande: () => appeler<{ titre: string; synthese: string }>("synthese-demande", { dossier }),

    async articles(syntdmd) {
      const r = await appeler<{ articles: ElementBackend[]; synthese: string }>("synthese-demande-clients", {
        dossier,
        syntdmd,
      });
      return { articles: versElements(r.articles), synthese: r.synthese };
    },

    async faitsEtDemandes(syntdmd, articles) {
      const r = await appeler<{ faits: ElementBackend[]; demandes: ElementBackend[] }>("demandes-et-faits", {
        dossier,
        syntdmd,
        articles,
      });
      return { faits: versElements(r.faits), demandes: versElements(r.demandes) };
    },

    async contradictions(valide: Valide) {
      const r = await appeler<{ contradictions: unknown[]; paragraphes: Paragraphe[] }>("contradictions", valide);
      return { brutes: r.contradictions, paragraphes: r.paragraphes };
    },

    async consequences(valide: Valide) {
      const r = await appeler<{ consequences: ElementBackend[]; risques: Paragraphe[] }>("consequences", valide);
      return { consequences: versElements(r.consequences), risques: r.risques };
    },

    acte: (valide: ValideActe) => appeler<{ nom: string; fichier: string; blocs: BlocActe[] }>("acte", valide),

    async question(question: string, historique: Message[], contexte: string) {
      const r = await appeler<{ reponse: string }>("question", {
        dossier,
        question,
        contexte,
        historique: historique.map((m) => ({ role: m.role, texte: m.texte })),
      });
      return r.reponse;
    },
  };
}
