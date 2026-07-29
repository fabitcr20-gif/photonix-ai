/**
 * Panel de exportación de una sesión ya editada: ZIP, Google Drive e
 * Instagram. Reutilizado en "Nueva edición" (justo después de procesar) y en
 * la página de Exportaciones (historial de sesiones listas).
 */
"use client";

import { useEffect, useState } from "react";
import { Loader2, CheckCircle2, AlertCircle, X } from "lucide-react";
import { apiGet, apiPostJson, apiDownloadFile } from "@/lib/api";
import type { PreviewPair } from "@/types";

// Regla de descarga: 1-5 fotos, cada una se descarga individualmente (un
// .zip para tan pocas fotos es una fricción innecesaria); más de 5, se
// mantiene el .zip de siempre. Ver backend/app/routers/export.py.
const MAX_INDIVIDUAL_DOWNLOADS = 5;

type Notice = { type: "success" | "error"; text: string };

export default function ExportPanel({ projectId, photoCount }: { projectId: string; photoCount: number }) {
  const [exporting, setExporting] = useState<string | null>(null);
  const [driveConnected, setDriveConnected] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [photos, setPhotos] = useState<PreviewPair[] | null>(null);
  const [loadingPhotos, setLoadingPhotos] = useState(false);

  const isIndividual = photoCount >= 1 && photoCount <= MAX_INDIVIDUAL_DOWNLOADS;

  useEffect(() => {
    apiGet<{ connected: boolean }>("/export/google-drive/status")
      .then((res) => setDriveConnected(res.connected))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!isIndividual) return;
    setLoadingPhotos(true);
    apiGet<PreviewPair[]>(`/ai/projects/${projectId}/preview-pairs`)
      .then(setPhotos)
      .catch(() => setNotice({ type: "error", text: "No pudimos cargar las fotos de esta sesión para descargarlas." }))
      .finally(() => setLoadingPhotos(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, isIndividual]);

  // El aviso se cierra solo -- igual que un toast -- para no dejar mensajes
  // viejos pegados en pantalla si el usuario exporta varias veces seguidas.
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), 6000);
    return () => clearTimeout(timer);
  }, [notice]);

  async function handleExportZip() {
    setExporting("zip");
    setNotice(null);
    try {
      await apiDownloadFile(`/export/${projectId}/zip`);
    } catch (err) {
      setNotice({ type: "error", text: err instanceof Error ? err.message : "Error al descargar el ZIP." });
    } finally {
      setExporting(null);
    }
  }

  async function handleExportPhoto(photoId: string) {
    setExporting(`photo-${photoId}`);
    setNotice(null);
    try {
      await apiDownloadFile(`/export/${projectId}/photo/${photoId}`);
    } catch (err) {
      setNotice({ type: "error", text: err instanceof Error ? err.message : "Error al descargar la foto." });
    } finally {
      setExporting(null);
    }
  }

  async function handleExportGoogleDrive() {
    if (!driveConnected) {
      try {
        const { authorization_url } = await apiGet<{ authorization_url: string }>("/export/google-drive/connect");
        window.location.href = authorization_url;
      } catch (err) {
        setNotice({ type: "error", text: err instanceof Error ? err.message : "No se pudo iniciar la conexión con Google Drive." });
      }
      return;
    }

    setExporting("google-drive");
    setNotice(null);
    try {
      const res = await apiPostJson<{ folder_url: string }>(`/export/${projectId}/google-drive`, {});
      setNotice({ type: "success", text: `Fotos subidas a Google Drive: ${res.folder_url}` });
    } catch (err) {
      setNotice({ type: "error", text: err instanceof Error ? err.message : "Error al subir a Google Drive." });
    } finally {
      setExporting(null);
    }
  }

  async function handleExportInstagram() {
    setExporting("instagram");
    setNotice(null);
    try {
      await apiPostJson(`/export/${projectId}/instagram`, {});
      setNotice({ type: "success", text: "Publicación en Instagram iniciada." });
    } catch (err) {
      setNotice({ type: "error", text: err instanceof Error ? err.message : "Esta integración todavía no está disponible." });
    } finally {
      setExporting(null);
    }
  }

  return (
    <div>
      {isIndividual ? (
        loadingPhotos ? (
          <p className="text-sm text-photonix-textMuted flex items-center gap-2">
            <Loader2 size={14} className="animate-spin" />
            Cargando fotos...
          </p>
        ) : photoCount === 1 && photos && photos[0] ? (
          <button
            onClick={() => handleExportPhoto(photos[0].photo_id)}
            disabled={exporting === `photo-${photos[0].photo_id}`}
            className="photonix-btn-primary inline-flex items-center gap-2"
          >
            {exporting === `photo-${photos[0].photo_id}` && <Loader2 size={16} className="animate-spin" />}
            {exporting === `photo-${photos[0].photo_id}` ? "Descargando..." : "Descargar JPG"}
          </button>
        ) : photos && photos.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {photos.map((p, i) => (
              <button
                key={p.photo_id}
                onClick={() => handleExportPhoto(p.photo_id)}
                disabled={exporting === `photo-${p.photo_id}`}
                className="photonix-btn-secondary inline-flex items-center gap-2"
              >
                {exporting === `photo-${p.photo_id}` && <Loader2 size={16} className="animate-spin" />}
                {exporting === `photo-${p.photo_id}` ? "Descargando..." : `Descargar JPG ${i + 1}`}
              </button>
            ))}
          </div>
        ) : (
          <p className="text-sm text-photonix-danger flex items-center gap-2">
            <AlertCircle size={14} />
            Esta sesión todavía no tiene fotos editadas disponibles para descargar.
          </p>
        )
      ) : (
        <button onClick={handleExportZip} disabled={exporting === "zip"} className="photonix-btn-secondary inline-flex items-center gap-2">
          {exporting === "zip" && <Loader2 size={16} className="animate-spin" />}
          {exporting === "zip" ? "Preparando ZIP..." : "Descargar en ZIP"}
        </button>
      )}

      <div className="flex flex-wrap gap-3 mt-3">
        <button onClick={handleExportGoogleDrive} disabled={exporting === "google-drive"} className="photonix-btn-secondary inline-flex items-center gap-2">
          {exporting === "google-drive" && <Loader2 size={16} className="animate-spin" />}
          {exporting === "google-drive" ? "Enviando..." : driveConnected ? "Subir a Google Drive" : "Conectar Google Drive"}
        </button>
        <button onClick={handleExportInstagram} disabled={exporting === "instagram"} className="photonix-btn-secondary inline-flex items-center gap-2">
          {exporting === "instagram" && <Loader2 size={16} className="animate-spin" />}
          {exporting === "instagram" ? "Enviando..." : "Subir a Instagram"}
        </button>
      </div>

      {notice && (
        <div
          role="alert"
          className={`mt-3 flex items-start gap-2.5 rounded-lg border px-3.5 py-2.5 text-sm ${
            notice.type === "error"
              ? "border-photonix-danger/30 bg-photonix-danger/10 text-photonix-danger"
              : "border-photonix-success/30 bg-photonix-success/10 text-photonix-success"
          }`}
        >
          {notice.type === "error" ? (
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
          ) : (
            <CheckCircle2 size={16} className="mt-0.5 shrink-0" />
          )}
          <span className="flex-1 break-words">{notice.text}</span>
          <button onClick={() => setNotice(null)} aria-label="Cerrar aviso" className="shrink-0 opacity-70 hover:opacity-100">
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
