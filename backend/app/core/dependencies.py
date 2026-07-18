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
