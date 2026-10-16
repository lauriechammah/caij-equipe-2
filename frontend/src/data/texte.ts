import type { Paragraphe } from "./types";

/** Texte d'Augure (un paragraphe par ligne, amorce en **gras**) → paragraphes affichables. */
export function versParagraphes(texte: string): Paragraphe[] {
  return texte
    .split(/\n+/)
    .map((l) => l.trim().replace(/^#+\s*/, ""))
    .filter((l) => l && !/^-{3,}$/.test(l))
    .map((l) => {
      const m = l.match(/^\*\*(.+?)\*\*\s*(.*)$/);
      return m ? { amorce: m[1], texte: m[2] } : { texte: l.replace(/\*\*/g, "") };
    });
}

/** L'inverse : paragraphes → texte, pour l'envoyer au backend. */
export function versTexte(paragraphes: Paragraphe[]): string {
  return paragraphes.map((p) => (p.amorce ? `**${p.amorce}** ${p.texte}` : p.texte)).join("\n");
}
