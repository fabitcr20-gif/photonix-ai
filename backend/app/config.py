"""
Configuración central de Photonix AI Backend.
Carga variables de entorno (.env) usando Pydantic Settings.
Todas las claves sensibles (Supabase, JWT, storage) viven SOLO en el .env,
nunca hardcodeadas en el código.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Info general de la app ---
    APP_NAME: str = "Photonix AI"
    APP_ENV: str = "development"  # development | production
    API_V1_PREFIX: str = "/api/v1"

    # --- Supabase (Auth + DB + Storage) ---
    SUPABASE_URL: str = "https://your-project.supabase.co"
    SUPABASE_ANON_KEY: str = "changeme"
    SUPABASE_SERVICE_ROLE_KEY: str = "changeme"  # Solo backend, nunca exponer al frontend
    SUPABASE_JWT_SECRET: str = "changeme"

    # --- Cuenta del fundador/administrador (acceso gratuito e ilimitado de por vida) ---
    FOUNDER_ADMIN_EMAIL: str = "fabitcr20@gmail.com"

    # --- Planes de monetización (Costa Rica, colones CRC) ---
    TRIAL_DAYS: int = 30
    PLAN_STARTER_PRICE_CRC: int = 3500
    PLAN_PRO_PRICE_CRC: int = 7000
    PLAN_STUDIO_PRICE_CRC: int = 12000
    MEMBERSHIP_DURATION_DAYS: int = 30  # Duración al aprobar un comprobante SINPE

    # --- SINPE Móvil (datos que se muestran al cliente para pagar) ---
    SINPE_PHONE_NUMBER: str = "8888-8888"
    SINPE_OWNER_NAME: str = "Photonix AI"
    SINPE_APPROVAL_SLA_TEXT: str = "Aprobamos tu comprobante en menos de 24 horas hábiles."

    # --- Correo (recordatorios automáticos de pago) ---
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "Photonix AI <no-reply@photonix.ai>"
    REMINDER_DAYS_BEFORE_EXPIRY: int = 3  # avisa desde N días antes del vencimiento
    ENABLE_REMINDER_SCHEDULER: bool = False  # activa el envío diario automático

    # --- Watchdog de sesiones atascadas ---
    # BackgroundTasks (ver ai_engine.py) no sobrevive un reinicio/crash del
    # servidor a mitad de un lote: sin esto, un proyecto quedaría en
    # status='processing' para siempre. Este watchdog corre periódicamente y
    # marca 'error' cualquier proyecto que lleve más de SESSION_STUCK_HOURS
    # en 'processing' -- así el cliente ve un error claro y puede reintentar
    # desde la misma pantalla (ya existe esa UI), en vez de esperar
    # indefinidamente sin saber qué pasó.
    ENABLE_SESSION_WATCHDOG: bool = True
    SESSION_WATCHDOG_INTERVAL_MINUTES: int = 15
    SESSION_STUCK_HOURS: int = 3

    # --- Integraciones de exportación (opcionales) ---
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_REDIRECT_URI: str = "http://localhost:8000/api/v1/export/google-drive/callback"
    # A dónde redirigir al navegador tras conectar Google Drive con éxito.
    FRONTEND_URL: str = "http://localhost:3000"
    INSTAGRAM_ACCESS_TOKEN: str = ""

    # --- Firma de tokens internos (ej. el "state" del OAuth de Google Drive) ---
    # Distinto de SUPABASE_JWT_SECRET: este es solo nuestro, no de Supabase.
    APP_SECRET_KEY: str = "changeme-genera-un-secreto-aleatorio-largo"

    # --- Almacenamiento de archivos (uploads de fotos y comprobantes) ---
    STORAGE_PROVIDER: str = "supabase"  # local | supabase | s3
    LOCAL_STORAGE_PATH: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 100
    # URL pública del backend: con STORAGE_PROVIDER='local' se usa para armar
    # URLs http accesibles desde el navegador hacia /media (ver main.py).
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"

    # --- S3 y compatibles (Amazon S3, Cloudflare R2, MinIO, Backblaze B2...) ---
    # Solo se usan si STORAGE_PROVIDER == "s3". S3_ENDPOINT_URL vacío = AWS S3
    # real; para R2/MinIO/etc, la URL de endpoint que da ese proveedor.
    S3_BUCKET: str = ""
    S3_REGION: str = ""
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_PUBLIC_URL_BASE: str = ""  # dominio propio/CDN delante del bucket, si existe

    # --- CORS ---
    FRONTEND_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- Seguridad ---
    RATE_LIMIT_ENABLED: bool = True

    # --- Motor de IA ---
    # Fotos procesadas en paralelo por lote. Cada una mantiene varias copias
    # completas en memoria durante el pipeline (ajustes, limpieza, remoción de
    # objetos), así que este número debe calibrarse contra la RAM real del
    # host, no contra sus núcleos de CPU. En un contenedor con poca memoria
    # (ej. el plan trial de Railway, 1GB) un valor alto revienta el proceso
    # (OOM kill) a mitad de un lote grande. 2 es un valor conservador seguro
    # para ~1GB; súbelo si el host tiene más memoria disponible.
    AI_MAX_WORKERS: int = 2

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Cachea la instancia de configuración para no releer el .env en cada request."""
    return Settings()
