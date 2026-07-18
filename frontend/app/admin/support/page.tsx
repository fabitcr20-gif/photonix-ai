/** Panel de administrador: tickets de soporte técnico de los clientes. */
"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPostJson } from "@/lib/api";
import type { SupportTicketAdminView } from "@/types";

const STATUS_LABELS: Record<string, string> = {
  open: "Abierto",
  in_progress: "En progreso",
  closed: "Cerrado",
};

export default function AdminSupportPage() {
  const [tickets, setTickets] = useState<SupportTicketAdminView[]>([]);
  const [loading, setLoading] = useState(true);
  const [replyDrafts, setReplyDrafts] = useState<Record<string, string>>({});
  const [sending, setSending] = useState<string | null>(null);

  async function loadTickets() {
    setLoading(true);
    const data = await apiGet<SupportTicketAdminView[]>("/admin/support/tickets");
    setTickets(data);
    setLoading(false);
  }

  useEffect(() => {
    loadTickets();
  }, []);

  async function handleReply(id: string) {
    const reply = (replyDrafts[id] ?? "").trim();
    if (!reply) return;
    setSending(id);
    try {
      await apiPostJson(`/admin/support/tickets/${id}/reply`, { reply, status: "closed" });
      await loadTickets();
      setReplyDrafts((prev) => ({ ...prev, [id]: "" }));
    } finally {
      setSending(null);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Soporte técnico</h1>
      <p className="text-photonix-textMuted mb-6">Tickets enviados por los clientes, más recientes primero.</p>

      {loading && <p className="text-photonix-textMuted">Cargando...</p>}

      {!loading && tickets.length === 0 && (
        <div className="photonix-card text-center text-photonix-textMuted">No hay tickets de soporte.</div>
      )}

      <div className="flex flex-col gap-4">
        {tickets.map((t) => (
          <div key={t.id} className="photonix-card">
            <div className="flex items-center justify-between mb-2">
              <div>
                <p className="font-medium">{t.subject}</p>
                <p className="text-xs text-photonix-textMuted">{t.profiles?.email ?? t.user_id}</p>
              </div>
              <span className="text-xs px-2 py-1 rounded-full bg-white/[0.04] text-photonix-textMuted">
                {STATUS_LABELS[t.status] ?? t.status}
              </span>
            </div>
            <p className="text-sm text-photonix-textMuted whitespace-pre-wrap mb-3">{t.message}</p>

            {t.admin_reply && (
              <div className="p-3 rounded-lg bg-white/[0.02] border border-photonix-border text-sm mb-3">
                <p className="text-xs text-photonix-textMuted mb-1">Tu respuesta</p>
                {t.admin_reply}
              </div>
            )}

            {t.status !== "closed" && (
              <div className="flex gap-2">
                <textarea
                  value={replyDrafts[t.id] ?? ""}
                  onChange={(e) => setReplyDrafts((prev) => ({ ...prev, [t.id]: e.target.value }))}
                  placeholder="Escribe una respuesta..."
                  rows={2}
                  className="photonix-input text-sm flex-1"
                />
                <button
                  onClick={() => handleReply(t.id)}
                  disabled={sending === t.id || !(replyDrafts[t.id] ?? "").trim()}
                  className="photonix-btn-primary text-sm"
                >
                  Responder
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
