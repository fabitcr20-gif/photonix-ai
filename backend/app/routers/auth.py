"""
Rutas de autenticación.
El registro/login real de credenciales (email+password, Google, Apple) lo
maneja Supabase Auth desde el FRONTEND (usando @supabase/supabase-js), ya que
Supabase gestiona el flujo OAuth con redirects. Este router se encarga de:
  1. Crear el perfil (`profiles`) en nuestra base de datos justo después del
     registro, guardando el checkbox de Términos y Condiciones y arrancando
     el trial gratuito de 30 días.
  2. Asignar automáticamente el rol 'admin' + plan 'founder' ilimitado si el
     email coincide con el correo del fundador/desarrollador.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.core.rate_limit import rate_limiter, reject_missing_user_agent
from app.core.security import AuthUser, get_current_user
from app.core.dependencies import resolve_active_plan, get_plan_limits
from app.database import get_supabase_admin
from app.schemas.auth import RegisterRequest
from app.schemas.user import ProfileResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])
settings = get_settings()


def _bootstrap_profile_and_membership(db, user: AuthUser, full_name: str | None = None) -> dict:
    """Crea el perfil + membresía inicial de un usuario autenticado que aún no
    los tiene. Se usa tanto en /complete-registration como como red de
    seguridad en /me, para cubrir cualquier forma de entrar a la cuenta:
    registro con correo (con o sin confirmación de correo pendiente), login
    posterior, o Google/Apple OAuth. Detecta al fundador por su correo y le da
    membresía 'founder' activa e ilimitada de por vida; todo el resto arranca
    con el trial gratuito de 30 días."""
    is_founder = user.email.lower() == settings.FOUNDER_ADMIN_EMAIL.lower()
    now = datetime.now(timezone.utc)
    trial_ends_at = None if is_founder else now + timedelta(days=settings.TRIAL_DAYS)

    profile_row = {
        "id": user.id,
        "email": user.email,
        "full_name": full_name or user.email.split("@")[0],
        "role": "admin" if is_founder else "client",
        "accepted_terms": True,
        "trial_ends_at": trial_ends_at.isoformat() if trial_ends_at else None,
    }
    db.table("profiles").upsert(profile_row).execute()

    if is_founder:
        existing_founder = (
            db.table("memberships")
            .select("id")
            .eq("user_id", user.id)
            .eq("plan", "founder")
            .limit(1)
            .execute()
        )
        if not existing_founder.data:
            db.table("memberships").insert(
                {
                    "user_id": user.id,
                    "plan": "founder",
                    "status": "active",
                    "starts_at": now.isoformat(),
                    "ends_at": None,  # sin expiración
                }
            ).execute()
    else:
        existing_membership = (
            db.table("memberships").select("id").eq("user_id", user.id).limit(1).execute()
        )
        if not existing_membership.data:
            db.table("memberships").insert(
                {
                    "user_id": user.id,
                    "plan": "trial",
                    "status": "active",
                    "starts_at": now.isoformat(),
                    "ends_at": trial_ends_at.isoformat(),
                }
            ).execute()

    return profile_row


@router.post(
    "/complete-registration",
    response_model=ProfileResponse,
    dependencies=[Depends(reject_missing_user_agent), Depends(rate_limiter(max_requests=5, window_seconds=60))],
)
async def complete_registration(
    payload: RegisterRequest, user: AuthUser = Depends(get_current_user)
):
    """Se llama justo después de que Supabase Auth crea el usuario (signUp),
    para inicializar su fila en `profiles`. Es idempotente: si el perfil ya
    existe (ej. se llamó dos veces), simplemente lo devuelve sin volver a
    validar el checkbox de términos ni duplicar la membresía."""
    db = get_supabase_admin()

    existing = db.table("profiles").select("*").eq("id", user.id).limit(1).execute()
    if existing.data:
        profile_row = existing.data[0]
    else:
        if not payload.accepted_terms:
            raise HTTPException(
                status_code=400,
                detail="Debes aceptar los Términos y Condiciones para registrarte.",
            )
        profile_row = _bootstrap_profile_and_membership(db, user, full_name=payload.full_name)

    is_founder = user.email.lower() == settings.FOUNDER_ADMIN_EMAIL.lower()
    active_plan = "founder" if is_founder else "trial"
    return ProfileResponse(
        **profile_row,
        membership_plan=active_plan,
        membership_status="active",
        active_plan=active_plan,
        plan_features=get_plan_limits(user),
    )


@router.get("/me", response_model=ProfileResponse)
async def get_me(user: AuthUser = Depends(get_current_user)):
    """Devuelve el perfil completo + estado de membresía del usuario autenticado.
    Si el perfil no existe todavía (ej. confirmó su correo y esta es su
    primera visita autenticada, o entró por Google/Apple sin pasar por el
    formulario de registro), se crea aquí mismo — así el usuario nunca queda
    "atrapado" sin perfil por no haber podido llamar a /complete-registration
    justo después del signUp."""
    db = get_supabase_admin()
    profile = db.table("profiles").select("*").eq("id", user.id).maybe_single().execute()

    if profile is None or not profile.data:
        profile_row = _bootstrap_profile_and_membership(db, user)
    else:
        profile_row = profile.data

    membership = (
        db.table("memberships")
        .select("plan, status")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    plan = membership.data[0]["plan"] if membership.data else None
    status_ = membership.data[0]["status"] if membership.data else None

    return ProfileResponse(
        **profile_row,
        membership_plan=plan,
        membership_status=status_,
        active_plan=resolve_active_plan(user),
        plan_features=get_plan_limits(user),
    )
