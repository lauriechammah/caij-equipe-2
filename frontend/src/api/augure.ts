declare const __AUGURE_MODEL__: string;

export type MessageAugure = { role: "system" | "user" | "assistant"; content: string };

const CONSIGNE =
  "Tu es Augure AI, assistant d'une notaire québécoise. Tu ne rédiges pas l'acte à sa place : " +
  "tu signales les contradictions, les informations manquantes et les options à trancher, " +
  "en citant les pièces du dossier. Réponds en français, brièvement.";

/**
 * Interroge Augure (API compatible OpenAI) via le proxy /api/augure de Vite.
 * `onTexte` reçoit le texte cumulé au fil du streaming.
 */
export async function demanderAugure(
  historique: MessageAugure[],
  contexte: string,
  onTexte: (texte: string) => void,
  signal?: AbortSignal,
): Promise<string> {
  const messages: MessageAugure[] = [
    { role: "system", content: `${CONSIGNE}\n\nContexte du mandat :\n${contexte}` },
    ...historique,
  ];

  const reponse = await fetch("/api/augure/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: __AUGURE_MODEL__, messages, stream: true }),
    signal,
  });
  if (!reponse.ok || !reponse.body) {
    throw new Error(`Augure a répondu ${reponse.status}`);
  }

  const lecteur = reponse.body.getReader();
  const decodeur = new TextDecoder();
  let tampon = "";
  let texte = "";

  for (;;) {
    const { done, value } = await lecteur.read();
    if (done) break;
    tampon += decodeur.decode(value, { stream: true });
    const lignes = tampon.split("\n");
    tampon = lignes.pop() ?? "";
    for (const ligne of lignes) {
      const donnees = ligne.replace(/^data:\s*/, "").trim();
      if (!donnees || donnees === "[DONE]" || !ligne.startsWith("data:")) continue;
      try {
        const morceau = JSON.parse(donnees).choices?.[0]?.delta?.content;
        if (morceau) {
          texte += morceau;
          onTexte(texte);
        }
      } catch {
        // ligne SSE incomplète : ignorée
      }
    }
  }
  return texte;
}
