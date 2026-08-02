"""
Punto de entrada de la API de Photonix AI (FastAPI).
Registra todos los routers del sistema: autenticación, usuarios, pagos,
panel admin, carga de archivos, motor de IA y marca de agua.
"""
import os
from contextlib import asynccontextmanager

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.core.security_headers import SecurityHeadersMiddleware
from app.database import get_supabase_admin
from app.routers import auth, users, payments, admin, uploads, ai_engine, watermark, export, support, feedback

logger = logging.getLogger("photonix.health")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Al arrancar, programa las tareas periódicas activas:
      - Si ENABLE_REMINDER_SCHEDULER=true, el envío diario de recordatorios de
        pago (ver services/reminder_service.py).
      - Si ENABLE_SESSION_WATCHDOG=true (por defecto), la detección de
        sesiones atascadas en 'processing' por un reinicio/crash del servidor
        (ver services/session_watchdog.py) -- corre cada
        SESSION_WATCHDOG_INTERVAL_MINUTES.
      - Si ENABLE_DB_BACKUP_SCHEDULER=true (por defecto), el respaldo diario
        de la base de datos (ver services/backup_service.py).
    apscheduler solo se importa si al menos una está activa, para no
    exigirla en instalaciones que no usan ninguna tarea automática."""
    scheduler = None
    if settings.ENABLE_REMINDER_SCHEDULER or settings.ENABLE_SESSION_WATCHDOG or settings.ENABLE_DB_BACKUP_SCHEDULER:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler(timezone="UTC")

        if settings.ENABLE_REMINDER_SCHEDULER:
            from app.services import reminder_service

            # 13:00 UTC ≈ 7:00 a.m. Costa Rica (UTC-6).
            scheduler.add_job(reminder_service.send_bulk_reminders, "cron", hour=13, minute=0)

        if settings.ENABLE_SESSION_WATCHDOG:
            from app.services import session_watchdog

            scheduler.add_job(
                session_watchdog.recover_stuck_projects,
                "interval",
                minutes=settings.SESSION_WATCHDOG_INTERVAL_MINUTES,
            )

        if settings.ENABLE_DB_BACKUP_SCHEDULER:
            from app.services import backup_service

            # 9:00 UTC ≈ 3:00 a.m. Costa Rica (UTC-6) -- fuera de horas pico.
            scheduler.add_job(backup_service.run_daily_backup, "cron", hour=9, minute=0)

        scheduler.start()

    yield

    if scheduler:
        scheduler.shutdown()


# En producción, Swagger UI (/docs), ReDoc (/redoc) y el esquema crudo
# (/openapi.json) quedan deshabilitados: exponen el mapa completo de la API
# -- incluidas las rutas de administrador y pagos -- a cualquiera que lo
# visite. En development quedan disponibles para trabajar cómodo.
_is_production = settings.APP_ENV == "production"

app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="API backend de Photonix AI — edición fotográfica automatizada con IA para fotógrafos profesionales.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# --- CORS: permite que el frontend (Next.js) consuma la API ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- Cabeceras de seguridad estándar en toda respuesta ---
app.add_middleware(SecurityHeadersMiddleware)

# --- Registro de routers, todos bajo el prefijo /api/v1 ---
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(payments.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(uploads.router, prefix=settings.API_V1_PREFIX)
app.include_router(ai_engine.router, prefix=settings.API_V1_PREFIX)
app.include_router(watermark.router, prefix=settings.API_V1_PREFIX)
app.include_router(export.router, prefix=settings.API_V1_PREFIX)
app.include_router(support.router, prefix=settings.API_V1_PREFIX)
app.include_router(feedback.router, prefix=settings.API_V1_PREFIX)

# --- Archivos estáticos: sirve por HTTP lo guardado con STORAGE_PROVIDER='local'
# (fotos, logos de marca de agua) para que el navegador pueda mostrarlas. Con
# STORAGE_PROVIDER='supabase' esto no se usa (las URLs ya son de Supabase Storage).
os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.LOCAL_STORAGE_PATH), name="media")


@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "status": "online", "docs": app.docs_url}


@app.get("/health")
async def health_check():
    """Antes devolvía {"status": "ok"} sin condición alguna -- si Supabase
    estaba caído, Railway (o cualquier orquestador leyendo este endpoint)
    seguía viendo la app como saludable, sin alertar ni intentar recuperarla.
    Ahora hace una consulta real y barata (una fila por id, sobre una tabla
    ya indexada por primary key) para confirmar que la app puede hablar de
    verdad con la base de datos, no solo que el proceso sigue vivo."""
    try:
        get_supabase_admin().table("profiles").select("id").limit(1).execute()
        return {"status": "ok", "database": "ok"}
    except Exception:
        logger.exception("Health check: Supabase no respondió correctamente")
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "unreachable"},
        )
