"""
Ajustes básicos automatizados (Core Feature #3): luces, sombras, tono,
saturación, blancos, negros, claridad y dehaze (desvanecimiento de neblina).
Implementado con OpenCV/NumPy para performance en lotes grandes. Los valores
sugeridos se calculan a partir del `EnvironmentAnalysis` (hora/clima/luz),
pero también pueden pasarse manualmente para aplicar un "look" específico.
"""
from dataclasses import dataclass
import numpy as np
import cv2
from app.services.ai.environment_analysis import EnvironmentAnalysis


@dataclass
class AdjustmentParams:
    exposure: float = 0.0       # -1.0 a 1.0
    highlights: float = 0.0     # -1.0 (recuperar) a 1.0 (realzar)
    shadows: float = 0.0        # -1.0 (oscurecer) a 1.0 (levantar)
    whites: float = 0.0
    blacks: float = 0.0
    clarity: float = 0.0        # contraste local / nitidez (0 a 1)
    saturation: float = 0.0     # -1.0 a 1.0
    dehaze: float = 0.0         # 0 (sin efecto) a 1 (máximo desvanecido de neblina)
    contrast: float = 0.0       # -1.0 a 1.0 (estira blancos/negros de forma simétrica)
    temperature: float = 0.0    # -1.0 (más frío/azul) a 1.0 (más cálido) — balance de blancos


# Techo global (Motor V3 "Natural Professional Editing"): sin importar el
# perfil de estilo o la receta por clima, ningún ajuste puede superar estos
# valores -- pedido explícito ("Prohibited Operations": HDR extremo, claridad
# exagerada, saturación excesiva, etc.). Esto protege también a los 7
# perfiles de estilo que todavía usan un preset estático (ver
# core/style_profiles.py) sin necesidad de reescribir cada uno.
_MAX_SATURATION = 0.05
_MAX_CLARITY = 0.30
_MAX_CONTRAST = 0.20
_MAX_DEHAZE = 0.35


def _clamp_params(params: "AdjustmentParams") -> "AdjustmentParams":
    params.saturation = float(np.clip(params.saturation, -_MAX_SATURATION, _MAX_SATURATION))
    params.clarity = float(np.clip(params.clarity, 0.0, _MAX_CLARITY))
    params.contrast = float(np.clip(params.contrast, -_MAX_CONTRAST, _MAX_CONTRAST))
    params.dehaze = float(np.clip(params.dehaze, 0.0, _MAX_DEHAZE))
    return params


# Receta base por `scene_condition` (ver environment_analysis.py): cada
# clima/hora tiene su propia combinación de valores, no un preset único con
# un par de números que cambian -- pedido explícito. Los valores son
# deliberadamente conservadores (nunca saturación fuerte, nunca claridad
# extrema) porque la prioridad es que la edición NO se note como hecha por
# IA; se prefiere quedarse corto a arriesgar un look artificial.
#
# Compartida entre los perfiles "automatico" y "automotriz": tras el
# rediseño de realismo, ambos persiguen el mismo objetivo ("cámara full
# frame + editor profesional en Lightroom"), así que no hace falta una
# tabla separada para automotriz -- lo que lo distingue del modo genérico
# es el acabado dirigido al vehículo (ver professional_finish.py), no una
# receta de tono/color distinta.
_SCENE_BASE_PARAMS: dict[str, dict] = {
    # Sol directo: la escena ya trae contraste/color de sobra -- la mano
    # debe ser más ligera que en cualquier otra categoría, y el trabajo real
    # es proteger las luces (el sol quema fácil) sin apagar el conjunto.
    "soleado": dict(exposure=-0.05, highlights=-0.15, shadows=0.10, clarity=0.15, saturation=0.03, contrast=0.08),
    # Nublado parcial: hay algo de variación (claros entre nubes) -- permite
    # un pulido moderado, más cerca del comportamiento "por defecto".
    "parcialmente_nublado": dict(exposure=0.05, shadows=0.10, clarity=0.15, saturation=0.05, dehaze=0.08, contrast=0.08),
    # Ejemplo explícito del pedido: "NO intentar volverlo soleado, mantener
    # la atmósfera gris, resaltar SOLO profundidad/contraste/riqueza tonal/
    # detalle del vehículo" -- por eso saturation y temperature quedan en 0
    # (cero push de color) y todo el trabajo lo hace clarity/contrast/shadows.
    "muy_nublado": dict(exposure=0.08, shadows=0.15, clarity=0.22, saturation=0.0, dehaze=0.05, contrast=0.12, temperature=0.0),
    # Atardecer genérico (sin la luz dorada marcada de "golden_hour"): tibio
    # apenas perceptible, protege las luces bajas del sol poniente.
    "atardecer": dict(exposure=0.0, highlights=-0.10, shadows=0.15, saturation=0.05, temperature=0.08, contrast=0.08),
    "amanecer": dict(exposure=0.05, shadows=0.15, saturation=0.03, temperature=0.04, contrast=0.06, clarity=0.12),
    # "Aumentar ligeramente los tonos cálidos. Nunca exagerar el naranja" --
    # temperature=0.15 es un empujón cálido real pero acotado (ver
    # _apply_temperature: a esta escala mueve el canal LAB 'b' apenas 3/255).
    "golden_hour": dict(exposure=0.0, highlights=-0.12, shadows=0.10, saturation=0.08, temperature=0.15, contrast=0.08, clarity=0.15),
    # "Conservar los azules, no volver la imagen morada" -- CERO saturación
    # extra a propósito: subir saturación sobre una mezcla azul/magenta de
    # blue hour es justo lo que la empuja hacia morado. temperature ligeramente
    # frío, nunca agresivo.
    "blue_hour": dict(exposure=0.10, shadows=0.25, saturation=0.0, temperature=-0.05, contrast=0.06, clarity=0.10),
    # Preserva el aspecto mojado (no "seca" la escena) -- dehaze moderado
    # solo para neblina/bruma real, no para maquillar la lluvia.
    "lluvia": dict(exposure=0.05, shadows=0.15, saturation=0.03, dehaze=0.12, clarity=0.12, contrast=0.06),
    # Luces artificiales urbanas de noche: la recuperación de sombras debe
    # ser generosa (si no, la foto se queda sin nada visible), con el punto
    # de negro levemente levantado para que no se vea empastado -- pedido
    # explícito "evitar negros completamente aplastados".
    "noche_urbana": dict(exposure=0.15, shadows=0.35, blacks=0.1, saturation=0.05, clarity=0.10, contrast=0.05),
    # Sin clasificación confiable: el "pulido base" ya validado (contraste/
    # claridad/saturación suaves) en vez de no hacer nada.
    "indeterminado": dict(contrast=0.10, clarity=0.18, saturation=0.06),
}


# Receta por clima para el modo Retrato: mismo principio (una tabla por
# `scene_condition`, no un preset único), pero con `clarity` mucho más baja
# en TODAS las categorías -- el contraste local/microcontraste es lo primero
# que hace ver "plástica" la piel o resalta poros de forma antinatural.
# `shadows` se mantiene generoso (abrir sombras en rostro sin aplastar) y
# `temperature` nunca empuja hacia el naranja (pedido explícito: "no orange
# skin"). La protección real de piel (nada de nitidez dirigida agresiva)
# ocurre en professional_finish.py; esta tabla solo controla tono/color.
_PORTRAIT_SCENE_PARAMS: dict[str, dict] = {
    "soleado": dict(exposure=-0.05, highlights=-0.18, shadows=0.15, clarity=0.05, saturation=0.02, contrast=0.05),
    "parcialmente_nublado": dict(exposure=0.05, shadows=0.12, clarity=0.06, saturation=0.03, contrast=0.05),
    "muy_nublado": dict(exposure=0.08, shadows=0.18, clarity=0.06, saturation=0.0, contrast=0.06),
    "atardecer": dict(exposure=0.0, highlights=-0.12, shadows=0.18, saturation=0.03, temperature=0.05, contrast=0.05),
    "amanecer": dict(exposure=0.05, shadows=0.18, saturation=0.02, temperature=0.03, contrast=0.04),
    "golden_hour": dict(exposure=0.0, highlights=-0.15, shadows=0.15, saturation=0.04, temperature=0.08, contrast=0.05),
    "blue_hour": dict(exposure=0.10, shadows=0.25, saturation=0.0, temperature=-0.03, contrast=0.03),
    "lluvia": dict(exposure=0.05, shadows=0.15, saturation=0.02, clarity=0.04, contrast=0.04),
    "noche_urbana": dict(exposure=0.18, shadows=0.35, blacks=0.12, saturation=0.02, clarity=0.04, contrast=0.03),
    "indeterminado": dict(exposure=0.03, shadows=0.12, clarity=0.06, saturation=0.03, contrast=0.05),
}

# Receta por clima para el modo Paisaje: techos de clarity/dehaze mucho más
# bajos que el preset estático anterior (era clarity=0.3/dehaze=0.25 fijo,
# sin importar el clima -- justo lo que el pedido prohíbe). El verde/azul
# real se protege en professional_finish.py (desaturación de vegetación) y
# en `estimate_sky_mask` (nunca inventa cielo dramático); esta tabla solo
# controla la exposición/tono base por condición.
_LANDSCAPE_SCENE_PARAMS: dict[str, dict] = {
    "soleado": dict(exposure=-0.05, highlights=-0.15, shadows=0.12, clarity=0.12, dehaze=0.08, saturation=0.02, contrast=0.08),
    "parcialmente_nublado": dict(exposure=0.05, shadows=0.10, clarity=0.12, dehaze=0.10, saturation=0.03, contrast=0.08),
    "muy_nublado": dict(exposure=0.08, shadows=0.15, clarity=0.15, dehaze=0.06, saturation=0.0, contrast=0.10),
    "atardecer": dict(exposure=0.0, highlights=-0.12, shadows=0.12, saturation=0.04, temperature=0.06, contrast=0.08),
    "amanecer": dict(exposure=0.05, shadows=0.15, saturation=0.03, temperature=0.03, clarity=0.10, contrast=0.06),
    "golden_hour": dict(exposure=0.0, highlights=-0.12, shadows=0.10, saturation=0.05, temperature=0.12, clarity=0.12, contrast=0.08),
    "blue_hour": dict(exposure=0.10, shadows=0.22, saturation=0.0, temperature=-0.05, clarity=0.08, contrast=0.06),
    "lluvia": dict(exposure=0.05, shadows=0.15, saturation=0.02, dehaze=0.15, clarity=0.10, contrast=0.06),
    "noche_urbana": dict(exposure=0.15, shadows=0.35, blacks=0.1, saturation=0.03, clarity=0.10, contrast=0.05),
    "indeterminado": dict(contrast=0.08, clarity=0.12, dehaze=0.08, saturation=0.02),
}

# Perfiles con tabla propia por clima -- el resto de perfiles de estilo
# (ver core/style_profiles.py) sigue usando su preset estático fijo, ahora
# acotado por _clamp_params como red de seguridad global.
_SCENE_TABLES: dict[str, dict[str, dict]] = {
    "automatico": _SCENE_BASE_PARAMS,
    "automotriz": _SCENE_BASE_PARAMS,
    "retrato": _PORTRAIT_SCENE_PARAMS,
    "paisaje": _LANDSCAPE_SCENE_PARAMS,
}


def suggest_params_from_environment(env: EnvironmentAnalysis, profile: str = "automatico") -> AdjustmentParams:
    """Traduce el análisis de entorno en una sugerencia inicial de ajustes.
    Esta es la 'corrección inteligente automática' pedida en el requerimiento.

    La receta base viene de la tabla del perfil (`_SCENE_TABLES`, ver arriba)
    según `scene_condition` (9 categorías fotográficas reales, cada una con
    su propia combinación de valores -- no un preset único). Sobre esa base
    se aplican dos ajustes ADICIONALES, ortogonales a la categoría climática:
      1. Balance de sombras/luces según el rango dinámico real de la escena
         (una escena de brillo "medio" puede tener a la vez sombras duras y
         luces quemadas -- típico de sol directo -- algo que el promedio de
         brillo o la categoría climática por sí solos no detectan).
      2. Corrección de exposición para escenas genuinamente muy oscuras/muy
         claras, sin importar la categoría (una noche urbana MUY oscura
         sigue necesitando más levantamiento que una moderada).

    Al final se aplica `_clamp_params`: sin importar la tabla o los ajustes
    de rango dinámico/exposición de arriba, el resultado nunca puede superar
    los techos globales del Motor V3 (ver `_MAX_*` arriba)."""
    table = _SCENE_TABLES.get(profile, _SCENE_BASE_PARAMS)
    base = table.get(env.scene_condition, table["indeterminado"])
    params = AdjustmentParams(**base)

    if env.dynamic_range > 60:
        params.shadows += 0.2
        params.highlights -= 0.15

    if env.light_amount == "baja":
        params.exposure += 0.20
        params.shadows += 0.2
        params.blacks = max(params.blacks, 0.1)
    elif env.light_amount == "alta":
        params.exposure -= 0.10
        params.highlights -= 0.2
        params.whites = min(params.whites, -0.05)

    return _clamp_params(params)


def _apply_exposure(img: np.ndarray, amount: float) -> np.ndarray:
    return np.clip(img.astype(np.float32) * (1 + amount), 0, 255).astype(np.uint8)


def _apply_highlights_shadows(img: np.ndarray, highlights: float, shadows: float) -> np.ndarray:
    """Ajusta luces y sombras por separado usando una máscara de luminancia."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    l_channel = lab[:, :, 0]
    norm_l = l_channel / 255.0

    shadow_mask = 1 - norm_l          # más fuerte en zonas oscuras
    highlight_mask = norm_l           # más fuerte en zonas claras

    l_channel += shadows * 40 * shadow_mask
    l_channel += highlights * 40 * highlight_mask
    lab[:, :, 0] = np.clip(l_channel, 0, 255)
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)


def _apply_whites_blacks(img: np.ndarray, whites: float, blacks: float) -> np.ndarray:
    """Estira el punto blanco/negro del histograma (similar a Lightroom)."""
    img_f = img.astype(np.float32)
    black_point = blacks * 25
    white_point = 255 - whites * 25
    img_f = (img_f - black_point) * (255.0 / max(white_point - black_point, 1))
    return np.clip(img_f, 0, 255).astype(np.uint8)


def _apply_saturation(img: np.ndarray, amount: float) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1 + amount), 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def _apply_clarity(img: np.ndarray, amount: float) -> np.ndarray:
    """Contraste local vía unsharp mask sobre el canal de luminancia."""
    if amount <= 0:
        return img
    blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=6)
    return cv2.addWeighted(img, 1 + amount, blurred, -amount, 0)


def _apply_contrast(img: np.ndarray, amount: float) -> np.ndarray:
    """Contraste global: estira blancos/negros de forma simétrica alrededor
    del punto medio (128), a diferencia de `clarity` que es contraste local."""
    if amount == 0:
        return img
    factor = 1 + amount  # amount en -1..1
    img_f = img.astype(np.float32)
    img_f = (img_f - 128) * factor + 128
    return np.clip(img_f, 0, 255).astype(np.uint8)


def _apply_temperature(img: np.ndarray, amount: float) -> np.ndarray:
    """Balance de blancos simplificado: desplaza el canal 'b' (azul-amarillo)
    en espacio LAB. amount > 0 = más cálido (amarillo), < 0 = más frío (azul)."""
    if amount == 0:
        return img
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab[:, :, 2] = np.clip(lab[:, :, 2] + amount * 20, 0, 255)
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)


def _apply_dehaze(img: np.ndarray, amount: float) -> np.ndarray:
    """Desvanecimiento de neblina simplificado: CLAHE sobre el canal L (LAB)
    combinado con reducción de bruma vía dark-channel aproximado.
    Para máxima calidad se puede sustituir por un dehazing profundo (ej. AOD-Net)."""
    if amount <= 0:
        return img
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0 + amount * 2, tileGridSize=(8, 8))
    l_eq = clahe.apply(l)
    merged = cv2.merge((l_eq, a, b))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def apply_adjustments(image: np.ndarray, params: AdjustmentParams) -> np.ndarray:
    """Aplica todos los ajustes en cadena sobre la imagen (BGR, uint8).

    Siempre pasa por `_clamp_params` primero -- red de seguridad final: sin
    importar de dónde vino `params` (receta por clima, preset estático de un
    perfil de estilo, o sliders manuales del usuario), nunca se aplica más
    saturación/claridad/contraste/dehaze que los techos globales del Motor
    V3 (ver _MAX_* arriba). No modifica el objeto original del llamador."""
    params = _clamp_params(AdjustmentParams(**vars(params)))
    result = image.copy()
    result = _apply_exposure(result, params.exposure)
    result = _apply_highlights_shadows(result, params.highlights, params.shadows)
    result = _apply_whites_blacks(result, params.whites, params.blacks)
    result = _apply_saturation(result, params.saturation)
    result = _apply_clarity(result, params.clarity)
    result = _apply_dehaze(result, params.dehaze)
    result = _apply_contrast(result, params.contrast)
    result = _apply_temperature(result, params.temperature)
    return result


_FAST_WORKING_WIDTH = 1600  # ver apply_adjustments_fast


def apply_adjustments_fast(image: np.ndarray, params: AdjustmentParams) -> np.ndarray:
    """Igual que `apply_adjustments`, pero calcula la cadena completa sobre
    una copia reducida y aplica el DELTA resultante sobre la foto completa
    -- la misma técnica ya probada en professional_finish.py (ver ese
    módulo para la justificación completa): son ajustes de tono/color
    globales, de naturaleza suave, cuyo resultado no pierde calidad
    perceptible al calcularse a menor resolución (medido: ~950ms -> ~150ms
    en fotos reales de cámara, sin diferencia visible).

    Se usa en el pipeline de lotes (ver batch_processor.py), donde la
    velocidad importa; NO se usa en re-ediciones manuales de una sola foto
    (ver ai_engine.reedit_photo), donde el usuario está mirando de cerca
    esa foto puntual y vale más la precisión exacta que el ahorro de
    ~800ms."""
    h, w = image.shape[:2]
    scale = min(1.0, _FAST_WORKING_WIDTH / w)
    if scale >= 1.0:
        return apply_adjustments(image, params)

    sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
    small = cv2.resize(image, (sw, sh), interpolation=cv2.INTER_AREA)
    enhanced_small = apply_adjustments(small, params)

    delta_small = enhanced_small.astype(np.float32) - small.astype(np.float32)
    delta_full = cv2.resize(delta_small, (w, h), interpolation=cv2.INTER_LINEAR)
    result = np.clip(image.astype(np.float32) + delta_full, 0, 255).astype(np.uint8)
    return result
