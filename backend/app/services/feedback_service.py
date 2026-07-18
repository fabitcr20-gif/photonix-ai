"""
Retroalimentación del cliente sobre una sesión ya editada. Flujo:
  1. Tras terminar de procesar una sesión, el cliente puede calificarla
     (1-5 estrellas) y dejar un comentario opcional, o descartar el aviso.
  2. El admin ve todas las calificaciones/comentarios en el Panel de
     Administrador y puede marcarlas como pendiente/en análisis/implementada/
     descartada para priorizar futuras versiones.
"""
from typing import Optional
from fastapi import HTTPException
from app.database import get_supabase_admin

VALID_STATUSES = {"pending", "in_review", "implemented", "discarded"}


def create_feedback(user_id: str, rating: int, comment: Optional[str], project_id: Optional[str]) -> dict:
    if not (1 <= rating <= 5):
        raise HTTPException(status_code=400, detail="La calificación debe estar entre 1 y 5.")
    db = get_supabase_admin()
    row = {"user_id": user_id, "rating": rating, "comment": comment, "project_id": project_id}
    result = db.table("feedback").insert(row).execute()
    return result.data[0]


def list_all_feedback() -> list[dict]:
    """Todo el feedback (para el admin), más reciente primero, con el correo
    del usuario y la cantidad de fotos de la sesión asociada."""
    db = get_supabase_admin()
    result = (
        db.table("feedback")
        .select("*, profiles(email), projects(total_count)")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


def update_feedback_status(feedback_id: str, status: str) -> dict:
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Estado inválido: {status}")
    db = get_supabase_admin()
    result = db.table("feedback").update({"status": status}).eq("id", feedback_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Retroalimentación no encontrada")
    return result.data[0]
