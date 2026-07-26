"""
Dependencies compartidas de FastAPI: resolución del plan activo del usuario y
verificación de membresía / funciones habilitadas según el plan (feature
gating). Se usa en las rutas que consumen el motor de IA y la carga masiva
para que lo que el usuario puede hacer esté en función del plan que pagó.
"""
from __future__ import annotations
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from app.core.security import AuthUser, get_current_user
from app.core.plans import get_features, PlanFeatures
from app.database import get_supabase_admin


def resolve_active_plan(user: AuthUser) -> str | None:
    """Devuelve el id del plan vigente del usuario en este momento (o None si
    no tiene trial ni membresía activa, o si el admin lo bloqueó por mora).
    El fundador siempre es 'founder' (nunca se bloquea a sí mismo)."""
    if user.is_admin:
        return "founder"

    db = get_supabase_admin()
    now = datetime.now(timezone.utc)

    profile = db.table("profiles").select("trial_ends_at, is_blocked").eq("id", user.id).single().execute()
    if profile.data and profile.data.get("is_blocked"):
        return None  # bloqueado manualmente por el admin: sin acceso sin importar trial/membresía

    trial_ends_at = profile.data.get("trial_ends_at") if profile.data else None
    if trial_ends_at and datetime.fromisoformat(trial_ends_at) > now:
        return "trial"

    membership = (
        db.table("memberships")
        .select("plan, status, ends_at")
        .eq("user_id", user.id)
        .eq("status", "active")
        .order("ends_at", desc=True)
        .limit(1)
        .execute()
    )
    if membership.data:
        ends_at = membership.data[0].get("ends_at")
        if ends_at and datetime.fromisoformat(ends_at) > now:
            return membership.data[0]["plan"]

    return None


def get_plan_limits(user: AuthUser) -> PlanFeatures:
    """Funciones/límites del plan activo del usuario (o los del plan Starter
    por defecto si no tiene ninguno vigente)."""
    return get_features(resolve_active_plan(user))


def get_photos_processed_this_month(user_id: str) -> int:
    """Cuenta fotos ya procesadas por este usuario desde el 1° del mes en
    curso (UTC) -- misma consulta que /uploads/stats/summary (el resumen que
    ve el usuario en su Dashboard), para que el número que se le muestra y el
    que realmente lo bloquea sean siempre el mismo."""
    db = get_supabase_admin()
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    result = (
        db.table("projects")
        .select("processed_count")
        .eq("user_id", user_id)
        .gte("created_at", month_start)
        .execute()
    )
    return sum(p.get("processed_count") or 0 for p in result.data)


def check_monthly_photo_quota(user: AuthUser, photos_in_this_batch: int) -> None:
    """Bloquea con 403 si procesar este lote haría que el usuario supere el
    techo mensual de su plan (ver PLAN_FEATURES.max_photos_per_month) --
    None = sin techo (Photonix Pro y Fundador). No cuenta fotos "en cola"
    todavía sin procesar de OTRAS sesiones -- se basa en processed_count real,
    igual que el resumen del Dashboard, para no bloquear con un número que el
    usuario no puede ver reflejado en ningún lado."""
    limit = get_plan_limits(user)["max_photos_per_month"]
    if limit is None:
        return
    used = get_photos_processed_this_month(user.id)
    if used + photos_in_this_batch > limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Esta sesión ({photos_in_this_batch} fotos) superaría tu límite mensual "
                f"del plan ({used}/{limit} fotos ya usadas este mes). "
                "Actualiza tu plan en Membresía y Pagos o espera al próximo mes."
            ),
        )


async def require_active_membership(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Permite el paso si el usuario es admin (fundador, ilimitado) o tiene
    trial vigente / membresía activa. Bloquea con 402 si no."""
    if resolve_active_plan(user) is None:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                "Tu cuenta no tiene acceso activo en este momento (prueba gratuita o membresía "
                "vencida, o cuenta bloqueada por mora). Renueva tu plan o contacta a soporte."
            ),
        )
    return user


def require_feature(feature: str):
    """Factory de dependency: exige que el plan activo del usuario incluya la
    función indicada (ej. 'object_removal'). Responde 403 con mensaje de
    upgrade si el plan actual no la incluye."""

    async def _dependency(user: AuthUser = Depends(require_active_membership)) -> AuthUser:
        features = get_plan_limits(user)
        if not features.get(feature, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Esta función requiere el plan Pro o Studio. "
                    "Actualiza tu plan en Membresía y Pagos para desbloquearla."
                ),
            )
        return user

    return _dependency
