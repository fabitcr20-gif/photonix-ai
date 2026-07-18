/**
 * Módulo de validación de comprobantes SINPE.
 * Lista los comprobantes pendientes con opciones para Aprobar (activa la
 * membresía 30 días) o Rechazar.
 */
"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPostJson } from "@/lib/api";
import type { SinpePaymentAdminView } from "@/types";

export default function SinpeValidationsPage() {
  const [payments, setPayments] = useState<SinpePaymentAdminView[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadPayments() {
    setLoading(true);
    const data = await apiGet<SinpePaymentAdminView[]>("/admin/sinpe/pending");
    setPayments(data);
    setLoading(false);
  }

  useEffect(() => {
    loadPayments();
  }, []);

  const [blockedIds, setBlockedIds] = useState<Set<string>>(new Set());

  async function handleReview(id: string, action: "approve" | "reject") {
    await apiPostJson(`/admin/sinpe/${id}/review`, { action });
    setPayments((prev) => prev.filter((p) => p.id !== id));
  }

  async function handleBlock(userId: string) {
    if (!confirm("¿Bloquear a este usuario por mora/comprobante inválido? Perderá acceso de inmediato.")) return;
    await apiPostJson(`/admin/users/${userId}/block`, {});
    setBlockedIds((prev) => new Set(prev).add(userId));
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Validación de Pagos SINPE</h1>
      <p className="text-photonix-textMuted mb-6">
        Revisa cada comprobante. Al aprobar, la membresía se activa automáticamente por 30 días.
      </p>

      {loading && <p className="text-photonix-textMuted">Cargando...</p>}

      {!loading && payments.length === 0 && (
        <div className="photonix-card text-center text-photonix-textMuted">
          No hay comprobantes pendientes de revisión.
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {payments.map((p) => (
          <div key={p.id} className="photonix-card">
            <img
              src={p.receipt_image_url}
              alt="Comprobante SINPE"
              className="w-full h-48 object-cover rounded-lg mb-4 bg-photonix-surfaceAlt"
            />
            <p className="text-sm text-photonix-textMuted">Usuario</p>
            <p className="font-medium mb-2">{p.user_email ?? p.user_id}</p>
            <p className="text-sm text-photonix-textMuted">Plan solicitado</p>
            <p className="font-medium mb-4 capitalize">{p.plan}</p>

            <div className="flex gap-2">
              <button onClick={() => handleReview(p.id, "approve")} className="photonix-btn-primary flex-1">
                Aprobar
              </button>
              <button
                onClick={() => handleReview(p.id, "reject")}
                className="flex-1 bg-photonix-danger/10 text-photonix-danger border border-photonix-danger/40 rounded-lg font-medium hover:bg-photonix-danger/20 transition-colors"
              >
                Rechazar
              </button>
            </div>
            <button
              onClick={() => handleBlock(p.user_id)}
              disabled={blockedIds.has(p.user_id)}
              className="w-full mt-2 text-xs text-photonix-textMuted hover:text-photonix-danger transition-colors"
            >
              {blockedIds.has(p.user_id) ? "Usuario bloqueado ✓" : "Bloquear usuario (comprobante inválido/mora)"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
