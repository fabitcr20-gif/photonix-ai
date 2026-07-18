"""
Rutas del motor de edición automatizada con IA.
Recibe un proyecto ya cargado (ver routers/uploads.py) y dispara el
procesamiento por lotes en segundo plano (BackgroundTasks de FastAPI; en
producción se recomienda una cola real como Celery/RQ para persistencia y
reintentos ante miles de fotos).
"""
from __future__ import annotations
import logging
import os
import shutil
import tempfile
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.core.dependencies import require_active_membership, get_plan_limits
from app.core.rate_limit import rate_limiter, reject_missing_user_agent
from app.core.security import AuthUser
from app.core.style_profiles import get_style_profile, list_style_profiles_public
from app.database import get_supabase_admin
from app.config import get_settings
from app.services import storage_service
from app.services.ai.basic_adjustments import AdjustmentParams
from app.services.ai.batch_processor import process_batch, process_single_image, BatchOptions
from app.services.watermark_service import apply_watermark_batch, WatermarkConfig

router = APIRouter(prefix="/ai", tags=["Motor de IA"])
settings = get_settings()
logger = logging.getLogger("photonix.ai_engine")


class ProcessProjectRequest(BaseModel):
    project_id: str
    auto_perspective: bool = True
    auto_adjustments: bool = True
    auto_cleanup: bool = True
    remove_plates: bool = False
    remove_logos: bool = False
    remove_poles_wires: bool = False

    # Perfil de estilo IA (ver core/style_profiles.py). 'automatico' o None
    # deja que la IA decida por foto según hora/clima/luz, igual que antes.
    style_profile: Optional[str] = None

    # Opciones avanzadas (acordeón del frontend). Todas opcionales: si no se
    # envían, no afectan el resultado. Cuando se envía cualquiera de estas o
    # un style_profile distinto de 'automatico', se congela un único ajuste
    # para todo el lote (como un preset de Lightroom) en vez de adaptarse
    # foto por foto.
    ai_intensity: float = 1.0        # 0.0-1.5, multiplicador global
    sharpness: Optional[float] = None        # 0-1 -> clarity
    contrast: Optional[float] = None         # -1..1
    white_balance: Optional[float] = None    # -1 (frío) a 1 (cálido) -> temperature
    noise_reduction: Optional[float] = None  # 0-1 -> BatchOptions.denoise_strength
    highlight_recovery: Optional[float] = None  # 0-1 -> highlights negativo
    shadow_recovery: Optional[float] = None     # 0-1 -> shadows positivo
    color_correction: Optional[float] = None    # -1..1 -> saturation

    # Contexto manual de clima/luz: el análisis automático (ver
    # environment_analysis.py) a veces adivina mal la condición real de la
    # toma, y equivocarse invierte el ajuste (ej. si cree que hay "alta" luz
    # cuando en realidad hay "baja", oscurece una foto que ya estaba oscura).
    # Si el usuario los indica, reemplazan la lectura automática para TODO el
    # lote antes de calcular los ajustes.
    weather_override: Optional[str] = None   # 'soleado' | 'nublado' | 'lluvia'
    light_override: Optional[str] = None     # 'baja' | 'media' | 'alta'


def _build_custom_adjustments(payload: ProcessProjectRequest) -> Optional[AdjustmentParams]:
    """Combina el perfil de estilo elegido con los sliders de opciones
    avanzadas en un único AdjustmentParams para todo el lote. Devuelve None
    si el usuario no tocó nada (perfil 'automatico' sin sliders), para que
    el motor siga adaptándose foto por foto como antes."""
    profile = get_style_profile(payload.style_profile) if payload.style_profile else None
    touched_sliders = any(
        v is not None
        for v in (
            payload.sharpness,
            payload.contrast,
            payload.white_balance,
            payload.highlight_recovery,
            payload.shadow_recovery,
            payload.color_correction,
        )
    )

    if (profile is None or profile.params is None) and not touched_sliders:
        return None  # 100% automático, adaptado por foto (comportamiento original)

    values = dict(profile.params) if (profile and profile.params) else {}

    if payload.sharpness is not None:
        values["clarity"] = payload.sharpness
    if payload.contrast is not None:
        values["contrast"] = payload.contrast
    if payload.white_balance is not None:
        values["temperature"] = payload.white_balance
    if payload.highlight_recovery is not None:
        values["highlights"] = -payload.highlight_recovery
    if payload.shadow_recovery is not None:
        values["shadows"] = payload.shadow_recovery
    if payload.color_correction is not None:
        values["saturation"] = payload.color_correction

    intensity = max(0.0, min(payload.ai_intensity, 1.5))
    values = {k: v * intensity for k, v in values.items()}

    return AdjustmentParams(**values)


def _filename_from_url(url: str) -> Optional[str]:
    """Nombre de archivo (sin ruta) a partir de una URL de almacenamiento --
    funciona igual sin importar el proveedor, porque todos usan el mismo
    esquema de nombre único por archivo (ver storage_service._generate_key)."""
    if not url:
        return None
    return os.path.basename(url.split("?", 1)[0].rstrip("/")) or None


def _final_photos_scratch_dir(project_id: str) -> str:
    """Carpeta LOCAL de trabajo (scratch) donde se escribe el resultado
    final (editado + marca de agua) mientras se procesa -- OpenCV/Pillow
    exigen rutas de disco reales. Una vez escrito aquí, `_persist_final_dir`
    lo sube al proveedor de almacenamiento configurado (ver storage_service.py)
    y limpia esta carpeta si el proveedor no es 'local'. Nunca es la fuente
    de verdad en producción con almacenamiento remoto -- solo un paso
    intermedio siempre necesario para el procesamiento de imagen."""
    return os.path.join(settings.LOCAL_STORAGE_PATH, "final-photos", project_id)


def _persist_final_dir(final_dir: str, project_id: str) -> None:
    """Sube cada archivo de la carpeta final de trabajo al proveedor de
    almacenamiento configurado (bucket 'final-photos', separado de las fotos
    originales) y limpia la copia local de scratch -- así el resultado
    sobrevive un reinicio del servidor o un redespliegue, no solo el disco
    efímero que lo procesó."""
    if not os.path.isdir(final_dir):
        return
    for fname in os.listdir(final_dir):
        storage_service.persist_local_file(os.path.join(final_dir, fname), "final-photos", project_id, fname)


def _apply_watermark_if_configured(db, user_id: str, image_paths: list[str], final_dir: str) -> None:
    """Aplica la marca de agua guardada por el usuario (ver watermark_service)
    a las fotos ya editadas. Si el usuario no configuró ninguna, simplemente
    copia las fotos editadas tal cual a la carpeta final."""
    os.makedirs(final_dir, exist_ok=True)
    watermark = db.table("watermarks").select("*").eq("user_id", user_id).limit(1).execute()

    if not watermark.data:
        for path in image_paths:
            shutil.copy(path, os.path.join(final_dir, os.path.basename(path)))
        return

    w = watermark.data[0]
    logo_bytes = storage_service.read_file_bytes(w["logo_url"])
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_logo:
        tmp_logo.write(logo_bytes)
        logo_path = tmp_logo.name

    try:
        config = WatermarkConfig(
            position=w["position"],
            opacity=w["opacity"],
            scale=w["scale"],
            custom_x=w.get("pos_x"),
            custom_y=w.get("pos_y"),
            rotation=w.get("rotation") or 0.0,
        )
        apply_watermark_batch(image_paths, logo_path, config, final_dir)
    finally:
        os.unlink(logo_path)


def _update_project(db, project_id: str, fields: dict, attempts: int = 3) -> bool:
    """Actualiza la fila del proyecto con reintentos cortos — un solo hiccup de
    red hacia Supabase no debe tumbar todo el lote ni dejarlo atascado en
    'processing' para siempre. Devuelve True si logró escribir."""
    for attempt in range(attempts):
        try:
            db.table("projects").update(fields).eq("id", project_id).execute()
            return True
        except Exception:
            logger.warning(
                "Fallo al actualizar proyecto %s (intento %d/%d): %s",
                project_id, attempt + 1, attempts, fields, exc_info=True,
            )
            if attempt < attempts - 1:
                time.sleep(1.5)
    return False


def _run_batch_job(project_id: str, user_id: str, options: BatchOptions):
    """Job de fondo: lee las fotos de ESTE proyecto (tabla `project_photos`),
    las procesa y va reportando avance real (processed_count/total_count) para
    que el frontend pueda mostrar una barra de progreso mientras dura la
    edición automatizada. Al terminar, aplica la marca de agua del usuario
    (si configuró una) y marca el proyecto como 'review' — recién ahí quedan
    listas las fotos finales para exportar (ZIP, Drive, Instagram).

    Todo el cuerpo está protegido: cualquier error (de red hacia Supabase, de
    lectura de un archivo, etc.) marca el proyecto como 'error' en vez de
    dejarlo atascado en 'processing' para siempre sin que el cliente se entere.

    El almacenamiento es independiente del proveedor configurado (ver
    storage_service.py): las fotos originales se descargan a un directorio
    temporal SOLO si el proveedor es remoto (con el proveedor local, se usa
    la ruta directa, sin copia) y esa copia se borra automáticamente al
    terminar el lote, incluso si algo falla a la mitad -- nunca queda un
    archivo temporal huérfano en el disco del servidor."""
    db = get_supabase_admin()
    try:
        photos = db.table("project_photos").select("original_url").eq("project_id", project_id).execute()
        edited_dir = os.path.join(settings.LOCAL_STORAGE_PATH, "edited-photos", project_id)

        with ExitStack() as stack:
            input_paths = [
                stack.enter_context(storage_service.local_copy(p["original_url"])) for p in photos.data
            ]
            input_paths = [p for p in input_paths if p is not None]

            total = len(input_paths)
            _update_project(
                db,
                project_id,
                {
                    "status": "processing",
                    "processed_count": 0,
                    "total_count": total,
                    "processing_started_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Throttleado a ~1 escritura cada 1.5s (en vez de una por foto): menos
            # llamadas de red a Supabase = menos puntos de fallo y menos tiempo
            # total, además de que un fallo puntual aquí no debe frenar el lote.
            last_write = {"t": 0.0}

            def on_progress(done: int, total: int) -> None:
                now = time.monotonic()
                if done < total and (now - last_write["t"]) < 1.5:
                    return
                last_write["t"] = now
                try:
                    db.table("projects").update({"processed_count": done}).eq("id", project_id).execute()
                except Exception:
                    logger.warning("No se pudo reportar avance de %s (%d/%d); se continúa", project_id, done, total)

            results = process_batch(input_paths, edited_dir, options, on_progress=on_progress)
            succeeded = sum(1 for r in results if r.success)

            if total > 0 and succeeded == 0:
                logger.error("Las %d fotos del proyecto %s fallaron al procesarse", total, project_id)
                _update_project(db, project_id, {"status": "error", "processed_count": total, "total_count": total})
                return

            qa_fallback_count = sum(1 for r in results if r.qa_fallback)
            if qa_fallback_count:
                logger.warning(
                    "%d/%d fotos del proyecto %s no pasaron el control de calidad automático; "
                    "se entregaron sin editar", qa_fallback_count, total, project_id,
                )

            edited_paths = [
                os.path.join(edited_dir, os.path.basename(p))
                for p in input_paths
                if os.path.isfile(os.path.join(edited_dir, os.path.basename(p)))
            ]
            final_dir = _final_photos_scratch_dir(project_id)
            _apply_watermark_if_configured(db, user_id, edited_paths, final_dir)

        # Fuera del ExitStack: ya se liberaron las descargas temporales de las
        # fotos originales. Ahora se persiste el resultado final en el
        # proveedor configurado y se limpia el scratch de edición intermedia
        # (nunca hace falta de nuevo: ni preview-pairs ni export.py la leen).
        _persist_final_dir(final_dir, project_id)
        shutil.rmtree(edited_dir, ignore_errors=True)

        _update_project(
            db,
            project_id,
            {
                "status": "review",
                "qa_fallback_count": qa_fallback_count,
                "processing_completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception:
        logger.exception("Fallo inesperado procesando el proyecto %s", project_id)
        _update_project(db, project_id, {"status": "error"})


@router.post(
    "/process",
    dependencies=[Depends(reject_missing_user_agent), Depends(rate_limiter(max_requests=10, window_seconds=60))],
)
async def process_project(
    payload: ProcessProjectRequest,
    background_tasks: BackgroundTasks,
    user: AuthUser = Depends(require_active_membership),
):
    """Dispara el procesamiento automatizado de todas las fotos de un proyecto."""
    db = get_supabase_admin()
    project = (
        db.table("projects").select("*").eq("id", payload.project_id).eq("user_id", user.id).execute()
    )
    if not project.data:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    # Eliminación de objetos (placas, postes, cables) requiere plan Pro/Studio.
    wants_object_removal = payload.remove_plates or payload.remove_logos or payload.remove_poles_wires
    if wants_object_removal and not get_plan_limits(user)["object_removal"]:
        raise HTTPException(
            status_code=403,
            detail=(
                "La eliminación de objetos (placas, logos, postes y cables) "
                "requiere el plan Pro o Studio. Actualiza tu plan para usarla."
            ),
        )

    if payload.weather_override and payload.weather_override not in {"soleado", "nublado", "lluvia"}:
        raise HTTPException(status_code=400, detail="weather_override inválido.")
    if payload.light_override and payload.light_override not in {"baja", "media", "alta"}:
        raise HTTPException(status_code=400, detail="light_override inválido.")

    options = BatchOptions(
        auto_perspective=payload.auto_perspective,
        auto_adjustments=payload.auto_adjustments,
        auto_cleanup=payload.auto_cleanup,
        remove_plates=payload.remove_plates,
        remove_logos=payload.remove_logos,
        remove_poles_wires=payload.remove_poles_wires,
        custom_adjustments=_build_custom_adjustments(payload),
        denoise_strength=payload.noise_reduction,
        weather_override=payload.weather_override,
        light_override=payload.light_override,
    )
    background_tasks.add_task(_run_batch_job, payload.project_id, user.id, options)

    return {"project_id": payload.project_id, "status": "processing_started"}


@router.get("/style-profiles")
async def get_style_profiles(user: AuthUser = Depends(require_active_membership)):
    """Catálogo de Perfiles de Estilo IA (Bodas, Retratos, Automóviles, etc.)
    para las tarjetas de selección del frontend."""
    return list_style_profiles_public()


@router.get("/projects/{project_id}/preview-pairs")
async def get_preview_pairs(project_id: str, user: AuthUser = Depends(require_active_membership)):
    """Pares (original, editada) de una sesión ya procesada, para el
    comparador Antes/Después. Vacío si el proyecto todavía no terminó."""
    db = get_supabase_admin()
    project = (
        db.table("projects").select("status").eq("id", project_id).eq("user_id", user.id).execute()
    )
    if not project.data:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if project.data[0]["status"] != "review":
        return []

    photos = db.table("project_photos").select("id, original_url").eq("project_id", project_id).execute()

    pairs = []
    for row in photos.data:
        filename = _filename_from_url(row["original_url"])
        if not filename:
            continue
        if storage_service.file_exists("final-photos", project_id, filename):
            final_url = storage_service.file_url("final-photos", project_id, filename)
            pairs.append({"photo_id": row["id"], "original_url": row["original_url"], "edited_url": final_url})

    return pairs[:20]  # limita cuántos pares se cargan en el navegador a la vez


class ReeditPhotoRequest(BaseModel):
    """Ajustes manuales para UNA sola foto ya editada (ver 'Edición manual').
    Reutiliza directamente los campos de AdjustmentParams; todos opcionales,
    los que no se envíen quedan en su valor neutro (0)."""
    exposure: float = 0.0
    highlights: float = 0.0
    shadows: float = 0.0
    whites: float = 0.0
    blacks: float = 0.0
    clarity: float = 0.0
    saturation: float = 0.0
    dehaze: float = 0.0
    contrast: float = 0.0
    temperature: float = 0.0


@router.post("/projects/{project_id}/photos/{photo_id}/reedit")
async def reedit_photo(
    project_id: str,
    photo_id: str,
    payload: ReeditPhotoRequest,
    user: AuthUser = Depends(require_active_membership),
):
    """Re-edita UNA sola foto de una sesión ya procesada con ajustes manuales,
    sin tocar el resto del lote. Reutiliza el mismo pipeline (perspectiva +
    ajustes + limpieza) y luego la marca de agua del usuario, sobrescribiendo
    solo el archivo final de esa foto. Corre de forma síncrona (una sola foto,
    no hace falta BackgroundTasks) y NO pasa por el control de calidad
    automático (es un cambio pedido explícitamente por el usuario)."""
    db = get_supabase_admin()
    project = (
        db.table("projects").select("status").eq("id", project_id).eq("user_id", user.id).execute()
    )
    if not project.data:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if project.data[0]["status"] != "review":
        raise HTTPException(status_code=400, detail="La sesión todavía no terminó de procesarse.")

    photo = (
        db.table("project_photos").select("id, original_url").eq("id", photo_id).eq("project_id", project_id).execute()
    )
    if not photo.data:
        raise HTTPException(status_code=404, detail="Foto no encontrada en esta sesión.")

    original_url = photo.data[0]["original_url"]
    edited_dir = os.path.join(settings.LOCAL_STORAGE_PATH, "edited-photos", project_id)
    final_dir = _final_photos_scratch_dir(project_id)

    with storage_service.local_copy(original_url) as original_path:
        if not original_path:
            raise HTTPException(status_code=404, detail="No se pudo leer la foto original.")

        filename = os.path.basename(original_path)
        edited_path = os.path.join(edited_dir, filename)

        options = BatchOptions(
            auto_perspective=True,
            auto_adjustments=True,
            auto_cleanup=True,
            custom_adjustments=AdjustmentParams(**payload.model_dump()),
            run_quality_check=False,
        )
        result = process_single_image(original_path, edited_path, options)
        if not result.success:
            raise HTTPException(status_code=500, detail=f"No se pudo re-editar la foto: {result.error}")

        _apply_watermark_if_configured(db, user.id, [edited_path], final_dir)

    # Fuera del `with`: ya se liberó la copia temporal de la foto original.
    # Se persiste el resultado en el proveedor configurado (sobrescribe la
    # versión final anterior de esta misma foto a propósito -- es una
    # actualización, no un archivo nuevo) y se limpia el scratch de edición.
    final_url = storage_service.persist_local_file(os.path.join(final_dir, filename), "final-photos", project_id, filename)
    edited_path = os.path.join(edited_dir, filename)
    if os.path.isfile(edited_path):
        os.remove(edited_path)

    return {"edited_url": f"{final_url}{'&' if '?' in final_url else '?'}t={int(time.time())}"}


@router.get("/projects/{project_id}/status")
async def get_project_status(project_id: str, user: AuthUser = Depends(require_active_membership)):
    db = get_supabase_admin()
    project = (
        db.table("projects")
        .select("status, name, processed_count, total_count, qa_fallback_count")
        .eq("id", project_id)
        .eq("user_id", user.id)
        .single()
        .execute()
    )
    if not project.data:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project.data
