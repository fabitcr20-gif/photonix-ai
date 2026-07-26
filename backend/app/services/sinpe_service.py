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
import logging
import time
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from app.database import get_supabase_admin
from app.models.membership import PLAN_CATALOG
from app.config import get_settings
from app.services.email_service import send_email

settings = get_settings()
logger = logging.getLogger("photonix.sinpe")


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
    """Aprueba o rechaza un comprobante. Al aprobar, activa la membresía 30 días.

    El UPDATE lleva `.eq("status", "pending")` además de `.eq("id", ...)`:
    es una actualización condicional atómica a nivel de base de datos, no un
    "leer el status, decidir, y luego escribir" en dos pasos separados. Antes
    se leía el comprobante primero y se decidía si estaba 'pending' en base a
    ESA lectura -- si dos administradores aprobaban/rechazaban el mismo
    comprobante casi al mismo tiempo, ambas lecturas podían ver 'pending'
    antes de que cualquiera de los dos escribiera, y los dos terminaban
    creando su propia membresía (duración duplicada) y disparando su propio
    correo de notificación. Con la condición en el UPDATE mismo, solo UNA de
    las dos peticiones concurrentes puede afectar la fila (la que llegue
    primero a Postgres) -- la otra no modifica nada (`result.data` vacío) y
    recibe un error claro de "ya fue revisado", exactamente como si hubiera
    llegado un segundo después en vez de al mismo tiempo."""
    db = get_supabase_admin()
    now = datetime.now(timezone.utc)
    new_status = "approved" if approve else "rejected"

    result = (
        db.table("sinpe_payments")
        .update({"status": new_status, "reviewed_by": admin_id, "reviewed_at": now.isoformat()})
        .eq("id", payment_id)
        .eq("status", "pending")
        .execute()
    )
    if not result.data:
        existing = db.table("sinpe_payments").select("id").eq("id", payment_id).maybe_single().execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Comprobante no encontrado")
        raise HTTPException(status_code=400, detail="Este comprobante ya fue revisado")

    payment_data = result.data[0]

    if approve:
        ends_at = now + timedelta(days=settings.MEMBERSHIP_DURATION_DAYS)
        membership_row = {
            "user_id": payment_data["user_id"],
            "plan": payment_data["plan"],
            "status": "active",
            "starts_at": now.isoformat(),
            "ends_at": ends_at.isoformat(),
        }
    else:
        membership_row = {
            "user_id": payment_data["user_id"],
            "plan": payment_data["plan"],
            "status": "rejected",
            "starts_at": None,
            "ends_at": None,
        }

    if not _insert_membership_with_retry(db, membership_row):
        # El UPDATE de arriba YA dejó el comprobante en 'approved'/'rejected',
        # pero la membresía nunca se creó -- sin esto, el cliente pagó y su
        # comprobante quedó "revisado" para siempre sin que su cuenta se
        # active, y como ya no está 'pending', reintentar la aprobación desde
        # el panel falla con "ya fue revisado" (justo el bug que se detectó
        # en la auditoría). Se revierte el comprobante a 'pending' -- una
        # compensación manual, ya que Supabase/PostgREST no da transacciones
        # multi-tabla desde este cliente -- para que vuelva a aparecer en la
        # cola de "Pagos Pendientes" del admin y se pueda reintentar, y se
        # avisa por correo al fundador para que no dependa de que alguien
        # note la reaparición por casualidad.
        db.table("sinpe_payments").update(
            {"status": "pending", "reviewed_by": None, "reviewed_at": None}
        ).eq("id", payment_id).execute()
        _alert_admin_membership_insert_failed(payment_id, payment_data, approve)
        raise HTTPException(
            status_code=502,
            detail=(
                "El comprobante se marcó como revisado pero no se pudo activar la membresía "
                "(problema de conexión con la base de datos). El comprobante volvió a la cola de "
                "pendientes -- inténtalo de nuevo en un momento."
            ),
        )

    _notify_payment_reviewed(db, payment_data["user_id"], payment_data["plan"], approve)
    return {"payment_id": payment_id, "status": new_status}


def _insert_membership_with_retry(db, membership_row: dict, attempts: int = 3) -> bool:
    """Intenta crear la membresía hasta `attempts` veces (backoff corto) --
    el caso real que esto cubre es un problema de red pasajero hacia
    Supabase justo después de que el UPDATE del comprobante ya tuvo éxito,
    no un error de datos (esos fallarían igual en el segundo intento, pero
    seguimos sin dejar la foto sin reintentar)."""
    for attempt in range(attempts):
        try:
            db.table("memberships").insert(membership_row).execute()
            return True
        except Exception:
            logger.warning(
                "Fallo al crear membresía tras aprobar/rechazar pago (intento %d/%d): user_id=%s plan=%s",
                attempt + 1, attempts, membership_row["user_id"], membership_row["plan"], exc_info=True,
            )
            if attempt < attempts - 1:
                time.sleep(1.5)
    return False


def _alert_admin_membership_insert_failed(payment_id: str, payment_data: dict, approved: bool) -> None:
    """Correo al fundador/admin cuando la membresía no se pudo crear después
    de aprobar/rechazar un pago, incluso tras reintentar -- necesita
    atención manual porque el comprobante se revirtió a 'pending' pero el
    problema de fondo (ej. Supabase caído) puede seguir sin resolverse."""
    accion = "aprobar" if approved else "rechazar"
    body = f"""
    <div style="font-family: sans-serif; color: #1a1f2b; line-height: 1.5;">
      <p>No se pudo crear la membresía después de {accion} el comprobante SINPE
      <strong>{payment_id}</strong> (usuario {payment_data.get('user_id')}, plan
      {payment_data.get('plan')}), incluso después de reintentar. El comprobante
      se revirtió automáticamente a estado "pendiente" -- revísalo manualmente
      en el Panel de Administrador.</p>
    </div>
    """
    try:
        send_email(settings.FOUNDER_ADMIN_EMAIL, "Photonix AI — Fallo al activar una membresía", body)
    except Exception:
        logger.exception("Tampoco se pudo enviar el correo de alerta al admin para el pago %s", payment_id)


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
