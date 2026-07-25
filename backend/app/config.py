"""
Configuración central de Photonix AI Backend.
Carga variables de entorno (.env) usando Pydantic Settings.
Todas las claves sensibles (Supabase, JWT, storage) viven SOLO en el .env,
nunca hardcodeadas en el código.
"""
from functools import lru_cache
from pydantic import model_validator
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
    # host, no contra sus núcleos de CPU. Con fotos reales de cámara/celular
    # (20-50MP), incluso 2 workers concurrentes pueden sumar varios cientos de
    # MB solo en buffers de imagen y tumbar un contenedor de 1GB (confirmado
    # en logs de producción: "Killed" del kernel a mitad de lote). batch_processor.py
    # ya libera esa memoria entre foto y foto (ver memory_utils.release_freed_memory), pero
    # el pico de UNA foto sola (~250-400MB medido en producción con fotos de
    # ~12MP; más con fotos más grandes) sigue dejando poco margen para correr
    # 2 a la vez sin arriesgar un OOM en un host de 1GB. 1 procesa una foto a
    # la vez -- ya no es el cuello de botella de velocidad que era antes de
    # liberar memoria entre fotos (16 fotos reales: ~1 min medido en
    # producción). Súbelo solo si el host tiene bastante más RAM disponible.
    AI_MAX_WORKERS: int = 1

    # Cuántas SESIONES (lotes) de distintos usuarios pueden procesarse al
    # mismo tiempo en este proceso -- ver ai_engine.py, _BATCH_EXECUTOR. La
    # misma razón de memoria de arriba (AI_MAX_WORKERS) aplica a nivel de
    # lote: cada sesión activa tiene su propio pico real de RAM por foto, y
    # correr 2 lotes de 2 usuarios distintos a la vez suma esos picos igual
    # que correr 2 fotos del mismo lote a la vez. La diferencia con el
    # comportamiento anterior: antes, un segundo usuario que intentaba
    # procesar mientras otro lote corría recibía un error 409 inmediato
    # ("Ya hay una edición en curso") y tenía que reintentar manualmente --
    # en un SaaS con más de un cliente pagando esto rompía el producto con
    # solo 2 usuarios activos a la vez, no con miles. Ahora su sesión se
    # ENCOLA de verdad (FIFO, sin límite de cuántas sesiones pueden esperar
    # su turno) y arranca automáticamente en cuanto hay un cupo libre, sin
    # que el usuario tenga que hacer nada. Sube este número solo si el host
    # tiene RAM de sobra para sostener varios lotes reales a la vez.
    AI_MAX_CONCURRENT_BATCHES: int = 1

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Secretos que tienen un valor placeholder por defecto arriba -- SOLO
    # para que el backend arranque en desarrollo sin exigir un .env
    # completo desde el primer minuto. En producción, un placeholder sin
    # reemplazar significa que Railway (o quien despliegue) se olvidó de
    # configurar la variable real -- y hoy la app arrancaba "exitosamente"
    # igual, respondiendo 500 en silencio en cada llamada a Supabase/JWT en
    # vez de fallar fuerte con un mensaje claro sobre CUÁL variable falta.
    # Para un SaaS que va a cobrar suscripciones, "arrancó bien" debe
    # significar "los secretos reales están puestos", no solo "el proceso
    # no crasheó".
    @model_validator(mode="after")
    def _reject_placeholder_secrets_in_production(self) -> "Settings":
        if self.APP_ENV != "production":
            return self
        placeholder_fields = {
            "SUPABASE_URL": "https://your-project.supabase.co",
            "SUPABASE_ANON_KEY": "changeme",
            "SUPABASE_SERVICE_ROLE_KEY": "changeme",
            "SUPABASE_JWT_SECRET": "changeme",
            "APP_SECRET_KEY": "changeme-genera-un-secreto-aleatorio-largo",
        }
        still_placeholder = [
            name for name, placeholder in placeholder_fields.items() if getattr(self, name) == placeholder
        ]
        if still_placeholder:
            raise ValueError(
                "APP_ENV=production pero estas variables de entorno todavía tienen su "
                f"valor placeholder de desarrollo, sin configurar de verdad: {', '.join(still_placeholder)}. "
                "Configúralas en el entorno de despliegue (ej. variables de Railway) antes de arrancar."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Cachea la instancia de configuración para no releer el .env en cada request."""
    return Settings()
