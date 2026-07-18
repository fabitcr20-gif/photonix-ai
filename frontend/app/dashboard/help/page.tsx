/** Ayuda: preguntas frecuentes, soporte técnico (tickets) y contacto. */
"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPostJson } from "@/lib/api";
import type { SupportTicket } from "@/types";

const FAQS = [
  {
    q: "¿Cómo elijo el mejor perfil de estilo para mi sesión?",
    a: "En 'Nueva edición', elige el perfil que más se parezca al tipo de sesión (Retrato, Automotriz, Producto, etc.). Si no estás seguro, deja 'Automático IA' y la IA decidirá según la hora, el clima y la luz de cada foto.",
  },
  {
    q: "¿Por qué no puedo eliminar placas de autos o postes de luz?",
    a: "Esa función requiere el plan Pro o Studio. Puedes actualizar tu plan desde 'Mi Membresía'.",
  },
  {
    q: "¿Dónde configuro mi marca de agua?",
    a: "En 'Marca de agua' puedes subir tu logo y arrastrarlo sobre una foto de muestra para ubicarlo exactamente donde quieras.",
  },
  {
    q: "¿Cómo exporto mis fotos ya editadas?",
    a: "Una vez que una sesión termine de procesarse, ve a 'Exportaciones' o al final de 'Nueva edición' para descargar en ZIP, subir a Google Drive o compartir en Instagram.",
  },
];

const STATUS_LABELS: Record<string, string> = {
  open: "Abierto",
  in_progress: "En progreso",
  closed: "Respondido",
};

export default function HelpPage() {
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  async function loadTickets() {
    try {
      const data = await apiGet<SupportTicket[]>("/support/tickets");
      setTickets(data);
    } catch {
      // silencioso: la lista de tickets es secundaria a la ayuda estática
    }
  }

  useEffect(() => {
    loadTickets();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!subject.trim() || !message.trim()) return;
    setSending(true);
    setFeedback(null);
    try {
      await apiPostJson("/support/tickets", { subject, message });
      setSubject("");
      setMessage("");
      setFeedback("Tu ticket fue enviado. Te responderemos aquí mismo.");
      loadTickets();
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : "No se pudo enviar el ticket.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold mb-1">Ayuda</h1>
      <p className="text-photonix-textMuted mb-6">Preguntas frecuentes y soporte técnico de Photonix AI.</p>

      <div className="flex flex-col gap-3 mb-8">
        {FAQS.map((item) => (
          <div key={item.q} className="photonix-card">
            <p className="font-medium text-sm mb-1.5">{item.q}</p>
            <p className="text-sm text-photonix-textMuted">{item.a}</p>
          </div>
        ))}
      </div>

      <div className="photonix-card mb-8">
        <h2 className="font-medium mb-1">Soporte técnico</h2>
        <p className="text-sm text-photonix-textMuted mb-4">
          ¿Encontraste un problema o necesitas ayuda? Escríbenos y te responderemos aquí mismo.
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Asunto"
            maxLength={200}
            className="photonix-input text-sm"
            required
          />
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Cuéntanos qué pasó..."
            rows={4}
            maxLength={5000}
            className="photonix-input text-sm"
            required
          />
          <button type="submit" disabled={sending} className="photonix-btn-primary self-start">
            {sending ? "Enviando..." : "Enviar ticket"}
          </button>
          {feedback && <p className="text-sm text-photonix-accent">{feedback}</p>}
        </form>
      </div>

      {tickets.length > 0 && (
        <div className="flex flex-col gap-3 mb-8">
          <h2 className="font-medium">Mis tickets</h2>
          {tickets.map((t) => (
            <div key={t.id} className="photonix-card">
              <div className="flex items-center justify-between mb-1.5">
                <p className="font-medium text-sm">{t.subject}</p>
                <span className="text-xs px-2 py-1 rounded-full bg-white/[0.04] text-photonix-textMuted">
                  {STATUS_LABELS[t.status] ?? t.status}
                </span>
              </div>
              <p className="text-sm text-photonix-textMuted whitespace-pre-wrap mb-2">{t.message}</p>
              {t.admin_reply && (
                <div className="p-3 rounded-lg bg-white/[0.02] border border-photonix-border text-sm">
                  <p className="text-xs text-photonix-textMuted mb-1">Respuesta del equipo</p>
                  {t.admin_reply}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="photonix-card">
        <h2 className="font-medium mb-1">¿Necesitas más ayuda?</h2>
        <p className="text-sm text-photonix-textMuted">
          Escríbenos a{" "}
          <a href="mailto:soporte@photonixai.cr" className="text-photonix-accent hover:underline">
            soporte@photonixai.cr
          </a>
        </p>
      </div>
    </div>
  );
}
