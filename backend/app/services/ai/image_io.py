"""
Lector universal de imágenes: envoltorio sobre `cv2.imread` que además sabe
decodificar RAW de cámara (vía rawpy) y HEIC/HEIF (vía pillow-heif) --
formatos que `storage_service.py` acepta en la subida (ver
ALLOWED_IMAGE_EXTENSIONS, incluye .heic/.dng/.cr2/.cr3/.nef/.arw/.raf/.orf/
.rw2) pero que OpenCV, incluso en su build headless completo, NO puede
decodificar por sí solo.

Sin este módulo, cualquier foto RAW o HEIC subida se "aceptaba" en la carga
(la validación de storage_service.py confía en la extensión para RAW, y
HEIC pasaba la verificación de Pillow) y fallaba en silencio recién al
procesarla con `cv2.imread` -- el escenario más común precisamente para el
público objetivo de Photonix AI (fotógrafos que disparan en RAW, o
cualquiera con iPhone subiendo su carrete tal cual, que por defecto es
HEIC).

Se usa como reemplazo directo de `cv2.imread(path)` en cualquier lugar del
pipeline que lea una foto de usuario desde disco -- misma firma, mismo
contrato (BGR uint8, o None si no se pudo leer)."""
from __future__ import annotations
import logging
import multiprocessing as mp
import os
import tempfile
import numpy as np
import cv2

logger = logging.getLogger("photonix.image_io")

_RAW_EXTENSIONS = {".dng", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2"}
_HEIC_EXTENSIONS = {".heic", ".heif"}

# Registrado a nivel de módulo (no perezoso/por-llamada): así CUALQUIER
# `PIL.Image.open()` en el resto del backend gana soporte de HEIC de forma
# transparente en cuanto algo importa este módulo -- en particular
# `storage_service._validate_is_real_image` (la validación de subida, que
# de otra forma rechazaría un HEIC real con "El archivo no es una imagen
# válida" antes de que llegara siquiera a procesarse) y la lectura de EXIF
# en `environment_analysis._read_exif`. Registrar el opener es idempotente
# y barato -- no hay costo por hacerlo una sola vez al importar.
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    logger.error("pillow-heif no está instalado; las fotos HEIC no se podrán leer.")


def read_image_bgr(path: str) -> "np.ndarray | None":
    """Devuelve la imagen decodificada como array BGR uint8 (mismo formato
    que `cv2.imread`), o `None` si no se pudo leer -- igual contrato que
    `cv2.imread`, para que el código que ya revisa `if image is None:` siga
    funcionando sin cambios en ningún llamador."""
    ext = "." + path.lower().rsplit(".", 1)[-1] if "." in path else ""

    if ext in _RAW_EXTENSIONS:
        return _read_raw(path)
    if ext in _HEIC_EXTENSIONS:
        return _read_heic(path)

    # NOTA sobre orientación EXIF: se investigó agregar aquí una corrección
    # manual (rotar/reflejar según la etiqueta EXIF Orientation), asumiendo
    # que cv2.imread la ignora como versiones antiguas de OpenCV. Se verificó
    # ANTES de dejarla enviada -- con la versión pineada en requirements.txt
    # (opencv-python-headless==4.10.0.84), cv2.imread YA aplica la corrección
    # de orientación EXIF automáticamente por defecto (confirmado comparando
    # contra cv2.IMREAD_IGNORE_ORIENTATION con un archivo de prueba real:
    # el resultado por defecto sale correctamente rotado, la bandera de
    # "ignorar" es la que da el raster crudo sin rotar). Agregar una
    # corrección propia aquí habría rotado la imagen DOS veces -- un bug real
    # que se detectó en pruebas antes de llegar a producción.
    return cv2.imread(path)



# rawpy envuelve LibRaw, una librería en C que parsea un formato binario
# complejo con historial real de CVEs por corrupción de memoria ante
# archivos malformados (ver ej. CVE-2020-35540 y similares). Un
# `try/except Exception` en Python NO puede atrapar un segfault nativo o un
# bucle infinito dentro de esa librería -- si eso pasara corriendo en el
# mismo proceso que uvicorn, un solo archivo RAW malicioso subido por
# CUALQUIER usuario (incluso en prueba gratuita) tumbaría el servidor
# completo, afectando a todos los usuarios a la vez, no solo a esa sesión.
# Por eso la decodificación corre en un PROCESO HIJO separado y desechable:
# si revienta o se cuelga, muere solo ese proceso -- el servidor principal
# ni se entera, más allá del timeout de abajo.
_RAW_DECODE_TIMEOUT_SECONDS = 20.0  # un RAW real tarda 1-3s; margen amplio antes de darlo por colgado


def _raw_decode_worker(path: str, output_npy_path: str) -> None:
    """Cuerpo del proceso hijo -- ver _read_raw. Escribe el resultado a un
    archivo temporal en vez de mandarlo de vuelta por una Queue/Pipe: para
    un array RGB de una foto real (decenas de MB), evita la complejidad y el
    riesgo de condición de carrera de serializar un objeto grande a través
    de multiprocessing.Queue justo antes de que el proceso termine (un
    gotcha documentado de esa API) -- un archivo en disco es simple y
    confiable."""
    import rawpy

    with rawpy.imread(path) as raw:
        # use_camera_wb: respeta el balance de blancos que la cámara ya
        # calculó (el fotógrafo lo vio así en el visor/LCD) en vez de forzar
        # una estimación automática distinta -- el resto del pipeline de
        # Photonix ya hace su propio ajuste de temperatura después, sobre
        # esta base. output_bps=8: el resto del pipeline trabaja en uint8
        # (OpenCV/BGR de 8 bits), no tiene sentido decodificar a 16 bits
        # para descartarlo enseguida.
        rgb = raw.postprocess(use_camera_wb=True, output_bps=8)
    np.save(output_npy_path, rgb)


def _read_raw(path: str) -> "np.ndarray | None":
    # 'spawn' explícito (no 'fork'): el proceso hijo arranca limpio, sin
    # heredar el estado de hilos/locks ya abiertos en el proceso de uvicorn
    # (heredar eso con 'fork' en un proceso multi-hilo es un problema
    # conocido y una fuente real de cuelgues sutiles) -- el costo extra de
    # arranque (cientos de ms) es insignificante frente a los 1-3s que ya
    # tarda decodificar un RAW real.
    ctx = mp.get_context("spawn")
    with tempfile.TemporaryDirectory(prefix="photonix-raw-") as tmp_dir:
        output_path = os.path.join(tmp_dir, "decoded.npy")
        process = ctx.Process(target=_raw_decode_worker, args=(path, output_path), daemon=True)
        process.start()
        process.join(timeout=_RAW_DECODE_TIMEOUT_SECONDS)

        if process.is_alive():
            logger.error(
                "Decodificación RAW colgada (>%.0fs) -- se mata el subproceso sin afectar al resto de la app: %s",
                _RAW_DECODE_TIMEOUT_SECONDS, path,
            )
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join()
            return None

        if process.exitcode != 0:
            # Cubre tanto un crash nativo real (exitcode negativo = murió por
            # una señal, ej. -11 = SIGSEGV) como cualquier excepción de
            # Python sin atrapar dentro del subproceso (exitcode 1) -- en
            # ambos casos el resultado es el mismo desde afuera: no hay
            # archivo de salida confiable, se trata como fallo de lectura.
            logger.error(
                "El subproceso de decodificación RAW terminó de forma anormal (código %s) -- "
                "aislado del proceso principal, no afectó a otros usuarios: %s",
                process.exitcode, path,
            )
            return None

        if not os.path.isfile(output_path):
            logger.error("El subproceso de RAW terminó sin error pero no generó resultado: %s", path)
            return None

        rgb = np.load(output_path)

    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _read_heic(path: str) -> "np.ndarray | None":
    try:
        from PIL import Image
    except ImportError:
        logger.error("Pillow no está disponible; no se puede decodificar el HEIC: %s", path)
        return None
    try:
        with Image.open(path) as img:
            rgb = np.array(img.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except Exception:
        logger.exception("No se pudo decodificar el HEIC: %s", path)
        return None
