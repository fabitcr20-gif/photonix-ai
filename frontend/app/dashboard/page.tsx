/** Resumen del dashboard: estado de membresía y accesos rápidos. */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiGet } from "@/lib/api";
import type { Profile, UploadStatsSummary } from "@/types";

const STATUS_LABELS: Record<string, string> = {
  processing: "Procesando",
  review: "Lista",
  error: "Error",
};

export default function DashboardHome() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [summary, setSummary] = useState<UploadStatsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([apiGet<Profile>("/auth/me"), apiGet<UploadStatsSummary>("/uploads/stats/summary")])
      .then(([p, s]) => {
        setProfile(p);
        setSummary(s);
      })
      .catch(() => setError("No pudimos cargar los datos de tu cuenta. Intenta recargar la página."))
      .finally(() => setLoading(false));
  }, []);

  const maxBatch = profile?.plan_features?.max_batch_photos ?? null;

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold mb-1">
        Hola{profile?.full_name ? `, ${profile.full_name}` : ""} 👋
      </h1>
      <p className="text-photonix-textMuted mb-8">
        Este es el resumen de tu cuenta en Photonix AI.
      </p>

      {loading && <p className="text-photonix-textMuted text-sm mb-6">Cargando...</p>}
      {error && <p className="text-sm text-photonix-danger mb-6">{error}</p>}

      {!loading && !error && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <div className="photonix-card">
              <p className="text-sm text-photonix-textMuted">Plan actual</p>
              <p className="text-xl font-semibold mt-1 capitalize">
                {profile?.membership_plan ?? "—"}
              </p>
            </div>
            <div className="photonix-card">
              <p className="text-sm text-photonix-textMuted">Estado</p>
              <p className="text-xl font-semibold mt-1 capitalize">
                {profile?.membership_status ?? "—"}
              </p>
            </div>
            <div className="photonix-card">
              <p className="text-sm text-photonix-textMuted">Fin de prueba gratuita</p>
              <p className="text-xl font-semibold mt-1">
                {profile?.trial_ends_at ? new Date(profile.trial_ends_at).toLocaleDateString("es-CR") : "—"}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
            <div className="photonix-card">
              <p className="text-sm text-photonix-textMuted">Fotos procesadas este mes</p>
              <p className="text-xl font-semibold mt-1">{summary?.photos_this_month ?? 0}</p>
            </div>
            <div className="photonix-card">
              <p className="text-sm text-photonix-textMuted">Uso de tu plan</p>
              <p className="text-sm mt-1">
                {maxBatch ? `Hasta ${maxBatch} fotos por carga masiva` : "Fotos por carga masiva ilimitadas"}
                {profile?.plan_features?.object_removal && " · Eliminación de objetos incluida"}
              </p>
            </div>
          </div>

          <div className="flex gap-3 mb-8">
            <Link href="/dashboard/upload" className="photonix-btn-primary">
              Cargar fotos
            </Link>
            <Link href="/dashboard/billing" className="photonix-btn-secondary">
              Ver planes
            </Link>
          </div>

          {summary && summary.recent_projects.length > 0 && (
            <div className="photonix-card">
              <h2 className="font-medium mb-3">Procesamientos recientes</h2>
              <div className="flex flex-col gap-2">
                {summary.recent_projects.map((p) => (
                  <div key={p.id} className="flex items-center justify-between text-sm py-2 border-b border-photonix-border last:border-0">
                    <div>
                      <p>{p.name}</p>
                      <p className="text-xs text-photonix-textMuted mt-0.5">
                        {p.total_count} fotos · {new Date(p.created_at).toLocaleDateString("es-CR")}
                      </p>
                    </div>
                    <span className={`photonix-chip ${p.status === "review" ? "!text-photonix-success" : ""}`}>
                      {STATUS_LABELS[p.status] ?? p.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
