"""
Agente de control de calidad post-edición (Core Feature de confiabilidad).

Después de los bugs de esta sesión (mosaicos/parches poligonales por una
condición de carrera de OpenCV, y contenido inventado por detectores de
placas/postes demasiado agresivos), esto es una red de seguridad automática:
compara cada foto editada contra su original ANTES de entregarla. Si la
edición se desvió demasiado de la estructura real de la foto -- la firma
exacta de esa clase de bug -- se descarta el resultado y se entrega la foto
original sin editar para esa foto puntual, en vez de arriesgar un resultado
dañado.

Se implementa un SSIM (Structural Similarity) simplificado a mano con
OpenCV/NumPy en vez de agregar `scikit-image` como dependencia nueva,
siguiendo el estilo del resto del pipeline (autocontenido, sin librerías de
visión pesadas adicionales). No es bit-exacto al SSIM de referencia, pero
captura lo mismo que importa aquí: cuánta estructura (bordes, geometría) se
conserva entre dos imágenes.

IMPORTANTE sobre qué comparar: NO se compara la foto final contra la foto
CRUDA original. Se probó eso primero y falló en la práctica -- una edición
legítima pero intensa (ej. "Intensidad IA" al 150% con claridad/dehaze al
máximo, algo que el usuario puede pedir libremente) puede bajar la similitud
contra el original hasta ~0.3-0.5, el mismo rango donde cae una corrupción
real. Comparar contra el original mezcla "qué tan fuerte fue el ajuste que
pidió el usuario" con "¿se rompió algo?", y esas son preguntas distintas.

En cambio, se compara la imagen justo ANTES del paso de limpieza (polvo/ruido,
`clean_image`) contra el resultado justo DESPUÉS de ese mismo paso. Ese es el
punto exacto de la pipeline donde vivieron los dos bugs reales de esta sesión
(el mosaico de `remove_sensor_dust` y el grano de la vieja
`fastNlMeansDenoisingColored`), y a diferencia de los ajustes de color/tono,
`clean_image` es una refinación que SIEMPRE debería ser sutil sin importar
qué tan agresivos fueron los ajustes previos -- así que su similitud
antes/después es mucho más estable y confiable como señal (medido con datos
reales: ~0.986-0.998 en ediciones legítimas, incluso las más extremas, contra
~0.47 en una corrupción de imagen completa simulada)."""
import numpy as np
import cv2

# Calibrado con datos reales (ver docstring del módulo): el piso observado en
# ediciones legítimas (incluyendo las más extremas permitidas por el slider de
# intensidad) fue ~0.986; una corrupción real de imagen completa (mosaico)
# cae a ~0.47. 0.85 deja margen amplio de ambos lados.
SSIM_THRESHOLD = 0.85

_COMPARE_WIDTH = 512  # reducir antes de comparar: más rápido, y no hace falta precisión de píxel


def _resize_for_compare(gray: np.ndarray) -> np.ndarray:
    h, w = gray.shape[:2]
    if w <= _COMPARE_WIDTH:
        return gray
    scale = _COMPARE_WIDTH / w
    return cv2.resize(gray, (_COMPARE_WIDTH, int(h * scale)), interpolation=cv2.INTER_AREA)


def compute_similarity(original_bgr: np.ndarray, edited_bgr: np.ndarray) -> float:
    """Similitud estructural aproximada entre 0 (nada en común) y 1 (idéntica).
    Compara luminancia (no color, para no penalizar ajustes de tono/temperatura
    legítimos) usando medias/varianzas/covarianza locales vía blur gaussiano,
    la misma idea detrás de SSIM."""
    g1 = _resize_for_compare(cv2.cvtColor(original_bgr, cv2.COLOR_BGR2GRAY)).astype(np.float64)
    g2 = _resize_for_compare(cv2.cvtColor(edited_bgr, cv2.COLOR_BGR2GRAY))
    if g2.shape != g1.shape:
        g2 = cv2.resize(g2, (g1.shape[1], g1.shape[0]), interpolation=cv2.INTER_AREA)
    g2 = g2.astype(np.float64)

    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    ksize = (11, 11)

    mu1 = cv2.GaussianBlur(g1, ksize, 1.5)
    mu2 = cv2.GaussianBlur(g2, ksize, 1.5)
    mu1_sq, mu2_sq, mu1_mu2 = mu1 * mu1, mu2 * mu2, mu1 * mu2

    sigma1_sq = cv2.GaussianBlur(g1 * g1, ksize, 1.5) - mu1_sq
    sigma2_sq = cv2.GaussianBlur(g2 * g2, ksize, 1.5) - mu2_sq
    sigma12 = cv2.GaussianBlur(g1 * g2, ksize, 1.5) - mu1_mu2

    ssim_map = ((2 * mu1_mu2 + c1) * (2 * sigma12 + c2)) / (
        (mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2)
    )
    return float(np.clip(np.mean(ssim_map), 0.0, 1.0))


def passes_quality_check(original_bgr: np.ndarray, edited_bgr: np.ndarray, threshold: float = SSIM_THRESHOLD) -> bool:
    return compute_similarity(original_bgr, edited_bgr) >= threshold
