"""
Módulo de carga de archivos.
- POST /uploads/single: carga individual (un solo dropzone).
- POST /uploads/batch: carga masiva — recibe una carpeta completa (el
  frontend usa <input webkitdirectory> o drag&drop de carpeta y envía todos
  los archivos como multipart/form-data en un solo request).
Ambas rutas exigen membresía activa (trial vigente o plan pagado aprobado).
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from app.core.dependencies import require_active_membership, get_plan_limits
from app.core.rate_limit import rate_limiter, reject_missing_user_agent
from app.core.security import AuthUser
from app.database import get_supabase_admin
from app.services import storage_service

router = APIRouter(prefix="/uploads", tags=["Carga de Archivos"])
_upload_guards = [Depends(reject_missing_user_agent), Depends(rate_limiter(max_requests=15, window_seconds=60))]

# Formatos soportados de fotografía (validados de verdad en storage_service.upload_file/upload_many).
SUPPORTED_FORMATS = storage_service.ALLOWED_IMAGE_EXTENSIONS


@router.post("/single", dependencies=_upload_guards)
async def upload_single_photo(
    file: UploadFile = File(...),
    user: AuthUser = Depends(require_active_membership),
):
    """Carga individual: un dropzone para una sola foto."""
    url = await storage_service.upload_file(
        file, bucket="raw-photos", path_prefix=user.id, allowed_extensions=SUPPORTED_FORMATS
    )
    project_id = _register_project(user.id, name="Carga individual", photo_urls=[url])
    return {"project_id": project_id, "uploaded": [url]}


@router.post("/batch", dependencies=_upload_guards)
async def upload_batch_photos(
    files: list[UploadFile] = File(...),
    project_name: str = "Nueva sesión",
    user: AuthUser = Depends(require_active_membership),
):
    """Carga masiva: acepta cientos/miles de archivos de una carpeta completa
    (RAW, JPEG, PNG, TIFF, HEIC, DNG y variantes RAW de cámara)."""
    max_photos = get_plan_limits(user)["max_batch_photos"]
    if max_photos is not None and len(files) > max_photos:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Tu plan permite hasta {max_photos} fotos por carga masiva "
                f"(tenías {len(files)}). Actualiza tu plan para sesiones más grandes."
            ),
        )

    urls = await storage_service.upload_many(
        files, bucket="raw-photos", path_prefix=user.id, allowed_extensions=SUPPORTED_FORMATS
    )
    project_id = _register_project(user.id, name=project_name, photo_urls=urls)
    return {"project_id": project_id, "uploaded_count": len(urls), "uploaded": urls}


@router.get("/projects")
async def list_projects(user: AuthUser = Depends(require_active_membership)):
    """Historial de sesiones del usuario (más reciente primero), con la
    cantidad de fotos de cada una — usado por las páginas Historial y
    Exportaciones del dashboard."""
    db = get_supabase_admin()
    projects = (
        db.table("projects")
        .select("id, name, status, processed_count, total_count, created_at")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )

    result = []
    for project in projects.data:
        count = (
            db.table("project_photos")
            .select("id", count="exact")
            .eq("project_id", project["id"])
            .execute()
        )
        result.append({**project, "photo_count": count.count or 0})
    return result


@router.get("/stats/summary")
async def get_upload_stats_summary(user: AuthUser = Depends(require_active_membership)):
    """Resumen para el Dashboard: fotos procesadas este mes y las sesiones
    más recientes, reutilizando la misma tabla `projects` que /uploads/projects."""
    db = get_supabase_admin()
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    this_month = (
        db.table("projects")
        .select("processed_count")
        .eq("user_id", user.id)
        .gte("created_at", month_start)
        .execute()
    )
    photos_this_month = sum(p.get("processed_count") or 0 for p in this_month.data)

    recent = (
        db.table("projects")
        .select("id, name, status, processed_count, total_count, created_at")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )

    return {"photos_this_month": photos_this_month, "recent_projects": recent.data}


class RenameProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


@router.patch("/projects/{project_id}")
async def rename_project(
    project_id: str,
    payload: RenameProjectRequest,
    user: AuthUser = Depends(require_active_membership),
):
    """Cambia el nombre de una sesión propia."""
    db = get_supabase_admin()
    result = (
        db.table("projects")
        .update({"name": payload.name})
        .eq("id", project_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    return result.data[0]


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, user: AuthUser = Depends(require_active_membership)):
    """Elimina una sesión: su registro, sus fotos asociadas y los archivos
    editados/finales -- en el proveedor de almacenamiento que esté
    configurado (local, Supabase Storage o S3/R2), no solo en disco local.
    Las fotos crudas NO se borran (viven en una carpeta compartida por
    usuario, no por sesión, y podrían pertenecer a otra sesión también)."""
    db = get_supabase_admin()
    project = db.table("projects").select("id").eq("id", project_id).eq("user_id", user.id).execute()
    if not project.data:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")

    db.table("project_photos").delete().eq("project_id", project_id).execute()
    db.table("projects").delete().eq("id", project_id).execute()

    for bucket in ("edited-photos", "final-photos"):
        storage_service.delete_prefix(bucket, project_id)

    return {"project_id": project_id, "deleted": True}


def _register_project(user_id: str, name: str, photo_urls: list[str]) -> str:
    """Crea el registro del proyecto/sesión y guarda qué fotos le pertenecen
    (necesario para poder exportarlas después, ej. como ZIP)."""
    db = get_supabase_admin()
    project_id = str(uuid.uuid4())
    db.table("projects").insert(
        {
            "id": project_id,
            "user_id": user_id,
            "name": name,
            "status": "processing",
        }
    ).execute()
    if photo_urls:
        db.table("project_photos").insert(
            [{"project_id": project_id, "original_url": url} for url in photo_urls]
        ).execute()
    return project_id
