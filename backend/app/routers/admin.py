"""
Panel de Administrador — EXCLUSIVO para el fundador/desarrollador (rol 'admin').
Incluye:
  - Estadísticas: usuarios nuevos por día/mes, usuarios activos.
  - Validación de comprobantes SINPE: listar pendientes, aprobar o rechazar.
  - Usuarios: listado completo + bloqueo/desbloqueo manual por mora o abuso.
Todas las rutas están protegidas con `require_admin`.
"""
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.core.roles import require_admin
from app.core.security import AuthUser
from app.database import get_supabase_admin
from app.services import sinpe_service, reminder_service, support_service, session_watchdog, feedback_service
from app.schemas.payment import SinpePaymentAdminView, SinpePaymentReviewRequest

router = APIRouter(prefix="/admin", tags=["Panel Admin"], dependencies=[Depends(require_admin)])


@router.get("/stats/new-users")
async def new_users_stats(granularity: str = "day", days: int = 30):
    """Cuenta de usuarios nuevos agrupados por día o mes, para graficar en el
    frontend (ej. Recharts). granularity: 'day' | 'month'."""
    db = get_supabase_admin()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = (
        db.table("profiles").select("created_at").gte("created_at", since).execute()
    )

    buckets: dict[str, int] = defaultdict(int)
    for row in result.data:
        created = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        key = created.strftime("%Y-%m-%d") if granularity == "day" else created.strftime("%Y-%m")
        buckets[key] += 1

    series = [{"date": k, "new_users": v} for k, v in sorted(buckets.items())]
    return {"granularity": granularity, "series": series, "total": len(result.data)}


@router.get("/stats/active-users")
async def active_users_stats():
    """Usuarios con trial vigente o membresía 'active' en este momento."""
    db = get_supabase_admin()
    now = datetime.now(timezone.utc).isoformat()

    trial_active = (
        db.table("profiles").select("id", count="exact").gt("trial_ends_at", now).execute()
    )
    membership_active = (
        db.table("memberships")
        .select("user_id", count="exact")
        .eq("status", "active")
        .gt("ends_at", now)
        .execute()
    )
    total_users = db.table("profiles").select("id", count="exact").execute()

    return {
        "active_trial_users": trial_active.count or 0,
        "active_paid_memberships": membership_active.count or 0,
        "total_registered_users": total_users.count or 0,
    }


@router.get("/sinpe/pending", response_model=list[SinpePaymentAdminView])
async def list_pending_sinpe():
    """Lista de comprobantes SINPE entrantes esperando revisión."""
    payments = sinpe_service.list_pending_payments()
    return [
        SinpePaymentAdminView(
            id=p["id"],
            user_id=p["user_id"],
            user_email=(p.get("profiles") or {}).get("email"),
            plan=p["plan"],
            receipt_image_url=p["receipt_image_url"],
            status=p["status"],
            created_at=p["created_at"],
        )
        for p in payments
    ]


@router.post("/sinpe/{payment_id}/review")
async def review_sinpe_payment(
    payment_id: str,
    payload: SinpePaymentReviewRequest,
    admin: AuthUser = Depends(require_admin),
):
    """Aprobar activa la membresía por 30 días; rechazar marca el comprobante
    como rechazado y notifica al cliente (vía estado de membresía)."""
    approve = payload.action == "approve"
    return sinpe_service.review_payment(payment_id, admin.id, approve)


@router.get("/users")
async def list_users():
    """Todos los clientes (sin contar al fundador) con su plan/estado vigente
    y si están bloqueados -- vista general para autorizar o bloquear por mora
    sin depender de que exista un comprobante SINPE pendiente."""
    db = get_supabase_admin()
    now = datetime.now(timezone.utc).isoformat()

    profiles = (
        db.table("profiles")
        .select("id, email, full_name, trial_ends_at, is_blocked, created_at")
        .neq("role", "admin")
        .order("created_at", desc=True)
        .execute()
    )
    memberships = (
        db.table("memberships")
        .select("user_id, plan, status, ends_at, created_at")
        .eq("status", "active")
        .execute()
    )
    latest_active = reminder_service.latest_active_membership_by_user(memberships.data)

    users = []
    for p in profiles.data:
        membership = latest_active.get(p["id"])
        if membership and membership.get("ends_at") and membership["ends_at"] > now:
            plan, ends_at, active = membership["plan"], membership["ends_at"], True
        elif p.get("trial_ends_at") and p["trial_ends_at"] > now:
            plan, ends_at, active = "trial", p["trial_ends_at"], True
        else:
            plan = membership["plan"] if membership else "trial"
            ends_at = membership.get("ends_at") if membership else p.get("trial_ends_at")
            active = False

        users.append(
            {
                "user_id": p["id"],
                "email": p["email"],
                "full_name": p.get("full_name"),
                "plan": plan,
                "ends_at": ends_at,
                "active": active and not p.get("is_blocked", False),
                "is_blocked": p.get("is_blocked", False),
                "created_at": p["created_at"],
            }
        )
    return users


@router.post("/users/{user_id}/block")
async def block_user(user_id: str):
    """Bloquea el acceso de un cliente de inmediato (mora, abuso, fraude en un
    comprobante, etc.), sin importar si su trial/membresía sigue vigente."""
    db = get_supabase_admin()
    result = db.table("profiles").update({"is_blocked": True}).eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return {"user_id": user_id, "is_blocked": True}


@router.post("/users/{user_id}/unblock")
async def unblock_user(user_id: str):
    """Restaura el acceso de un cliente previamente bloqueado."""
    db = get_supabase_admin()
    result = db.table("profiles").update({"is_blocked": False}).eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return {"user_id": user_id, "is_blocked": False}


@router.get("/reminders/due")
async def list_due_reminders():
    """Clientes cuya prueba gratuita o membresía vence pronto o ya venció."""
    return reminder_service.get_users_needing_reminder()


@router.post("/reminders/send/{user_id}")
async def send_single_reminder(user_id: str):
    """Envía el recordatorio de pago a un único cliente."""
    due_by_id = {u["user_id"]: u for u in reminder_service.get_users_needing_reminder(days_before=3650)}
    user_due = due_by_id.get(user_id)
    if not user_due:
        raise HTTPException(
            status_code=404,
            detail="Ese usuario no requiere un recordatorio en este momento.",
        )
    sent = reminder_service.send_payment_reminder(user_due)
    return {"user_id": user_id, "sent": sent}


@router.post("/reminders/send-all")
async def send_all_reminders():
    """Envía el recordatorio de pago a todos los clientes que lo necesiten ahora."""
    return reminder_service.send_bulk_reminders()


@router.post("/sessions/recover-stuck")
async def recover_stuck_sessions():
    """Dispara manualmente el watchdog de sesiones atascadas (ver
    services/session_watchdog.py) -- útil para verificar que funciona o para
    forzar una recuperación inmediata sin esperar al siguiente ciclo
    automático."""
    return session_watchdog.recover_stuck_projects()


class TicketReplyRequest(BaseModel):
    reply: str = Field(..., min_length=1, max_length=5000)
    status: str = "closed"  # 'open' | 'in_progress' | 'closed'


@router.get("/support/tickets")
async def list_support_tickets():
    """Todos los tickets de soporte, más recientes primero."""
    return support_service.list_all_tickets()


@router.post("/support/tickets/{ticket_id}/reply")
async def reply_support_ticket(ticket_id: str, payload: TicketReplyRequest):
    return support_service.reply_ticket(ticket_id, payload.reply, payload.status)


@router.get("/feedback")
async def list_feedback():
    """Toda la retroalimentación de clientes, más reciente primero."""
    return feedback_service.list_all_feedback()


class FeedbackStatusRequest(BaseModel):
    status: str  # 'pending' | 'in_review' | 'implemented' | 'discarded'


@router.post("/feedback/{feedback_id}/status")
async def set_feedback_status(feedback_id: str, payload: FeedbackStatusRequest):
    return feedback_service.update_feedback_status(feedback_id, payload.status)


@router.get("/stats/photos")
async def photos_stats():
    """Total de fotos procesadas y tiempo promedio de procesamiento (entre
    projects.processing_started_at y processing_completed_at, solo sesiones
    que terminaron con éxito)."""
    db = get_supabase_admin()
    projects = (
        db.table("projects")
        .select("processed_count, processing_started_at, processing_completed_at")
        .execute()
    )
    total_photos = sum(p.get("processed_count") or 0 for p in projects.data)

    durations = []
    for p in projects.data:
        if p.get("processing_started_at") and p.get("processing_completed_at"):
            started = datetime.fromisoformat(p["processing_started_at"].replace("Z", "+00:00"))
            completed = datetime.fromisoformat(p["processing_completed_at"].replace("Z", "+00:00"))
            durations.append((completed - started).total_seconds())

    avg_seconds = round(sum(durations) / len(durations)) if durations else None
    return {"total_photos_processed": total_photos, "avg_processing_seconds": avg_seconds}


@router.get("/stats/payments")
async def payments_stats():
    """Cuenta de comprobantes SINPE por estado."""
    db = get_supabase_admin()
    result = db.table("sinpe_payments").select("status").execute()
    counts = {"pending": 0, "approved": 0, "rejected": 0}
    for row in result.data:
        if row["status"] in counts:
            counts[row["status"]] += 1
    return counts
