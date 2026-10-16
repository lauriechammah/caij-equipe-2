// Types partagés par les écrans, le backend (api/backend.ts) et le mandat d'exemple (api/exemple.ts).

export type Fichier = { numero: string; titre: string };

/** Un dossier client tel que le backend le décrit (GET /api/pipeline/dossiers). */
export type Mandat = {
  /** Nom du dossier côté backend (docs/dossiers_fictifs/<dossier>). */
  dossier: string;
  /** Noms des clients s'ils sont connus ; sinon le type d'acte. */
  titre: string;
  typeActe: string;
  /** Référence du modèle (« Famille, Doc. 11.1 »). */
  reference: string;
  /** Dossier fictif dont le mandat reprend le modèle d'acte (lui-même pour un dossier fictif). */
  modeleActe: string;
  pieces: Fichier[];
  modele: Fichier | null;
  /** Sans modèle .docx, l'étape 8 ne peut pas produire l'acte. */
  modeleWord: boolean;
  /** Actes déjà produits, le plus récent d'abord. */
  actes: { nom: string; creeLe: string; fichier: string }[];
  /** Mandat d'exemple : contenu fixe, sans appel au backend. */
  exemple?: boolean;
};

/** Paragraphe avec, au besoin, une amorce en gras (« Union parentale : … »). */
export type Paragraphe = { amorce?: string; texte: string };

/** « coche » / « decoche » / « attente » (à confirmer avec le client). */
export type EtatCase = "coche" | "decoche" | "attente";

/** Élément d'une liste à cocher : article, fait, demande ou conséquence. */
export type Element = {
  titre: string;
  source: string;
  etat: EtatCase;
  url?: string;
  texte?: string;
  /** Conséquence complète renvoyée par le backend, rendue telle quelle à l'étape 8. */
  consequence?: unknown;
};

/** Bloc de l'acte : intertitre, paragraphe, ou passage surligné « à revoir ». */
export type BlocActe =
  | { type: "titre"; texte: string }
  | { type: "texte"; texte: string }
  | { type: "revoir"; texte: string; note: string };

/** Acte produit à l'étape 8 ; `fichier` est l'URL du .docx (vide pour l'exemple). */
export type ActeProduit = { nom: string; fichier: string; blocs: BlocActe[] };

export type SourceCitee = { numero: string; libelle: string };

export type Message =
  | { role: "user"; texte: string }
  | {
      role: "assistant";
      texte: string;
      puces?: { amorce: string; texte: string }[];
      sources?: SourceCitee[];
      enCours?: boolean;
    };
