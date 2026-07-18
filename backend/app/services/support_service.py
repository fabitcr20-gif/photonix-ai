"""
Servicio de soporte técnico (tickets). Flujo:
  1. El cliente escribe un ticket (asunto + mensaje) desde 'Ayuda'.
  2. El admin lo ve en el Panel de Administrador y responde.
  3. El cliente ve la respuesta en su lista de tickets.
"""
from datetime import datetime, timezone
from fastapi import HTTPException
from app.database import get_supabase_admin

VALID_STATUSES = {"open", "in_progress", "closed"}


def create_ticket(user_id: str, subject: str, message: str) -> dict:
    db = get_supabase_admin()
    row = {"user_id": user_id, "subject": subject, "message": message, "status": "open"}
    result = db.table("support_tickets").insert(row).execute()
    return result.data[0]


def list_tickets_for_user(user_id: str) -> list[dict]:
    db = get_supabase_admin()
    result = (
        db.table("support_tickets")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


def list_all_tickets() -> list[dict]:
    """Todos los tickets (para el admin), más recientes primero."""
    db = get_supabase_admin()
    result = (
        db.table("support_tickets")
        .select("*, profiles(email)")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


def reply_ticket(ticket_id: str, reply: str, status: str = "closed") -> dict:
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Estado inválido: {status}")
    db = get_supabase_admin()
    ticket = db.table("support_tickets").select("id").eq("id", ticket_id).execute()
    if not ticket.data:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    result = (
        db.table("support_tickets")
        .update({"admin_reply": reply, "status": status, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", ticket_id)
        .execute()
    )
    return result.data[0]
