"""
Orquestador del motor de IA: procesa por lotes (batch) miles de fotografías
aplicando, en orden, todo el pipeline de edición automatizada:

  1. Análisis de entorno (hora/clima/luz, con posible override manual) -> sugiere ajustes
  2. Corrección de perspectiva
  3. Ajustes básicos (luces, sombras, tono, saturación, blancos, negros,
     claridad, dehaze)
  4. Limpieza de imagen (polvo, ruido digital, ruido de color)
  5. Control de calidad automático del paso de limpieza (ver qa_check.py) -
     descarta ese resultado puntual si se desvió demasiado de la estructura
     real, sin importar qué tan intensos fueron los ajustes de color/tono
  6. Eliminación de objetos (placas, logos, postes, cables) - opcional
  7. Marca de agua - opcional (ver watermark_service.py)

Usa `ThreadPoolExecutor` para procesar varias imágenes en paralelo (las
operaciones de OpenCV liberan el GIL en su mayoría), lo que permite escalar a
sesiones de miles de fotos sin bloquear el event loop de FastAPI. Para cargas
extremas, este mismo módulo puede ejecutarse como workers separados (ej. Celery
+ Redis) sin cambiar la lógica de negocio.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Optional
import os
import cv2

from app.services.ai.environment_analysis import analyze_environment, EnvironmentAnalysis
from app.services.ai.perspective_correction import correct_perspective
from app.services.ai.basic_adjustments import suggest_params_from_environment, apply_adjustments, AdjustmentParams
from app.services.ai.image_cleanup import clean_image
from app.services.ai.object_removal import auto_remove_unwanted_elements
from app.services.ai.qa_check import passes_quality_check

# Ya paralelizamos por foto con ThreadPoolExecutor (ver process_batch). Si además
# dejamos que OpenCV reparta cada llamada (fastNlMeansDenoisingColored, CLAHE, etc.)
# entre sus propios hilos internos, con N imágenes en paralelo se sobre-suscriben
# los núcleos (N hilos de Python x N hilos internos de OpenCV), lo que en la
# práctica puede corromper los buffers de funciones como
# fastNlMeansDenoisingColored bajo contención real (mosaico/parches poligonales
# en el resultado, de forma intermitente). Cada hilo de Python ya es "una imagen
# completa", así que OpenCV no necesita paralelizar también internamente.
cv2.setNumThreads(1)


@dataclass
class BatchOptions:
    auto_perspective: bool = True
    auto_adjustments: bool = True
    auto_cleanup: bool = True
    remove_plates: bool = False
    remove_logos: bool = False
    remove_poles_wires: bool = False
    custom_adjustments: Optional[AdjustmentParams] = None  # override manual, ej. "Mi Estilo"
    denoise_strength: Optional[float] = None  # 0.0-1.0; None = usa el default de clean_image
    # Contexto manual de clima/luz (ver ai_engine.ProcessProjectRequest): si se
    # indican, reemplazan la lectura automática de EnvironmentAnalysis antes de
    # calcular los ajustes, para corregir adivinanzas erróneas que causan
    # sobre/sub-exposición.
    weather_override: Optional[str] = None
    light_override: Optional[str] = None
    run_quality_check: bool = True  # ver qa_check.py; se desactiva en re-ediciones manuales


@dataclass
class ProcessedImageResult:
    input_path: str
    output_path: str
    environment: Optional[EnvironmentAnalysis] = None
    success: bool = True
    error: Optional[str] = None
    qa_fallback: bool = False  # True si el resultado editado no pasó el control de calidad
    # y se entregó la foto original sin tocar en su lugar (ver qa_check.py)


def process_single_image(input_path: str, output_path: str, options: BatchOptions) -> ProcessedImageResult:
    """Procesa una sola imagen a través de todo el pipeline de IA."""
    try:
        image = cv2.imread(input_path)
        if image is None:
            raise ValueError("No se pudo leer la imagen (formato no soportado por OpenCV; "
                              "para RAW nativo usar rawpy antes de este paso).")

        env = analyze_environment(input_path)
        if options.weather_override:
            env.weather_guess = options.weather_override
        if options.light_override:
            env.light_amount = options.light_override
        applied_params: Optional[AdjustmentParams] = None

        if options.auto_perspective:
            image = correct_perspective(image)

        if options.auto_adjustments:
            applied_params = options.custom_adjustments or suggest_params_from_environment(env)
            image = apply_adjustments(image, applied_params)

        qa_fallback = False
        if options.auto_cleanup:
            pre_cleanup = image.copy()  # ver qa_check.py: se compara justo antes/después de este paso
            if options.denoise_strength is not None:
                image = clean_image(image, denoise_strength=options.denoise_strength)
            else:
                # Levantar sombras/exposición revela ruido de sensor y de
                # compresión que antes quedaba oculto en lo oscuro; entre más
                # se levantó, más limpieza de ruido hace falta para que el
                # resultado salga listo para exportar sin que el usuario
                # tenga que retocarlo a mano.
                shadow_lift = max(0.0, applied_params.shadows) if applied_params else 0.0
                exposure_lift = max(0.0, applied_params.exposure) if applied_params else 0.0
                adaptive_strength = min(1.0, 0.35 + shadow_lift * 0.5 + exposure_lift * 0.3)
                image = clean_image(image, denoise_strength=adaptive_strength)

            # Agente de control de calidad: `clean_image` debería ser siempre
            # una refinación sutil, sin importar qué tan agresivos fueron los
            # ajustes de color/tono previos (por eso se compara contra el
            # estado justo ANTES de este paso, no contra la foto cruda). Si el
            # resultado se desvió demasiado, es la firma de una corrupción
            # (mosaico, contenido dañado); se descarta ese paso y se sigue con
            # la imagen de antes de limpiar en vez de arriesgar un resultado dañado.
            if options.run_quality_check and not passes_quality_check(pre_cleanup, image):
                image = pre_cleanup
                qa_fallback = True
            else:
                del pre_cleanup  # copia completa de la imagen; ya no hace falta tras la comparación

        if options.remove_plates or options.remove_logos or options.remove_poles_wires:
            image = auto_remove_unwanted_elements(
                image,
                remove_plates=options.remove_plates,
                remove_logos=options.remove_logos,
                remove_poles_wires=options.remove_poles_wires,
            )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cv2.imwrite(output_path, image, [cv2.IMWRITE_JPEG_QUALITY, 95])

        return ProcessedImageResult(
            input_path=input_path, output_path=output_path, environment=env, qa_fallback=qa_fallback
        )
    except Exception as exc:  # noqa: BLE001 - queremos capturar cualquier fallo por imagen
        return ProcessedImageResult(input_path=input_path, output_path=output_path, success=False, error=str(exc))


def process_batch(
    input_paths: list[str],
    output_dir: str,
    options: BatchOptions | None = None,
    max_workers: int = 8,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> list[ProcessedImageResult]:
    """Procesa una lista de imágenes en paralelo. Diseñado para escalar a
    sesiones de 500 a 5000+ fotografías sin degradar el rendimiento:
      - `max_workers` controla el paralelismo (ajustar según CPU disponible).
      - `on_progress(done, total)` permite reportar avance en tiempo real al
        frontend (ej. vía WebSocket o polling).
    """
    options = options or BatchOptions()
    results: list[ProcessedImageResult] = []
    total = len(input_paths)
    done = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for path in input_paths:
            filename = os.path.basename(path)
            output_path = os.path.join(output_dir, filename)
            futures[executor.submit(process_single_image, path, output_path, options)] = path

        for future in as_completed(futures):
            results.append(future.result())
            done += 1
            if on_progress:
                on_progress(done, total)

    return results
