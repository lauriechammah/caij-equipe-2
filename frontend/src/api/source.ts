import type { ActeProduit, Element, Message, Paragraphe } from "../data/types";

/** Ce que le notaire a validé aux étapes 1 à 5, envoyé aux étapes 6 à 8. */
export type Valide = {
  dossier: string;
  syntdmd: string;
  articles: Element[];
  synthese_droit: string;
  faits: Element[];
  demandes: Element[];
};

export type ValideActe = Valide & { contradictions: unknown[]; consequences: Element[] };

/**
 * D'où viennent les contenus du parcours : le backend pour un vrai dossier
 * (api/backend.ts), du contenu fixe pour le mandat d'exemple (api/exemple.ts).
 */
export interface Source {
  /** Étape 1 : noms des clients et synthèse de la demande. */
  syntheseDemande(): Promise<{ titre: string; synthese: string }>;
  /** Étapes 2 et 3 : articles applicables et synthèse du droit applicable. */
  articles(syntdmd: string): Promise<{ articles: Element[]; synthese: string }>;
  /** Étapes 4 et 5 : éléments factuels et demandes des clients. */
  faitsEtDemandes(syntdmd: string, articles: Element[]): Promise<{ faits: Element[]; demandes: Element[] }>;
  /** Étape 6 : contradictions (brutes, pour l'étape 8, et en paragraphes). */
  contradictions(valide: Valide): Promise<{ brutes: unknown[]; paragraphes: Paragraphe[] }>;
  /** Étape 7 : conséquences possibles et synthèse des risques. */
  consequences(valide: Valide): Promise<{ consequences: Element[]; risques: Paragraphe[] }>;
  /** Étape 8 : projet d'acte. */
  acte(valide: ValideActe): Promise<ActeProduit>;
  /** Panneau Augure et « Régénérer ». `onTexte` reçoit la réponse au fil de l'eau quand c'est possible. */
  question(question: string, historique: Message[], contexte: string, onTexte?: (texte: string) => void): Promise<string>;
}
