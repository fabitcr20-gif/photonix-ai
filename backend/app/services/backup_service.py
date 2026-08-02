"""
Respaldo de la base de datos -- capa propia e independiente del plan de
Supabase (ver nota en config.py: el plan Free no trae backups automáticos).

Exporta cada tabla definida en sql/schema.sql a un archivo JSON comprimido
(vía el mismo cliente de Supabase que usa el resto del sistema -- no
requiere pg_dump ni una conexión Postgres directa) y lo guarda en el bucket
de Storage 'db-backups', separado de las tablas y buckets en vivo -- así un
borrado accidental, un bug o una migración mala no se lleva también el
respaldo. El esquema (columnas, constraints, índices) ya vive versionado en
sql/schema.sql; combinado con estos volcados de datos, alcanza para
reconstruir la base de datos completa si hiciera falta.

Los respaldos con más de DB_BACKUP_RETENTION_DAYS se borran solos en cada
corrida para no acumular espacio indefinidamente.
"""
from __future__ import annotations

import gzip
import json
import logging
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.database import get_supabase_admin
from app.services import storage_service

logger = logging.getLogger("photonix.backup")
settings = get_settings()

BACKUP_BUCKET = "db-backups"
_FILENAME_FORMAT = "%Y-%m-%dT%H-%M-%SZ"

# Todas las tablas de negocio definidas en sql/schema.sql -- si se agrega una
# tabla nueva ahí, hay que sumarla aquí también para que quede respaldada.
_TABLES = [
    "profiles",
    "memberships",
    "sinpe_payments",
    "projects",
    "project_photos",
    "watermarks",
    "google_drive_connections",
    "feedback",
    "support_tickets",
]


def _ensure_bucket_exists() -> None:
    """Crea el bucket de respaldos la primera vez que hace falta -- privado
    (no público como los buckets de fotos), idempotente. Solo aplica al
    proveedor Supabase: con 'local' storage_service ya crea carpetas solas,
    y con 's3' el bucket se asume pre-provisionado fuera de la app."""
    if settings.STORAGE_PROVIDER != "supabase":
        return
    try:
        get_supabase_admin().storage.create_bucket(BACKUP_BUCKET, options={"public": False})
    except Exception as exc:
        if "already exists" not in str(exc).lower() and "duplicate" not in str(exc).lower():
            raise


def run_daily_backup() -> dict:
    """Exporta todas las tablas a un único archivo JSON comprimido con
    timestamp y lo sube al bucket de respaldos. Devuelve metadata de la
    corrida (filas por tabla, tamaño, respaldos viejos borrados) para poder
    loguearlo o exponerlo en un endpoint de admin."""
    _ensure_bucket_exists()
    db = get_supabase_admin()

    dump: dict[str, list[dict]] = {}
    row_counts: dict[str, int] = {}
    for table in _TABLES:
        try:
            rows = db.table(table).select("*").execute().data
            dump[table] = rows
            row_counts[table] = len(rows)
        except Exception:
            logger.exception("No se pudo respaldar la tabla '%s' -- se omite de este backup.", table)

    payload = json.dumps(dump, default=str).encode("utf-8")
    compressed = gzip.compress(payload)

    filename = f"backup-{datetime.now(timezone.utc).strftime(_FILENAME_FORMAT)}.json.gz"
    provider = storage_service.get_provider()
    provider.save(f"{BACKUP_BUCKET}/{filename}", compressed, "application/gzip")

    pruned = _prune_old_backups(provider)

    logger.info(
        "Respaldo de base de datos completado: %s (%.1fKB, %d tablas, %d respaldos viejos borrados)",
        filename, len(compressed) / 1024, len(dump), pruned,
    )
    return {
        "filename": filename,
        "size_bytes": len(compressed),
        "tables": row_counts,
        "pruned_old_backups": pruned,
    }


def _prune_old_backups(provider) -> int:
    """Borra los respaldos con más de DB_BACKUP_RETENTION_DAYS, según la
    fecha embebida en el propio nombre de archivo -- más simple que depender
    de metadata del proveedor, y funciona igual en local/supabase/s3."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.DB_BACKUP_RETENTION_DAYS)
    deleted = 0
    for key in provider.list_keys(BACKUP_BUCKET):
        filename = key.rsplit("/", 1)[-1]
        try:
            file_date = datetime.strptime(
                filename.removeprefix("backup-").removesuffix(".json.gz"), _FILENAME_FORMAT
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if file_date < cutoff:
            provider.delete(key)
            deleted += 1
    return deleted


def list_backups() -> list[dict]:
    """Nombres de los respaldos disponibles, más reciente primero (el propio
    nombre ya trae el timestamp, así que ordenar alfabéticamente basta) --
    para listarlos en el panel de admin."""
    _ensure_bucket_exists()
    provider = storage_service.get_provider()
    filenames = [
        key.rsplit("/", 1)[-1]
        for key in provider.list_keys(BACKUP_BUCKET)
        if key.endswith(".json.gz")
    ]
    return [{"filename": name} for name in sorted(filenames, reverse=True)]


def read_backup(filename: str) -> bytes:
    """Bytes crudos (.json.gz) de un respaldo, para descargarlo."""
    return storage_service.get_provider().read(f"{BACKUP_BUCKET}/{filename}")
