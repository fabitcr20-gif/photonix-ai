/**
 * "Nueva edición" — flujo principal de Photonix AI: cargar fotos, elegir un
 * perfil de estilo IA (o dejar que la IA decida), ajustar opciones avanzadas
 * reales, procesar con progreso en vivo, comparar antes/después y exportar.
 */
"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { Sparkles } from "lucide-react";
import Dropzone from "@/components/Dropzone";
import Accordion from "@/components/Accordion";
import LabeledSlider from "@/components/LabeledSlider";
import StyleProfileCard from "@/components/StyleProfileCard";
import BeforeAfterSlider from "@/components/BeforeAfterSlider";
import ManualEditModal from "@/components/ManualEditModal";
import ExportPanel from "@/components/ExportPanel";
import FeedbackPrompt from "@/components/FeedbackPrompt";
import { apiGet, apiPostFormWithProgress, apiPostJson } from "@/lib/api";
import type { Profile, StyleProfile, PreviewPair } from "@/types";

const PROCESSING_MESSAGES = [
  "Analizando iluminación...",
  "Corrigiendo balance de blancos...",
  "Aplicando ajustes automáticos...",
  "Optimizando nitidez y limpieza...",
  "Preparando exportación...",
];

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${bytes} B`;
}

export default function UploadPage() {
  return (
    <Suspense fallback={null}>
      <UploadPageContent />
    </Suspense>
  );
}

function UploadPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [mode, setMode] = useState<"single" | "folder">("single");
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [startingProcess, setStartingProcess] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [previewPairs, setPreviewPairs] = useState<PreviewPair[]>([]);
  const [previewIndex, setPreviewIndex] = useState(0);

  const [styleProfiles, setStyleProfiles] = useState<StyleProfile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState("automatico");

  const [removePlates, setRemovePlates] = useState(false);
  const [removePolesWires, setRemovePolesWires] = useState(false);

  // Opciones avanzadas: null = "no tocado" (la IA decide por sí sola).
  const [aiIntensity, setAiIntensity] = useState(100);
  const [sharpness, setSharpness] = useState<number | null>(null);
  const [contrast, setContrast] = useState<number | null>(null);
  const [whiteBalance, setWhiteBalance] = useState<number | null>(null);
  const [noiseReduction, setNoiseReduction] = useState<number | null>(null);
  const [highlightRecovery, setHighlightRecovery] = useState<number | null>(null);
  const [shadowRecovery, setShadowRecovery] = useState<number | null>(null);
  const [colorCorrection, setColorCorrection] = useState<number | null>(null);

  // Contexto manual de clima/luz: "automatico" deja que la IA lo adivine (comportamiento original).
  const [weatherOverride, setWeatherOverride] = useState("automatico");
  const [lightOverride, setLightOverride] = useState("automatico");

  const [processingStatus, setProcessingStatus] = useState<{
    status: string;
    processed_count: number;
    total_count: number;
    qa_fallback_count?: number;
  } | null>(null);
  const [processingMessageIndex, setProcessingMessageIndex] = useState(0);
  const processingStartedAt = useRef<number | null>(null);

  const [editingPhotoId, setEditingPhotoId] = useState<string | null>(null);
  const [feedbackDoneFor, setFeedbackDoneFor] = useState<Set<string>>(new Set());

  const canRemoveObjects = profile?.plan_features?.object_removal ?? false;
  const maxBatchPhotos = profile?.plan_features?.max_batch_photos ?? null;
  const totalSizeBytes = files.reduce((sum, f) => sum + f.size, 0);
  const detectedFormats = Array.from(
    new Set(files.map((f) => f.name.split(".").pop()?.toUpperCase() ?? "?"))
  ).join(", ");

  useEffect(() => {
    apiGet<Profile>("/auth/me").then(setProfile).catch(() => {});
    apiGet<StyleProfile[]>("/ai/style-profiles").then(setStyleProfiles).catch(() => {});
  }, []);

  useEffect(() => {
    if (searchParams.get("drive") === "connected") {
      setMessage("Tu cuenta de Google Drive quedó conectada. Ya puedes exportar tu sesión ahí.");
      router.replace(pathname);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  useEffect(() => {
    if (profile && !canRemoveObjects) {
      setRemovePlates(false);
      setRemovePolesWires(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile]);

  // Cicla los mensajes de "qué está haciendo la IA" mientras procesa.
  useEffect(() => {
    if (processingStatus?.status !== "processing") return;
    const interval = setInterval(() => {
      setProcessingMessageIndex((i) => (i + 1) % PROCESSING_MESSAGES.length);
    }, 2200);
    return () => clearInterval(interval);
  }, [processingStatus?.status]);

  // Consulta el avance real cada 2s mientras el proyecto esté "processing".
  useEffect(() => {
    if (!projectId || processingStatus?.status !== "processing") return;
    let cancelled = false; // guarda contra setState si el efecto ya se limpió (unmount o cambio de projectId)

    const interval = setInterval(async () => {
      try {
        const res = await apiGet<{
          status: string;
          processed_count: number;
          total_count: number;
          qa_fallback_count?: number;
        }>(`/ai/projects/${projectId}/status`);
        if (cancelled) return;
        setProcessingStatus(res);
        if (res.status === "review") {
          setMessage("¡Listo! Tus fotos ya fueron editadas y están listas para comparar y exportar.");
          apiGet<PreviewPair[]>(`/ai/projects/${projectId}/preview-pairs`)
            .then((pairs) => {
              if (!cancelled) setPreviewPairs(pairs);
            })
            .catch(() => {});
        }
        if (res.status === "error") {
          setMessage(
            "Hubo un problema al editar esta sesión (por ejemplo, una interrupción de red). No se perdió nada — puedes intentarlo de nuevo."
          );
        }
        if (res.status === "cancelled") {
          setMessage("Cancelaste la edición. Las fotos que ya se alcanzaron a editar no se perdieron.");
        }
      } catch {
        // se reintenta en el próximo tick
      }
    }, 2000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [projectId, processingStatus?.status]);

  function selectProfile(p: StyleProfile) {
    setSelectedProfileId(p.id);
    if (canRemoveObjects) {
      setRemovePlates(p.suggest_remove_plates);
      setRemovePolesWires(p.suggest_remove_poles_wires);
    }
  }

  async function handleUpload() {
    if (files.length === 0) return;
    setUploading(true);
    setUploadProgress(0);
    setMessage(null);
    try {
      const formData = new FormData();
      if (mode === "single") {
        formData.append("file", files[0]);
        const res = await apiPostFormWithProgress<{ project_id: string }>(
          "/uploads/single",
          formData,
          setUploadProgress
        );
        setProjectId(res.project_id);
      } else {
        files.forEach((f) => formData.append("files", f));
        formData.append("project_name", `Sesión ${new Date().toLocaleDateString("es-CR")}`);
        const res = await apiPostFormWithProgress<{ project_id: string }>(
          "/uploads/batch",
          formData,
          setUploadProgress
        );
        setProjectId(res.project_id);
      }
      setMessage("Carga completada. Elige un perfil de estilo y comienza la edición automática.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Error al cargar las fotos.");
    } finally {
      setUploading(false);
    }
  }

  async function handleProcess() {
    if (!projectId || startingProcess || isProcessing) return;
    setMessage(null);
    setPreviewPairs([]);
    setStartingProcess(true);
    try {
      // Se espera la confirmación real del backend ANTES de mostrar
      // "procesando" -- si esta llamada falla (plan sin permiso, límite de
      // tasa, ya hay otra edición en curso, red caída), la pantalla no debe
      // quedar congelada en "procesando" para siempre sin ningún error.
      await apiPostJson("/ai/process", {
        project_id: projectId,
        auto_perspective: true,
        auto_adjustments: true,
        auto_cleanup: true,
        remove_plates: removePlates,
        remove_logos: false,
        remove_poles_wires: removePolesWires,
        style_profile: selectedProfileId,
        ai_intensity: aiIntensity / 100,
        sharpness: sharpness != null ? sharpness / 100 : null,
        contrast: contrast != null ? contrast / 100 : null,
        white_balance: whiteBalance != null ? whiteBalance / 100 : null,
        noise_reduction: noiseReduction != null ? noiseReduction / 100 : null,
        highlight_recovery: highlightRecovery != null ? highlightRecovery / 100 : null,
        shadow_recovery: shadowRecovery != null ? shadowRecovery / 100 : null,
        color_correction: colorCorrection != null ? colorCorrection / 100 : null,
        weather_override: weatherOverride !== "automatico" ? weatherOverride : null,
        light_override: lightOverride !== "automatico" ? lightOverride : null,
      });
      processingStartedAt.current = Date.now();
      setProcessingMessageIndex(0);
      setProcessingStatus({ status: "processing", processed_count: 0, total_count: 0 });
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo iniciar la edición. Intenta de nuevo.");
    } finally {
      setStartingProcess(false);
    }
  }

  const isProcessing = processingStatus?.status === "processing";
  const isReview = processingStatus?.status === "review";
  const isError = processingStatus?.status === "error";
  const isCancelled = processingStatus?.status === "cancelled";

  let etaLabel = "";
  if (isProcessing && processingStatus && processingStartedAt.current) {
    const elapsedSec = (Date.now() - processingStartedAt.current) / 1000;
    const { processed_count, total_count } = processingStatus;
    if (processed_count > 0 && total_count > 0) {
      const perPhoto = elapsedSec / processed_count;
      const remaining = Math.max(0, Math.round((total_count - processed_count) * perPhoto));
      const speed = (processed_count / elapsedSec).toFixed(1);
      etaLabel = `${speed} fotos/s · ~${remaining}s restantes`;
    }
  }

  // Ninguna edición real de esta app tarda más de un minuto o dos incluso
  // con lotes grandes (medido en producción) -- pasado ese umbral, algo
  // anormal está pasando (no necesariamente un cuelgue: puede ser un lote
  // enorme, o el servidor bajo carga). En vez de dejar un spinner infinito
  // sin ninguna señal, se avisa y se ofrece cancelar.
  const [isTakingLong, setIsTakingLong] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    if (!isProcessing) {
      setIsTakingLong(false);
      return;
    }
    const timeout = setTimeout(() => setIsTakingLong(true), 60_000);
    return () => clearTimeout(timeout);
  }, [isProcessing, projectId]);

  async function handleCancel() {
    if (!projectId || cancelling) return;
    setCancelling(true);
    try {
      await apiPostJson(`/ai/projects/${projectId}/cancel`, {});
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cancelar. Intenta de nuevo.");
    } finally {
      setCancelling(false);
    }
  }

  return (
    <div className="max-w-4xl photonix-fade-in">
      <h1 className="text-3xl font-semibold tracking-tightish mb-2">
        Procesamiento con Inteligencia Artificial
      </h1>
      <p className="text-photonix-textMuted mb-8">
        Carga tu sesión, elige cómo quieres que la IA la edite, y en minutos tendrás tus fotos
        listas para comparar y exportar.
      </p>

      {/* 1. Carga */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setMode("single")}
          disabled={uploading || isProcessing}
          className={`${mode === "single" ? "photonix-btn-primary" : "photonix-btn-secondary"} disabled:opacity-60 disabled:cursor-not-allowed`}
        >
          Carga individual
        </button>
        <button
          onClick={() => setMode("folder")}
          disabled={uploading || isProcessing}
          className={`${mode === "folder" ? "photonix-btn-primary" : "photonix-btn-secondary"} disabled:opacity-60 disabled:cursor-not-allowed`}
        >
          Carga masiva (carpeta)
        </button>
      </div>

      <Dropzone mode={mode} onFilesSelected={setFiles} />

      {files.length > 0 && (
        <div className="flex flex-wrap gap-4 mt-3 text-xs text-photonix-textMuted">
          <span>{files.length} fotografía{files.length !== 1 ? "s" : ""}</span>
          <span>{formatBytes(totalSizeBytes)}</span>
          <span>Formato: {detectedFormats}</span>
          {mode === "folder" && (
            <span>Tu plan permite {maxBatchPhotos ? `hasta ${maxBatchPhotos} fotos` : "fotos ilimitadas"}</span>
          )}
        </div>
      )}

      <div className="mt-4">
        <button onClick={handleUpload} disabled={uploading || files.length === 0} className="photonix-btn-primary">
          {uploading ? "Cargando..." : "Cargar fotos"}
        </button>
      </div>

      {uploading && (
        <div className="mt-4">
          <div className="h-1.5 rounded-full bg-photonix-border overflow-hidden">
            <div className="h-full bg-gradient-to-r from-photonix-accent to-photonix-accent2 transition-all duration-200" style={{ width: `${uploadProgress}%` }} />
          </div>
          <p className="text-xs text-photonix-textMuted mt-1">{uploadProgress}% subido</p>
        </div>
      )}

      {isError && (
        <div className="mt-6 p-4 rounded-xl2 border border-photonix-danger/40 bg-photonix-danger/10 text-sm photonix-fade-in">
          No se pudo completar la edición de esta sesión (probablemente por una interrupción de red).
          Ninguna foto se perdió — elige tus opciones abajo y presiona &quot;Procesar&quot; de nuevo.
        </div>
      )}

      {/* 2. Perfil de estilo */}
      {projectId && !isProcessing && !isReview && (
        <div className="mt-10 photonix-fade-in">
          <h2 className="text-lg font-medium mb-1">Estilo IA</h2>
          <p className="text-sm text-photonix-textMuted mb-4">
            Elige el tipo de sesión para que la IA aplique el ajuste más adecuado.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {styleProfiles.map((p) => (
              <StyleProfileCard key={p.id} profile={p} selected={selectedProfileId === p.id} onSelect={() => selectProfile(p)} />
            ))}
          </div>

          {/* 3. Opciones avanzadas */}
          <div className="mt-6 flex flex-col gap-3">
            <Accordion title="Opciones avanzadas" subtitle="Ajusta manualmente lo que la IA aplicará">
              <LabeledSlider label="Intensidad IA" value={aiIntensity} min={0} max={150} onChange={setAiIntensity} formatValue={(v) => `${v}%`} />
              <LabeledSlider label="Nitidez" value={sharpness ?? 0} onChange={setSharpness} />
              <LabeledSlider label="Contraste" value={contrast ?? 0} onChange={setContrast} />
              <LabeledSlider label="Balance de blancos" value={whiteBalance ?? 0} onChange={setWhiteBalance} formatValue={(v) => (v > 0 ? `+${v} cálido` : v < 0 ? `${v} frío` : "0")} />
              <LabeledSlider label="Reducción de ruido" value={noiseReduction ?? 0} min={0} max={100} onChange={setNoiseReduction} />
              <LabeledSlider label="Recuperación de altas luces" value={highlightRecovery ?? 0} min={0} max={100} onChange={setHighlightRecovery} />
              <LabeledSlider label="Recuperación de sombras" value={shadowRecovery ?? 0} min={0} max={100} onChange={setShadowRecovery} />
              <LabeledSlider label="Corrección de color" value={colorCorrection ?? 0} onChange={setColorCorrection} />

              <div className="mt-4 pt-4 border-t border-photonix-border grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-photonix-textMuted block mb-1.5">Condición climática</label>
                  <select
                    value={weatherOverride}
                    onChange={(e) => setWeatherOverride(e.target.value)}
                    className="photonix-input text-sm w-full"
                  >
                    <option value="automatico">Automático (IA)</option>
                    <option value="soleado">Soleado</option>
                    <option value="nublado">Nublado</option>
                    <option value="lluvia">Lluvia</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-photonix-textMuted block mb-1.5">Nivel de luz</label>
                  <select
                    value={lightOverride}
                    onChange={(e) => setLightOverride(e.target.value)}
                    className="photonix-input text-sm w-full"
                  >
                    <option value="automatico">Automático (IA)</option>
                    <option value="baja">Baja</option>
                    <option value="media">Media</option>
                    <option value="alta">Alta</option>
                  </select>
                </div>
              </div>
              <p className="text-xs text-photonix-textMuted mt-2">
                Si la IA está sobre-exponiendo o dejando muy oscuras tus fotos, dinos la condición real
                de la sesión para corregirlo.
              </p>
            </Accordion>

            <Accordion title="Eliminación de elementos" subtitle={canRemoveObjects ? "Placas, postes y cables" : "Requiere plan Pro o Studio"}>
              <label className="flex items-center gap-2 text-sm mb-2">
                <input type="checkbox" checked={removePlates} disabled={!canRemoveObjects} onChange={(e) => setRemovePlates(e.target.checked)} className="accent-photonix-accent" />
                Eliminar placas de autos
                {!canRemoveObjects && (
                  <Link href="/dashboard/billing" className="text-xs text-photonix-accent hover:underline">Actualizar plan</Link>
                )}
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={removePolesWires} disabled={!canRemoveObjects} onChange={(e) => setRemovePolesWires(e.target.checked)} className="accent-photonix-accent" />
                Eliminar postes de luz y cables eléctricos
                {!canRemoveObjects && (
                  <Link href="/dashboard/billing" className="text-xs text-photonix-accent hover:underline">Actualizar plan</Link>
                )}
              </label>
            </Accordion>
          </div>

          <button
            onClick={handleProcess}
            disabled={startingProcess}
            className="photonix-btn-primary mt-6 inline-flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <Sparkles size={16} />
            {startingProcess
              ? "Iniciando..."
              : `Procesar ${files.length} foto${files.length !== 1 ? "s" : ""} con IA`}
          </button>
        </div>
      )}

      {/* 4. Progreso */}
      {isProcessing && processingStatus && (
        <div className="mt-10 photonix-card photonix-fade-in">
          <p className="text-sm font-medium mb-3">{PROCESSING_MESSAGES[processingMessageIndex]}</p>
          <div className="h-1.5 rounded-full bg-photonix-border overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-photonix-accent to-photonix-accent2 transition-all duration-300"
              style={{
                width:
                  processingStatus.total_count > 0
                    ? `${Math.round((processingStatus.processed_count / processingStatus.total_count) * 100)}%`
                    : "4%",
              }}
            />
          </div>
          <div className="flex justify-between text-xs text-photonix-textMuted mt-2">
            <span>
              {processingStatus.total_count > 0
                ? `Foto ${processingStatus.processed_count} de ${processingStatus.total_count}`
                : "Preparando sesión..."}
            </span>
            <span>
              {processingStatus.total_count > 0
                ? `${Math.round((processingStatus.processed_count / processingStatus.total_count) * 100)}%`
                : ""}
            </span>
          </div>
          {etaLabel && <p className="text-xs text-photonix-textMuted mt-1">{etaLabel}</p>}

          {isTakingLong && (
            <div className="mt-4 pt-4 border-t border-photonix-border flex items-center justify-between gap-3 flex-wrap">
              <p className="text-xs text-photonix-textMuted">
                La edición está tardando más de lo habitual. Podés seguir esperando o cancelarla — las
                fotos ya editadas hasta ahora no se pierden.
              </p>
              <button
                onClick={handleCancel}
                disabled={cancelling}
                className="photonix-btn-secondary text-xs px-3 py-1.5 whitespace-nowrap disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {cancelling ? "Cancelando..." : "Cancelar edición"}
              </button>
            </div>
          )}
        </div>
      )}

      {isCancelled && (
        <div className="mt-6 p-4 rounded-xl2 border border-photonix-border bg-white/[0.02] text-sm photonix-fade-in">
          Cancelaste la edición. Las fotos que ya se alcanzaron a editar no se perdieron — podés
          intentarlo de nuevo cuando quieras.
        </div>
      )}

      {message && <p className="text-sm text-photonix-accent mt-4">{message}</p>}

      {isReview && !!processingStatus?.qa_fallback_count && (
        <div className="mt-4 p-4 rounded-xl2 border border-photonix-border bg-white/[0.02] text-sm photonix-fade-in">
          {processingStatus.qa_fallback_count} foto{processingStatus.qa_fallback_count !== 1 ? "s" : ""} no
          pasaron nuestro control de calidad automático y se entregaron sin editar, para proteger tu
          contenido en vez de arriesgar un resultado dañado.
        </div>
      )}

      {/* 5. Antes/Después */}
      {isReview && previewPairs.length > 0 && (
        <div className="mt-10 photonix-fade-in">
          <h2 className="text-lg font-medium mb-1">Antes / Después</h2>
          <p className="text-sm text-photonix-textMuted mb-4">
            Foto {previewIndex + 1} de {previewPairs.length}
          </p>
          <BeforeAfterSlider
            beforeUrl={previewPairs[previewIndex].original_url}
            afterUrl={previewPairs[previewIndex].edited_url}
            onEditClick={() => setEditingPhotoId(previewPairs[previewIndex].photo_id)}
          />
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => setPreviewIndex((i) => Math.max(0, i - 1))}
              disabled={previewIndex === 0}
              className="photonix-btn-secondary text-sm"
            >
              Anterior
            </button>
            <button
              onClick={() => setPreviewIndex((i) => Math.min(previewPairs.length - 1, i + 1))}
              disabled={previewIndex === previewPairs.length - 1}
              className="photonix-btn-secondary text-sm"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}

      {editingPhotoId && projectId && (
        <ManualEditModal
          projectId={projectId}
          photoId={editingPhotoId}
          onClose={() => setEditingPhotoId(null)}
          onSaved={(editedUrl) => {
            setPreviewPairs((pairs) =>
              pairs.map((p) => (p.photo_id === editingPhotoId ? { ...p, edited_url: editedUrl } : p))
            );
          }}
        />
      )}

      {/* 6. Exportar */}
      {isReview && projectId && (
        <div className="mt-10 photonix-card photonix-fade-in">
          <h2 className="font-medium mb-1">Exportar sesión</h2>
          <p className="text-sm text-photonix-textMuted mb-4">
            Tus fotos ya editadas (con marca de agua incluida, si configuraste una).
          </p>
          <ExportPanel projectId={projectId} />
        </div>
      )}

      {isReview && projectId && !feedbackDoneFor.has(projectId) && (
        <FeedbackPrompt
          projectId={projectId}
          onDone={() => setFeedbackDoneFor((prev) => new Set(prev).add(projectId))}
        />
      )}
    </div>
  );
}
