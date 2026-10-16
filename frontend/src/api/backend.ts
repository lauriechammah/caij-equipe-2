/** Élément de liste renvoyé par le backend : article, fait ou demande. */
export type ElementBackend = {
  titre: string;
  source: string;
  url?: string;
  texte?: string;
  demande?: string;
  categorie?: string;
  a_confirmer?: boolean;
  /** Conséquence complète renvoyée par get_type_consequences, rendue telle quelle à l'étape 8. */
  consequence?: unknown;
  etat?: string;
};

export type ParagrapheBackend = { amorce?: string; texte: string };
export type BlocBackend =
  | { type: "titre"; texte: string }
  | { type: "texte"; texte: string }
  | { type: "revoir"; texte: string; note: string };

/** Ce que le notaire a validé aux étapes 1 à 5, envoyé aux étapes 6 à 8. */
export type Valide = {
  dossier: string;
  syntdmd: string;
  articles: ElementBackend[];
  synthese_droit: string;
  faits: ElementBackend[];
  demandes: ElementBackend[];
};

/**
 * Appelle le backend Python via le proxy /api/pipeline de Vite.
 * Les étapes interrogent le Compagnon et Augure : compter quelques minutes.
 */
async function appeler<T>(route: string, corps: unknown): Promise<T> {
  const reponse = await fetch(`/api/pipeline/${route}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corps),
  });
  const donnees = await reponse.json().catch(() => ({}));
  if (!reponse.ok) throw new Error(donnees.erreur ?? `Le backend a répondu ${reponse.status}`);
  return donnees as T;
}

/** Étapes 2 et 3 : articles applicables et synthèse du droit applicable. */
export function syntheseDemandeClients(dossier: string, syntdmd: string) {
  return appeler<{ articles: ElementBackend[]; synthese: string }>("synthese-demande-clients", { dossier, syntdmd });
}

/** Étapes 4 et 5 : éléments factuels et demandes des clients, à partir des articles retenus. */
export function demandesEtFaits(dossier: string, syntdmd: string, articles: ElementBackend[]) {
  return appeler<{ faits: ElementBackend[]; demandes: ElementBackend[] }>("demandes-et-faits", {
    dossier,
    syntdmd,
    articles,
  });
}

/** Étape 6 : contradictions (brutes, pour l'étape 8, et mises en paragraphes pour l'affichage). */
export function contradictions(valide: Valide) {
  return appeler<{ contradictions: unknown[]; paragraphes: ParagrapheBackend[] }>("contradictions", valide);
}

/** Étape 7 : conséquences possibles et synthèse des risques. */
export function consequences(valide: Valide) {
  return appeler<{ consequences: ElementBackend[]; risques: ParagrapheBackend[] }>("consequences", valide);
}

/** Étape 8 : projet d'acte Word ; `fichier` est l'URL de téléchargement du .docx. */
export function acte(valide: Valide & { contradictions: unknown[]; consequences: ElementBackend[] }) {
  return appeler<{ fichier: string; blocs: BlocBackend[]; questions: string[]; resume: string }>("acte", valide);
}
