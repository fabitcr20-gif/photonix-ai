/**
 * Panel de exportación de una sesión ya editada: ZIP, Google Drive e
 * Instagram. Reutilizado en "Nueva edición" (justo después de procesar) y en
 * la página de Exportaciones (historial de sesiones listas).
 */
"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPostJson, apiDownloadFile } from "@/lib/api";
import type { PreviewPair } from "@/types";

// Regla de descarga: 1-5 fotos, cada una se descarga individualmente (un
// .zip para tan pocas fotos es una fricción innecesaria); más de 5, se
// mantiene el .zip de siempre. Ver backend/app/routers/export.py.
const MAX_INDIVIDUAL_DOWNLOADS = 5;

export default function ExportPanel({ projectId, photoCount }: { projectId: string; photoCount: number }) {
  const [exporting, setExporting] = useState<string | null>(null);
  const [driveConnected, setDriveConnected] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
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
      .catch(() => setMessage("No pudimos cargar las fotos de esta sesión para descargarlas."))
      .finally(() => setLoadingPhotos(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, isIndividual]);

  async function handleExportZip() {
    setExporting("zip");
    setMessage(null);
    try {
      await apiDownloadFile(`/export/${projectId}/zip`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Error al descargar el ZIP.");
    } finally {
      setExporting(null);
    }
  }

  async function handleExportPhoto(photoId: string) {
    setExporting(`photo-${photoId}`);
    setMessage(null);
    try {
      await apiDownloadFile(`/export/${projectId}/photo/${photoId}`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Error al descargar la foto.");
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
        setMessage(err instanceof Error ? err.message : "No se pudo iniciar la conexión con Google Drive.");
      }
      return;
    }

    setExporting("google-drive");
    setMessage(null);
    try {
      const res = await apiPostJson<{ folder_url: string }>(`/export/${projectId}/google-drive`, {});
      setMessage(`Fotos subidas a Google Drive: ${res.folder_url}`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Error al subir a Google Drive.");
    } finally {
      setExporting(null);
    }
  }

  async function handleExportInstagram() {
    setExporting("instagram");
    setMessage(null);
    try {
      await apiPostJson(`/export/${projectId}/instagram`, {});
      setMessage("Publicación en Instagram iniciada.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Esta integración todavía no está disponible.");
    } finally {
      setExporting(null);
    }
  }

  return (
    <div>
      {isIndividual ? (
        loadingPhotos ? (
          <p className="text-sm text-photonix-textMuted">Cargando fotos...</p>
        ) : photoCount === 1 && photos && photos[0] ? (
          <button
            onClick={() => handleExportPhoto(photos[0].photo_id)}
            disabled={exporting === `photo-${photos[0].photo_id}`}
            className="photonix-btn-primary"
          >
            {exporting === `photo-${photos[0].photo_id}` ? "Descargando..." : "Descargar JPG"}
          </button>
        ) : (
          <div className="flex flex-wrap gap-2">
            {(photos || []).map((p, i) => (
              <button
                key={p.photo_id}
                onClick={() => handleExportPhoto(p.photo_id)}
                disabled={exporting === `photo-${p.photo_id}`}
                className="photonix-btn-secondary"
              >
                {exporting === `photo-${p.photo_id}` ? "Descargando..." : `Descargar JPG ${i + 1}`}
              </button>
            ))}
          </div>
        )
      ) : (
        <button onClick={handleExportZip} disabled={exporting === "zip"} className="photonix-btn-secondary">
          {exporting === "zip" ? "Preparando ZIP..." : "Descargar en ZIP"}
        </button>
      )}

      <div className="flex flex-wrap gap-3 mt-3">
        <button onClick={handleExportGoogleDrive} disabled={exporting === "google-drive"} className="photonix-btn-secondary">
          {exporting === "google-drive" ? "Enviando..." : driveConnected ? "Subir a Google Drive" : "Conectar Google Drive"}
        </button>
        <button onClick={handleExportInstagram} disabled={exporting === "instagram"} className="photonix-btn-secondary">
          {exporting === "instagram" ? "Enviando..." : "Subir a Instagram"}
        </button>
      </div>
      {message && <p className="text-sm text-photonix-accent mt-3">{message}</p>}
    </div>
  );
}
