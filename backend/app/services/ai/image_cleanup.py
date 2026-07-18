"""
Limpieza de imagen por IA (Core Feature #4): borrador de polvo, reducción de
ruido digital y reducción de ruido de color (chroma noise).
- Ruido digital (luminancia): `cv2.bilateralFilter` (suaviza preservando bordes).
- Ruido de color: suavizado selectivo de los canales de crominancia (a, b en LAB),
  preservando el detalle de luminancia (L) para no perder nitidez.
- Polvo/manchas del sensor: detección de manchas pequeñas y oscuras/circulares
  vía blob detection + inpainting (`cv2.inpaint`), típico de fondos lisos
  (cielos, paredes) donde el polvo del sensor es más visible.
"""
import numpy as np
import cv2


def reduce_digital_noise(image: np.ndarray, strength: float = 0.5) -> np.ndarray:
    """strength: 0.0 (sin efecto) a 1.0 (máxima reducción de ruido).

    Se usa `bilateralFilter` (edge-preserving) en vez de
    `fastNlMeansDenoisingColored`: en este stack, esa función de OpenCV
    resultó tener un bug real de corrupción -- en vez de suavizar, introduce
    grano/ruido de color visible (confirmado de forma reproducible y
    determinística, no es un problema de concurrencia). `bilateralFilter` da
    un resultado limpio equivalente sin ese riesgo."""
    sigma = 15 + strength * 60
    return cv2.bilateralFilter(image, d=9, sigmaColor=sigma, sigmaSpace=sigma)


def reduce_color_noise(image: np.ndarray, strength: float = 0.5) -> np.ndarray:
    """Difumina solo los canales de color (a, b) en espacio LAB, manteniendo
    la luminancia (L) intacta para no perder nitidez aparente. El ruido de
    color (motas verdes/magenta) es más visible que el de luminancia para el
    ojo humano, así que aquí se usa una ventana más grande que en
    `reduce_digital_noise` para la misma `strength`."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    ksize = max(3, int(strength * 15) | 1)  # kernel impar
    a_blur = cv2.medianBlur(a, ksize)
    b_blur = cv2.medianBlur(b, ksize)
    merged = cv2.merge((l, a_blur, b_blur))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def remove_sensor_dust(image: np.ndarray, sensitivity: float = 0.5) -> np.ndarray:
    """Detecta pequeñas manchas circulares oscuras (polvo del sensor) sobre
    zonas de bajo detalle (cielos, fondos lisos) y las repara con inpainting.

    Superficies con textura fina (grava, follaje, cables sobre cielo nublado)
    generan muchos falsos positivos: diferencias de contraste locales que
    parecen "motas" pero son detalle real de la foto. Si se les hace inpaint
    igual, el resultado es un mosaico/parche deforme sobre esas zonas. Para
    evitarlo: (1) solo se acepta como polvo lo que es realmente circular
    (relación área/perímetro cercana a un círculo), y (2) si el total de
    "polvo" detectado supera un pequeño porcentaje de la imagen, se asume que
    es textura mal clasificada y se aborta sin tocar la foto, en vez de
    inpaintear áreas grandes."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.medianBlur(gray, 5)
    diff = cv2.absdiff(gray, blurred)

    threshold = int(15 + (1 - sensitivity) * 25)  # más sensible -> umbral más bajo
    _, mask = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)

    # Solo motas pequeñas, compactas y circulares (evita marcar bordes,
    # texturas o hilos/cables, que producen contornos alargados o irregulares).
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    dust_mask = np.zeros_like(gray)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 2 or area > 60:
            continue
        perimeter = cv2.arcLength(cnt, True)
        if perimeter <= 0:
            continue
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        if circularity < 0.6:  # 1.0 = círculo perfecto; descarta formas alargadas/ruido de textura
            continue
        cv2.drawContours(dust_mask, [cnt], -1, 255, thickness=cv2.FILLED)

    if not np.any(dust_mask):
        return image

    # Si lo detectado como "polvo" cubre una fracción grande de la imagen, casi
    # seguro es textura real (grava, follaje) mal clasificada, no polvo de
    # sensor real (que son unas pocas motas aisladas). Mejor no tocar la foto.
    max_dust_fraction = 0.015
    if np.count_nonzero(dust_mask) > max_dust_fraction * dust_mask.size:
        return image

    dust_mask = cv2.dilate(dust_mask, np.ones((3, 3), np.uint8), iterations=1)
    return cv2.inpaint(image, dust_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)


def clean_image(image: np.ndarray, denoise_strength: float = 0.4, dust_sensitivity: float = 0.4) -> np.ndarray:
    """Pipeline completo de limpieza: polvo -> ruido de color -> ruido digital."""
    result = remove_sensor_dust(image, dust_sensitivity)
    result = reduce_color_noise(result, denoise_strength)
    result = reduce_digital_noise(result, denoise_strength)
    return result
