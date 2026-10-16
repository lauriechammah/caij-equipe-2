// Contenu de démonstration repris des maquettes Figma (dossier Benoit / Morin).

export type Statut = "En cours" | "Terminé";

export type Mandat = {
  dossier: string;
  client: string;
  type: string;
  meta: string;
  statut: Statut;
};

export const MANDATS: Mandat[] = [
  { dossier: "2026-0644", client: "Benoit / Morin", type: "Charte de vie commune", meta: "Aujourd’hui, 11 h 40", statut: "En cours" },
  { dossier: "2026-0631", client: "Tremblay", type: "Testament notarié", meta: "2 oct 2026", statut: "Terminé" },
  { dossier: "2026-0618", client: "Gagnon / Roy", type: "Vente d’immeuble", meta: "24 sept 2026", statut: "Terminé" },
  { dossier: "2026-0602", client: "Lavoie", type: "Mandat de protection", meta: "15 sept 2026", statut: "Terminé" },
  { dossier: "2026-0587", client: "Côté / Bouchard", type: "Contrat de mariage", meta: "3 sept 2026", statut: "Terminé" },
  { dossier: "2026-0570", client: "Pelletier", type: "Donation entre vifs", meta: "21 août 2026", statut: "Terminé" },
];

export const TITRE_MANDAT = "Benoit / Morin, charte de vie commune";
export const CHEMIN_DOSSIER = "Documents › Dossiers › 2026-0644 Benoit-Morin";

export type Fichier = { numero: string; titre: string };

export const PIECES: Fichier[] = [
  { numero: "0", titre: "Mise en contexte et mandat" },
  { numero: "1", titre: "Notes d’entrevue de la notaire, 5 octobre 2026" },
  { numero: "2", titre: "Questionnaire rempli par Sarah Benoit" },
  { numero: "3", titre: "Questionnaire rempli par David Morin" },
  { numero: "4", titre: "Courriel de Sarah Benoit, 16 octobre 2026" },
];

export const MODELE: Fichier = { numero: "M", titre: "Modèle de charte de vie commune" };

export const TYPES_ACTE = [
  "Charte de vie commune",
  "Vente d’un immeuble au comptant",
  "Servitude de passage en cas d’enclave",
  "Convention d’indivision",
  "Mandat de protection",
  "Testament simple avec fiducie pour enfants",
];

/** Paragraphe avec, au besoin, une amorce en gras (« Union parentale : … »). */
export type Paragraphe = { amorce?: string; texte: string };

/** « coche » / « decoche » / « attente » (à confirmer avec le client). */
export type EtatCase = "coche" | "decoche" | "attente";
export type Element = { titre: string; source: string; etat: EtatCase };

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

export const SYNTHESE_DEMANDE: Paragraphe[] = [
  { texte: "Sarah Benoit (34 ans, médecin en fin de résidence en médecine d’urgence) et David Morin (36 ans, ébéniste à son compte depuis 2018) font vie commune depuis le 1er juillet 2021 au 77, rue des Remparts-Sud, à Lévis, dans une maison qui appartient à Sarah seule. Ils n’ont jamais été mariés et n’ont aucun contrat de vie commune. Leur premier enfant doit naître en mars 2027." },
  { texte: "Ils demandent à Me Paradis de préparer une charte de vie commune qui exprime leurs valeurs et leur façon de vivre ensemble, pour la rencontre du lundi 2 novembre 2026. Chacun a rempli un questionnaire séparément." },
  { texte: "Sarah souhaite aussi aborder le « côté financier ». Dans son courriel du 16 octobre, elle demande d’intégrer à la charte quatre clauses : la maison lui reste en cas de séparation, aucune pension entre conjoints, ses REER et son fonds de pension lui restent, et David s’engage à la suivre à Toronto en 2028-2029. Elle précise ne pas en avoir encore parlé à David." },
];

export const ARTICLES: Element[] = [
  { titre: "Formation de l’union parentale", source: "Article 521.20 CcQ", etat: "coche" },
  { titre: "Composition du patrimoine d’union parentale", source: "Article 521.30 CcQ", etat: "coche" },
  { titre: "Exclusion d’un bien par acte notarié en minute", source: "Article 521.31 CcQ", etat: "coche" },
  { titre: "Renonciation au patrimoine d’union parentale", source: "Article 521.33 CcQ", etat: "coche" },
  { titre: "Partage à parts égales de la valeur nette", source: "Article 521.34 CcQ", etat: "coche" },
  { titre: "Protection de la résidence familiale", source: "Article 401 à 407 CcQ", etat: "coche" },
  { titre: "Vocation successorale du conjoint en union parentale", source: "Article 653 CcQ", etat: "coche" },
  { titre: "Modèle de charte de vie commune", source: "RD/NS Famille 11.1", etat: "coche" },
];

export const SYNTHESE_ARTICLES: Paragraphe[] = [
  { amorce: "Union parentale :", texte: "à la naissance de l’enfant, prévue en mars 2027, Sarah et David formeront une union parentale (article 521.20 CcQ)." },
  { amorce: "Patrimoine d’union parentale :", texte: "la maison du 77, rue des Remparts-Sud, qui sert de résidence familiale, en ferait alors partie, avec les meubles qui la garnissent et les véhicules utilisés pour la famille (article 521.30). À la fin de l’union, sa valeur nette se partage à parts égales (article 521.34). Les épargnes-retraite (REER, régimes de retraite) n’en font pas partie." },
  { amorce: "Exclusion ou renonciation :", texte: "exclure la maison exige un acte notarié en minute (article 521.31) ; renoncer au patrimoine exige un accord des deux conjoints, aussi par acte notarié en minute (article 521.33). La résidence familiale reste protégée par les articles 401 à 407." },
  { amorce: "Portée de la charte :", texte: "la charte de vie commune n’a pas la portée d’un contrat (pièce 1) : elle ne peut pas produire ces effets. Les demandes financières de Sarah sont à traiter dans un acte distinct, avec le consentement éclairé de David." },
];

export const FAITS: Element[] = [
  { titre: "Vie commune depuis le 1er juillet 2021 ; jamais mariés ; aucun contrat de vie commune", source: "Pièce 1", etat: "coche" },
  { titre: "Maison du 77, rue des Remparts-Sud, à Lévis, achetée par Sarah seule en 2023", source: "Pièces 1 et 4", etat: "coche" },
  { titre: "Mise de fonds fournie par Sarah : ses économies et un don de ses parents", source: "Pièce 4", etat: "coche" },
  { titre: "Naissance du premier enfant prévue en mars 2027", source: "Pièce 1", etat: "coche" },
  { titre: "Sarah termine sa résidence en médecine d’urgence en juin 2027", source: "Pièce 1", etat: "coche" },
  { titre: "David est ébéniste à son compte depuis 2018 ; son atelier est à Lévis", source: "Pièce 1", etat: "coche" },
  { titre: "Sarah paie l’hypothèque et les taxes ; David, l’épicerie et l’électricité ; comptes séparés", source: "Pièce 2", etat: "coche" },
  { titre: "Moka, labrador de 5 ans, appartenait à David avant la relation", source: "Pièce 1", etat: "decoche" },
  { titre: "Jacqueline Morin, mère de David, 71 ans, vit seule à Montmagny", source: "Pièce 3", etat: "coche" },
];

export const DEMANDES: Element[] = [
  { titre: "Rédiger la charte à partir des valeurs communes : la famille, l’honnêteté, le soutien mutuel", source: "Pièces 2 et 3", etat: "coche" },
  { titre: "Prendre les repas ensemble, sans écrans à table", source: "Pièce 1", etat: "coche" },
  { titre: "Aucune punition corporelle ; des règles claires pour les enfants", source: "Pièces 2 et 3", etat: "coche" },
  { titre: "Inscrire la fidélité et ce qu’elle signifie pour le couple", source: "Sarah : oui (pièce 2), David : « ça va de soi » (pièce 3)", etat: "attente" },
  { titre: "Partage du congé parental", source: "Sarah : majorité à David (pièce 2), David : moitié-moitié (pièce 3)", etat: "attente" },
  { titre: "La maison reste à Sarah seule en cas de séparation", source: "Courriel de Sarah (pièce 4), relève d’un acte notarié distinct", etat: "attente" },
  { titre: "Aucune pension entre conjoints", source: "Courriel de Sarah (pièce 4)", etat: "attente" },
  { titre: "Le REER et le fonds de pension de Sarah restent à elle", source: "Courriel de Sarah (pièce 4)", etat: "attente" },
  { titre: "Engagement écrit de David à suivre Sarah à Toronto en 2028-2029", source: "Pièce 4, contredit le questionnaire de David (pièce 3)", etat: "decoche" },
];

export const CONTRADICTIONS: Paragraphe[] = [
  { amorce: "Nombre d’enfants :", texte: "Sarah : un, peut-être deux (pièce 2). David : trois ou quatre, rapprochés (pièce 3)." },
  { amorce: "Toronto, 2028-2029 :", texte: "Sarah demande un engagement écrit de David (pièce 4) ; David écrit : « Je ne déménage pas à Toronto » (pièce 3)." },
  { amorce: "Tâches et congé parental :", texte: "Sarah attend de David la plus grande part et la majorité du congé (pièce 2) ; David propose moitié-moitié et ne peut pas fermer l’atelier (pièce 3)." },
  { amorce: "Religion :", texte: "David tient au baptême (pièce 3) ; Sarah n’en veut pas (pièce 2)." },
  { amorce: "Langue :", texte: "Sarah veut élever l’enfant dans les deux langues (pièce 2) ; David privilégie le français (pièce 3)." },
  { amorce: "École :", texte: "public au primaire pour les deux ; au secondaire, privé si possible pour Sarah, public pour David." },
  { amorce: "Fidélité :", texte: "Sarah veut qu’elle soit écrite (pièce 2) ; pour David, « ça va de soi » (pièce 3)." },
  { amorce: "Maison :", texte: "Sarah pense la protéger par la charte (pièce 4), qui n’a pas la portée d’un contrat (pièce 1)." },
];

export const CONSEQUENCES: Element[] = [
  { titre: "Partage de la valeur de la maison dans le patrimoine d’union parentale", source: "Article 521.30 et 521.34", etat: "coche" },
  { titre: "Exclusion ou renonciation : acte notarié en minute, accord de David requis", source: "Article 521.31 et 521.33", etat: "coche" },
  { titre: "Déménagement à Toronto avec l’enfant : décision à prendre à deux", source: "Pièces 3 et 4", etat: "coche" },
  { titre: "Impartialité envers les deux conjoints : David n’est pas informé du courriel", source: "Pièce 4", etat: "coche" },
  { titre: "Protection de la résidence familiale", source: "Article 401 à 407, s’applique, rien à vérifier", etat: "decoche" },
  { titre: "Vocation successorale du conjoint survivant", source: "Article 653, à traiter dans un mandat distinct", etat: "decoche" },
];

export const SYNTHESE_RISQUES: Paragraphe[] = [
  { amorce: "Risque juridique :", texte: "les clauses financières demandées ne peuvent pas figurer dans la charte. À la naissance, la maison entre dans le patrimoine d’union parentale ; seul un acte notarié en minute, avec l’accord de David, peut l’en exclure." },
  { amorce: "Risque relationnel :", texte: "les demandes du courriel n’ont pas été discutées avec David : les présenter comme rédigées par la notaire compromettrait son impartialité." },
];

/** Bloc de l'acte : intertitre, paragraphe, ou passage surligné « à revoir ». */
export type BlocActe =
  | { type: "titre"; texte: string }
  | { type: "texte"; texte: string }
  | { type: "revoir"; texte: string; note: string };

export const ACTE: BlocActe[] = [
  { type: "titre", texte: "Préambule" },
  { type: "texte", texte: "Nous, Sarah Benoit, médecin, et David Morin, ébéniste, faisons vie commune depuis le 1er juillet 2021 à Lévis et attendons notre premier enfant en mars 2027. Cette charte exprime nos valeurs et nos intentions ; elle n’a pas la portée d’un contrat." },
  { type: "titre", texte: "Nos valeurs" },
  { type: "texte", texte: "Nous accordons une grande importance à la famille, à l’honnêteté et au soutien mutuel dans les moments difficiles." },
  { type: "titre", texte: "La fidélité" },
  { type: "revoir", texte: "Nous nous engageons à la fidélité, au sens que nous lui donnons ensemble : [à préciser]", note: "À revoir : Sarah souhaite l’écrire ; pour David, « ça va de soi »" },
  { type: "titre", texte: "Les enfants" },
  { type: "revoir", texte: "Nous souhaitons avoir [un ou deux / trois ou quatre] enfants.", note: "À revoir : divergence relevée à l’étape 6" },
  { type: "texte", texte: "Nous n’aurons jamais recours à la punition corporelle et fixerons à nos enfants des règles claires." },
  { type: "titre", texte: "Le partage des tâches et le congé parental" },
  { type: "revoir", texte: "Le congé parental sera partagé [majoritairement par David / à parts égales].", note: "À revoir : pièces 2 et 3 divergentes" },
  { type: "titre", texte: "La religion et la langue" },
  { type: "revoir", texte: "[Baptême / pas de baptême.] Notre enfant sera élevé [en français / dans les deux langues].", note: "À revoir : pièces 2 et 3 divergentes" },
  { type: "titre", texte: "Nos projets" },
  { type: "revoir", texte: "Sarah envisage une formation complémentaire à Toronto en 2028-2029 ; nous en discuterons ensemble.", note: "À revoir : David refuse de déménager (pièce 3) ; demande d’engagement exclue à l’étape 5" },
];

/** Annexes de l'acte : libellé et étape d'origine. */
export const ANNEXES: { libelle: string; etape: number }[] = [
  { libelle: "Synthèse de la demande", etape: 1 },
  { libelle: "Articles retenus", etape: 2 },
  { libelle: "Synthèse des articles", etape: 3 },
  { libelle: "Éléments factuels", etape: 4 },
  { libelle: "Demandes des clients", etape: 5 },
  { libelle: "Contradictions soulevées", etape: 6 },
  { libelle: "Conséquences et synthèse des risques", etape: 7 },
];

// Espace de travail (éditeur du projet de charte)

export const DOCUMENTS_EDITEUR: Fichier[] = [
  { numero: "G1", titre: "Projet de charte, v1" },
  { numero: "G2", titre: "Synthèse des divergences entre les questionnaires" },
];

export type BlocCharte =
  | { type: "titre"; texte: string }
  | { type: "texte"; texte: string }
  | { type: "discuter"; texte: string };

export const CHARTE_V1: BlocCharte[] = [
  { type: "titre", texte: "Préambule" },
  { type: "texte", texte: "Nous, Sarah Benoit, médecin, née à Sherbrooke le 11 avril 1992, et David Morin, ébéniste, né à Lévis le 2 décembre 1989, faisons vie commune depuis le 1er juillet 2021 au 77, rue des Remparts-Sud, à Lévis. Nous attendons notre premier enfant, dont la naissance est prévue en mars 2027." },
  { type: "texte", texte: "Par cette charte, nous voulons mettre par écrit notre vision de la vie à deux et de la famille que nous fondons. Elle exprime nos valeurs et nos intentions ; elle n’a pas la portée d’un contrat." },
  { type: "titre", texte: "Nos valeurs" },
  { type: "texte", texte: "Nous accordons une grande importance à la famille, à l’honnêteté et au soutien mutuel dans les moments difficiles. Sarah tient particulièrement à l’égalité et à l’autonomie de chacun ; David, à la loyauté et au plaisir d’être ensemble." },
  { type: "titre", texte: "Notre vie de famille" },
  { type: "texte", texte: "Nous tenons aux repas pris ensemble, sans écrans à table. Moka, notre labrador, fait partie de la famille." },
  { type: "titre", texte: "Les enfants" },
  { type: "discuter", texte: "Sarah souhaite un, peut-être deux enfants (pièce 2). David en souhaite trois ou quatre, rapprochés (pièce 3). Clause laissée ouverte pour la rencontre du 2 novembre." },
  { type: "texte", texte: "Nous nous engageons à ne jamais recourir à la punition corporelle et à fixer à nos enfants des règles claires." },
  { type: "titre", texte: "L’éducation" },
  { type: "texte", texte: "Nous souhaitons que notre enfant fréquente l’école publique au primaire." },
];

// Augure AI

export type Source = { numero: string; libelle: string };
export type Message =
  | { role: "user"; texte: string }
  | {
      role: "assistant";
      texte: string;
      puces?: { amorce: string; texte: string }[];
      sources?: Source[];
      enCours?: boolean;
    };

export const CONVERSATION_DEMO: Message[] = [
  { role: "user", texte: "Le courriel de Sarah du 16 octobre peut-il être intégré tel quel à la charte ?" },
  {
    role: "assistant",
    texte: "Pas tel quel. La plupart de ces demandes relèvent du volet financier, alors que la charte « n’a pas la portée d’un contrat » (pièce 1).",
    puces: [
      { amorce: "Maison, pension, REER :", texte: "à traiter séparément, au regard de l’union parentale qui s’appliquera à la naissance (pièces 1 et 4)." },
      { amorce: "Toronto :", texte: "David écrit « Je ne déménage pas à Toronto » (pièce 3). À présenter comme point de discussion, pas comme engagement." },
      { amorce: "À signaler :", texte: "Sarah n’en a pas encore parlé à David (pièce 4)." },
    ],
    sources: [
      { numero: "1", libelle: "Notes d’entrevue" },
      { numero: "3", libelle: "Questionnaire David Morin" },
      { numero: "4", libelle: "Courriel Sarah Benoit" },
    ],
  },
];

export const SUGGESTIONS = ["Relever les divergences", "Comparer au modèle 11.1", "Reformuler la section 3"];
