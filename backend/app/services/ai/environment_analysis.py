"""
Análisis de entorno (Core Feature #1 del motor de IA).
Lee metadatos EXIF y analiza la imagen en sí para estimar:
  - Hora del día (madrugada, mañana, mediodía, atardecer, noche)
  - Condición de clima probable (soleado, nublado, lluvia) — heurística por
    histograma de color/contraste (placeholder listo para reemplazar por un
    modelo de clasificación entrenado, ej. un CNN fine-tuneado).
  - Cantidad de luz (brillo promedio, rango dinámico).
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


def _classify_time_of_day(exif: dict) -> tuple[str, Optional[str]]:
    """Clasifica la hora del día a partir de DateTimeOriginal del EXIF."""
    dt_str = exif.get("DateTimeOriginal") or exif.get("DateTime")
    if not dt_str:
        return "indeterminado", None
    try:
        dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return "indeterminado", None

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
    return label, dt.isoformat()


def _estimate_light_and_weather(image_path: str) -> tuple[float, float, str, str]:
    """Heurística de brillo/clima basada en histograma de luminancia (canal Y)
    y saturación de color (canal S en HSV). Sirve como base rápida; en
    producción se puede sustituir por un modelo entrenado (ej. ResNet ligero)
    sin cambiar la firma de esta función."""
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        return 0.0, 0.0, "indeterminado", "indeterminado"

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

    return avg_brightness, dynamic_range, light_amount, weather_guess


def analyze_environment(image_path: str) -> EnvironmentAnalysis:
    """Punto de entrada: analiza una imagen y devuelve un `EnvironmentAnalysis`
    completo, combinando EXIF + heurística visual."""
    exif = _read_exif(image_path)
    time_of_day, captured_at = _classify_time_of_day(exif)
    avg_brightness, dynamic_range, light_amount, weather_guess = _estimate_light_and_weather(image_path)

    return EnvironmentAnalysis(
        captured_at=captured_at,
        time_of_day=time_of_day,
        weather_guess=weather_guess,
        light_amount=light_amount,
        avg_brightness=round(avg_brightness, 2),
        dynamic_range=round(dynamic_range, 2),
        iso=exif.get("ISOSpeedRatings"),
        focal_length_mm=float(exif["FocalLength"]) if exif.get("FocalLength") else None,
        aperture=float(exif["FNumber"]) if exif.get("FNumber") else None,
    )
