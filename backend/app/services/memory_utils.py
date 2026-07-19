"""
Utilidad compartida para devolver memoria liberada al sistema operativo.

En Linux, glibc (malloc) no siempre le devuelve al SO la memoria que Python
ya liberó -- la retiene en el arena del proceso "por si acaso". Con
operaciones que reservan temporalmente cientos de MB (descargas, decodificar
imágenes, conversiones a float32 para ajustes de tono/limpieza de ruido),
eso hace que un proceso de larga duración (el servidor web, no un script que
arranca y termina) quede cada vez más "inflado" con cada foto/descarga,
hasta acumular lo suficiente para un OOM kill en un host con RAM ajustada
-- aunque ninguna operación individual necesite tanta memoria.
"""
import ctypes
import gc
import sys

_libc = ctypes.CDLL("libc.so.6") if sys.platform.startswith("linux") else None


def release_freed_memory() -> None:
    """Fuerza a que la memoria ya liberada por Python se devuelva al SO.
    Solo aplica en Linux (glibc); en macOS/desarrollo es no-op."""
    gc.collect()
    if _libc is not None:
        _libc.malloc_trim(0)
