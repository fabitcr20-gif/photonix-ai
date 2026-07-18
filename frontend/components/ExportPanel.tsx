/**
 * Panel de exportación de una sesión ya editada: ZIP, Google Drive e
 * Instagram. Reutilizado en "Nueva edición" (justo después de procesar) y en
 * la página de Exportaciones (historial de sesiones listas).
 */
"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPostJson, apiDownloadFile } from "@/lib/api";

export default function ExportPanel({ projectId }: { projectId: string }) {
  const [exporting, setExporting] = useState<string | null>(null);
  const [driveConnected, setDriveConnected] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    apiGet<{ connected: boolean }>("/export/google-drive/status")
      .then((res) => setDriveConnected(res.connected))
      .catch(() => {});
  }, []);

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
      <div className="flex flex-wrap gap-3">
        <button onClick={handleExportZip} disabled={exporting === "zip"} className="photonix-btn-secondary">
          {exporting === "zip" ? "Preparando ZIP..." : "Descargar en ZIP"}
        </button>
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
