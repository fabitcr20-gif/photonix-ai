/** Vista previa rápida (antes/después) de una sesión ya editada, sin salir de Exportaciones/Historial. */
"use client";

import { useEffect, useState } from "react";
import { X, Loader2 } from "lucide-react";
import BeforeAfterSlider from "@/components/BeforeAfterSlider";
import { apiGet } from "@/lib/api";
import type { PreviewPair } from "@/types";

export default function ProjectPreviewModal({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const [pairs, setPairs] = useState<PreviewPair[]>([]);
  const [loading, setLoading] = useState(true);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    apiGet<PreviewPair[]>(`/ai/projects/${projectId}/preview-pairs`)
      .then(setPairs)
      .finally(() => setLoading(false));
  }, [projectId]);

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div className="photonix-card w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium">Vista previa</h3>
          <button onClick={onClose} aria-label="Cerrar" className="text-photonix-textMuted hover:text-photonix-text">
            <X size={18} />
          </button>
        </div>

        {loading && (
          <p className="text-sm text-photonix-textMuted flex items-center gap-2">
            <Loader2 size={14} className="animate-spin" /> Cargando...
          </p>
        )}

        {!loading && pairs.length === 0 && (
          <p className="text-sm text-photonix-textMuted">Esta sesión todavía no tiene fotos editadas para mostrar.</p>
        )}

        {!loading && pairs.length > 0 && (
          <>
            <p className="text-xs text-photonix-textMuted mb-2">
              Foto {index + 1} de {pairs.length}
            </p>
            <BeforeAfterSlider beforeUrl={pairs[index].original_url} afterUrl={pairs[index].edited_url} />
            <div className="flex gap-2 mt-3">
              <button
                onClick={() => setIndex((i) => Math.max(0, i - 1))}
                disabled={index === 0}
                className="photonix-btn-secondary text-sm"
              >
                Anterior
              </button>
              <button
                onClick={() => setIndex((i) => Math.min(pairs.length - 1, i + 1))}
                disabled={index === pairs.length - 1}
                className="photonix-btn-secondary text-sm"
              >
                Siguiente
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
