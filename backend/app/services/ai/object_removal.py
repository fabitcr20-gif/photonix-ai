"""
Eliminación de elementos (Object Removal) — Core Feature #4b.
Detección y borrado automático de: placas de autos, marcas/logos de terceros,
postes de luz y cables eléctricos.

IMPORTANTE (nota de arquitectura): la DETECCIÓN de cada tipo de objeto es un
problema de visión por computadora especializado. Aquí se define la interfaz
estable (`detect_*` -> lista de máscaras/bboxes) con una implementación base
funcional por heurística clásica de OpenCV, y puntos de extensión claros para
enchufar modelos entrenados sin cambiar el resto del pipeline:
  - Placas de autos: reemplazar `detect_license_plates` por un detector YOLO
    entrenado en datasets de placas (ej. YOLOv8 + OCR de matrícula).
  - Logos/marcas: reemplazar `detect_logos` por matching contra un banco de
    logos conocidos (ej. embeddings CLIP + búsqueda por similitud).
  - Postes/cables: reemplazar `detect_poles_and_wires` por un modelo de
    segmentación semántica (ej. U-Net entrenado en escenas urbanas/aéreas).

Una vez detectada la máscara del objeto, `remove_objects` usa inpainting
(cv2.inpaint / cv2.INPAINT_TELEA) para "borrar" el objeto de forma creíble.
Para resultados más avanzados, esta función puede sustituirse por un modelo
de inpainting generativo (ej. LaMa, Stable Diffusion inpainting).
"""
from __future__ import annotations
import numpy as np
import cv2


def detect_license_plates(image: np.ndarray) -> np.ndarray:
    """Detecta regiones rectangulares con alta densidad de bordes verticales/
    horizontales (patrón típico de una placa) usando un clasificador Haar
    preentrenado de OpenCV como base rápida.
    Devuelve una máscara binaria (255 = región a eliminar).

    El cascade Haar genérico da muchos falsos positivos en cualquier zona con
    bordes repetitivos (rejillas, difusores, parrillas) -- si se les hace
    caso, el inpainting borra piezas reales del auto. Para evitarlo: exige
    mucha más evidencia (`minNeighbors` alto) y descarta cualquier detección
    cuyo tamaño/proporción no sea plausible para una placa real."""
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    img_h, img_w = image.shape[:2]
    try:
        plate_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_russian_plate_number.xml"
        )
        plates = plate_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=12)
        for (x, y, w, h) in plates:
            aspect = w / h if h else 0
            width_ratio = w / img_w
            # Una placa real: proporción ancha (~2:1 a 3.5:1) y un tamaño
            # razonable respecto al ancho de la foto (ni un punto, ni medio auto).
            if not (1.8 <= aspect <= 3.5 and 0.03 <= width_ratio <= 0.15):
                continue
            # Rejillas/difusores tienen la misma proporción que una placa pero
            # muchísima más textura (huecos oscuros repetidos): una placa real
            # es una superficie casi lisa con caracteres, así que su densidad
            # de bordes y variación de brillo son mucho más bajas.
            roi_edges = edges[y:y + h, x:x + w]
            roi_gray = gray[y:y + h, x:x + w]
            if roi_edges.size == 0:
                continue
            edge_density = np.count_nonzero(roi_edges) / roi_edges.size
            if edge_density > 0.035 or float(np.std(roi_gray)) > 30:
                continue
            cv2.rectangle(mask, (x, y), (x + w, y + h), 255, thickness=cv2.FILLED)
    except cv2.error:
        pass  # Clasificador no disponible en este build de OpenCV; no bloquea el pipeline.
    return mask


def detect_logos(image: np.ndarray, reference_logos: list[np.ndarray] | None = None) -> np.ndarray:
    """Detecta logos conocidos mediante matching de features (ORB) contra un
    banco de referencias (`reference_logos`). Si no se provee banco, no marca
    nada (placeholder seguro: nunca borra de más)."""
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    if not reference_logos:
        return mask

    orb = cv2.ORB_create(nfeatures=800)
    gray_scene = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    kp_scene, des_scene = orb.detectAndCompute(gray_scene, None)
    if des_scene is None:
        return mask

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    for ref in reference_logos:
        gray_ref = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY) if ref.ndim == 3 else ref
        kp_ref, des_ref = orb.detectAndCompute(gray_ref, None)
        if des_ref is None:
            continue
        matches = bf.match(des_ref, des_scene)
        good = sorted(matches, key=lambda m: m.distance)[:25]
        pts = np.array([kp_scene[m.trainIdx].pt for m in good], dtype=np.int32)
        if len(pts) >= 4:
            x, y, w, h = cv2.boundingRect(pts)
            cv2.rectangle(mask, (x, y), (x + w, y + h), 255, thickness=cv2.FILLED)

    return mask


def detect_poles_and_wires(image: np.ndarray) -> np.ndarray:
    """Detecta líneas largas, delgadas y casi-rectas típicas de postes
    (verticales) y cables eléctricos (diagonales/curvas suaves contra el
    cielo) usando Canny + Hough probabilístico, filtrando por longitud/ángulo.

    Con criterios sueltos, esto engancha CUALQUIER línea recta larga de la
    foto: molduras del auto, líneas de la carrocería, bordes de la calle,
    rejillas del parachoques -- y el inpainting termina borrando piezas
    reales del auto (no solo postes/cables). Para que sea seguro: (1) solo se
    consideran líneas dentro del tercio superior de la foto (donde
    normalmente están el cielo y los cables/postes reales, no el auto), (2)
    se exige una longitud mínima proporcional al ancho de la imagen en vez de
    un valor fijo en píxeles, y (3) se sube el umbral de Hough para pedir más
    evidencia por línea."""
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    img_h, img_w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    min_length = max(100, int(img_w * 0.12))
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=150, minLineLength=min_length, maxLineGap=8)

    if lines is None:
        return mask

    sky_boundary = img_h * 0.35
    for line in lines:
        x1, y1, x2, y2 = line[0]
        # El auto (sujeto principal) casi siempre ocupa el resto del cuadro;
        # postes/cables reales están arriba, contra el cielo.
        if max(y1, y2) > sky_boundary:
            continue
        length = np.hypot(x2 - x1, y2 - y1)
        if length < min_length:
            continue
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        # Postes: casi verticales (~90°). Cables: casi horizontales/diagonales suaves.
        is_pole = 85 <= angle <= 95
        is_wire = angle <= 10 or angle >= 170
        if is_pole or is_wire:
            cv2.line(mask, (x1, y1), (x2, y2), 255, thickness=6)

    return mask


def remove_objects(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Elimina cualquier región marcada en `mask` (255 = eliminar) usando
    inpainting. Combina múltiples máscaras (placas + logos + postes/cables)
    antes de llamar a esta función con `combine_masks`."""
    if not np.any(mask):
        return image
    mask_dilated = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=1)
    return cv2.inpaint(image, mask_dilated, inpaintRadius=5, flags=cv2.INPAINT_TELEA)


def combine_masks(*masks: np.ndarray) -> np.ndarray:
    combined = masks[0].copy()
    for m in masks[1:]:
        combined = cv2.bitwise_or(combined, m)
    return combined


def auto_remove_unwanted_elements(
    image: np.ndarray,
    remove_plates: bool = False,
    remove_logos: bool = False,
    remove_poles_wires: bool = False,
    reference_logos: list[np.ndarray] | None = None,
) -> np.ndarray:
    """Pipeline de conveniencia: detecta y elimina en un solo paso los
    elementos indeseados seleccionados por el usuario."""
    masks = []
    if remove_plates:
        masks.append(detect_license_plates(image))
    if remove_logos:
        masks.append(detect_logos(image, reference_logos))
    if remove_poles_wires:
        masks.append(detect_poles_and_wires(image))

    if not masks:
        return image

    final_mask = combine_masks(*masks)
    return remove_objects(image, final_mask)
