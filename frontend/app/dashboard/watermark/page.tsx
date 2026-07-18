/**
 * Página de configuración de Marca de Agua.
 * Sube un logo PNG transparente y se arrastra libremente sobre una vista
 * previa (foto de muestra) para posicionarlo con precisión, además de
 * botones rápidos para los 5 puntos cardinales. La posición se guarda como
 * porcentaje del ancho/alto (ver backend/app/services/watermark_service.py),
 * así se ve igual sin importar el tamaño real de cada foto procesada.
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { apiGet, apiPostForm } from "@/lib/api";
import type { WatermarkPosition } from "@/types";

interface WatermarkConfigData {
  logo_url: string;
  position: WatermarkPosition;
  opacity: number;
  scale: number;
  pos_x: number | null;
  pos_y: number | null;
  rotation: number | null;
}

const PRESETS: { value: WatermarkPosition; label: string; x: number; y: number }[] = [
  { value: "north", label: "Norte", x: 50, y: 12 },
  { value: "south", label: "Sur", x: 50, y: 88 },
  { value: "east", label: "Este", x: 88, y: 50 },
  { value: "west", label: "Oeste", x: 12, y: 50 },
  { value: "center", label: "Centro", x: 50, y: 50 },
];

export default function WatermarkPage() {
  const previewRef = useRef<HTMLDivElement>(null);

  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [position, setPosition] = useState<WatermarkPosition>("south");
  const [opacity, setOpacity] = useState(0.8);
  const [scale, setScale] = useState(0.18);
  const [posX, setPosX] = useState(50);
  const [posY, setPosY] = useState(88);
  const [rotation, setRotation] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<WatermarkConfigData | null>("/watermark/config")
      .then((cfg) => {
        if (!cfg) return;
        setLogoUrl(cfg.logo_url);
        setPosition(cfg.position);
        setOpacity(cfg.opacity);
        setScale(cfg.scale);
        if (cfg.pos_x != null) setPosX(cfg.pos_x);
        if (cfg.pos_y != null) setPosY(cfg.pos_y);
        if (cfg.rotation != null) setRotation(cfg.rotation);
      })
      .catch(() => setError("No pudimos cargar tu configuración guardada de marca de agua."));
  }, []);

  async function handleUploadLogo() {
    if (!logoFile) return;
    setError(null);
    if (!logoFile.type.includes("png")) {
      setError("El logo debe ser un archivo PNG con fondo transparente.");
      return;
    }
    try {
      const formData = new FormData();
      formData.append("logo", logoFile);
      const res = await apiPostForm<{ logo_url: string }>("/watermark/upload-logo", formData);
      setLogoUrl(res.logo_url);
      setStatus("Logo cargado. Arrástralo sobre la vista previa para ubicarlo donde quieras.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo subir el logo.");
    }
  }

  function applyPreset(preset: (typeof PRESETS)[number]) {
    setPosition(preset.value);
    setPosX(preset.x);
    setPosY(preset.y);
  }

  function handlePointerDown(e: React.PointerEvent<HTMLImageElement>) {
    e.preventDefault();
    setDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  }

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!dragging || !previewRef.current) return;
    const rect = previewRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
    const y = Math.max(0, Math.min(100, ((e.clientY - rect.top) / rect.height) * 100));
    setPosX(x);
    setPosY(y);
    setPosition("custom");
  }

  function handlePointerUp() {
    setDragging(false);
  }

  async function handleSaveConfig() {
    if (!logoUrl) return;
    setError(null);
    try {
      const formData = new FormData();
      formData.append("logo_url", logoUrl);
      formData.append("position", position);
      formData.append("opacity", String(opacity));
      formData.append("scale", String(scale));
      formData.append("pos_x", String(posX));
      formData.append("pos_y", String(posY));
      formData.append("rotation", String(rotation));
      await apiPostForm("/watermark/config", formData);
      setStatus("Configuración de marca de agua guardada.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar la configuración.");
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold mb-1">Marca de Agua</h1>
      <p className="text-photonix-textMuted mb-6">
        Sube tu logo en PNG con fondo transparente y arrástralo sobre la vista previa para ubicarlo exactamente donde quieras.
      </p>

      <div className="photonix-card mb-6">
        <h2 className="font-medium mb-3">1. Logo (PNG transparente)</h2>
        <input
          type="file"
          accept="image/png"
          onChange={(e) => setLogoFile(e.target.files?.[0] ?? null)}
          className="photonix-input mb-4"
        />
        <button onClick={handleUploadLogo} disabled={!logoFile} className="photonix-btn-secondary">
          Subir logo
        </button>
        {error && <p className="text-sm text-photonix-danger mt-3">{error}</p>}
      </div>

      {logoUrl && (
        <div className="photonix-card mb-6">
          <h2 className="font-medium mb-1">2. Vista previa — arrastra el logo</h2>
          <p className="text-sm text-photonix-textMuted mb-4">
            Haz clic y arrastra el logo sobre la foto de muestra, o usa un punto cardinal como atajo.
          </p>

          <div
            ref={previewRef}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            className="relative w-full rounded-xl2 overflow-hidden select-none border border-photonix-border"
            style={{ aspectRatio: "3 / 2" }}
          >
            <img
              src="/watermark-sample.svg"
              alt="Foto de muestra"
              className="absolute inset-0 w-full h-full object-cover pointer-events-none"
              draggable={false}
            />
            <img
              src={logoUrl}
              alt="Tu marca de agua"
              onPointerDown={handlePointerDown}
              draggable={false}
              className="absolute cursor-move"
              style={{
                left: `${posX}%`,
                top: `${posY}%`,
                width: `${scale * 100}%`,
                transform: `translate(-50%, -50%) rotate(${rotation}deg)`,
                opacity,
                touchAction: "none",
              }}
            />
          </div>

          <div className="grid grid-cols-5 gap-2 mt-4">
            {PRESETS.map((p) => (
              <button
                key={p.value}
                onClick={() => applyPreset(p)}
                className={position === p.value ? "photonix-btn-primary text-xs" : "photonix-btn-secondary text-xs"}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {logoUrl && (
        <div className="photonix-card">
          <h2 className="font-medium mb-4">3. Opacidad y tamaño</h2>

          <div className="mb-4">
            <label className="text-xs text-photonix-textMuted">Opacidad: {Math.round(opacity * 100)}%</label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={opacity}
              onChange={(e) => setOpacity(Number(e.target.value))}
              className="w-full accent-photonix-accent"
            />
          </div>

          <div className="mb-6">
            <label className="text-xs text-photonix-textMuted">Tamaño relativo: {Math.round(scale * 100)}%</label>
            <input
              type="range"
              min={0.05}
              max={0.6}
              step={0.01}
              value={scale}
              onChange={(e) => setScale(Number(e.target.value))}
              className="w-full accent-photonix-accent"
            />
          </div>

          <div className="mb-6">
            <label className="text-xs text-photonix-textMuted">Rotación: {rotation}°</label>
            <input
              type="range"
              min={-180}
              max={180}
              step={1}
              value={rotation}
              onChange={(e) => setRotation(Number(e.target.value))}
              className="w-full accent-photonix-accent"
            />
          </div>

          <button onClick={handleSaveConfig} className="photonix-btn-primary">
            Guardar posición favorita
          </button>

          {status && <p className="text-sm text-photonix-accent mt-4">{status}</p>}
        </div>
      )}
    </div>
  );
}
