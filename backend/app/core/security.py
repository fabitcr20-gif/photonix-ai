"""
Verificación de tokens JWT emitidos por Supabase Auth.
Los proyectos de Supabase pueden firmar los tokens de sesión de dos formas:
  - Esquema nuevo (por defecto en proyectos recientes): llaves asimétricas
    (ES256/RS256), verificables con la clave pública publicada en
    `/auth/v1/.well-known/jwks.json`.
  - Esquema clásico (proyectos antiguos): un secreto compartido (HS256),
    `SUPABASE_JWT_SECRET`.
Este módulo intenta primero el esquema nuevo (JWKS) y cae al secreto
compartido si el proyecto no publica llaves asimétricas, para funcionar con
cualquiera de los dos sin configuración adicional.
"""
import logging
import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)
_jwks_client = PyJWKClient(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")
logger = logging.getLogger("photonix.security")


class AuthUser:
    """Representa al usuario autenticado extraído del JWT."""

    def __init__(self, user_id: str, email: str, role: str):
        self.id = user_id
        self.email = email
        self.role = role  # 'admin' | 'client'

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def decode_supabase_jwt(token: str) -> dict:
    try:
        try:
            signing_key = _jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience="authenticated",
            )
        except PyJWKClientError:
            # El proyecto no publica llaves asimétricas: usa el esquema
            # clásico de secreto compartido.
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        return payload
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido o expirado: {exc}",
        )


def _resolve_server_role(user_id: str, email: str) -> str:
    """Determina el rol EXCLUSIVAMENTE desde fuentes que el cliente no puede
    manipular:
      1. El correo coincide con FOUNDER_ADMIN_EMAIL (variable de entorno del
         servidor, no dato de la request) -> 'admin'.
      2. Si no, se consulta `profiles.role` en la base de datos con la
         service role key -> esa columna solo la escribe el backend
         (ver `_bootstrap_profile_and_membership` en routers/auth.py).

    IMPORTANTE -- por qué NO se usa `user_metadata` del JWT: Supabase Auth
    expone `PUT /auth/v1/user` (usado por el SDK como
    `supabase.auth.updateUser({ data: {...} })`), que permite a CUALQUIER
    usuario autenticado modificar su propio `user_metadata` con su propio
    access token, sin privilegios especiales. El JWT resultante es válido y
    está firmado correctamente por Supabase, pero el CONTENIDO de
    `user_metadata` lo eligió el usuario, no el servidor -- confiar en él
    para autorización permite que cualquier cliente se autoasigne el rol de
    administrador ejecutando `updateUser({ data: { role: "admin" } })` desde
    la consola del navegador. `profiles.role`, en cambio, vive en una tabla
    que solo el backend puede escribir (con la service role key, que nunca
    se expone al cliente) -- es la única fuente de verdad válida para el rol."""
    if email.lower() == settings.FOUNDER_ADMIN_EMAIL.lower():
        return "admin"

    from app.database import get_supabase_admin  # import diferido: evita ciclo de imports en el arranque

    try:
        profile = get_supabase_admin().table("profiles").select("role").eq("id", user_id).maybe_single().execute()
    except Exception:
        logger.exception("No se pudo resolver el rol de %s desde la base de datos; se usa 'client' por defecto", user_id)
        return "client"  # ante cualquier duda o fallo, el rol menos privilegiado

    if not profile or not profile.data:
        return "client"  # perfil aún no creado (primera request tras el registro): rol seguro por defecto
    return profile.data.get("role") or "client"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthUser:
    """Dependency de FastAPI: exige un JWT válido y devuelve el usuario actual,
    con el rol resuelto del lado del servidor (ver `_resolve_server_role`) --
    nunca a partir de datos que el navegador pueda enviar o modificar."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="No autenticado")

    payload = decode_supabase_jwt(credentials.credentials)
    user_id = payload.get("sub")
    email = payload.get("email", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido: falta el identificador del usuario.")

    role = _resolve_server_role(user_id, email)
    return AuthUser(user_id=user_id, email=email, role=role)
