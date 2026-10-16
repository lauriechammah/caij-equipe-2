// Structure du parcours (libellés des étapes), indépendante du dossier.

export type Etape = {
  numero: number;
  libelle: string;
  titre: string;
  document: string;
};

export const ETAPES: Etape[] = [
  { numero: 1, libelle: "Demande", titre: "Synthèse de la demande client", document: "Synthèse de la demande" },
  { numero: 2, libelle: "Articles", titre: "Articles soulevés", document: "Articles retenus" },
  { numero: 3, libelle: "Synthèse juridique", titre: "Synthèse des articles", document: "Synthèse des articles" },
  { numero: 4, libelle: "Faits", titre: "Éléments factuels", document: "Éléments factuels" },
  { numero: 5, libelle: "Demandes", titre: "Demandes des clients", document: "Demandes des clients" },
  { numero: 6, libelle: "Contradictions", titre: "Contradictions soulevées", document: "Contradictions" },
  { numero: 7, libelle: "Conséquences", titre: "Conséquences possibles", document: "Conséquences et risques" },
  { numero: 8, libelle: "Acte", titre: "Projet d’acte", document: "Projet d’acte" },
];

/** Annexes de l'acte : les documents des étapes 1 à 7. */
export const ANNEXES = ETAPES.slice(0, 7).map((e) => ({ libelle: e.document, etape: e.numero }));
