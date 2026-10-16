import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import type { Source } from "../api/source";
import type { Message } from "../data/types";
import { Icon } from "./Icon";

/** Questions proposées : valables pour tout dossier. */
const SUGGESTIONS = ["Relever les contradictions", "Quelles informations manquent ?", "Questions à poser au client"];

/** Rend le **gras** Markdown renvoyé par Augure. */
function enLigne(ligne: string) {
  return ligne.split(/\*\*(.+?)\*\*/g).map((morceau, i) => (i % 2 ? <strong key={i}>{morceau}</strong> : morceau));
}

function texteComplet(m: Extract<Message, { role: "assistant" }>) {
  const puces = m.puces?.map((p) => `• ${p.amorce} ${p.texte}`).join("\n") ?? "";
  return [m.texte, puces].filter(Boolean).join("\n");
}

/** Zone droite ouverte : conversation avec Augure AI sur le dossier en cours. */
export function PanneauAugure({
  source,
  contexte,
  initiale = [],
  onFermer,
  onInserer,
}: {
  source: Source;
  /** Où en est le notaire (étape, synthèse), joint à chaque question. */
  contexte: string;
  /** Conversation de départ (le mandat d'exemple en a une). */
  initiale?: Message[];
  onFermer: () => void;
  onInserer?: (texte: string) => void;
}) {
  const [messages, setMessages] = useState<Message[]>(initiale);
  const [saisie, setSaisie] = useState("");
  const [occupe, setOccupe] = useState(false);
  const [copie, setCopie] = useState<number | null>(null);
  const finRef = useRef<HTMLDivElement>(null);
  const monte = useRef(true);

  useEffect(() => {
    finRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  useEffect(() => {
    monte.current = true;
    return () => {
      monte.current = false;
    };
  }, []);

  async function envoyer(question: string) {
    const q = question.trim();
    if (!q || occupe) return;
    setSaisie("");
    setOccupe(true);

    const historique = messages;
    setMessages((ms) => [...ms, { role: "user", texte: q }, { role: "assistant", texte: "", enCours: true }]);
    const remplacerDernier = (m: Message) => monte.current && setMessages((ms) => [...ms.slice(0, -1), m]);

    try {
      const texte = await source.question(q, historique, contexte, (partiel) =>
        remplacerDernier({ role: "assistant", texte: partiel, enCours: true }),
      );
      remplacerDernier({ role: "assistant", texte: texte || "Augure n’a pas renvoyé de réponse." });
    } catch (e) {
      remplacerDernier({
        role: "assistant",
        texte: `Augure est injoignable (${e instanceof Error ? e.message : String(e)}).`,
      });
    } finally {
      if (monte.current) setOccupe(false);
    }
  }

  function soumettre(e: FormEvent) {
    e.preventDefault();
    envoyer(saisie);
  }

  function touche(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      envoyer(saisie);
    }
  }

  async function copier(i: number, texte: string) {
    try {
      await navigator.clipboard.writeText(texte);
      setCopie(i);
      setTimeout(() => setCopie(null), 1500);
    } catch {
      // presse-papiers refusé : rien à faire
    }
  }

  return (
    <aside className="augure" aria-label="Augure AI">
      <div className="augure__entete">
        <div className="augure__marque">
          <span className="augure__logo">
            <Icon nom="sparkle-entete" />
          </span>
          <h2>Augure AI</h2>
        </div>
        <button type="button" className="augure__fermer" onClick={onFermer} aria-label="Fermer Augure AI">
          <Icon nom="x-panneau" />
        </button>
      </div>

      <div className="augure__conversation">
        {messages.length === 0 && (
          <p className="augure__accueil">
            Posez une question sur ce dossier : Augure lit les pièces avant de répondre, et cite celles sur
            lesquelles il s’appuie.
          </p>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="question">
              <p>{m.texte}</p>
            </div>
          ) : (
            <div key={i} className="reponse">
              <div className="reponse__auteur">
                <Icon nom="sparkle-petit" />
                Augure AI
              </div>
              {m.texte ? (
                m.texte.split(/\n+/).map((ligne, j) => <p key={j}>{enLigne(ligne)}</p>)
              ) : (
                <p className="reponse__attente">Augure lit le dossier…</p>
              )}
              {m.puces?.map((p) => (
                <div key={p.amorce} className="reponse__puce">
                  <span className="reponse__point">•</span>
                  <p>
                    <strong>{p.amorce}</strong> {p.texte}
                  </p>
                </div>
              ))}
              {m.sources && (
                <div className="reponse__sources">
                  {m.sources.map((s) => (
                    <span key={s.numero} className="source">
                      <span className="source__numero">{s.numero}</span>
                      {s.libelle}
                    </span>
                  ))}
                </div>
              )}
              {!m.enCours && m.texte && (
                <div className="reponse__actions">
                  {onInserer && (
                    <button type="button" className="lien-accent lien-accent--icone" onClick={() => onInserer(texteComplet(m))}>
                      <Icon nom="insert" />
                      Insérer
                    </button>
                  )}
                  <button type="button" className="lien-accent lien-accent--icone" onClick={() => copier(i, texteComplet(m))}>
                    <Icon nom="copy" />
                    {copie === i ? "Copié" : "Copier"}
                  </button>
                </div>
              )}
            </div>
          ),
        )}
        <div ref={finRef} />
      </div>

      <div className="augure__suggestions">
        {SUGGESTIONS.map((s) => (
          <button key={s} type="button" className="suggestion" onClick={() => envoyer(s)} disabled={occupe}>
            {s}
          </button>
        ))}
      </div>

      <form className="augure__saisie" onSubmit={soumettre}>
        <div className="saisie">
          <textarea
            value={saisie}
            onChange={(e) => setSaisie(e.target.value)}
            onKeyDown={touche}
            placeholder="Posez une question"
            rows={1}
            aria-label="Posez une question"
          />
          <div className="saisie__pied">
            <button type="submit" className="saisie__envoyer" disabled={occupe || !saisie.trim()} aria-label="Envoyer">
              <Icon nom="arrow-r-blanc" />
            </button>
          </div>
        </div>
      </form>
    </aside>
  );
}
