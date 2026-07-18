"""
Watchdog de sesiones atascadas (Core Feature de confiabilidad).

BackgroundTasks de FastAPI (ver routers/ai_engine.py) vive solo en memoria
del proceso: si el servidor se reinicia o crashea a mitad de un lote, ese
trabajo simplemente desaparece y el proyecto queda en status='processing'
para siempre, sin que el cliente se entere ni pueda hacer nada al respecto
(no hay botón de reintento para un proyecto "processing", solo para uno en
"error" -- ver frontend/app/dashboard/upload/page.tsx).

Este módulo corre periódicamente (ver main.py) y detecta esos casos: si un
proyecto lleva más de `SESSION_STUCK_HOURS` en 'processing', se asume
abandonado y se marca 'error'. El cliente ve entonces el mensaje de error ya
existente y puede reintentar con un clic, en vez de esperar indefinidamente.

Ninguna foto se pierde con esto: las fotos ya persistidas en 'final-photos'
antes del crash siguen ahí (ver storage_service.py); lo único que cambia es
que el ESTADO del proyecto refleja la realidad en vez de quedar congelado.
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.database import get_supabase_admin

logger = logging.getLogger("photonix.watchdog")
settings = get_settings()


def recover_stuck_projects(stuck_after_hours: int | None = None) -> dict:
    """Marca 'error' cualquier proyecto en 'processing' que lleve más de
    `stuck_after_hours` sin terminar. Devuelve cuántos se detectaron y
    recuperaron, para poder loguearlo/exponerlo en un endpoint de admin."""
    hours = stuck_after_hours if stuck_after_hours is not None else settings.SESSION_STUCK_HOURS
    db = get_supabase_admin()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    stuck = (
        db.table("projects")
        .select("id, name, user_id, created_at, processed_count, total_count")
        .eq("status", "processing")
        .lt("created_at", cutoff)
        .execute()
    )

    recovered = []
    for project in stuck.data:
        try:
            db.table("projects").update({"status": "error"}).eq("id", project["id"]).execute()
            recovered.append(project["id"])
            logger.warning(
                "Proyecto atascado recuperado por el watchdog: %s (%s) -- llevaba más de %dh en "
                "'processing' (%d/%d fotos), probablemente por un reinicio/crash del servidor.",
                project["id"], project.get("name"), hours,
                project.get("processed_count") or 0, project.get("total_count") or 0,
            )
        except Exception:
            logger.exception("El watchdog no pudo actualizar el proyecto atascado %s", project["id"])

    return {"checked_cutoff_hours": hours, "stuck_found": len(stuck.data), "recovered": recovered}
