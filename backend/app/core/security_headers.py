"""Middleware que agrega cabeceras HTTP de seguridad estándar a toda respuesta."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # HSTS solo tiene sentido con HTTPS real (producción); en development
        # (http://localhost) el navegador la ignora igual, pero no hace daño.
        if get_settings().APP_ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
