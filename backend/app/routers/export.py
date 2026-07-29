"""
Rutas de exportación de sesiones/proyectos:
  - Descarga en ZIP de todas las fotos de un proyecto (sin configuración extra).
  - Conexión OAuth con Google Drive + subida de fotos a una carpeta del Drive
    del cliente (requiere credenciales de Google Cloud, ver README.md).
  - Subida a Instagram (placeholder: requiere una app de Meta for Developers).
"""
from __future__ import annotations
import io
import os
import zipfile
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse

from app.config import get_settings
from app.core.dependencies import require_active_membership
from app.core.security import AuthUser, get_current_user
from app.database import get_supabase_admin
from app.services import google_drive_service, storage_service
from app.services.ai.batch_processor import edited_filename

router = APIRouter(prefix="/export", tags=["Exportación"])
settings = get_settings()

STATE_PURPOSE = "google_drive_connect"


def _get_owned_project(db, project_id: str, user_id: str) -> dict:
    project = (
        db.table("projects")
        .select("id, name, status")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not project.data:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project.data[0]


def _safe_project_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in " _-" else "_" for c in name).strip() or "sesion"


def _read_final_photos(project: dict) -> list[tuple[str, bytes]]:
    """Lee en memoria las fotos YA EDITADAS y con marca de agua de un
    proyecto (bucket 'final-photos', separado de las originales -- ver
    ai_engine.py), sin importar el proveedor de almacenamiento configurado.
    Solo están disponibles una vez que el proyecto terminó de procesarse
    (status == 'review')."""
    if project["status"] != "review":
        raise HTTPException(
            status_code=409,
            detail="Todavía no se ha terminado de editar esta sesión. Espera a que el procesamiento finalice.",
        )

    filenames = sorted(storage_service.list_files("final-photos", project["id"]))
    if not filenames:
        raise HTTPException(status_code=404, detail="Este proyecto no tiene fotos editadas para exportar")

    files: list[tuple[str, bytes]] = []
    for index, fname in enumerate(filenames, start=1):
        content = storage_service.read_file("final-photos", project["id"], fname)
        files.append((f"foto_{index:03d}{os.path.splitext(fname)[1]}", content))
    return files


@router.get("/{project_id}/zip")
async def export_project_zip(project_id: str, user: AuthUser = Depends(require_active_membership)):
    """Descarga en un único .zip todas las fotos ya editadas (con marca de
    agua incluida, si el usuario configuró una) de un proyecto."""
    db = get_supabase_admin()
    project = _get_owned_project(db, project_id, user.id)
    files = _read_final_photos(project)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in files:
            zip_file.writestr(filename, content)
    buffer.seek(0)

    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in project["name"]).strip() or "sesion"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.zip"'},
    )


_IMAGE_MEDIA_TYPES = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".tif": "image/tiff", ".tiff": "image/tiff", ".webp": "image/webp",
}


@router.get("/{project_id}/photo/{photo_id}")
async def export_single_photo(project_id: str, photo_id: str, user: AuthUser = Depends(require_active_membership)):
    """Descarga UNA sola foto ya editada -- usada por el frontend cuando la
    sesión tiene entre 1 y 5 fotos (ver ExportPanel.tsx: generar un .zip para
    tan pocas fotos es una fricción innecesaria para el usuario). No toca
    `_read_final_photos`/`export_project_zip` de arriba -- esas siguen
    exactamente igual para sesiones de más de 5 fotos, con su mismo nombrado
    interno ("foto_NNN.ext")."""
    db = get_supabase_admin()
    project = _get_owned_project(db, project_id, user.id)
    if project["status"] != "review":
        raise HTTPException(
            status_code=409,
            detail="Todavía no se ha terminado de editar esta sesión. Espera a que el procesamiento finalice.",
        )

    photo = (
        db.table("project_photos")
        .select("id, original_url")
        .eq("id", photo_id)
        .eq("project_id", project_id)
        .execute()
    )
    if not photo.data:
        raise HTTPException(status_code=404, detail="Foto no encontrada en esta sesión.")

    fname = edited_filename(photo.data[0]["original_url"])
    if not fname or not storage_service.file_exists("final-photos", project_id, fname):
        raise HTTPException(status_code=404, detail="Esta foto todavía no tiene un resultado editado disponible.")

    content = storage_service.read_file("final-photos", project_id, fname)
    ext = os.path.splitext(fname)[1].lower() or ".jpg"

    # Posición de esta foto dentro de la sesión (mismo orden de subida que
    # usan preview-pairs/historial) -- solo para armar un nombre legible,
    # NO afecta en nada al nombrado interno del .zip de arriba.
    all_photos = (
        db.table("project_photos")
        .select("id")
        .eq("project_id", project_id)
        .order("created_at")
        .execute()
    )
    ids_in_order = [p["id"] for p in all_photos.data]
    position = (ids_in_order.index(photo_id) + 1) if photo_id in ids_in_order else 1

    safe_name = _safe_project_name(project["name"])
    download_name = f"{safe_name}_{position:03d}_photonix{ext}"

    return StreamingResponse(
        io.BytesIO(content),
        media_type=_IMAGE_MEDIA_TYPES.get(ext, "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )


# --- Google Drive -----------------------------------------------------------


def _require_google_configured():
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        raise HTTPException(
            status_code=501,
            detail=(
                "La integración con Google Drive todavía no está configurada. "
                "Agrega GOOGLE_OAUTH_CLIENT_ID y GOOGLE_OAUTH_CLIENT_SECRET en backend/.env "
                "(ver README.md)."
            ),
        )


@router.get("/google-drive/status")
async def google_drive_status(user: AuthUser = Depends(get_current_user)):
    return {"connected": google_drive_service.is_connected(user.id)}


@router.get("/google-drive/connect")
async def connect_google_drive(user: AuthUser = Depends(get_current_user)):
    """Devuelve la URL de autorización de Google a la que el frontend debe
    redirigir al navegador (no es una llamada fetch/XHR: es una navegación
    completa, porque el consentimiento ocurre en la pantalla de Google)."""
    _require_google_configured()
    state = jwt.encode(
        {
            "user_id": user.id,
            "purpose": STATE_PURPOSE,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        settings.APP_SECRET_KEY,
        algorithm="HS256",
    )
    return {"authorization_url": google_drive_service.build_authorization_url(state)}


@router.get("/google-drive/callback")
async def google_drive_callback(code: str, state: str):
    """Google redirige aquí después de que el usuario autoriza el acceso. No
    llega con el header Authorization (es una navegación del navegador, no un
    fetch autenticado): el `state` firmado es lo que identifica al usuario."""
    try:
        payload = jwt.decode(state, settings.APP_SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Enlace de conexión inválido o expirado.")

    if payload.get("purpose") != STATE_PURPOSE:
        raise HTTPException(status_code=400, detail="Enlace de conexión inválido.")

    google_drive_service.exchange_code_for_tokens(payload["user_id"], code)
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/dashboard/upload?drive=connected")


@router.delete("/google-drive/connection")
async def disconnect_google_drive(user: AuthUser = Depends(get_current_user)):
    google_drive_service.disconnect(user.id)
    return {"connected": False}


@router.post("/{project_id}/google-drive")
async def export_to_google_drive(project_id: str, user: AuthUser = Depends(require_active_membership)):
    """Sube las fotos del proyecto a una carpeta nueva en el Google Drive del cliente."""
    _require_google_configured()
    db = get_supabase_admin()
    project = _get_owned_project(db, project_id, user.id)
    files = _read_final_photos(project)

    folder_link = google_drive_service.upload_project_photos(user.id, project["name"], files)
    return {"folder_url": folder_link}


# --- Instagram (pendiente de configurar) ------------------------------------


@router.post("/{project_id}/instagram")
async def export_to_instagram(project_id: str, user: AuthUser = Depends(require_active_membership)):
    """Publica las fotos del proyecto en Instagram (requiere una app de Meta
    for Developers con el Instagram Graph API habilitado — ver README.md)."""
    if not settings.INSTAGRAM_ACCESS_TOKEN:
        raise HTTPException(
            status_code=501,
            detail=(
                "La integración con Instagram todavía no está configurada. "
                "El administrador debe crear una app en Meta for Developers con "
                "el Instagram Graph API habilitado y agregar el token en el backend."
            ),
        )
    # TODO: publicación vía Instagram Graph API una vez haya credenciales.
    raise HTTPException(status_code=501, detail="Integración con Instagram en construcción.")
