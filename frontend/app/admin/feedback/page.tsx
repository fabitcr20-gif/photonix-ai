/** Panel de administrador: retroalimentación de clientes tras cada sesión editada. */
"use client";

import { useEffect, useState } from "react";
import { Star } from "lucide-react";
import { apiGet, apiPostJson } from "@/lib/api";
import type { FeedbackAdminView } from "@/types";

const STATUS_LABELS: Record<string, string> = {
  pending: "Pendiente",
  in_review: "En análisis",
  implemented: "Implementada",
  discarded: "Descartada",
};

export default function AdminFeedbackPage() {
  const [items, setItems] = useState<FeedbackAdminView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<FeedbackAdminView[]>("/admin/feedback");
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la retroalimentación.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleStatusChange(id: string, status: string) {
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, status: status as FeedbackAdminView["status"] } : i)));
    await apiPostJson(`/admin/feedback/${id}/status`, { status });
  }

  const averageRating = items.length
    ? (items.reduce((sum, i) => sum + i.rating, 0) / items.length).toFixed(1)
    : "—";

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Retroalimentación</h1>
      <p className="text-photonix-textMuted mb-6">Calificaciones y comentarios enviados por los clientes.</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        <div className="photonix-card">
          <p className="text-sm text-photonix-textMuted">Calificación promedio</p>
          <p className="text-3xl font-semibold mt-1">{averageRating} / 5</p>
        </div>
        <div className="photonix-card">
          <p className="text-sm text-photonix-textMuted">Respuestas recibidas</p>
          <p className="text-3xl font-semibold mt-1">{items.length}</p>
        </div>
      </div>

      {loading && <p className="text-photonix-textMuted">Cargando...</p>}
      {error && <p className="text-sm text-photonix-danger">{error}</p>}

      {!loading && !error && items.length === 0 && (
        <div className="photonix-card text-center text-photonix-textMuted">
          Todavía no hay retroalimentación de clientes.
        </div>
      )}

      <div className="flex flex-col gap-4">
        {items.map((item) => (
          <div key={item.id} className="photonix-card">
            <div className="flex items-center justify-between mb-2">
              <div>
                <p className="font-medium">{item.profiles?.email ?? item.user_id}</p>
                <p className="text-xs text-photonix-textMuted">
                  {new Date(item.created_at).toLocaleDateString("es-CR")}
                  {item.projects?.total_count != null && ` · sesión de ${item.projects.total_count} fotos`}
                </p>
              </div>
              <div className="flex gap-0.5">
                {[1, 2, 3, 4, 5].map((n) => (
                  <Star
                    key={n}
                    size={16}
                    className={n <= item.rating ? "fill-photonix-accent text-photonix-accent" : "text-photonix-border"}
                  />
                ))}
              </div>
            </div>

            {item.comment && <p className="text-sm text-photonix-textMuted mb-3">{item.comment}</p>}

            <select
              value={item.status}
              onChange={(e) => handleStatusChange(item.id, e.target.value)}
              className="photonix-input text-xs w-auto px-3 py-1.5"
            >
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>
    </div>
  );
}
