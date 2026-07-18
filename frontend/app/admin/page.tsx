/**
 * Panel de Administrador — Vista de estadísticas.
 * Gráficos de nuevos usuarios registrados (por día/mes) y usuarios activos,
 * usando Recharts. Solo accesible para el rol 'admin' (protegido en backend).
 */
"use client";

import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { apiGet } from "@/lib/api";
import type { NewUsersStatsPoint } from "@/types";

interface ActiveUsersStats {
  active_trial_users: number;
  active_paid_memberships: number;
  total_registered_users: number;
}

interface PhotosStats {
  total_photos_processed: number;
  avg_processing_seconds: number | null;
}

interface PaymentsStats {
  pending: number;
  approved: number;
  rejected: number;
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  return `${Math.round(seconds / 60)} min`;
}

export default function AdminStatsPage() {
  const [granularity, setGranularity] = useState<"day" | "month">("day");
  const [series, setSeries] = useState<NewUsersStatsPoint[]>([]);
  const [activeStats, setActiveStats] = useState<ActiveUsersStats | null>(null);
  const [photosStats, setPhotosStats] = useState<PhotosStats | null>(null);
  const [paymentsStats, setPaymentsStats] = useState<PaymentsStats | null>(null);

  useEffect(() => {
    apiGet<{ series: NewUsersStatsPoint[] }>(`/admin/stats/new-users?granularity=${granularity}&days=30`).then((res) =>
      setSeries(res.series)
    );
    apiGet<ActiveUsersStats>("/admin/stats/active-users").then(setActiveStats);
    apiGet<PhotosStats>("/admin/stats/photos").then(setPhotosStats).catch(() => {});
    apiGet<PaymentsStats>("/admin/stats/payments").then(setPaymentsStats).catch(() => {});
  }, [granularity]);

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Estadísticas</h1>
      <p className="text-photonix-textMuted mb-6">Crecimiento y actividad de usuarios en Photonix AI.</p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="photonix-card">
          <p className="text-sm text-photonix-textMuted">Usuarios registrados</p>
          <p className="text-3xl font-semibold mt-1">{activeStats?.total_registered_users ?? "—"}</p>
        </div>
        <div className="photonix-card">
          <p className="text-sm text-photonix-textMuted">En prueba gratuita activa</p>
          <p className="text-3xl font-semibold mt-1">{activeStats?.active_trial_users ?? "—"}</p>
        </div>
        <div className="photonix-card">
          <p className="text-sm text-photonix-textMuted">Membresías pagadas activas</p>
          <p className="text-3xl font-semibold mt-1">{activeStats?.active_paid_memberships ?? "—"}</p>
        </div>
        <div className="photonix-card">
          <p className="text-sm text-photonix-textMuted">Fotos procesadas (total)</p>
          <p className="text-3xl font-semibold mt-1">{photosStats?.total_photos_processed ?? "—"}</p>
        </div>
        <div className="photonix-card">
          <p className="text-sm text-photonix-textMuted">Tiempo promedio de procesamiento</p>
          <p className="text-3xl font-semibold mt-1">{formatDuration(photosStats?.avg_processing_seconds ?? null)}</p>
        </div>
        <div className="photonix-card">
          <p className="text-sm text-photonix-textMuted">Pagos SINPE</p>
          <p className="text-sm mt-1">
            {paymentsStats?.pending ?? 0} pendientes · {paymentsStats?.approved ?? 0} aprobados ·{" "}
            {paymentsStats?.rejected ?? 0} rechazados
          </p>
        </div>
      </div>

      <div className="photonix-card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-medium">Nuevos usuarios</h2>
          <div className="flex gap-2">
            <button onClick={() => setGranularity("day")} className={granularity === "day" ? "photonix-btn-primary text-xs" : "photonix-btn-secondary text-xs"}>
              Por día
            </button>
            <button onClick={() => setGranularity("month")} className={granularity === "month" ? "photonix-btn-primary text-xs" : "photonix-btn-secondary text-xs"}>
              Por mes
            </button>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={series}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a3849" />
            <XAxis dataKey="date" stroke="#9fb0c0" fontSize={12} />
            <YAxis stroke="#9fb0c0" fontSize={12} allowDecimals={false} />
            <Tooltip contentStyle={{ background: "#182231", border: "1px solid #2a3849", borderRadius: 8 }} />
            <Line type="monotone" dataKey="new_users" stroke="#4f8ef7" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
