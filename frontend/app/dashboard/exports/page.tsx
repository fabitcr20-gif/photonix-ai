/** Exportaciones: sesiones ya editadas, listas para descargar o enviar. */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Pencil, Eye, Trash2, Check, X } from "lucide-react";
import ExportPanel from "@/components/ExportPanel";
import ProjectPreviewModal from "@/components/ProjectPreviewModal";
import { apiGet, apiPatchJson, apiDelete } from "@/lib/api";
import type { ProjectSummary } from "@/types";

export default function ExportsPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [nameDraft, setNameDraft] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    apiGet<ProjectSummary[]>("/uploads/projects")
      .then((all) => setProjects(all.filter((p) => p.status === "review")))
      .finally(() => setLoading(false));
  }, []);

  function startRename(p: ProjectSummary) {
    setRenamingId(p.id);
    setNameDraft(p.name);
  }

  async function confirmRename(id: string) {
    const name = nameDraft.trim();
    if (!name) return;
    await apiPatchJson(`/uploads/projects/${id}`, { name });
    setProjects((prev) => prev.map((p) => (p.id === id ? { ...p, name } : p)));
    setRenamingId(null);
  }

  async function handleDelete(id: string) {
    if (!confirm("¿Eliminar esta sesión? Las fotos editadas se perderán. Esta acción no se puede deshacer.")) return;
    setDeletingId(id);
    try {
      await apiDelete(`/uploads/projects/${id}`);
      setProjects((prev) => prev.filter((p) => p.id !== id));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold mb-1">Exportaciones</h1>
      <p className="text-photonix-textMuted mb-6">Sesiones ya editadas, listas para descargar o compartir.</p>

      {loading && <p className="text-photonix-textMuted text-sm">Cargando...</p>}

      {!loading && projects.length === 0 && (
        <div className="photonix-card text-center text-photonix-textMuted">
          No tienes sesiones listas todavía.{" "}
          <Link href="/dashboard/upload" className="text-photonix-accent hover:underline">
            Empieza una edición nueva
          </Link>
          .
        </div>
      )}

      <div className="flex flex-col gap-3">
        {projects.map((p) => (
          <div key={p.id} className="photonix-card">
            <div className="flex items-center justify-between gap-3">
              <button
                onClick={() => setExpandedId(expandedId === p.id ? null : p.id)}
                className="flex-1 min-w-0 text-left"
              >
                {renamingId === p.id ? (
                  <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                    <input
                      value={nameDraft}
                      onChange={(e) => setNameDraft(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && confirmRename(p.id)}
                      autoFocus
                      className="photonix-input text-sm py-1 px-2 flex-1"
                    />
                    <button onClick={() => confirmRename(p.id)} aria-label="Guardar nombre" className="text-photonix-accent">
                      <Check size={16} />
                    </button>
                    <button onClick={() => setRenamingId(null)} aria-label="Cancelar" className="text-photonix-textMuted">
                      <X size={16} />
                    </button>
                  </div>
                ) : (
                  <>
                    <p className="font-medium text-sm truncate">{p.name}</p>
                    <p className="text-xs text-photonix-textMuted mt-0.5">
                      {p.photo_count} fotos · {new Date(p.created_at).toLocaleDateString("es-CR")}
                    </p>
                  </>
                )}
              </button>

              {renamingId !== p.id && (
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => startRename(p)}
                    aria-label="Cambiar nombre"
                    className="p-2 rounded-lg text-photonix-textMuted hover:text-photonix-text hover:bg-white/[0.04] transition-colors"
                  >
                    <Pencil size={15} />
                  </button>
                  <button
                    onClick={() => setPreviewId(p.id)}
                    aria-label="Vista previa"
                    className="p-2 rounded-lg text-photonix-textMuted hover:text-photonix-text hover:bg-white/[0.04] transition-colors"
                  >
                    <Eye size={15} />
                  </button>
                  <button
                    onClick={() => handleDelete(p.id)}
                    disabled={deletingId === p.id}
                    aria-label="Eliminar sesión"
                    className="p-2 rounded-lg text-photonix-textMuted hover:text-photonix-danger hover:bg-photonix-danger/10 transition-colors"
                  >
                    <Trash2 size={15} />
                  </button>
                  <span className="photonix-chip ml-1">{expandedId === p.id ? "Ocultar" : "Exportar"}</span>
                </div>
              )}
            </div>
            {expandedId === p.id && (
              <div className="mt-4 pt-4 border-t border-photonix-border">
                <ExportPanel projectId={p.id} />
              </div>
            )}
          </div>
        ))}
      </div>

      {previewId && <ProjectPreviewModal projectId={previewId} onClose={() => setPreviewId(null)} />}
    </div>
  );
}
