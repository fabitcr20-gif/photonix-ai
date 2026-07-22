"""
Análisis de entorno (Core Feature #1 del motor de IA).
Lee metadatos EXIF y analiza la imagen en sí para estimar:
  - Hora del día (madrugada, mañana, mediodía, atardecer, noche)
  - Condición de clima probable (soleado, nublado, lluvia) — heurística por
    histograma de color/contraste (placeholder listo para reemplazar por un
    modelo de clasificación entrenado, ej. un CNN fine-tuneado).
  - Cantidad de luz (brillo promedio, rango dinámico).
  - `scene_condition`: clasificación combinada en una de 9 categorías
    fotográficas reales (ver `_classify_scene_condition`), cada una con su
    propia receta de edición en `basic_adjustments.suggest_params_from_environment`
    y `professional_finish.py` -- pedido explícito: "cada clima debe tener
    un pipeline completamente distinto", no un único preset para todas.
Esta info alimenta a `basic_adjustments.py` para decidir la corrección ideal.
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import numpy as np
import cv2
from PIL import Image
from PIL.ExifTags import TAGS


@dataclass
class EnvironmentAnalysis:
    captured_at: Optional[str]
    time_of_day: str          # 'madrugada' | 'mañana' | 'mediodía' | 'atardecer' | 'noche'
    weather_guess: str        # 'soleado' | 'nublado' | 'lluvia' | 'indeterminado'
    light_amount: str         # 'baja' | 'media' | 'alta'
    avg_brightness: float     # 0-255
    dynamic_range: float      # desviación estándar de luminancia
    color_temperature: str = "neutro"  # 'calido' | 'neutro' | 'frio' -- sesgo global R vs B
    scene_condition: str = "indeterminado"
    # 'soleado' | 'parcialmente_nublado' | 'muy_nublado' | 'atardecer' |
    # 'amanecer' | 'lluvia' | 'noche_urbana' | 'golden_hour' | 'blue_hour' |
    # 'indeterminado'
    iso: Optional[int] = None
    focal_length_mm: Optional[float] = None
    aperture: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _read_exif(image_path: str) -> dict:
    """Extrae los tags EXIF relevantes usando Pillow."""
    exif_data = {}
    try:
        with Image.open(image_path) as img:
            raw_exif = img._getexif() or {}
            for tag_id, value in raw_exif.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = value
    except Exception:
        pass  # Muchos RAW no exponen EXIF vía Pillow directamente; usar exiftool en producción.
    return exif_data


def _classify_time_of_day(exif: dict) -> tuple[str, Optional[str], Optional[int]]:
    """Clasifica la hora del día a partir de DateTimeOriginal del EXIF."""
    dt_str = exif.get("DateTimeOriginal") or exif.get("DateTime")
    if not dt_str:
        return "indeterminado", None, None
    try:
        dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return "indeterminado", None, None

    hour = dt.hour
    if 5 <= hour < 8:
        label = "madrugada"
    elif 8 <= hour < 12:
        label = "mañana"
    elif 12 <= hour < 16:
        label = "mediodía"
    elif 16 <= hour < 19:
        label = "atardecer"
    else:
        label = "noche"
    return label, dt.isoformat(), hour


def _estimate_light_and_weather(image_path: str) -> tuple[float, float, str, str, float]:
    """Heurística de brillo/clima basada en histograma de luminancia (canal Y)
    y saturación de color (canal S en HSV). Sirve como base rápida; en
    producción se puede sustituir por un modelo entrenado (ej. ResNet ligero)
    sin cambiar la firma de esta función."""
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        return 0.0, 0.0, "indeterminado", "indeterminado", 0.0

    ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    luminance = ycrcb[:, :, 0].astype(np.float32)
    avg_brightness = float(np.mean(luminance))
    dynamic_range = float(np.std(luminance))

    if avg_brightness < 80:
        light_amount = "baja"
    elif avg_brightness < 170:
        light_amount = "media"
    else:
        light_amount = "alta"

    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    avg_saturation = float(np.mean(hsv[:, :, 1]))
    # Cielos nublados/lluvia tienden a bajo contraste y baja saturación;
    # escenas soleadas suelen tener alto contraste y colores más saturados.
    if dynamic_range > 55 and avg_saturation > 90:
        weather_guess = "soleado"
    elif dynamic_range < 30 and avg_saturation < 60:
        weather_guess = "lluvia"
    elif avg_saturation < 80:
        weather_guess = "nublado"
    else:
        weather_guess = "indeterminado"

    return avg_brightness, dynamic_range, light_amount, weather_guess, avg_saturation


def _estimate_color_temperature(image_path: str) -> str:
    """Sesgo de temperatura de color GLOBAL (para clasificación de escena, no
    para corrección -- esa se calcula sobre el fondo solamente en
    professional_finish.py, para no sesgarse con el color de la pintura del
    auto). Compara el promedio de los canales R y B: luz cálida (amanecer,
    atardecer, golden hour, interiores con tungsteno) empuja R > B; luz fría
    (sombra abierta, cielo nublado denso, blue hour) empuja B > R."""
    img = cv2.imread(image_path)
    if img is None:
        return "neutro"
    b, g, r = cv2.split(img.astype(np.float32))
    mean_b, mean_r = float(b.mean()), float(r.mean())
    diff = mean_r - mean_b
    if diff > 8:
        return "calido"
    if diff < -8:
        return "frio"
    return "neutro"


def _classify_scene_condition(
    hour: Optional[int],
    time_of_day: str,
    weather_guess: str,
    light_amount: str,
    avg_brightness: float,
    dynamic_range: float,
    avg_saturation: float,
    color_temperature: str,
) -> str:
    """Combina todas las señales en UNA de 9 categorías fotográficas reales.
    Cada una alimenta una receta de edición distinta (ver
    suggest_params_from_environment) -- el pedido explícito es que el clima
    cambie el pipeline, no solo un par de números.

    Nota sobre "lluvia": se probó una heurística de detección automática de
    pavimento mojado (reflejos especulares en la mitad inferior del
    encuadre) y se descartó -- dio falsos positivos en 2 de 2 fotos reales
    de prueba, ambas con pavimento seco (una con agregado de concreto claro,
    otra con grava clara incrustada en asfalto oscuro: ambas texturas
    estáticas se leían como "reflejo brillante de baja saturación" con el
    umbral simple que se probó). Clasificar mal una foto seca como lluviosa
    dispararía un tratamiento de imagen inapropiado, exactamente lo que este
    pipeline busca evitar -- mejor no detectarlo automáticamente que
    detectarlo mal. La categoría "lluvia" hoy depende de `weather_guess`
    (heurística ya existente, más conservadora) o del override manual del
    usuario en el frontend.

    Orden de prioridad: nubosidad primero (la señal visual más directa y
    menos ambigua -- un cielo nublado a las 4:50pm sigue siendo un cielo
    nublado, no "atardecer" solo porque el reloj EXIF caiga en esa ventana;
    ver nota abajo, esto fue un bug real encontrado con una foto de prueba)
    -> lluvia -> ventanas de luz dorada/azul/noche por hora exacta (EXIF,
    solo cuando el clima YA se leyó como despejado/indeterminado, nunca
    para pisar por encima de un "nublado" real) -> soleado -> genérico por
    hora si no hubo EXIF. Si no hay EXIF de hora, se cae de vuelta a
    clima/luz medidos directo de la imagen.

    Bug real encontrado y corregido durante el desarrollo: la primera
    versión priorizaba la ventana horaria SOBRE el clima detectado, así que
    una foto genuinamente nublada tomada a las 16:50 salía clasificada como
    "atardecer" (con su receta de tonos cálidos) solo por la hora del
    reloj, ignorando que el cielo gris y la temperatura de color neutra de
    la propia foto decían lo contrario. Verificado con una foto real
    (cielo cubierto, sin luz dorada) que efectivamente disparaba ese bug
    antes de este reordenamiento."""
    if weather_guess == "nublado":
        # Grado de nubosidad: "muy nublado" = luz plana y pareja (rango
        # dinámico y saturación ambos muy bajos); "parcialmente nublado" deja
        # algo más de variación (claros de sol entre nubes).
        if dynamic_range < 35 and avg_saturation < 55:
            return "muy_nublado"
        return "parcialmente_nublado"

    if weather_guess == "lluvia":
        return "lluvia"

    if hour is not None:
        # Ventanas horarias reales de golden/blue hour (aprox., valen para
        # cualquier latitud tropical/templada sin necesitar geolocalización):
        # blue hour es un tramo corto justo antes del amanecer/después del
        # atardecer con luz azulada residual pero SIN sol directo; golden
        # hour es la hora siguiente al amanecer o previa al atardecer, con
        # sol bajo y cálido. Solo se llega aquí si el clima NO es nublado,
        # así que estas ventanas reflejan luz de cielo despejado real.
        if 5 <= hour < 6 or 18 <= hour < 19:
            if color_temperature != "calido" and avg_brightness < 130:
                return "blue_hour"
        if 6 <= hour < 8:
            return "amanecer" if color_temperature != "calido" else "golden_hour"
        if 16 <= hour < 18:
            return "golden_hour" if color_temperature == "calido" else "atardecer"
        if hour >= 19 or hour < 5:
            # De noche pero con brillo medible = luces artificiales urbanas,
            # no oscuridad total.
            if avg_brightness > 25:
                return "noche_urbana"

    if weather_guess == "soleado":
        return "soleado"

    if time_of_day in ("atardecer",):
        return "golden_hour" if color_temperature == "calido" else "atardecer"
    if time_of_day == "madrugada":
        return "amanecer"
    if time_of_day == "noche" and avg_brightness > 25:
        return "noche_urbana"

    return "indeterminado"


def reclassify_after_override(env: EnvironmentAnalysis) -> str:
    """Recalcula `scene_condition` después de un override MANUAL de
    weather_guess/light_amount (ver BatchOptions.weather_override en
    batch_processor.py) -- si el usuario corrige el clima que la IA
    detectó mal, la categoría de escena (y con ella la receta de edición
    completa) debe reflejar esa corrección, no quedarse pegada a la
    lectura automática original que el usuario acaba de decir que estaba
    mal. Usa un mapeo directo y predecible (no las mismas heurísticas de
    `_classify_scene_condition`): un override es una señal fuerte y
    deliberada, no otra estimación a ponderar."""
    if env.weather_guess == "lluvia":
        return "lluvia"
    if env.weather_guess == "nublado":
        return "muy_nublado" if env.light_amount == "baja" else "parcialmente_nublado"
    if env.weather_guess == "soleado":
        if env.time_of_day == "atardecer":
            return "golden_hour" if env.color_temperature == "calido" else "atardecer"
        return "soleado"
    return env.scene_condition


def analyze_environment(image_path: str) -> EnvironmentAnalysis:
    """Punto de entrada: analiza una imagen y devuelve un `EnvironmentAnalysis`
    completo, combinando EXIF + heurística visual."""
    exif = _read_exif(image_path)
    time_of_day, captured_at, hour = _classify_time_of_day(exif)
    avg_brightness, dynamic_range, light_amount, weather_guess, avg_saturation = _estimate_light_and_weather(
        image_path
    )
    color_temperature = _estimate_color_temperature(image_path)
    scene_condition = _classify_scene_condition(
        hour,
        time_of_day,
        weather_guess,
        light_amount,
        avg_brightness,
        dynamic_range,
        avg_saturation,
        color_temperature,
    )

    return EnvironmentAnalysis(
        captured_at=captured_at,
        time_of_day=time_of_day,
        weather_guess=weather_guess,
        light_amount=light_amount,
        avg_brightness=round(avg_brightness, 2),
        dynamic_range=round(dynamic_range, 2),
        color_temperature=color_temperature,
        scene_condition=scene_condition,
        iso=exif.get("ISOSpeedRatings"),
        focal_length_mm=float(exif["FocalLength"]) if exif.get("FocalLength") else None,
        aperture=float(exif["FNumber"]) if exif.get("FNumber") else None,
    )
