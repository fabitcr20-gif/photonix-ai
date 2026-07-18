/**
 * Comparador Antes/Después profesional: slider deslizable (clip-path, sin
 * desalineación de imágenes), modo lado a lado, zoom sincronizado (afecta
 * ambas imágenes por igual) y pantalla completa.
 */
"use client";

import { useRef, useState } from "react";
import { Maximize2, Minimize2, Columns2, GripVertical, ZoomIn, ZoomOut, Pencil } from "lucide-react";

export default function BeforeAfterSlider({
  beforeUrl,
  afterUrl,
  label,
  onEditClick,
}: {
  beforeUrl: string;
  afterUrl: string;
  label?: string;
  onEditClick?: () => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [sliderPos, setSliderPos] = useState(50);
  const [dragging, setDragging] = useState(false);
  const [sideBySide, setSideBySide] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [zoom, setZoom] = useState(1);

  function updateFromPointer(clientX: number) {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const pct = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
    setSliderPos(pct);
  }

  function handlePointerDown(e: React.PointerEvent) {
    setDragging(true);
    (e.target as Element).setPointerCapture(e.pointerId);
    updateFromPointer(e.clientX);
  }
  function handlePointerMove(e: React.PointerEvent) {
    if (!dragging) return;
    updateFromPointer(e.clientX);
  }
  function handlePointerUp() {
    setDragging(false);
  }

  return (
    <div className={fullscreen ? "fixed inset-0 z-50 bg-black flex flex-col p-6" : "flex flex-col"}>
      <div className="flex items-center justify-between mb-3">
        {label && <p className="text-sm text-photonix-textMuted">{label}</p>}
        <div className="flex items-center gap-2 ml-auto">
          {onEditClick && (
            <button
              onClick={onEditClick}
              aria-label="Editar esta foto manualmente"
              className="photonix-btn-secondary text-xs px-2.5 py-1.5 inline-flex items-center gap-1.5"
            >
              <Pencil size={14} />
              Editar
            </button>
          )}
          <button
            onClick={() => setZoom((z) => Math.max(1, z - 0.25))}
            aria-label="Alejar"
            className="photonix-btn-secondary text-xs px-2.5 py-1.5"
          >
            <ZoomOut size={14} />
          </button>
          <span className="text-xs text-photonix-textMuted w-10 text-center tabular-nums">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
            aria-label="Acercar"
            className="photonix-btn-secondary text-xs px-2.5 py-1.5"
          >
            <ZoomIn size={14} />
          </button>
          <button
            onClick={() => setSideBySide((v) => !v)}
            aria-pressed={sideBySide}
            aria-label="Comparación lado a lado"
            className="photonix-btn-secondary text-xs px-2.5 py-1.5"
          >
            <Columns2 size={14} />
          </button>
          <button
            onClick={() => setFullscreen((v) => !v)}
            aria-label="Pantalla completa"
            className="photonix-btn-secondary text-xs px-2.5 py-1.5"
          >
            {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        </div>
      </div>

      {sideBySide ? (
        <div className="grid grid-cols-2 gap-2 flex-1 min-h-0">
          {[
            { url: beforeUrl, tag: "Antes" },
            { url: afterUrl, tag: "Después" },
          ].map(({ url, tag }) => (
            <div key={tag} className="relative rounded-xl2 overflow-hidden border border-photonix-border bg-black" style={{ aspectRatio: fullscreen ? undefined : "3 / 2" }}>
              <div className="w-full h-full overflow-hidden flex items-center justify-center">
                <img
                  src={url}
                  alt={tag}
                  className="max-w-none transition-transform duration-150"
                  style={{ width: "100%", height: "100%", objectFit: "contain", transform: `scale(${zoom})` }}
                />
              </div>
              <span className="absolute top-2 left-2 text-xs px-2 py-1 rounded-full bg-black/60 text-white">{tag}</span>
            </div>
          ))}
        </div>
      ) : (
        <div
          ref={containerRef}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          className="relative w-full flex-1 min-h-0 rounded-xl2 overflow-hidden select-none border border-photonix-border bg-black cursor-ew-resize"
          style={{ aspectRatio: fullscreen ? undefined : "3 / 2" }}
        >
          <div className="absolute inset-0 overflow-hidden" style={{ transform: `scale(${zoom})`, transformOrigin: "center" }}>
            <img src={beforeUrl} alt="Antes" className="absolute inset-0 w-full h-full object-contain pointer-events-none" draggable={false} />
            <img
              src={afterUrl}
              alt="Después"
              className="absolute inset-0 w-full h-full object-contain pointer-events-none"
              style={{ clipPath: `inset(0 ${100 - sliderPos}% 0 0)` }}
              draggable={false}
            />
          </div>

          <span className="absolute top-2 left-2 text-xs px-2 py-1 rounded-full bg-black/60 text-white pointer-events-none">Antes</span>
          <span className="absolute top-2 right-2 text-xs px-2 py-1 rounded-full bg-black/60 text-white pointer-events-none">Después</span>

          <div className="absolute top-0 bottom-0 w-px bg-white/80 pointer-events-none" style={{ left: `${sliderPos}%` }} />
          <div
            onPointerDown={handlePointerDown}
            className="absolute top-1/2 w-8 h-8 -translate-y-1/2 -translate-x-1/2 rounded-full bg-white flex items-center justify-center shadow-md"
            style={{ left: `${sliderPos}%` }}
          >
            <GripVertical size={14} className="text-black" />
          </div>
        </div>
      )}
    </div>
  );
}
