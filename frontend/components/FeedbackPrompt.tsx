/**
 * Aviso discreto y descartable para pedir retroalimentación tras terminar de
 * procesar una sesión. No es un modal bloqueante: el usuario puede seguir
 * viendo el antes/después y exportar sin responderlo.
 */
"use client";

import { useState } from "react";
import { Star, X } from "lucide-react";
import { apiPostJson } from "@/lib/api";

export default function FeedbackPrompt({ projectId, onDone }: { projectId: string; onDone: () => void }) {
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [comment, setComment] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (rating === 0) {
      setError("Elige una calificación de 1 a 5 estrellas.");
      return;
    }
    setSending(true);
    setError(null);
    try {
      await apiPostJson("/feedback", { rating, comment: comment.trim() || null, project_id: projectId });
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo enviar tu retroalimentación.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mt-6 p-4 rounded-xl2 border border-photonix-border bg-white/[0.02] text-sm photonix-fade-in relative">
      <button
        onClick={onDone}
        aria-label="Cerrar"
        className="absolute top-3 right-3 text-photonix-textMuted hover:text-photonix-text"
      >
        <X size={16} />
      </button>
      <p className="font-medium mb-1">¿Cómo fue tu experiencia con esta sesión?</p>
      <p className="text-xs text-photonix-textMuted mb-3">Tu opinión nos ayuda a mejorar Photonix AI.</p>

      <div className="flex gap-1 mb-3">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            onClick={() => setRating(n)}
            onMouseEnter={() => setHoverRating(n)}
            onMouseLeave={() => setHoverRating(0)}
            aria-label={`${n} estrella${n !== 1 ? "s" : ""}`}
            className="p-0.5"
          >
            <Star
              size={22}
              className={n <= (hoverRating || rating) ? "fill-photonix-accent text-photonix-accent" : "text-photonix-border"}
            />
          </button>
        ))}
      </div>

      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Comentario opcional"
        rows={2}
        className="photonix-input w-full text-sm mb-3"
        maxLength={2000}
      />

      {error && <p className="text-photonix-danger text-xs mb-2">{error}</p>}

      <div className="flex gap-2">
        <button onClick={handleSubmit} disabled={sending} className="photonix-btn-primary text-sm">
          {sending ? "Enviando..." : "Enviar sugerencia"}
        </button>
        <button onClick={onDone} className="photonix-btn-secondary text-sm">
          Ahora no
        </button>
      </div>
    </div>
  );
}
