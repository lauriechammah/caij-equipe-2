import {
  ACTE,
  ARTICLES,
  CONSEQUENCES,
  CONTRADICTIONS,
  DEMANDES,
  EXEMPLE,
  FAITS,
  SYNTHESE_ARTICLES,
  SYNTHESE_DEMANDE,
  SYNTHESE_RISQUES,
} from "../data/exemple";
import { versTexte } from "../data/texte";
import { demanderAugure } from "./augure";
import type { Source } from "./source";

const attendre = <T>(valeur: T) => new Promise<T>((r) => setTimeout(() => r(valeur), 400));

/** Le mandat d'exemple : mêmes étapes que le backend, contenu fixe, sans appel réseau (sauf Augure). */
export const sourceExemple: Source = {
  syntheseDemande: () => attendre({ titre: EXEMPLE.titre, synthese: versTexte(SYNTHESE_DEMANDE) }),
  articles: () => attendre({ articles: ARTICLES, synthese: versTexte(SYNTHESE_ARTICLES) }),
  faitsEtDemandes: () => attendre({ faits: FAITS, demandes: DEMANDES }),
  contradictions: () => attendre({ brutes: [], paragraphes: CONTRADICTIONS }),
  consequences: () => attendre({ consequences: CONSEQUENCES, risques: SYNTHESE_RISQUES }),
  acte: () => attendre({ nom: "Exemple — charte de vie commune", fichier: "", blocs: ACTE }),

  // Pas de pièces côté backend pour l'exemple : Augure répond avec le contexte de l'écran.
  question: (question, historique, contexte, onTexte) =>
    demanderAugure(
      [
        ...historique.map((m) => ({ role: m.role, content: m.texte })),
        { role: "user" as const, content: question },
      ],
      contexte,
      onTexte ?? (() => {}),
    ),
};
