/**
 * Recordatorios de pago: lista clientes cuya prueba gratuita o membresía
 * vence pronto o ya venció, con opción de enviarles un recordatorio por
 * correo individualmente o a todos a la vez. Ver backend/app/services/reminder_service.py.
 */
"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPostJson } from "@/lib/api";
import type { ReminderDue } from "@/types";

export default function RemindersPage() {
  const [items, setItems] = useState<ReminderDue[]>([]);
  const [loading, setLoading] = useState(true);
  const [sendingAll, setSendingAll] = useState(false);
  const [sentIds, setSentIds] = useState<Set<string>>(new Set());

  async function loadReminders() {
    setLoading(true);
    const data = await apiGet<ReminderDue[]>("/admin/reminders/due");
    setItems(data);
    setLoading(false);
  }

  useEffect(() => {
    loadReminders();
  }, []);

  async function sendOne(userId: string) {
    await apiPostJson(`/admin/reminders/send/${userId}`, {});
    setSentIds((prev) => new Set(prev).add(userId));
  }

  async function sendAll() {
    setSendingAll(true);
    await apiPostJson("/admin/reminders/send-all", {});
    setSentIds(new Set(items.map((i) => i.user_id)));
    setSendingAll(false);
  }

  async function toggleBlock(userId: string, currentlyBlocked: boolean) {
    const action = currentlyBlocked ? "unblock" : "block";
    if (!currentlyBlocked && !confirm("¿Bloquear a este usuario por mora? Perderá acceso de inmediato.")) return;
    await apiPostJson(`/admin/users/${userId}/${action}`, {});
    setItems((prev) => prev.map((i) => (i.user_id === userId ? { ...i, is_blocked: !currentlyBlocked } : i)));
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Recordatorios de Pago</h1>
      <p className="text-photonix-textMuted mb-6">
        Clientes cuya prueba gratuita o membresía vence pronto, o ya venció.
      </p>

      {!loading && items.length > 0 && (
        <button onClick={sendAll} disabled={sendingAll} className="photonix-btn-primary mb-6">
          {sendingAll ? "Enviando..." : `Enviar recordatorio a todos (${items.length})`}
        </button>
      )}

      {loading && <p className="text-photonix-textMuted">Cargando...</p>}

      {!loading && items.length === 0 && (
        <div className="photonix-card text-center text-photonix-textMuted">
          No hay clientes que necesiten un recordatorio ahora mismo.
        </div>
      )}

      <div className="flex flex-col gap-3">
        {items.map((item) => (
          <div key={item.user_id} className="photonix-card flex items-center justify-between gap-4">
            <div>
              <p className="font-medium">
                {item.full_name ?? item.email}
                {item.is_blocked && (
                  <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-photonix-danger/10 text-photonix-danger border border-photonix-danger/40">
                    Bloqueado
                  </span>
                )}
              </p>
              <p className="text-sm text-photonix-textMuted">
                {item.email} · Plan <span className="capitalize">{item.plan}</span> ·{" "}
                {item.expired ? (
                  <span className="text-photonix-danger">Venció el</span>
                ) : (
                  "Vence el"
                )}{" "}
                {new Date(item.ends_at).toLocaleDateString("es-CR")}
              </p>
            </div>
            <div className="flex gap-2 shrink-0">
              <button
                onClick={() => sendOne(item.user_id)}
                disabled={sentIds.has(item.user_id)}
                className="photonix-btn-secondary"
              >
                {sentIds.has(item.user_id) ? "Enviado ✓" : "Enviar recordatorio"}
              </button>
              <button
                onClick={() => toggleBlock(item.user_id, item.is_blocked)}
                className={
                  item.is_blocked
                    ? "photonix-btn-secondary"
                    : "bg-photonix-danger/10 text-photonix-danger border border-photonix-danger/40 rounded-lg font-medium px-4 hover:bg-photonix-danger/20 transition-colors text-sm"
                }
              >
                {item.is_blocked ? "Desbloquear" : "Bloquear"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
