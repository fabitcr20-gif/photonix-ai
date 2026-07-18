"""
Recordatorios automáticos de pago. Detecta clientes (nunca el fundador/admin,
que tiene acceso ilimitado de por vida) cuya prueba gratuita o membresía
activa vence pronto o ya venció, y les envía un correo recordándoles renovar
por SINPE Móvil. Se puede disparar manualmente desde el Panel de Administrador
(ver routers/admin.py) o automáticamente todos los días (ver main.py, tarea
programada opcional vía APScheduler).
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.database import get_supabase_admin
from app.models.membership import PLAN_CATALOG
from app.services.email_service import send_email

settings = get_settings()


def latest_active_membership_by_user(memberships: list[dict]) -> dict[str, dict]:
    """De una lista de membresías con status='active', se queda con la más
    reciente (por fecha de creación) para cada usuario."""
    latest: dict[str, dict] = {}
    for m in memberships:
        uid = m["user_id"]
        if uid not in latest or (m.get("created_at") or "") > (latest[uid].get("created_at") or ""):
            latest[uid] = m
    return latest


def get_users_needing_reminder(days_before: int | None = None) -> list[dict]:
    """Clientes (rol != admin) cuyo trial o membresía activa vence dentro de
    `days_before` días, o ya venció. Cada item: user_id, email, full_name,
    plan, ends_at, expired."""
    days_before = settings.REMINDER_DAYS_BEFORE_EXPIRY if days_before is None else days_before
    db = get_supabase_admin()
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=days_before)

    profiles = (
        db.table("profiles")
        .select("id, email, full_name, role, trial_ends_at, is_blocked")
        .neq("role", "admin")
        .execute()
    )
    memberships = (
        db.table("memberships")
        .select("user_id, plan, status, ends_at, created_at")
        .eq("status", "active")
        .execute()
    )
    latest_active = latest_active_membership_by_user(memberships.data)

    due: list[dict] = []
    for p in profiles.data:
        uid = p["id"]
        membership = latest_active.get(uid)

        ends_at_raw = None
        plan = "trial"
        if membership and membership.get("ends_at"):
            ends_at_raw = membership["ends_at"]
            plan = membership["plan"]
        elif p.get("trial_ends_at"):
            ends_at_raw = p["trial_ends_at"]
            plan = "trial"

        if not ends_at_raw:
            continue  # sin trial ni membresía con fecha de vencimiento: nada que recordar

        ends_at = datetime.fromisoformat(ends_at_raw.replace("Z", "+00:00"))
        if ends_at <= horizon:
            due.append(
                {
                    "user_id": uid,
                    "email": p["email"],
                    "full_name": p.get("full_name"),
                    "plan": plan,
                    "ends_at": ends_at_raw,
                    "expired": ends_at <= now,
                    "is_blocked": p.get("is_blocked", False),
                }
            )
    return due


def _reminder_email_body(full_name: str | None, plan: str, ends_at: str, expired: bool) -> str:
    plan_name = PLAN_CATALOG.get(plan, {}).get("name", plan)
    greeting = f"Hola {full_name}," if full_name else "Hola,"
    status_line = "tu membresía ya venció" if expired else "tu membresía está por vencer"
    return f"""
    <div style="font-family: sans-serif; color: #1a1f2b; line-height: 1.5;">
      <p>{greeting}</p>
      <p>Te escribimos porque {status_line} en <strong>Photonix AI</strong>
      (plan <strong>{plan_name}</strong>, vence el {ends_at[:10]}).</p>
      <p>Para seguir editando tus sesiones sin interrupciones, realiza tu pago por
      SINPE Móvil al <strong>{settings.SINPE_PHONE_NUMBER}</strong> a nombre de
      <strong>{settings.SINPE_OWNER_NAME}</strong> y sube el comprobante desde tu
      panel, en la sección "Membresía y Pagos".</p>
      <p>— El equipo de Photonix AI</p>
    </div>
    """


def send_payment_reminder(user: dict) -> bool:
    """Envía el correo de recordatorio a un único usuario (dict devuelto por
    get_users_needing_reminder)."""
    subject = "Photonix AI — Recordatorio de pago de tu membresía"
    body = _reminder_email_body(user.get("full_name"), user["plan"], user["ends_at"], user["expired"])
    return send_email(user["email"], subject, body)


def send_bulk_reminders() -> dict:
    """Envía recordatorios a todos los clientes que lo necesiten ahora mismo.
    Pensado para correrse manualmente (Panel Admin) o en una tarea diaria."""
    due_users = get_users_needing_reminder()
    sent = sum(1 for u in due_users if send_payment_reminder(u))
    return {"checked": len(due_users), "reminders_sent": sent}
