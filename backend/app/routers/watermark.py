"""
Rutas del módulo de Marca de Agua: subir logo PNG transparente y guardar/
actualizar la configuración de posicionamiento del usuario.
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from typing import Optional
from app.core.security import AuthUser, get_current_user
from app.database import get_supabase_admin
from app.services import storage_service

router = APIRouter(prefix="/watermark", tags=["Marca de Agua"])

VALID_POSITIONS = {"north", "south", "east", "west", "center", "custom"}


@router.post("/upload-logo")
async def upload_logo(
    logo: UploadFile = File(...),
    user: AuthUser = Depends(get_current_user),
):
    """Sube el logo del fotógrafo. Debe ser PNG con fondo transparente."""
    if logo.content_type != "image/png":
        raise HTTPException(status_code=400, detail="El logo debe ser un archivo PNG con transparencia.")
    logo_url = await storage_service.upload_file(
        logo, bucket="watermark-logos", path_prefix=user.id, allowed_extensions=storage_service.ALLOWED_LOGO_EXTENSIONS
    )
    return {"logo_url": logo_url}


@router.post("/config")
async def save_watermark_config(
    logo_url: str = Form(...),
    position: str = Form("south"),
    opacity: float = Form(0.8),
    scale: float = Form(0.18),
    pos_x: Optional[float] = Form(None),
    pos_y: Optional[float] = Form(None),
    rotation: float = Form(0.0),
    user: AuthUser = Depends(get_current_user),
):
    """Guarda (o actualiza) la configuración de marca de agua del usuario:
    posición (N/S/E/O/Centro/coordenadas X-Y personalizadas), opacidad, tamaño
    y rotación. pos_x/pos_y son el CENTRO del logo como porcentaje (0-100) del
    ancho/alto de la foto (no píxeles absolutos) — así la posición arrastrada
    en la vista previa del frontend se ve igual en cualquier foto que se procese."""
    if position not in VALID_POSITIONS:
        raise HTTPException(status_code=400, detail=f"Posición inválida: {position}")
    if position == "custom" and (pos_x is None or pos_y is None):
        raise HTTPException(status_code=400, detail="pos_x y pos_y son requeridos para posición 'custom'.")

    db = get_supabase_admin()
    row = {
        "user_id": user.id,
        "logo_url": logo_url,
        "position": position,
        "opacity": max(0.0, min(opacity, 1.0)),
        "scale": max(0.01, min(scale, 1.0)),
        "pos_x": round(max(0.0, min(pos_x, 100.0))) if pos_x is not None else None,
        "pos_y": round(max(0.0, min(pos_y, 100.0))) if pos_y is not None else None,
        "rotation": max(-180.0, min(rotation, 180.0)),
    }
    db.table("watermarks").upsert(row, on_conflict="user_id").execute()
    return row


@router.get("/config")
async def get_watermark_config(user: AuthUser = Depends(get_current_user)):
    db = get_supabase_admin()
    result = db.table("watermarks").select("*").eq("user_id", user.id).execute()
    return result.data[0] if result.data else None
