"""
Acabado profesional de fotografía automotriz (rediseño del algoritmo de
edición automática): el vehículo como sujeto principal, colores fieles sin
sobresaturación, recuperación de rango dinámico local sin aspecto de HDR
artificial, y protección explícita de personas presentes en la toma.

Este módulo es deliberadamente independiente de `basic_adjustments.py`
(exposición/sombras/luces/blancos/negros manuales -- AdjustmentParams): ese
sistema sigue existiendo tal cual para edición manual y perfiles de estilo,
donde el usuario espera un control directo y predecible. Lo de aquí es un
paso de acabado adicional, aplicado siempre (automático o manual), que le da
a CUALQUIER foto procesada por Photonix AI la característica que pidió el
usuario explícitamente: que el auto se vea como el protagonista -- más nítido
y con más profundidad que el fondo -- sin inventar nada de la escena.

Todas las funciones son deliberadamente conservadoras en sus valores por
defecto: cada una se probó visualmente contra fotos reales para evitar los
resultados que el usuario pidió explícitamente evitar (plástico, HDR
artificial, sobresaturación, halos).
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import cv2

from app.services.ai.subject_segmentation import (
    estimate_subject_mask,
    estimate_people_mask,
    estimate_sky_mask,
)
from app.services.memory_utils import release_freed_memory


@dataclass
class SceneMasks:
    subject: np.ndarray  # 1.0 = vehículo, 0.0 = fondo
    people: np.ndarray  # 1.0 = persona detectada
    sky: np.ndarray  # 1.0 = cielo despejado detectado (0 si no hay evidencia)


def compute_scene_masks(image: np.ndarray) -> SceneMasks:
    subject = estimate_subject_mask(image)
    people = estimate_people_mask(image)
    sky = estimate_sky_mask(image, subject)
    return SceneMasks(subject=subject, people=people, sky=sky)


def _apply_directional_clarity(
    image: np.ndarray, subject_mask: np.ndarray, subject_amount: float, background_amount: float
) -> np.ndarray:
    """Enfoque/microcontraste local (unsharp mask) cuya intensidad varía
    según la máscara de sujeto: positivo (realza) sobre el vehículo, negativo
    y suave (relaja, no desenfoca) sobre el fondo -- crea separación visual
    sin que el fondo se vea artificialmente borroso.

    El desenfoque gaussiano es, por definición, información de baja
    frecuencia -- calcularlo sobre una copia reducida y reescalarlo de vuelta
    no pierde calidad perceptible (es una optimización estándar en unsharp
    masking) y evita pasar un kernel grande sobre los ~10MP completos de la
    foto original."""
    h, w = image.shape[:2]
    blur_width = 900
    scale = min(1.0, blur_width / w)
    if scale < 1.0:
        small = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        blurred_small = cv2.GaussianBlur(small, (0, 0), sigmaX=6 * scale)
        blurred = cv2.resize(blurred_small, (w, h), interpolation=cv2.INTER_LINEAR)
    else:
        blurred = cv2.GaussianBlur(image, (0, 0), sigmaX=6)

    amount_map = background_amount + (subject_amount - background_amount) * subject_mask
    amount_map3 = amount_map[:, :, None]
    img_f = image.astype(np.float32)
    blur_f = blurred.astype(np.float32)
    result = img_f * (1 + amount_map3) - blur_f * amount_map3
    return np.clip(result, 0, 255).astype(np.uint8)


def _apply_vibrance(image: np.ndarray, amount: float) -> np.ndarray:
    """Aumenta la saturación más donde el color ya es poco intenso, y casi
    nada donde ya es vivo (pintura, luces) -- sube la intensidad de color
    perceptible sin sobresaturar lo que ya estaba saturado. Es la misma idea
    detrás del control "Vibrance" de Lightroom/Capture One, a diferencia de
    "Saturation" (que sube todo por igual y sí sobresatura fácilmente)."""
    if amount <= 0:
        return image
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    sat = hsv[:, :, 1]
    sat_norm = sat / 255.0
    boost = amount * (1.0 - sat_norm) * 50.0
    hsv[:, :, 1] = np.clip(sat + boost, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def _apply_local_dynamic_range(image: np.ndarray, strength: float) -> np.ndarray:
    """CLAHE (ecualización adaptativa local) sobre el canal de luminancia,
    mezclado con el original -- recupera detalle en zonas de bajo contraste
    local (cielo, capó, parabrisas, llantas negras) sin necesitar saber QUÉ
    es cada zona semánticamente: donde hay poco contraste local, CLAHE lo
    recupera; donde ya hay suficiente, apenas la toca. Se mezcla con el
    original a `strength` (no se usa CLAHE al 100%) porque a fuerza completa
    el resultado se ve plano/con aspecto de HDR artificial -- exactamente lo
    que el usuario pidió evitar."""
    if strength <= 0:
        return image
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=1.0 + strength * 2.0, tileGridSize=(8, 8))
    l_eq = clahe.apply(l)
    l_final = cv2.addWeighted(l, 1 - strength, l_eq, strength, 0)
    merged = cv2.merge((l_final, a, b))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def _apply_highlight_rolloff(image: np.ndarray, knee: float = 225.0, strength: float = 0.6) -> np.ndarray:
    """Comprime suavemente los valores por encima de `knee` en vez de dejar
    que se corten de golpe en 255 -- protege capó/pintura brillante/faros de
    quemarse sin oscurecer el resto de la foto. Los valores por debajo de
    `knee` quedan intactos (`base`); solo el excedente por encima se
    comprime y se suma de vuelta."""
    img_f = image.astype(np.float32)
    base = np.minimum(img_f, knee)
    over = np.clip(img_f - knee, 0, None)
    compressed_over = over / (1.0 + strength * over / max(1.0, 255.0 - knee))
    result = base + compressed_over
    return np.clip(result, 0, 255).astype(np.uint8)


def _apply_shadow_floor_protection(image: np.ndarray, floor: float = 8.0, strength: float = 0.5) -> np.ndarray:
    """Evita que las sombras se empasten en negro puro: levanta suavemente
    solo los valores MUY cercanos a 0, preservando la profundidad general de
    las sombras (no es una recuperación de sombras global, esa la controla
    AdjustmentParams.shadows -- esto solo protege el piso para que quede
    "negro profundo con textura", no "negro empastado sin detalle")."""
    img_f = image.astype(np.float32)
    under = np.clip(floor - img_f, 0, None)
    lifted = img_f + under * strength * (under / max(1.0, floor))
    return np.clip(lifted, 0, 255).astype(np.uint8)


def _apply_white_balance_from_background(image: np.ndarray, subject_mask: np.ndarray, strength: float = 0.35) -> np.ndarray:
    """Balance de blancos automático (gray-world) calculado SOLO sobre el
    fondo (pavimento, paredes, vegetación), excluyendo al vehículo -- si se
    calculara sobre toda la foto, la pintura del auto (un solo color, a
    veces dominante en la escena) sesgaría la estimación y el algoritmo
    intentaría "corregir" el color real del auto, justo lo que el usuario
    pidió no hacer. Se mezcla a `strength` (no 100%) para respetar la
    temperatura real de la luz de la escena en vez de neutralizarla del todo."""
    h, w = image.shape[:2]
    bg_weight = 1.0 - subject_mask
    total_weight = float(bg_weight.sum())
    if total_weight < 0.05 * h * w:
        return image  # casi no hay fondo confiable para estimar -- no adivinar

    img_f = image.astype(np.float32)
    b, g, r = cv2.split(img_f)
    mean_b = float((b * bg_weight).sum() / total_weight)
    mean_g = float((g * bg_weight).sum() / total_weight)
    mean_r = float((r * bg_weight).sum() / total_weight)
    mean_gray = (mean_b + mean_g + mean_r) / 3.0
    if min(mean_b, mean_g, mean_r) < 1.0:
        return image

    scale_b = 1.0 + (mean_gray / mean_b - 1.0) * strength
    scale_g = 1.0 + (mean_gray / mean_g - 1.0) * strength
    scale_r = 1.0 + (mean_gray / mean_r - 1.0) * strength
    # Nunca corregir más de +-12%: una escena con luz muy cálida/fría de
    # verdad (atardecer, sombra azulada) debe seguir viéndose así -- esto
    # solo corrige sesgos moderados del sensor/balance automático de la
    # cámara, no reinterpreta la luz real de la toma.
    scale_b, scale_g, scale_r = (float(np.clip(s, 0.88, 1.12)) for s in (scale_b, scale_g, scale_r))

    b = np.clip(b * scale_b, 0, 255)
    g = np.clip(g * scale_g, 0, 255)
    r = np.clip(r * scale_r, 0, 255)
    return cv2.merge([b, g, r]).astype(np.uint8)


def _apply_sky_depth(image: np.ndarray, sky_mask: np.ndarray, amount: float = 0.18) -> np.ndarray:
    """Profundiza levemente el azul del cielo SOLO donde se detectó cielo
    despejado real (ver estimate_sky_mask) -- nunca inventa nubes, nunca
    cambia el clima, nunca toca cielo nublado/blanco."""
    if not np.any(sky_mask):
        return image
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    s, v = hsv[:, :, 1], hsv[:, :, 2]
    hsv[:, :, 1] = np.clip(s * (1 + amount * sky_mask), 0, 255)
    hsv[:, :, 2] = np.clip(v * (1 - amount * 0.12 * sky_mask), 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def _preserve_people(edited: np.ndarray, original: np.ndarray, people_mask: np.ndarray) -> np.ndarray:
    """Devuelve los píxeles originales sin editar en cualquier zona marcada
    como persona -- ver estimate_people_mask. El usuario pidió explícitamente
    nunca modificar a las personas presentes en la foto."""
    if not np.any(people_mask):
        return edited
    mask3 = people_mask[:, :, None]
    result = edited.astype(np.float32) * (1 - mask3) + original.astype(np.float32) * mask3
    return np.clip(result, 0, 255).astype(np.uint8)


_FINISH_WORKING_WIDTH = 1600  # ver nota de memoria abajo


def _run_finish_steps(image: np.ndarray, masks: SceneMasks, auto_white_balance: bool) -> np.ndarray:
    """La cadena real de ajustes de acabado, sin importar a qué resolución
    se llame -- ver `apply_professional_finish` para por qué se corre a una
    resolución reducida en vez de sobre la foto completa."""
    result = image
    if auto_white_balance:
        result = _apply_white_balance_from_background(result, masks.subject, strength=0.35)
    result = _apply_local_dynamic_range(result, strength=0.30)
    result = _apply_vibrance(result, amount=0.35)
    result = _apply_directional_clarity(result, masks.subject, subject_amount=0.22, background_amount=-0.08)
    result = _apply_sky_depth(result, masks.sky, amount=0.18)
    result = _apply_highlight_rolloff(result, knee=228.0, strength=0.55)
    result = _apply_shadow_floor_protection(result, floor=8.0, strength=0.5)
    return result


def _resize_mask(mask: np.ndarray, w: int, h: int) -> np.ndarray:
    return cv2.resize(mask, (w, h), interpolation=cv2.INTER_LINEAR)


def apply_professional_finish(
    image: np.ndarray,
    masks: SceneMasks,
    *,
    auto_white_balance: bool = True,
) -> np.ndarray:
    """Aplica el paso de acabado completo. Conservador por diseño: cada
    función individual ya limita su propio efecto máximo, y aquí se usan
    valores medios probados visualmente contra fotos reales para lograr un
    resultado "premium, limpio y natural" (pedido explícito del usuario) sin
    parecer un filtro.

    Nota de memoria (importante): cada paso de `_run_finish_steps` convierte
    la foto completa a float32 (4x el tamaño del uint8 original) al menos
    una vez, y varios mantienen 2-3 búfers así simultáneos -- a resolución
    completa (~10MP en fotos reales de cámara/celular) eso alcanza cientos
    de MB por paso, y encadenados sin liberar entre uno y otro tumban un host
    de 1GB (confirmado con un OOM kill real en producción durante el
    desarrollo de este pipeline; el `release_freed_memory()` entre pasos NO
    fue suficiente, porque el problema es el PICO de un solo paso, no la
    acumulación entre pasos). La solución real: correr toda la cadena sobre
    una copia reducida (`_FINISH_WORKING_WIDTH`, ~1600px -- son ajustes de
    tono/color/contraste local, de naturaleza suave, que no necesitan
    resolución completa para calcularse bien), obtener el DELTA que produjo
    (cuánto cambió cada píxel), reescalar ese delta a resolución completa, y
    sumarlo sobre la foto original -- así el resultado conserva el detalle
    fino de la foto completa, y la foto completa solo pasa por operaciones
    float32 una vez (no una vez por cada uno de los 6-7 pasos)."""
    h, w = image.shape[:2]
    scale = min(1.0, _FINISH_WORKING_WIDTH / w)

    if scale >= 1.0:
        result = _run_finish_steps(image, masks, auto_white_balance)
        result = _preserve_people(result, image, masks.people)
        release_freed_memory()
        return result

    sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
    small = cv2.resize(image, (sw, sh), interpolation=cv2.INTER_AREA)
    small_masks = SceneMasks(
        subject=_resize_mask(masks.subject, sw, sh),
        people=_resize_mask(masks.people, sw, sh),
        sky=_resize_mask(masks.sky, sw, sh),
    )

    enhanced_small = _run_finish_steps(small, small_masks, auto_white_balance)
    delta_small = enhanced_small.astype(np.float32) - small.astype(np.float32)
    del small, enhanced_small, small_masks
    release_freed_memory()

    delta_full = cv2.resize(delta_small, (w, h), interpolation=cv2.INTER_LINEAR)
    del delta_small

    result = np.clip(image.astype(np.float32) + delta_full, 0, 255).astype(np.uint8)
    del delta_full

    result = _preserve_people(result, image, masks.people)
    release_freed_memory()
    return result
