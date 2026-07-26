/** Historial de sesiones del usuario. */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiGet } from "@/lib/api";
import type { ProjectSummary } from "@/types";

const STATUS_LABELS: Record<string, string> = {
  processing: "Procesando",
  review: "Lista",
};

export default function HistoryPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<ProjectSummary[]>("/uploads/projects")
      .then(setProjects)
      .catch(() => setError("No pudimos cargar tu historial. Intenta recargar la página."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold mb-1">Historial</h1>
      <p className="text-photonix-textMuted mb-6">Todas tus sesiones, más reciente primero.</p>

      {loading && <p className="text-photonix-textMuted text-sm">Cargando...</p>}
      {error && <p className="text-sm text-photonix-danger mb-4">{error}</p>}

      {!loading && !error && projects.length === 0 && (
        <div className="photonix-card text-center text-photonix-textMuted">
          Todavía no has cargado ninguna sesión.{" "}
          <Link href="/dashboard/upload" className="text-photonix-accent hover:underline">
            Empieza una edición nueva
          </Link>
          .
        </div>
      )}

      <div className="flex flex-col gap-2">
        {projects.map((p) => (
          <div key={p.id} className="photonix-card flex items-center justify-between">
            <div>
              <p className="font-medium text-sm">{p.name}</p>
              <p className="text-xs text-photonix-textMuted mt-0.5">
                {p.photo_count} fotos · {new Date(p.created_at).toLocaleDateString("es-CR")}
              </p>
            </div>
            <span className={`photonix-chip ${p.status === "review" ? "!text-photonix-success" : ""}`}>
              {STATUS_LABELS[p.status] ?? p.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
