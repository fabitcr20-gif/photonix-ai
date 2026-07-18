"""
Control de acceso basado en roles (RBAC) para Photonix AI. Tres niveles:
  - Invitado: sin token válido. No es un rol almacenado -- `get_current_user`
    (app/core/security.py) responde 401 antes de que exista un `AuthUser`.
  - Cliente ('client'): cualquier usuario autenticado sin privilegios de admin.
  - Administrador ('admin'): fundador/desarrollador, resuelto EXCLUSIVAMENTE
    del lado del servidor (correo del fundador o columna `profiles.role`,
    nunca de datos que el navegador pueda enviar -- ver
    `_resolve_server_role` en security.py).
"""
from fastapi import Depends, HTTPException, status
from app.core.security import AuthUser, get_current_user


def require_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Dependency que bloquea el acceso a cualquier usuario que no sea admin."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso exclusivo para administradores.",
        )
    return user


def require_client_or_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Cualquier usuario autenticado (cliente o admin) puede pasar."""
    return user
