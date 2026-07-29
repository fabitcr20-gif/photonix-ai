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
from time import perf_counter
from typing import Optional
import numpy as np
import cv2

from app.services.ai.subject_segmentation import (
    estimate_subject_mask,
    estimate_people_mask,
    estimate_sky_mask,
)
from app.services.memory_utils import release_freed_memory


class _StageTimer:
    """Acumula duraciones por etapa en un dict compartido (ms) -- ver
    `apply_professional_finish` y `compute_scene_masks`. No hace nada si no
    se le pasa un dict (costo cero en el camino feliz sin métricas)."""

    def __init__(self, timings: Optional[dict] = None):
        self.timings = timings

    def stage(self, name: str):
        return _StageContext(self.timings, name)


class _StageContext:
    def __init__(self, timings: Optional[dict], name: str):
        self.timings = timings
        self.name = name

    def __enter__(self):
        self.t0 = perf_counter()
        return self

    def __exit__(self, *exc):
        if self.timings is not None:
            self.timings[self.name] = self.timings.get(self.name, 0.0) + (perf_counter() - self.t0) * 1000


@dataclass
class SceneMasks:
    subject: np.ndarray  # 1.0 = vehículo, 0.0 = fondo
    people: np.ndarray  # 1.0 = persona detectada
    sky: np.ndarray  # 1.0 = cielo despejado detectado (0 si no hay evidencia)


def compute_scene_masks(image: np.ndarray, timings: Optional[dict] = None, portrait_mode: bool = False) -> SceneMasks:
    with _StageTimer(timings).stage("Segmentacion"):
        people = estimate_people_mask(image)
        # Modo Retrato: la persona ES el sujeto principal -- se usa la
        # máscara de personas como "subject" (protagonista a realzar) en vez
        # del GrabCut genérico pensado para un objeto centrado tipo vehículo.
        subject = people if portrait_mode else estimate_subject_mask(image)
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
    result = image * (1 + amount_map3) - blurred * amount_map3
    return np.clip(result, 0, 255)


# Conversión BGR<->LAB/HSV en punto flotante REAL (no uint8 convertido a
# float después) -- confirmado con una imagen de prueba (degradado limpio)
# que un simple round-trip BGR->LAB->BGR con entrada/salida uint8 ya
# introduce banding por sí solo (188 saltos de hasta 5 niveles en un
# degradado perfecto, sin cambiar nada), porque OpenCV usa una aproximación
# de precisión limitada cuando la entrada es uint8. Con entrada float32 en
# 0-1 la conversión se hace en aritmética de punto flotante completa --
# confirmado que reduce esos 188 saltos a 6. Por eso estos helpers escalan a
# 0-1 antes de llamar a cv2 y de vuelta a 0-255 después; nunca pasan por
# uint8 salvo en CLAHE (única operación que lo exige), y ahí se usa 16-bit.
_LAB_L_MAX = 100.0  # rango nativo de L en LAB float32 (no 0-255)


def _bgr_to_lab_f32(img_0_255: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(np.clip(img_0_255, 0, 255) / 255.0, cv2.COLOR_BGR2LAB)


def _lab_to_bgr_f32(lab: np.ndarray) -> np.ndarray:
    return np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2BGR) * 255.0, 0, 255)


def _bgr_to_hsv_f32(img_0_255: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(np.clip(img_0_255, 0, 255) / 255.0, cv2.COLOR_BGR2HSV)


def _hsv_to_bgr_f32(hsv: np.ndarray) -> np.ndarray:
    return np.clip(cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR) * 255.0, 0, 255)


def _apply_vibrance(image: np.ndarray, amount: float) -> np.ndarray:
    """Aumenta la saturación más en los colores ya presentes pero apagados
    (pintura bajo nublado, follaje, ladrillo), y casi nada en los dos
    extremos: ni en lo que ya es vivo (pintura saturada, luces -- evita
    sobresaturar), ni en lo que es prácticamente neutro (cielo nublado,
    concreto, pavimento). Ese segundo límite es importante: un peso que
    sube sin techo a medida que la saturación baja (como una simple
    `(1 - sat_norm)`) amplifica MÁS que nada el tinte casi invisible que
    trae de fábrica cualquier zona gris (ruido de compresión JPEG, un
    balance de blancos levemente imperfecto) -- confirmado en una foto
    real donde un cielo nublado gris quedaba con un tinte magenta apenas
    perceptible, y con ese peso sin techo se volvía claramente visible.
    Por eso el peso es una curva en forma de joroba (pico en saturación
    media, cero en ambos extremos) en vez de monótona decreciente. Misma
    idea detrás del control "Vibrance" de Lightroom/Capture One, a
    diferencia de "Saturation" (que sube todo por igual y sí sobresatura
    fácilmente)."""
    if amount <= 0:
        return image
    hsv = _bgr_to_hsv_f32(image)
    sat = hsv[:, :, 1]  # ya en 0-1 (escala nativa float, no 0-255)
    weight = 4.0 * sat * (1.0 - sat)  # 0 en sat=0 y 1, pico en 0.5
    boost = amount * weight * (60.0 / 255.0)
    hsv[:, :, 1] = np.clip(sat + boost, 0, 1)
    return _hsv_to_bgr_f32(hsv)


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
    lab = _bgr_to_lab_f32(image)
    l = lab[:, :, 0]
    l_u16 = np.clip(l / _LAB_L_MAX * 65535.0, 0, 65535).astype(np.uint16)
    clahe = cv2.createCLAHE(clipLimit=1.0 + strength * 2.0, tileGridSize=(8, 8))
    l_eq_u16 = clahe.apply(l_u16)
    l_eq = l_eq_u16.astype(np.float32) / 65535.0 * _LAB_L_MAX
    lab[:, :, 0] = cv2.addWeighted(l, 1 - strength, l_eq, strength, 0)
    return _lab_to_bgr_f32(lab)


def _apply_highlight_rolloff(image: np.ndarray, knee: float = 225.0, strength: float = 0.6) -> np.ndarray:
    """Comprime suavemente los valores por encima de `knee` en vez de dejar
    que se corten de golpe en 255 -- protege capó/pintura brillante/faros de
    quemarse sin oscurecer el resto de la foto. Los valores por debajo de
    `knee` quedan intactos (`base`); solo el excedente por encima se
    comprime y se suma de vuelta."""
    base = np.minimum(image, knee)
    over = np.clip(image - knee, 0, None)
    compressed_over = over / (1.0 + strength * over / max(1.0, 255.0 - knee))
    result = base + compressed_over
    return np.clip(result, 0, 255)


def _apply_scurve_contrast(image: np.ndarray, strength: float = 0.15) -> np.ndarray:
    """Curva de contraste en S suave sobre la luminancia (canal L en LAB,
    el color en a/b queda intacto): sube el contraste en tonos medios
    protegiendo sombras y luces extremas de saturarse, a diferencia de un
    estiramiento lineal simétrico (que empuja negros/blancos hacia los
    extremos por igual sin importar qué tan cerca ya estén). Es la curva
    real detrás de cualquier look "cinematográfico" de Lightroom/Capture
    One -- pedido explícito: "curva en S muy suave... evitar negros
    completamente aplastados... evitar blancos quemados... mantener
    textura." Se mezcla con la identidad según `strength` (una S completa
    sin mezclar se ve exagerada)."""
    if strength <= 0:
        return image
    # Misma curva de antes, pero evaluada directamente sobre el canal L
    # continuo (float) en vez de una tabla de 256 entradas aplicada con
    # `cv2.LUT` (que exige L cuantizado a uint8 primero) -- evita esa
    # cuantización extra sin cambiar la forma de la curva.
    k = 3.0 + strength * 8.0  # qué tan pronunciada es la S
    sig_min = 1.0 / (1.0 + np.exp(k * 0.5))   # sigmoide en x=0
    sig_max = 1.0 / (1.0 + np.exp(-k * 0.5))  # sigmoide en x=1

    lab = _bgr_to_lab_f32(image)
    x = lab[:, :, 0] / _LAB_L_MAX
    sigmoid = 1.0 / (1.0 + np.exp(-k * (x - 0.5)))
    sigmoid = (sigmoid - sig_min) / (sig_max - sig_min)  # normaliza a 0..1 exacto
    blended = x * (1 - strength) + sigmoid * strength
    lab[:, :, 0] = np.clip(blended * _LAB_L_MAX, 0, _LAB_L_MAX)
    return _lab_to_bgr_f32(lab)


def _apply_reflection_softening(
    image: np.ndarray, subject_mask: np.ndarray, strength: float = 0.4, ceiling: float = 235.0
) -> np.ndarray:
    """Suaviza SOLO los reflejos más intensos sobre el vehículo (manchas muy
    brillantes -- típico de un reflejo directo de cielo/sol sobre pintura o
    cristal) sin tocar el resto del brillo/reflejo natural de la carrocería,
    que es justamente lo que le da la sensación de material real. Pedido
    explícito: "nunca eliminarlos completamente... solo suavizar reflejos
    demasiado fuertes... conservar la sensación del material." Por eso solo
    actúa sobre el excedente por encima de `ceiling` (un reflejo brillante
    normal, por debajo del techo, queda exactamente igual) y solo dentro de
    la máscara del vehículo (un cielo brillante de fondo no es "un reflejo
    del auto", no debe tocarse aquí)."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # lineal, sin cambio de escala -- se queda en 0-255
    hot = (gray > ceiling).astype(np.float32) * subject_mask
    if not np.any(hot):
        return image
    hot_mask = cv2.GaussianBlur(hot, (0, 0), sigmaX=4)

    lab = _bgr_to_lab_f32(image)
    l = lab[:, :, 0]
    ceiling_l = ceiling / 255.0 * _LAB_L_MAX  # ceiling llegó en escala 0-255, L nativo es 0-100
    excess = np.clip(l - ceiling_l, 0, None)
    lab[:, :, 0] = np.clip(l - excess * strength * hot_mask, 0, _LAB_L_MAX)
    return _lab_to_bgr_f32(lab)


def _apply_vegetation_desaturation(image: np.ndarray, ceiling: float = 140.0, strength: float = 0.6) -> np.ndarray:
    """Recorta SOLO el exceso de saturación en el rango de matiz
    verde/amarillo (césped, árboles, follaje) -- pedido explícito: "los
    verdes nunca deben verse fosforescentes... avoid radioactive trees...
    preserve color variation." Por eso actúa como `_apply_highlight_rolloff`
    (solo el excedente por encima de `ceiling`, nunca toca vegetación ya
    moderada) y solo dentro de la banda de matiz verde/amarillo (40-190
    grados, escala nativa 0-360) -- el resto de la foto (pintura, piel,
    cielo) no se toca aquí en absoluto."""
    hsv = _bgr_to_hsv_f32(image)
    hue, sat = hsv[:, :, 0], hsv[:, :, 1]  # hue: 0-360, sat: 0-1 (escala nativa)
    is_green_yellow = ((hue >= 40) & (hue <= 190)).astype(np.float32)
    ceiling_norm = ceiling / 255.0
    excess = np.clip(sat - ceiling_norm, 0, None)
    hsv[:, :, 1] = np.clip(sat - excess * strength * is_green_yellow, 0, 1)
    return _hsv_to_bgr_f32(hsv)


def _apply_shadow_floor_protection(image: np.ndarray, floor: float = 8.0, strength: float = 0.5) -> np.ndarray:
    """Evita que las sombras se empasten en negro puro: levanta suavemente
    solo los valores MUY cercanos a 0, preservando la profundidad general de
    las sombras (no es una recuperación de sombras global, esa la controla
    AdjustmentParams.shadows -- esto solo protege el piso para que quede
    "negro profundo con textura", no "negro empastado sin detalle")."""
    under = np.clip(floor - image, 0, None)
    lifted = image + under * strength * (under / max(1.0, floor))
    return np.clip(lifted, 0, 255)


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

    b, g, r = cv2.split(image)
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
    return cv2.merge([b, g, r])


def _apply_sky_depth(image: np.ndarray, sky_mask: np.ndarray, amount: float = 0.18) -> np.ndarray:
    """Profundiza levemente el azul del cielo SOLO donde se detectó cielo
    despejado real (ver estimate_sky_mask) -- nunca inventa nubes, nunca
    cambia el clima, nunca toca cielo nublado/blanco."""
    if not np.any(sky_mask):
        return image
    hsv = _bgr_to_hsv_f32(image)
    s, v = hsv[:, :, 1], hsv[:, :, 2]  # ambos 0-1 (escala nativa), los factores multiplicativos no cambian
    hsv[:, :, 1] = np.clip(s * (1 + amount * sky_mask), 0, 1)
    hsv[:, :, 2] = np.clip(v * (1 - amount * 0.12 * sky_mask), 0, 1)
    return _hsv_to_bgr_f32(hsv)


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


def _run_finish_steps(
    image: np.ndarray,
    masks: SceneMasks,
    auto_white_balance: bool,
    portrait_mode: bool = False,
    timings: Optional[dict] = None,
) -> np.ndarray:
    """La cadena real de ajustes de acabado, sin importar a qué resolución
    se llame -- ver `apply_professional_finish` para por qué se corre a una
    resolución reducida en vez de sobre la foto completa.

    Devuelve FLOAT32 (0-255 sin cuantizar), no uint8: igual que en
    basic_adjustments.py, encadenar ~9 pasos que cada uno redondeaba a uint8
    a la entrada/salida es lo que producía el banding/posterización
    confirmado con una imagen de prueba real -- ver ese módulo para el
    detalle completo. Quien llama a esta función decide cuándo cuantizar a
    uint8 (ver `apply_professional_finish`)."""
    timer = _StageTimer(timings)
    result = image.astype(np.float32)
    if auto_white_balance:
        with timer.stage("Balance de blancos"):
            result = _apply_white_balance_from_background(result, masks.subject, strength=0.35)
    # Piel: el microcontraste local (CLAHE) es lo primero que hace ver
    # textura de poros/plástico artificial -- pedido explícito "no skin
    # pores enhanced" -- por eso corre mucho más suave en modo Retrato.
    with timer.stage("CLAHE"):
        result = _apply_local_dynamic_range(result, strength=0.15 if portrait_mode else 0.30)
    with timer.stage("Contraste S"):
        result = _apply_scurve_contrast(result, strength=0.15)
    with timer.stage("Vibrance"):
        # 0.35 -> 0.5: pedido explícito del usuario ("que los colores tengan
        # vivacidad, pero que no se vean tan saturados") -- sigue siendo la
        # misma función protectora (sube más los colores apagados, casi no
        # toca los que ya son vivos), así que más "amount" da más color
        # perceptible sin el riesgo de sobresaturación que tendría subir un
        # "Saturation" uniforme.
        result = _apply_vibrance(result, amount=0.5)
    with timer.stage("Vegetacion"):
        result = _apply_vegetation_desaturation(result)
    # Nitidez dirigida: mucho más suave sobre una persona (evita textura de
    # piel/poros exagerada) que sobre un vehículo (donde sí se busca resaltar
    # carrocería/rines/faros frente al fondo).
    subject_amount = 0.08 if portrait_mode else 0.22
    background_amount = -0.05 if portrait_mode else -0.08
    with timer.stage("Nitidez"):
        result = _apply_directional_clarity(result, masks.subject, subject_amount=subject_amount, background_amount=background_amount)
    with timer.stage("Reflejos"):
        result = _apply_reflection_softening(result, masks.subject, strength=0.4)
    with timer.stage("Cielo"):
        result = _apply_sky_depth(result, masks.sky, amount=0.18)
    with timer.stage("Compresion altas luces"):
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
    portrait_mode: bool = False,
    timings: Optional[dict] = None,
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

    timer = _StageTimer(timings)

    if scale >= 1.0:
        result_f32 = _run_finish_steps(image, masks, auto_white_balance, portrait_mode, timings)
        with timer.stage("Render final"):
            result = np.clip(result_f32, 0, 255).astype(np.uint8)
            del result_f32
            # Fuera de modo Retrato, cualquier persona detectada es
            # incidental (no el sujeto pedido) y nunca debe tocarse. En modo
            # Retrato la persona ES el sujeto -- ya se editó con cuidado
            # arriba (CLAHE/nitidez suaves), revertirla la dejaría intacta
            # y el resto de la foto editada, justo lo opuesto de lo pedido.
            if not portrait_mode:
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

    enhanced_small = _run_finish_steps(small, small_masks, auto_white_balance, portrait_mode, timings)

    with timer.stage("Render final"):
        delta_small = enhanced_small.astype(np.float32) - small.astype(np.float32)
        del small, enhanced_small, small_masks
        release_freed_memory()

        delta_full = cv2.resize(delta_small, (w, h), interpolation=cv2.INTER_LINEAR)
        del delta_small

        result = np.clip(image.astype(np.float32) + delta_full, 0, 255).astype(np.uint8)
        del delta_full

        if not portrait_mode:
            result = _preserve_people(result, image, masks.people)
    release_freed_memory()
    return result
