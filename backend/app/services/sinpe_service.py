"""
Servicio de pagos vía SINPE Móvil (pasarela manual, típica de Costa Rica).
Flujo:
  1. El cliente ve el número SINPE y el nombre del dueño de la cuenta (config).
  2. Hace la transferencia desde su banco/app SINPE.
  3. Sube la captura del comprobante (.jpg/.png) + elige el plan deseado.
  4. Se crea un registro `sinpe_payments` con status='pending'.
  5. Un admin revisa la imagen y Aprueba o Rechaza desde el Panel de Administrador.
  6. Al aprobar, se activa/renueva la membresía del usuario por 30 días.
"""
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from app.database import get_supabase_admin
from app.models.membership import PLAN_CATALOG
from app.config import get_settings
from app.services.email_service import send_email

settings = get_settings()


def validate_plan(plan: str) -> None:
    if plan not in PLAN_CATALOG or plan in ("trial", "founder"):
        raise HTTPException(status_code=400, detail=f"Plan inválido: {plan}")


def create_pending_payment(user_id: str, plan: str, receipt_image_url: str) -> dict:
    """Registra el comprobante subido por el usuario en estado 'pending'."""
    validate_plan(plan)
    db = get_supabase_admin()
    row = {
        "user_id": user_id,
        "plan": plan,
        "receipt_image_url": receipt_image_url,
        "status": "pending",
    }
    result = db.table("sinpe_payments").insert(row).execute()

    # También refleja el intento de membresía como 'pending' para que la UI
    # del cliente muestre "Pendiente de aprobación".
    db.table("memberships").insert(
        {
            "user_id": user_id,
            "plan": plan,
            "status": "pending",
            "starts_at": None,
            "ends_at": None,
        }
    ).execute()
    return result.data[0]


def list_payments_for_user(user_id: str) -> list[dict]:
    """Historial de comprobantes SINPE de un cliente (más reciente primero),
    para que vea el estado de cada uno: pendiente, aprobado o rechazado."""
    db = get_supabase_admin()
    result = (
        db.table("sinpe_payments")
        .select("id, plan, status, created_at, reviewed_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


def list_pending_payments() -> list[dict]:
    """Lista todos los comprobantes SINPE pendientes de revisión (para el admin)."""
    db = get_supabase_admin()
    result = (
        db.table("sinpe_payments")
        # sinpe_payments tiene dos relaciones hacia profiles (user_id y
        # reviewed_by), así que hay que indicarle a PostgREST cuál usar para
        # el embed -- si no, responde 300/ambiguo en vez de la lista.
        .select("*, profiles!sinpe_payments_user_id_fkey(email)")
        .eq("status", "pending")
        .order("created_at", desc=False)
        .execute()
    )
    return result.data


def review_payment(payment_id: str, admin_id: str, approve: bool) -> dict:
    """Aprueba o rechaza un comprobante. Al aprobar, activa la membresía 30 días."""
    db = get_supabase_admin()
    payment = db.table("sinpe_payments").select("*").eq("id", payment_id).single().execute()
    if not payment.data:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    if payment.data["status"] != "pending":
        raise HTTPException(status_code=400, detail="Este comprobante ya fue revisado")

    now = datetime.now(timezone.utc)
    new_status = "approved" if approve else "rejected"

    db.table("sinpe_payments").update(
        {
            "status": new_status,
            "reviewed_by": admin_id,
            "reviewed_at": now.isoformat(),
        }
    ).eq("id", payment_id).execute()

    if approve:
        ends_at = now + timedelta(days=settings.MEMBERSHIP_DURATION_DAYS)
        db.table("memberships").insert(
            {
                "user_id": payment.data["user_id"],
                "plan": payment.data["plan"],
                "status": "active",
                "starts_at": now.isoformat(),
                "ends_at": ends_at.isoformat(),
            }
        ).execute()
    else:
        db.table("memberships").insert(
            {
                "user_id": payment.data["user_id"],
                "plan": payment.data["plan"],
                "status": "rejected",
                "starts_at": None,
                "ends_at": None,
            }
        ).execute()

    _notify_payment_reviewed(db, payment.data["user_id"], payment.data["plan"], approve)
    return {"payment_id": payment_id, "status": new_status}


def _notify_payment_reviewed(db, user_id: str, plan: str, approved: bool) -> None:
    """Correo al cliente cuando su comprobante SINPE cambia de estado (mismo
    patrón de envío que reminder_service.send_payment_reminder)."""
    profile = db.table("profiles").select("email, full_name").eq("id", user_id).single().execute()
    if not profile.data:
        return
    plan_name = PLAN_CATALOG.get(plan, {}).get("name", plan)
    greeting = f"Hola {profile.data['full_name']}," if profile.data.get("full_name") else "Hola,"
    if approved:
        subject = "Photonix AI — Tu pago fue aprobado"
        body = f"""
        <div style="font-family: sans-serif; color: #1a1f2b; line-height: 1.5;">
          <p>{greeting}</p>
          <p>Tu comprobante SINPE Móvil fue <strong>aprobado</strong> y tu plan
          <strong>{plan_name}</strong> ya está activo por
          {settings.MEMBERSHIP_DURATION_DAYS} días.</p>
          <p>— El equipo de Photonix AI</p>
        </div>
        """
    else:
        subject = "Photonix AI — No pudimos validar tu comprobante"
        body = f"""
        <div style="font-family: sans-serif; color: #1a1f2b; line-height: 1.5;">
          <p>{greeting}</p>
          <p>No pudimos validar el comprobante SINPE Móvil que subiste para el
          plan <strong>{plan_name}</strong> (por ejemplo, el monto no coincidía
          o la imagen no era legible). Puedes subir un nuevo comprobante desde
          la sección "Mi Membresía" de tu panel.</p>
          <p>— El equipo de Photonix AI</p>
        </div>
        """
    send_email(profile.data["email"], subject, body)


def get_plan_catalog() -> list[dict]:
    """Catálogo público de planes para mostrar en la página de precios."""
    return [
        {"id": pid, "name": p["name"], "price_crc": p["price_crc"], "duration_days": p["duration_days"]}
        for pid, p in PLAN_CATALOG.items()
        if pid not in ("founder",)  # el plan founder no es público
    ]
