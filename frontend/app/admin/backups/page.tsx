/**
 * Respaldos de la base de datos: lista los respaldos diarios automáticos
 * (ver backend/app/services/backup_service.py), permite disparar uno manual
 * y descargar cualquiera a la propia computadora del admin -- la única
 * copia realmente independiente de Supabase.
 */
"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPostJson, apiDownloadFile } from "@/lib/api";
import type { BackupInfo } from "@/types";

function parseBackupDate(filename: string): Date | null {
  const match = filename.match(/^backup-(\d{4})-(\d{2})-(\d{2})T(\d{2})-(\d{2})-(\d{2})Z\.json\.gz$/);
  if (!match) return null;
  const [, y, mo, d, h, mi, s] = match;
  return new Date(Date.UTC(Number(y), Number(mo) - 1, Number(d), Number(h), Number(mi), Number(s)));
}

export default function BackupsPage() {
  const [items, setItems] = useState<BackupInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadBackups() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<BackupInfo[]>("/admin/backups");
      setItems(data);
    } catch {
      setError("No se pudo cargar la lista de respaldos.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBackups();
  }, []);

  async function runNow() {
    setRunning(true);
    setError(null);
    try {
      await apiPostJson("/admin/backups/run", {});
      await loadBackups();
    } catch {
      setError("No se pudo ejecutar el respaldo. Intenta de nuevo.");
    } finally {
      setRunning(false);
    }
  }

  async function download(filename: string) {
    try {
      await apiDownloadFile(`/admin/backups/${filename}/download`);
    } catch {
      setError("No se pudo descargar ese respaldo.");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Respaldos de la Base de Datos</h1>
      <p className="text-photonix-textMuted mb-6">
        Todos los días se guarda automáticamente una copia completa de la base de datos, aparte de las
        tablas en vivo. Descarga cualquier respaldo a tu computadora para tener una copia fuera de
        Supabase.
      </p>

      <button onClick={runNow} disabled={running} className="photonix-btn-primary mb-6">
        {running ? "Ejecutando respaldo..." : "Ejecutar respaldo ahora"}
      </button>

      {error && <p className="text-photonix-danger mb-4">{error}</p>}

      {loading && <p className="text-photonix-textMuted">Cargando...</p>}

      {!loading && items.length === 0 && !error && (
        <div className="photonix-card text-center text-photonix-textMuted">
          Todavía no hay respaldos. Se genera el primero automáticamente, o puedes ejecutar uno ahora.
        </div>
      )}

      <div className="flex flex-col gap-3">
        {items.map((item) => {
          const date = parseBackupDate(item.filename);
          return (
            <div key={item.filename} className="photonix-card flex items-center justify-between gap-4">
              <div>
                <p className="font-medium">
                  {date ? date.toLocaleString("es-CR", { dateStyle: "medium", timeStyle: "short" }) : item.filename}
                </p>
                <p className="text-sm text-photonix-textMuted">{item.filename}</p>
              </div>
              <button onClick={() => download(item.filename)} className="photonix-btn-secondary shrink-0">
                Descargar
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
