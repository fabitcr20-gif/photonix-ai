"""
Aprovisiona (o actualiza) la cuenta del fundador/administrador de Photonix AI:
crea el usuario en Supabase Auth con la contraseña indicada (o una generada
aleatoriamente), y le asigna rol 'admin' + membresía 'founder' activa e
ilimitada de por vida — sin pasar por el flujo de registro normal ni pagar.
Es idempotente: correrlo varias veces no duplica el usuario ni la membresía.

Con esta cuenta el fundador puede iniciar sesión con correo/contraseña (además
de que, si alguna vez usa Google/Apple con el mismo correo, también se le
reconoce como admin automáticamente) para monitorear pagos SINPE, aprobarlos o
rechazarlos, y disparar recordatorios de pago a los demás usuarios.

Uso:
    cd backend
    source venv/bin/activate
    export FOUNDER_ADMIN_PASSWORD="una-contraseña-segura"   # opcional
    python -m scripts.bootstrap_founder_admin

Requiere que backend/.env tenga las credenciales reales de Supabase
(SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY) — con las de ejemplo no funcionará.
"""
import os
import secrets
from datetime import datetime, timezone

from app.config import get_settings
from app.database import get_supabase_admin

settings = get_settings()


def _find_user_by_email(db, email: str):
    page = db.auth.admin.list_users()
    users = page.users if hasattr(page, "users") else page
    return next((u for u in users if (u.email or "").lower() == email.lower()), None)


def bootstrap() -> None:
    db = get_supabase_admin()
    email = settings.FOUNDER_ADMIN_EMAIL
    password = os.environ.get("FOUNDER_ADMIN_PASSWORD") or secrets.token_urlsafe(12)

    user_id = None
    try:
        created = db.auth.admin.create_user(
            {
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"full_name": "Fundador Photonix AI", "role": "admin"},
            }
        )
        user_id = created.user.id
        print(f"Usuario creado en Supabase Auth: {email}")
    except Exception as exc:
        print(f"No se pudo crear el usuario (probablemente ya existía): {exc}")
        match = _find_user_by_email(db, email)
        if not match:
            raise RuntimeError(
                "No se pudo crear ni encontrar el usuario del fundador. "
                "Verifica SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY en backend/.env."
            ) from exc
        user_id = match.id
        db.auth.admin.update_user_by_id(user_id, {"password": password})
        print(f"Usuario existente actualizado (contraseña restablecida): {email}")

    now = datetime.now(timezone.utc)

    # Perfil con rol admin, términos aceptados y sin límite de prueba gratuita.
    db.table("profiles").upsert(
        {
            "id": user_id,
            "email": email,
            "full_name": "Fundador Photonix AI",
            "role": "admin",
            "accepted_terms": True,
            "trial_ends_at": None,
        }
    ).execute()

    # Membresía 'founder' activa e ilimitada (solo si no existe ya una).
    existing = (
        db.table("memberships")
        .select("id")
        .eq("user_id", user_id)
        .eq("plan", "founder")
        .limit(1)
        .execute()
    )
    if not existing.data:
        db.table("memberships").insert(
            {
                "user_id": user_id,
                "plan": "founder",
                "status": "active",
                "starts_at": now.isoformat(),
                "ends_at": None,
            }
        ).execute()
        print("Membresía 'founder' (ilimitada, de por vida) activada.")
    else:
        print("Ya existía una membresía 'founder' activa; no se duplicó.")

    print("\n=== Credenciales del administrador ===")
    print(f"Correo:     {email}")
    print(f"Contraseña: {password}")
    print("Guarda esta contraseña en un lugar seguro (ej. tu gestor de contraseñas).")
    print("No se volverá a mostrar; si la pierdes, vuelve a correr este script.")
    print("=======================================\n")


if __name__ == "__main__":
    bootstrap()
