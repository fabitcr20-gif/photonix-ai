"""
Protecciones contra abuso/bots (Core Feature de ciberseguridad), sin depender
de servicios externos (sin CAPTCHA todavía -- requeriría una cuenta de
hCaptcha/Cloudflare Turnstile que el proyecto no tiene configurada).

Incluye:
  - `rate_limiter(max_requests, window_seconds)`: dependency-factory (mismo
    patrón que `require_feature` en `dependencies.py`) que limita cuántas
    veces una misma IP puede golpear una ruta en una ventana de tiempo.
  - `reject_missing_user_agent`: rechaza requests a rutas sensibles que no
    mandan un `User-Agent` -- los navegadores reales siempre lo mandan; los
    bots/scripts simples muchas veces no.

El contador vive en un diccionario en memoria del proceso: sirve perfecto
para un solo worker (como este despliegue), pero NO se comparte entre
procesos. Si en producción se corre con varios workers de uvicorn/gunicorn,
hace falta un store compartido (ej. Redis) para que el límite sea real entre
todos los procesos -- el mismo tipo de nota que ya existe en ai_engine.py
sobre BackgroundTasks vs. Celery/RQ.
"""
from __future__ import annotations
import logging
import time
from collections import defaultdict
from threading import Lock
from fastapi import HTTPException, Request, status
from app.config import get_settings

logger = logging.getLogger("photonix.security")

_buckets: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def _client_ip(request: Request) -> str:
    # Respeta X-Forwarded-For si hay un proxy/balanceador delante (ej. en
    # producción detrás de un load balancer); si no, usa la IP directa.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limiter(max_requests: int, window_seconds: int):
    """Factory de dependency de FastAPI: como máximo `max_requests` peticiones
    por IP cada `window_seconds` segundos a la ruta donde se use."""

    async def _dependency(request: Request) -> None:
        if not get_settings().RATE_LIMIT_ENABLED:
            return
        ip = _client_ip(request)
        key = f"{request.url.path}:{ip}"
        now = time.monotonic()

        with _lock:
            hits = _buckets[key]
            cutoff = now - window_seconds
            while hits and hits[0] < cutoff:
                hits.pop(0)

            if len(hits) >= max_requests:
                retry_after = max(1, int(window_seconds - (now - hits[0])))
                logger.warning("Rate limit excedido: %s (%d hits en %ds)", key, len(hits), window_seconds)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Demasiadas solicitudes. Intenta de nuevo en unos momentos.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    return _dependency


async def reject_missing_user_agent(request: Request) -> None:
    """Rechaza con 400 si falta el header User-Agent -- heurística simple
    para descartar bots/scripts básicos en rutas sensibles/costosas."""
    if not request.headers.get("user-agent"):
        logger.warning("Request sin User-Agent bloqueada: %s %s", request.method, request.url.path)
        raise HTTPException(status_code=400, detail="Solicitud inválida.")
