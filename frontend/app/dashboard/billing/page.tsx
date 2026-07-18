/**
 * Página de Membresía y Pagos — Pasarela SINPE Móvil (Costa Rica).
 * Muestra los 3 planes (Starter/Pro/Studio), los datos SINPE para transferir,
 * y permite subir el comprobante (.jpg/.png) para dejar el pago en estado
 * "Pendiente de aprobación" hasta que un admin lo valide.
 */
"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPostForm } from "@/lib/api";
import type { PlanInfo, Profile, SinpePaymentHistoryItem } from "@/types";

const CRC = new Intl.NumberFormat("es-CR", { style: "currency", currency: "CRC", maximumFractionDigits: 0 });
const ALLOWED_RECEIPT_TYPES = ["image/jpeg", "image/png", "image/jpg"];
const MAX_RECEIPT_SIZE_MB = 10;

const STATUS_LABELS: Record<string, string> = {
  pending: "Pendiente de aprobación",
  approved: "Aprobado",
  rejected: "Rechazado",
};

export default function BillingPage() {
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [sinpeInfo, setSinpeInfo] = useState<{ phone_number: string; owner_name: string; approval_sla: string } | null>(
    null
  );
  const [history, setHistory] = useState<SinpePaymentHistoryItem[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<string>("");
  const [receipt, setReceipt] = useState<File | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  function loadHistory() {
    apiGet<SinpePaymentHistoryItem[]>("/payments/history").then(setHistory).catch(() => {});
  }

  useEffect(() => {
    apiGet<PlanInfo[]>("/payments/plans").then((data) => {
      setPlans(data);
      apiGet<Profile>("/auth/me")
        .then((profile) => {
          const current = profile.active_plan && data.some((p) => p.id === profile.active_plan);
          setSelectedPlan(current ? (profile.active_plan as string) : data[0]?.id ?? "");
        })
        .catch(() => setSelectedPlan(data[0]?.id ?? ""));
    });
    apiGet<{ phone_number: string; owner_name: string; approval_sla: string }>("/payments/sinpe-info").then(
      setSinpeInfo
    );
    loadHistory();
  }, []);

  function handleReceiptChange(file: File | null) {
    setFormError(null);
    if (file && !ALLOWED_RECEIPT_TYPES.includes(file.type)) {
      setFormError("El comprobante debe ser una imagen .jpg o .png.");
      setReceipt(null);
      return;
    }
    if (file && file.size > MAX_RECEIPT_SIZE_MB * 1024 * 1024) {
      setFormError(`El comprobante no puede pesar más de ${MAX_RECEIPT_SIZE_MB} MB.`);
      setReceipt(null);
      return;
    }
    setReceipt(file);
  }

  async function handleSubmit() {
    if (!receipt || !selectedPlan) return;
    setFormError(null);
    setStatus("Enviando comprobante...");
    try {
      const formData = new FormData();
      formData.append("plan", selectedPlan);
      formData.append("receipt", receipt);
      await apiPostForm("/payments/sinpe/upload-receipt", formData);
      setStatus("Comprobante enviado. Tu membresía quedó \"Pendiente de aprobación\".");
      setReceipt(null);
      loadHistory();
    } catch (err) {
      setStatus(null);
      setFormError(err instanceof Error ? err.message : "Error al enviar el comprobante.");
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold mb-1">Membresía y Pagos</h1>
      <p className="text-photonix-textMuted mb-6">Planes en colones costarricenses (₡), pago vía SINPE Móvil.</p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {plans.map((plan) => (
          <button
            key={plan.id}
            onClick={() => setSelectedPlan(plan.id)}
            className={`photonix-card text-left transition-colors ${
              selectedPlan === plan.id ? "border-photonix-accent" : ""
            }`}
          >
            <p className="text-sm text-photonix-textMuted">{plan.name}</p>
            <p className="text-2xl font-semibold mt-1">{CRC.format(plan.price_crc)}</p>
            <p className="text-xs text-photonix-textMuted mt-1">/ mes</p>
          </button>
        ))}
      </div>

      <div className="photonix-card mb-6">
        <h2 className="font-medium mb-2">1. Realiza tu pago por SINPE Móvil</h2>
        {sinpeInfo && (
          <>
            <p className="text-sm text-photonix-textMuted">
              Transfiere a <span className="text-photonix-text font-medium">{sinpeInfo.phone_number}</span> a nombre de{" "}
              <span className="text-photonix-text font-medium">{sinpeInfo.owner_name}</span>.
            </p>
            <p className="text-xs text-photonix-textMuted mt-2">{sinpeInfo.approval_sla}</p>
          </>
        )}
      </div>

      <div className="photonix-card mb-6">
        <h2 className="font-medium mb-3">2. Sube el comprobante de la transferencia</h2>
        <input
          type="file"
          accept="image/jpeg,image/png"
          onChange={(e) => handleReceiptChange(e.target.files?.[0] ?? null)}
          className="photonix-input mb-4"
        />
        {formError && <p className="text-sm text-photonix-danger mb-3">{formError}</p>}
        <button onClick={handleSubmit} disabled={!receipt} className="photonix-btn-primary">
          Enviar comprobante
        </button>
        {status && <p className="text-sm text-photonix-accent mt-3">{status}</p>}
      </div>

      <div className="photonix-card">
        <h2 className="font-medium mb-3">Historial de pagos</h2>
        {history.length === 0 && (
          <p className="text-sm text-photonix-textMuted">Todavía no has enviado ningún comprobante.</p>
        )}
        <div className="flex flex-col gap-2">
          {history.map((item) => (
            <div key={item.id} className="flex items-center justify-between text-sm py-2 border-b border-photonix-border last:border-0">
              <div>
                <p className="capitalize">{item.plan}</p>
                <p className="text-xs text-photonix-textMuted">
                  {new Date(item.created_at).toLocaleDateString("es-CR")}
                </p>
              </div>
              <span
                className={`photonix-chip ${
                  item.status === "approved"
                    ? "!text-photonix-success"
                    : item.status === "rejected"
                    ? "!text-photonix-danger"
                    : ""
                }`}
              >
                {STATUS_LABELS[item.status] ?? item.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
