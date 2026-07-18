/**
 * Comparador Antes/Después profesional (inspirado en Lightroom/Capture One):
 * slider deslizable con línea divisoria sincronizada (clip-path sobre un
 * único par de <img>, sin duplicar ni desalinear píxeles), orientación
 * horizontal o vertical, modo lado a lado, zoom sincronizado y pantalla
 * completa.
 *
 * Decisiones deliberadas:
 * - Se usa <img> nativo en vez de next/image: las fotos pueden venir del
 *   backend local, de Supabase Storage o de un bucket S3/R2 con dominio
 *   propio (ver storage_service.py) -- una lista fija de `remotePatterns`
 *   en next.config.js sería frágil ante ese multi-proveedor. En cambio se
 *   cuida el rendimiento con decoding="async", carga eager solo de la foto
 *   visible, y un estado de carga con shimmer para no bloquear el layout.
 * - El aspect ratio del contenedor se calcula de las dimensiones reales de
 *   la imagen ya cargada (naturalWidth/naturalHeight) en vez de un 3:2 fijo,
 *   para que fotos verticales (retrato) no queden recortadas ni deformadas.
 * - Este componente asume que la sesión YA terminó de procesarse (lo monta
 *   `upload/page.tsx` solo cuando `isReview` es true) -- el estado
 *   "la IA todavía está procesando" se maneja aguas arriba, no aquí.
 */
"use client";

import { useEffect, useRef, useState } from "react";
import {
  Maximize2,
  Minimize2,
  Columns2,
  GripVertical,
  ZoomIn,
  ZoomOut,
  Pencil,
  ImageOff,
  SeparatorHorizontal,
} from "lucide-react";

type Orientation = "horizontal" | "vertical";

const DEFAULT_ASPECT = 3 / 2;
const MIN_ASPECT = 9 / 21; // límite para paneos verticales muy extremos
const MAX_ASPECT = 21 / 9; // límite para panorámicas muy extremas

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
  const [orientation, setOrientation] = useState<Orientation>("horizontal");

  const [beforeLoaded, setBeforeLoaded] = useState(false);
  const [afterLoaded, setAfterLoaded] = useState(false);
  const [beforeError, setBeforeError] = useState(false);
  const [afterError, setAfterError] = useState(false);
  const [aspect, setAspect] = useState(DEFAULT_ASPECT);

  const missing = !beforeUrl || !afterUrl;
  const bothLoaded = beforeLoaded && afterLoaded;
  const anyError = beforeError || afterError || missing;

  // El slider empieza siempre centrado y las cargas se reinician cada vez
  // que cambian las URLs (ej. al pasar a la siguiente foto del lote).
  useEffect(() => {
    setSliderPos(50);
    setBeforeLoaded(false);
    setAfterLoaded(false);
    setBeforeError(false);
    setAfterError(false);
    setAspect(DEFAULT_ASPECT);
  }, [beforeUrl, afterUrl]);

  function handleAfterImageLoad(e: React.SyntheticEvent<HTMLImageElement>) {
    const img = e.currentTarget;
    if (img.naturalWidth > 0 && img.naturalHeight > 0) {
      const natural = img.naturalWidth / img.naturalHeight;
      setAspect(Math.min(MAX_ASPECT, Math.max(MIN_ASPECT, natural)));
    }
    setAfterLoaded(true);
  }

  function updateFromPointer(clientX: number, clientY: number) {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const pct =
      orientation === "horizontal"
        ? ((clientX - rect.left) / rect.width) * 100
        : ((clientY - rect.top) / rect.height) * 100;
    setSliderPos(Math.max(0, Math.min(100, pct)));
  }

  function handlePointerDown(e: React.PointerEvent) {
    // Foco explícito: en un widget ARIA custom no se puede depender del
    // enfoque-al-clic por defecto del navegador (no siempre ocurre con
    // Pointer Events), y sin foco las flechas del teclado no funcionan.
    (e.currentTarget as HTMLElement).focus();
    setDragging(true);
    (e.target as Element).setPointerCapture(e.pointerId);
    updateFromPointer(e.clientX, e.clientY);
  }
  function handlePointerMove(e: React.PointerEvent) {
    if (!dragging) return;
    updateFromPointer(e.clientX, e.clientY);
  }
  function handlePointerUp() {
    setDragging(false);
  }
  function handleKeyDown(e: React.KeyboardEvent) {
    const step = e.shiftKey ? 10 : 3;
    if (
      (orientation === "horizontal" && (e.key === "ArrowLeft" || e.key === "ArrowRight")) ||
      (orientation === "vertical" && (e.key === "ArrowUp" || e.key === "ArrowDown"))
    ) {
      e.preventDefault();
      const dir = e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 1;
      setSliderPos((p) => Math.max(0, Math.min(100, p + dir * step)));
    }
  }

  const clipInset =
    orientation === "horizontal" ? `0 ${100 - sliderPos}% 0 0` : `0 0 ${100 - sliderPos}% 0`;

  return (
    <div className={fullscreen ? "fixed inset-0 z-50 bg-black flex flex-col p-6" : "flex flex-col"}>
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        {label && <p className="text-sm text-photonix-textMuted">{label}</p>}
        <div className="flex items-center gap-2 ml-auto flex-wrap">
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
          {!sideBySide && (
            <button
              onClick={() => setOrientation((o) => (o === "horizontal" ? "vertical" : "horizontal"))}
              aria-label="Cambiar orientación del divisor"
              title={orientation === "horizontal" ? "Divisor horizontal" : "Divisor vertical"}
              className="photonix-btn-secondary text-xs px-2.5 py-1.5"
            >
              <SeparatorHorizontal size={14} className={orientation === "vertical" ? "rotate-90" : ""} />
            </button>
          )}
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

      {anyError ? (
        <div
          className="flex-1 min-h-0 rounded-xl2 border border-photonix-border bg-photonix-surfaceAlt flex flex-col items-center justify-center gap-2 text-center px-6 py-16"
          style={{ aspectRatio: fullscreen ? undefined : aspect }}
        >
          <ImageOff className="text-photonix-textMuted" size={28} />
          <p className="text-sm text-photonix-danger">
            {missing ? "Faltan una o ambas imágenes de esta foto." : "No se pudo cargar una de las imágenes."}
          </p>
          <p className="text-xs text-photonix-textMuted">Intenta recargar la página o vuelve a esta sesión más tarde.</p>
        </div>
      ) : sideBySide ? (
        <div className="grid grid-cols-2 gap-2 flex-1 min-h-0">
          {[
            { url: beforeUrl, tag: "ANTES" },
            { url: afterUrl, tag: "DESPUÉS" },
          ].map(({ url, tag }) => (
            <div
              key={tag}
              className="relative rounded-xl2 overflow-hidden border border-photonix-border bg-black"
              style={{ aspectRatio: fullscreen ? undefined : aspect }}
            >
              {!bothLoaded && <div className="absolute inset-0 photonix-skeleton" />}
              <div className="w-full h-full overflow-hidden flex items-center justify-center">
                <img
                  src={url}
                  alt={tag === "ANTES" ? "Foto original" : "Foto editada por IA"}
                  decoding="async"
                  className={`max-w-none transition-opacity duration-300 ${bothLoaded ? "opacity-100" : "opacity-0"}`}
                  style={{ width: "100%", height: "100%", objectFit: "contain", transform: `scale(${zoom})` }}
                  onLoad={() => (tag === "ANTES" ? setBeforeLoaded(true) : setAfterLoaded(true))}
                  onError={() => (tag === "ANTES" ? setBeforeError(true) : setAfterError(true))}
                />
              </div>
              <span className="absolute top-2 left-2 text-[11px] font-semibold tracking-wide px-2 py-1 rounded-full bg-black/60 text-white backdrop-blur-sm">
                {tag}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div
          ref={containerRef}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          className={`relative w-full flex-1 min-h-0 rounded-xl2 overflow-hidden select-none border border-photonix-border bg-black ${
            orientation === "horizontal" ? "cursor-ew-resize" : "cursor-ns-resize"
          } ${bothLoaded ? "photonix-fade-in" : ""}`}
          style={{ aspectRatio: fullscreen ? undefined : aspect }}
        >
          {!bothLoaded && <div className="absolute inset-0 photonix-skeleton" />}

          <div className="absolute inset-0 overflow-hidden" style={{ transform: `scale(${zoom})`, transformOrigin: "center" }}>
            <img
              src={beforeUrl}
              alt="Foto original"
              decoding="async"
              className={`absolute inset-0 w-full h-full object-contain pointer-events-none transition-opacity duration-300 ${
                bothLoaded ? "opacity-100" : "opacity-0"
              }`}
              draggable={false}
              onLoad={() => setBeforeLoaded(true)}
              onError={() => setBeforeError(true)}
            />
            <img
              src={afterUrl}
              alt="Foto editada por IA"
              decoding="async"
              className={`absolute inset-0 w-full h-full object-contain pointer-events-none transition-opacity duration-300 ${
                bothLoaded ? "opacity-100" : "opacity-0"
              }`}
              style={{ clipPath: `inset(${clipInset})` }}
              draggable={false}
              onLoad={handleAfterImageLoad}
              onError={() => setAfterError(true)}
            />
          </div>

          <span className="absolute top-2 left-2 text-[11px] font-semibold tracking-wide px-2 py-1 rounded-full bg-black/60 text-white backdrop-blur-sm pointer-events-none">
            ANTES
          </span>
          <span className="absolute top-2 right-2 text-[11px] font-semibold tracking-wide px-2 py-1 rounded-full bg-black/60 text-white backdrop-blur-sm pointer-events-none">
            DESPUÉS
          </span>

          <div
            className="absolute bg-white/80 pointer-events-none"
            style={
              orientation === "horizontal"
                ? { top: 0, bottom: 0, left: `${sliderPos}%`, width: 1 }
                : { left: 0, right: 0, top: `${sliderPos}%`, height: 1 }
            }
          />
          <div
            role="slider"
            tabIndex={0}
            aria-label="Línea divisoria antes/después"
            aria-valuenow={Math.round(sliderPos)}
            aria-valuemin={0}
            aria-valuemax={100}
            onPointerDown={handlePointerDown}
            onKeyDown={handleKeyDown}
            className="absolute w-9 h-9 rounded-full bg-white flex items-center justify-center shadow-lg outline-none focus-visible:ring-2 focus-visible:ring-photonix-accent transition-transform hover:scale-105"
            style={{
              touchAction: "none",
              ...(orientation === "horizontal"
                ? { left: `${sliderPos}%`, top: "50%", transform: "translate(-50%, -50%)" }
                : { top: `${sliderPos}%`, left: "50%", transform: "translate(-50%, -50%)" }),
            }}
          >
            <GripVertical size={16} className={`text-black ${orientation === "vertical" ? "rotate-90" : ""}`} />
          </div>
        </div>
      )}
    </div>
  );
}
