"""
Servicio de almacenamiento de archivos (fotos, comprobantes SINPE, logos de
marca de agua). Todo el resto del backend habla con este módulo únicamente
-- nunca con un proveedor concreto directamente -- para poder cambiar de
almacenamiento sin tocar ningún router ni el pipeline de IA.

Arquitectura (ver `StorageProvider` más abajo):
  - `local`    -> disco local. Solo para desarrollo: la mayoría de plataformas
                  de hosting (Railway, Render, Fly.io) NO conservan el disco
                  del contenedor entre despliegues -- usarlo en producción
                  significa perder las fotos de los clientes en el próximo
                  `git push`, salvo que se monte un volumen persistente.
  - `supabase` -> Supabase Storage. Ya es almacenamiento de objetos
                  persistente y sobrevive redespliegues del backend.
  - `s3`       -> cualquier almacenamiento que hable el protocolo S3: Amazon
                  S3, Cloudflare R2, MinIO, Backblaze B2, etc. Se selecciona
                  el proveedor real con S3_ENDPOINT_URL (vacío = AWS S3).

Todo `key` tiene la forma 'bucket/resto/de/la/ruta' (ej.
'raw-photos/{user_id}/{uuid}.jpg'), igual en los tres proveedores, así que
las URLs ya guardadas en la base de datos siguen siendo válidas si se migra
de un proveedor a otro (ver `key_from_url`).

Garantías que este módulo ofrece al resto del sistema:
  - Las fotos ORIGINALES (bucket 'raw-photos') nunca se sobrescriben: cada
    subida genera una clave nueva verificada como única (`_generate_key`).
  - Las fotos EDITADAS/finales (bucket 'final-photos') se guardan aparte de
    las originales, y se persisten en el proveedor configurado -- no solo en
    el disco efímero del servidor que las procesó (`persist_local_file`).
  - El pipeline de IA siempre trabaja sobre una ruta de disco real
    (OpenCV/Pillow lo exigen) sin importar el proveedor: `local_copy()`
    descarga a un archivo temporal si hace falta y lo borra automáticamente
    al terminar, incluso si el procesamiento falla a la mitad.
  - Toda operación de red (subir/bajar/borrar) reintenta con backoff corto
    ante fallos transitorios (`_with_retries`).
"""
from __future__ import annotations

import logging
import mimetypes
import os
import shutil
import tempfile
import time
import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager
from io import BytesIO
from typing import Iterator, Optional

from fastapi import UploadFile, HTTPException
from PIL import Image

from app.config import get_settings

logger = logging.getLogger("photonix.storage")
settings = get_settings()

# Formatos aceptados por tipo de subida -- se usan para validar tanto la
# extensión del nombre de archivo como (cuando Pillow puede decodificarlo)
# el contenido real, para que un archivo renombrado con otra extensión no
# pase como imagen válida.
ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".heic",
    ".dng", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2",
}
ALLOWED_RECEIPT_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_LOGO_EXTENSIONS = {".png"}
_RAW_CAMERA_EXTENSIONS = {".dng", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2"}

_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 1.5


def _with_retries(operation_name: str, fn, *args, **kwargs):
    """Reintenta una operación de red del proveedor de almacenamiento hasta
    _RETRY_ATTEMPTS veces con backoff corto -- un hiccup de red puntual no
    debe tumbar una subida/descarga completa."""
    last_exc: Optional[Exception] = None
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - cualquier fallo de red/proveedor es candidato a reintento
            last_exc = exc
            logger.warning(
                "Fallo en %s (intento %d/%d): %s", operation_name, attempt, _RETRY_ATTEMPTS, exc
            )
            if attempt < _RETRY_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF_SECONDS * attempt)
    assert last_exc is not None
    raise last_exc


# --------------------------------------------------------------------------
# Interfaz común de proveedor
# --------------------------------------------------------------------------


class StorageProvider(ABC):
    """Todo proveedor nuevo (Google Cloud Storage, Azure Blob Storage, ...)
    solo necesita implementar estos 6 métodos para conectarse al resto del
    sistema sin cambiar ningún router ni el pipeline de IA."""

    @abstractmethod
    def save(self, key: str, data: bytes, content_type: str) -> str:
        """Guarda `data` bajo `key` y devuelve la URL pública/canónica."""

    @abstractmethod
    def read(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """No debe lanzar si `key` ya no existe (idempotente: reintentar un
        borrado nunca debe ser un error)."""

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def list_keys(self, prefix: str) -> list[str]: ...

    @abstractmethod
    def url_for(self, key: str) -> str: ...

    @abstractmethod
    def key_from_url(self, url: str) -> Optional[str]:
        """Extrae `key` de una URL previamente devuelta por ESTE proveedor,
        o None si la URL no le pertenece (ej. quedó de un proveedor
        distinto tras una migración, o es una ruta de disco cruda)."""


# --------------------------------------------------------------------------
# Local (desarrollo)
# --------------------------------------------------------------------------


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: str, public_url_base: str):
        self.base_path = base_path
        self.public_url_base = public_url_base.rstrip("/")

    def path_for(self, key: str) -> str:
        return os.path.join(self.base_path, key)

    def save(self, key: str, data: bytes, content_type: str) -> str:
        dest = self.path_for(key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        # Escribe a un archivo temporal en el mismo directorio y renombra:
        # `os.replace` es atómico dentro de un mismo filesystem, así que un
        # crash a mitad de escritura nunca deja un archivo corrupto a medias
        # en la ruta final (protección contra sobrescrituras parciales).
        fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(dest))
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp_path, dest)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
        return self.url_for(key)

    def read(self, key: str) -> bytes:
        with open(self.path_for(key), "rb") as f:
            return f.read()

    def delete(self, key: str) -> None:
        try:
            os.remove(self.path_for(key))
        except FileNotFoundError:
            pass

    def exists(self, key: str) -> bool:
        return os.path.isfile(self.path_for(key))

    def list_keys(self, prefix: str) -> list[str]:
        prefix_dir = self.path_for(prefix)
        if not os.path.isdir(prefix_dir):
            return []
        return sorted(
            f"{prefix.rstrip('/')}/{name}"
            for name in os.listdir(prefix_dir)
            if os.path.isfile(os.path.join(prefix_dir, name))
        )

    def url_for(self, key: str) -> str:
        return f"{self.public_url_base}/media/{key}"

    def key_from_url(self, url: str) -> Optional[str]:
        prefix = f"{self.public_url_base}/media/"
        if url.startswith(prefix):
            return url[len(prefix):]
        return None


# --------------------------------------------------------------------------
# Supabase Storage
# --------------------------------------------------------------------------


class SupabaseStorageProvider(StorageProvider):
    """`key` = 'bucket/resto/de/la/ruta'; se separa el primer segmento como
    nombre de bucket real de Supabase Storage."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from app.database import get_supabase_admin

            self._client = get_supabase_admin()
        return self._client

    @staticmethod
    def _split(key: str) -> tuple[str, str]:
        bucket, _, rest = key.partition("/")
        return bucket, rest

    def save(self, key: str, data: bytes, content_type: str) -> str:
        bucket, path = self._split(key)

        def _upload():
            self._get_client().storage.from_(bucket).upload(
                path, data, {"content-type": content_type, "x-upsert": "true"}
            )

        _with_retries(f"supabase.upload({key})", _upload)
        return self.url_for(key)

    def read(self, key: str) -> bytes:
        bucket, path = self._split(key)
        return _with_retries(f"supabase.download({key})", self._get_client().storage.from_(bucket).download, path)

    def delete(self, key: str) -> None:
        bucket, path = self._split(key)
        try:
            _with_retries(f"supabase.remove({key})", self._get_client().storage.from_(bucket).remove, [path])
        except Exception:
            logger.warning("No se pudo borrar %s de Supabase Storage (puede que ya no existiera)", key, exc_info=True)

    def exists(self, key: str) -> bool:
        bucket, path = self._split(key)
        folder, _, filename = path.rpartition("/")
        try:
            listing = self._get_client().storage.from_(bucket).list(folder)
        except Exception:
            return False
        return any(item.get("name") == filename for item in (listing or []))

    def list_keys(self, prefix: str) -> list[str]:
        bucket, path = self._split(prefix)
        try:
            listing = self._get_client().storage.from_(bucket).list(path)
        except Exception:
            logger.warning("No se pudo listar %s en Supabase Storage", prefix, exc_info=True)
            return []
        return [f"{bucket}/{path.rstrip('/')}/{item['name']}" for item in (listing or []) if item.get("id")]

    def url_for(self, key: str) -> str:
        bucket, path = self._split(key)
        return self._get_client().storage.from_(bucket).get_public_url(path)

    def key_from_url(self, url: str) -> Optional[str]:
        marker = "/storage/v1/object/public/"
        idx = url.find(marker)
        if idx == -1:
            return None
        return url[idx + len(marker):]


# --------------------------------------------------------------------------
# S3 y compatibles (AWS S3, Cloudflare R2, MinIO, Backblaze B2, ...)
# --------------------------------------------------------------------------


class S3CompatibleStorageProvider(StorageProvider):
    """`key` se usa directamente como object key dentro de S3_BUCKET.
    `boto3` se importa de forma diferida para que el resto de la app no lo
    necesite instalado si nunca se usa este proveedor."""

    def __init__(self):
        import boto3
        from botocore.config import Config

        if not settings.S3_BUCKET:
            raise RuntimeError("STORAGE_PROVIDER='s3' requiere configurar S3_BUCKET en el entorno.")

        self._bucket = settings.S3_BUCKET
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            region_name=settings.S3_REGION or None,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
            # Los reintentos los maneja `_with_retries` de forma uniforme
            # para los 3 proveedores; se desactivan los propios de boto3
            # para no reintentar dos veces cada fallo.
            config=Config(retries={"max_attempts": 1}),
        )

    def save(self, key: str, data: bytes, content_type: str) -> str:
        _with_retries(
            f"s3.put_object({key})",
            self._client.put_object,
            Bucket=self._bucket, Key=key, Body=data, ContentType=content_type,
        )
        return self.url_for(key)

    def read(self, key: str) -> bytes:
        response = _with_retries(f"s3.get_object({key})", self._client.get_object, Bucket=self._bucket, Key=key)
        return response["Body"].read()

    def delete(self, key: str) -> None:
        try:
            _with_retries(f"s3.delete_object({key})", self._client.delete_object, Bucket=self._bucket, Key=key)
        except Exception:
            logger.warning("No se pudo borrar %s de S3 (puede que ya no existiera)", key, exc_info=True)

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    def list_keys(self, prefix: str) -> list[str]:
        keys: list[str] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            keys.extend(obj["Key"] for obj in page.get("Contents", []))
        return sorted(keys)

    def url_for(self, key: str) -> str:
        if settings.S3_PUBLIC_URL_BASE:
            return f"{settings.S3_PUBLIC_URL_BASE.rstrip('/')}/{key}"
        region_part = f".{settings.S3_REGION}" if settings.S3_REGION and settings.S3_REGION != "us-east-1" else ""
        return f"https://{self._bucket}.s3{region_part}.amazonaws.com/{key}"

    def key_from_url(self, url: str) -> Optional[str]:
        candidates = [settings.S3_PUBLIC_URL_BASE, f"https://{self._bucket}.s3.amazonaws.com"]
        for base in filter(None, candidates):
            prefix = base.rstrip("/") + "/"
            if url.startswith(prefix):
                return url[len(prefix):]
        return None


# --------------------------------------------------------------------------
# Selección del proveedor activo
# --------------------------------------------------------------------------

_provider: Optional[StorageProvider] = None


def get_provider() -> StorageProvider:
    global _provider
    if _provider is not None:
        return _provider
    if settings.STORAGE_PROVIDER == "s3":
        _provider = S3CompatibleStorageProvider()
    elif settings.STORAGE_PROVIDER == "supabase":
        _provider = SupabaseStorageProvider()
    else:
        _provider = LocalStorageProvider(settings.LOCAL_STORAGE_PATH, settings.BACKEND_PUBLIC_URL)
    return _provider


# --------------------------------------------------------------------------
# Validación de subidas
# --------------------------------------------------------------------------


def _validate_extension(filename: str, allowed: set[str]) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado ({ext or 'sin extensión'}). Formatos permitidos: {', '.join(sorted(allowed))}",
        )
    return ext


def _validate_is_real_image(data: bytes, filename: str) -> None:
    """Verifica que el contenido sea realmente una imagen válida, no solo
    que el nombre/content-type lo aparente -- evita que un archivo
    ejecutable/script disfrazado con extensión de imagen llegue a guardarse."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in _RAW_CAMERA_EXTENSIONS:
        return  # Pillow no decodifica RAW de cámara; se confía en extensión + tamaño.
    try:
        Image.open(BytesIO(data)).verify()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="El archivo no es una imagen válida.") from exc


def _generate_key(bucket: str, path_prefix: str, filename: str, provider: StorageProvider) -> str:
    """Genera una clave nueva y verificada como única -- protección real
    contra sobrescrituras, no solo "improbable colisión de UUID"."""
    ext = os.path.splitext(filename)[1].lower()
    for _ in range(5):
        candidate = f"{uuid.uuid4().hex}{ext}"
        key = f"{bucket}/{path_prefix}/{candidate}" if path_prefix else f"{bucket}/{candidate}"
        if not provider.exists(key):
            return key
    # Cinco colisiones seguidas de UUID son, en la práctica, imposibles; si
    # de verdad ocurre, es síntoma de un bug real (ej. `exists` roto), no
    # mala suerte -- mejor fallar fuerte que arriesgar una sobrescritura.
    raise HTTPException(status_code=500, detail="No se pudo generar una ruta de almacenamiento única.")


# --------------------------------------------------------------------------
# API pública (lo que usan los routers/servicios)
# --------------------------------------------------------------------------


async def upload_file(
    file: UploadFile,
    bucket: str,
    path_prefix: str = "",
    allowed_extensions: Optional[set[str]] = None,
) -> str:
    """Sube un archivo NUEVO (genera una clave única, nunca sobrescribe algo
    existente) al proveedor configurado. Valida extensión, contenido real y
    tamaño máximo antes de guardar nada."""
    allowed = allowed_extensions or ALLOWED_IMAGE_EXTENSIONS
    filename = file.filename or "upload"
    _validate_extension(filename, allowed)

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"Archivo demasiado grande ({size_mb:.1f}MB). Máximo permitido: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )
    _validate_is_real_image(contents, filename)

    provider = get_provider()
    key = _generate_key(bucket, path_prefix, filename, provider)
    content_type = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    url = _with_retries(f"upload({key})", provider.save, key, contents, content_type)
    logger.info("Archivo guardado: %s (%.2fMB, proveedor=%s)", key, size_mb, settings.STORAGE_PROVIDER)
    return url


async def upload_many(
    files: list[UploadFile],
    bucket: str,
    path_prefix: str = "",
    allowed_extensions: Optional[set[str]] = None,
) -> list[str]:
    """Sube múltiples archivos (carga masiva) y devuelve sus URLs."""
    urls = []
    for file in files:
        urls.append(await upload_file(file, bucket, path_prefix, allowed_extensions))
    return urls


@contextmanager
def local_copy(location: str) -> Iterator[Optional[str]]:
    """Da acceso a `location` como una ruta de archivo real en disco, sin
    importar el proveedor -- OpenCV/Pillow exigen rutas de archivo reales,
    nunca URLs. Con el proveedor local es la ruta directa (sin copia). Con
    un proveedor remoto, descarga a un archivo temporal que se borra
    automáticamente al salir del bloque `with`, incluso si el procesamiento
    lanza una excepción a la mitad -- el disco nunca acumula copias
    temporales huérfanas. Da `None` si `location` no se pudo resolver."""
    provider = get_provider()
    key = provider.key_from_url(location)

    if key is None:
        # No es una URL de este proveedor (ruta de disco heredada, o quedó
        # de un proveedor anterior tras una migración): se usa tal cual si
        # es una ruta real, o se declara irresoluble.
        yield location if os.path.isfile(location) else None
        return

    if isinstance(provider, LocalStorageProvider):
        path = provider.path_for(key)
        yield path if os.path.isfile(path) else None
        return

    try:
        data = _with_retries(f"read({key})", provider.read, key)
    except Exception:
        logger.exception("No se pudo descargar %s (clave %s) para procesarla", location, key)
        yield None
        return

    # Importante: se conserva el nombre de archivo ORIGINAL (no uno aleatorio
    # de tempfile) dentro de un directorio temporal propio. El resto del
    # pipeline (batch_processor.py, _apply_watermark_if_configured, etc.)
    # deriva el nombre de salida de `os.path.basename(input_path)` -- si aquí
    # se generara un nombre al azar, el archivo editado/final quedaría con
    # un nombre que ya no coincide con el de la foto original y se rompería
    # el emparejamiento antes/después.
    tmp_dir = tempfile.mkdtemp(prefix="photonix-dl-")
    tmp_path = os.path.join(tmp_dir, os.path.basename(key))
    try:
        with open(tmp_path, "wb") as f:
            f.write(data)
        # Libera los bytes descargados apenas quedan en disco. Sin esto, cada
        # `local_copy` suspendida (ver _run_batch_job: se abren todas las del
        # lote de una vez con ExitStack, antes de procesar la primera) retiene
        # su copia completa en memoria durante TODO el lote -- con lotes de
        # decenas de fotos eso se suma al de por sí ajustado presupuesto de
        # memoria de un host pequeño (ver AI_MAX_WORKERS en config.py).
        del data
        yield tmp_path
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def persist_local_file(local_path: str, bucket: str, path_prefix: str, filename: str) -> str:
    """Sube un archivo que el pipeline de procesamiento acaba de escribir en
    disco (scratch local, siempre necesario para OpenCV/Pillow) al proveedor
    de almacenamiento configurado. Con el proveedor local, mueve el archivo
    dentro de su propia carpeta de medios (comportamiento de siempre). Con
    un proveedor remoto, sube los bytes y borra la copia local -- el disco
    del servidor que procesó la foto nunca es la única copia que sobrevive
    a un reinicio o redespliegue. Sobrescribe intencionalmente si `key` ya
    existe (uso esperado: una re-edición actualiza el mismo archivo final)."""
    provider = get_provider()
    key = f"{bucket}/{path_prefix}/{filename}" if path_prefix else f"{bucket}/{filename}"

    if isinstance(provider, LocalStorageProvider):
        dest = provider.path_for(key)
        if os.path.abspath(local_path) != os.path.abspath(dest):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(local_path, dest)
        return provider.url_for(key)

    with open(local_path, "rb") as f:
        data = f.read()
    content_type = mimetypes.guess_type(filename)[0] or "image/jpeg"
    url = _with_retries(f"upload({key})", provider.save, key, data, content_type)
    os.unlink(local_path)
    return url


def read_file_bytes(location: str) -> bytes:
    """Lee los bytes de un archivo ya subido, sin importar el proveedor."""
    provider = get_provider()
    key = provider.key_from_url(location)
    if key is not None:
        return _with_retries(f"read({key})", provider.read, key)
    if os.path.isfile(location):
        with open(location, "rb") as f:
            return f.read()
    import httpx

    response = httpx.get(location, timeout=30)
    response.raise_for_status()
    return response.content


def file_exists(bucket: str, path_prefix: str, filename: str) -> bool:
    provider = get_provider()
    key = f"{bucket}/{path_prefix}/{filename}" if path_prefix else f"{bucket}/{filename}"
    return provider.exists(key)


def file_url(bucket: str, path_prefix: str, filename: str) -> str:
    provider = get_provider()
    key = f"{bucket}/{path_prefix}/{filename}" if path_prefix else f"{bucket}/{filename}"
    return provider.url_for(key)


def read_file(bucket: str, path_prefix: str, filename: str) -> bytes:
    provider = get_provider()
    key = f"{bucket}/{path_prefix}/{filename}" if path_prefix else f"{bucket}/{filename}"
    return _with_retries(f"read({key})", provider.read, key)


def list_files(bucket: str, path_prefix: str) -> list[str]:
    """Nombres de archivo (sin ruta) bajo bucket/path_prefix."""
    provider = get_provider()
    prefix = f"{bucket}/{path_prefix}" if path_prefix else bucket
    return [key.rsplit("/", 1)[-1] for key in provider.list_keys(prefix)]


def delete_file(location: str) -> None:
    provider = get_provider()
    key = provider.key_from_url(location)
    if key is not None:
        provider.delete(key)


def delete_prefix(bucket: str, path_prefix: str) -> None:
    """Borra todos los archivos bajo bucket/path_prefix (ej. al eliminar una
    sesión completa) en el proveedor configurado. Con el proveedor local
    también elimina la carpeta contenedora, ya vacía."""
    provider = get_provider()
    prefix = f"{bucket}/{path_prefix}" if path_prefix else bucket
    for key in provider.list_keys(prefix):
        provider.delete(key)
    if isinstance(provider, LocalStorageProvider):
        shutil.rmtree(provider.path_for(prefix), ignore_errors=True)


