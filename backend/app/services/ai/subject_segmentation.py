"""
Segmentación aproximada de escena para fotografía automotriz: separa el
vehículo (sujeto) del fondo, y detecta personas para excluirlas de cualquier
ajuste dirigido al sujeto.

Deliberadamente NO usa un modelo de segmentación por red neuronal (que
requeriría cargar pesos de un modelo en memoria y sumar latencia de
inferencia por foto -- en un host con RAM ya ajustada, ver AI_MAX_WORKERS en
config.py, ese costo adicional es justo el tipo de cosa que ya causó cuelgues
por falta de memoria en esta app). En su lugar usa GrabCut (algoritmo clásico
ya incluido en OpenCV, sin dependencias nuevas), sembrado con la composición
típica de fotografía automotriz profesional: el vehículo centrado, ocupando
la mayoría del encuadre. No es tan preciso como un modelo entrenado en partes
de vehículos, pero diferencia sujeto/fondo de forma confiable para ese tipo
de composición, con costo de cómputo acotado y medido (~0.3-0.7s por foto a
la resolución reducida que se usa aquí).
"""
from __future__ import annotations
import numpy as np
import cv2

# GrabCut es costoso en CPU y su costo crece con resolución x iteraciones --
# medido con fotos reales: 400px/4 iteraciones tardaba hasta ~2s en fotos con
# escenas más complejas (más iteraciones necesarias para que el modelo de
# mezcla de gaussianas converja). 320px/3 iteraciones da una máscara
# visualmente equivalente (comparado lado a lado con la de 400px/4) en
# ~0.85s -- ver subject_segmentation en el historial de cambios para la
# comparación visual que respaldó este ajuste.
_GRABCUT_WIDTH = 320
_GRABCUT_ITERATIONS = 3


def estimate_subject_mask(image: np.ndarray) -> np.ndarray:
    """Devuelve una máscara float32 (mismo tamaño que `image`) en [0, 1]:
    1.0 = sujeto (vehículo), 0.0 = fondo. Si GrabCut no logra converger en
    algo útil (foto atípica: muy oscura, plana, o el vehículo no domina el
    encuadre), devuelve una máscara neutra (0.5 en todos lados) -- en vez de
    forzar una diferenciación sujeto/fondo poco confiable, el resto del
    pipeline simplemente no diferencia mucho ese caso puntual."""
    h, w = image.shape[:2]
    scale = min(1.0, _GRABCUT_WIDTH / w)
    small = (
        cv2.resize(image, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
        if scale < 1.0
        else image.copy()
    )
    sh, sw = small.shape[:2]

    mask = np.zeros((sh, sw), np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    # Rectángulo semilla: deja un margen de fondo/piso arriba y a los lados,
    # asumiendo que el vehículo domina el centro del encuadre (composición
    # estándar en las sesiones reales de Photonix AI).
    margin_x, margin_y = max(1, int(sw * 0.06)), max(1, int(sh * 0.10))
    rect = (margin_x, margin_y, max(1, sw - 2 * margin_x), max(1, sh - 2 * margin_y))

    try:
        cv2.grabCut(small, mask, rect, bgd_model, fgd_model, _GRABCUT_ITERATIONS, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return np.full((h, w), 0.5, dtype=np.float32)

    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1.0, 0.0).astype(np.float32)

    # Si GrabCut prácticamente no encontró sujeto (o marcó casi toda la
    # imagen como sujeto), el resultado no es confiable -- neutro.
    coverage = float(fg.mean())
    if coverage < 0.05 or coverage > 0.92:
        return np.full((h, w), 0.5, dtype=np.float32)

    # Suaviza el borde de la máscara: evita un contorno duro/visible entre
    # sujeto y fondo una vez aplicado el retoque diferencial.
    fg = cv2.GaussianBlur(fg, (0, 0), sigmaX=max(1.0, sw * 0.012))
    return cv2.resize(fg, (w, h), interpolation=cv2.INTER_LINEAR)


_FACE_CASCADE: cv2.CascadeClassifier | None = None


def _get_face_cascade() -> cv2.CascadeClassifier:
    global _FACE_CASCADE
    if _FACE_CASCADE is None:
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _FACE_CASCADE = cv2.CascadeClassifier(path)
    return _FACE_CASCADE


_FACE_DETECT_WIDTH = 640  # cascadas Haar en resolución completa (~10MP) tardan varios segundos por foto


def estimate_people_mask(image: np.ndarray) -> np.ndarray:
    """Detecta rostros (proxy práctico y liviano para "hay una persona aquí",
    sin necesitar un detector de personas completo) y devuelve una máscara
    float32 en [0, 1] cubriendo una estimación generosa del cuerpo a partir
    de cada rostro. Se usa para excluir esa zona de cualquier ajuste dirigido
    al vehículo -- las personas en la foto nunca deben retocarse."""
    h, w = image.shape[:2]
    mask = np.zeros((h, w), np.float32)

    scale = min(1.0, _FACE_DETECT_WIDTH / w)
    gray_full = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray_full, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA) if scale < 1.0 else gray_full

    faces = _get_face_cascade().detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    if len(faces) == 0:
        return mask

    for (x, y, fw, fh) in faces:
        x, y, fw, fh = (int(v / scale) for v in (x, y, fw, fh))
        body_x0 = max(0, x - fw)
        body_x1 = min(w, x + fw * 2)
        body_y0 = max(0, y - int(fh * 0.5))
        body_y1 = min(h, y + fh * 6)
        cv2.rectangle(mask, (body_x0, body_y0), (body_x1, body_y1), 1.0, thickness=-1)

    return cv2.GaussianBlur(mask, (0, 0), sigmaX=max(2.0, w * 0.01))


_SKY_DETECT_WIDTH = 480  # analizar en resolución completa (~10MP) es innecesario y lento para esto


def estimate_sky_mask(image: np.ndarray, subject_mask: np.ndarray) -> np.ndarray:
    """Aproxima la región de cielo despejado: parte superior del encuadre,
    fuera del vehículo, con tono azulado y brillante. Devuelve una máscara
    float32 en [0, 1]; toda-ceros si no hay evidencia suficiente de cielo
    despejado real (evita tratar paredes claras o cielo nublado uniforme
    como si fuera cielo azul)."""
    h, w = image.shape[:2]
    scale = min(1.0, _SKY_DETECT_WIDTH / w)
    sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
    small_img = cv2.resize(image, (sw, sh), interpolation=cv2.INTER_AREA) if scale < 1.0 else image
    small_subject = cv2.resize(subject_mask, (sw, sh), interpolation=cv2.INTER_LINEAR) if scale < 1.0 else subject_mask

    hsv = cv2.cvtColor(small_img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    is_blueish = (hue > 85) & (hue < 145)
    is_bright = val > 90
    is_not_washed_out = sat > 25  # descarta cielo nublado/blanco uniforme
    sky_color = (is_blueish & is_bright & is_not_washed_out).astype(np.float32)

    upper_region = np.zeros((sh, sw), np.float32)
    upper_region[: int(sh * 0.55), :] = 1.0

    sky = sky_color * upper_region * (1.0 - small_subject)

    if np.count_nonzero(sky) < 0.02 * sh * sw:
        return np.zeros((h, w), np.float32)

    sky = cv2.GaussianBlur(sky, (0, 0), sigmaX=max(2.0, sw * 0.01))
    return cv2.resize(sky, (w, h), interpolation=cv2.INTER_LINEAR)
