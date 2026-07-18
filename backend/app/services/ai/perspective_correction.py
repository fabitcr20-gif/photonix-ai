"""
Corrección de perspectiva automática (Core Feature #2).
Detecta líneas dominantes (bordes de edificios, paredes, horizontes) con
Canny + Transformada de Hough, estima el ángulo de inclinación dominante y
aplica una corrección de rotación/perspectiva con `cv2.warpPerspective`.

Nota de producción: para arquitectura/interiores se recomienda evolucionar
esto a un modelo de detección de líneas de fuga (vanishing point) tipo
"deep vanishing point detection", pero esta heurística por Hough ya resuelve
el caso común de horizontes torcidos y verticales inclinadas.
"""
import numpy as np
import cv2


def _detect_dominant_angle(gray: np.ndarray) -> float:
    """Devuelve el ángulo a corregir, o 0.0 si no hay evidencia suficientemente
    fuerte de un horizonte torcido.

    En fotografía automotriz/lifestyle el fondo suele tener postes, cables y
    cercas en ángulos variados que NO son el horizonte: si se les hace caso,
    la 'corrección' termina rotando el auto y cambiando su pose respecto a la
    toma original (justo lo que no queremos). Para evitar falsos positivos
    solo se corrige cuando hay muchas líneas independientes que coinciden en
    (casi) el mismo ángulo -- un horizonte/pared real produce ese consenso;
    postes y cables sueltos, no."""
    edges = cv2.Canny(gray, 60, 160, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=120)
    if lines is None:
        return 0.0

    angles = []
    for line in lines[:150]:
        rho, theta = line[0]
        angle_deg = (theta * 180 / np.pi) - 90
        # Solo líneas cercanas a la horizontal (+-8°): una toma ya bien
        # encuadrada no debería necesitar más que eso, y limitar la ventana
        # reduce las chances de enganchar cables/postes muy inclinados.
        if -8 <= angle_deg <= 8:
            angles.append(angle_deg)

    # Requiere un consenso amplio y ajustado entre líneas independientes
    # (un horizonte real las alinea casi todas); si son pocas o están
    # dispersas, es ruido de fondo y no se corrige nada.
    if len(angles) < 8:
        return 0.0
    median_angle = float(np.median(angles))
    if float(np.std(angles)) > 1.0:
        return 0.0
    return median_angle


def correct_perspective(image: np.ndarray) -> np.ndarray:
    """Corrige automáticamente horizontes torcidos evidentes. Devuelve la
    imagen corregida (mismo tamaño, bordes rellenados). Deliberadamente
    conservador: solo actúa ante evidencia fuerte y limita la corrección
    máxima, para nunca alterar la pose/ángulo original de la toma."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    angle = _detect_dominant_angle(gray)

    # Ventana de corrección: por debajo de 0.5° no vale la pena tocar la foto;
    # por encima de 3° es casi seguro un falso positivo (una toma de acción
    # real casi nunca sale tan torcida), así que se descarta en vez de aplicar
    # una rotación agresiva no solicitada.
    if abs(angle) < 0.5 or abs(angle) > 3.0:
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, scale=1.0)
    corrected = cv2.warpAffine(
        image, rotation_matrix, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT
    )
    return corrected


def auto_crop_straightened(image: np.ndarray, margin_pct: float = 0.03) -> np.ndarray:
    """Recorta un pequeño margen tras enderezar, para eliminar bordes reflejados."""
    h, w = image.shape[:2]
    mx, my = int(w * margin_pct), int(h * margin_pct)
    return image[my:h - my, mx:w - mx]
