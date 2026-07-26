"""
Eliminación de elementos (Object Removal) — Core Feature #4b.
Detección y borrado automático de: placas de autos, marcas/logos de terceros,
postes de luz y cables eléctricos.

IMPORTANTE (nota de arquitectura): la DETECCIÓN de cada tipo de objeto es un
problema de visión por computadora especializado. Aquí se define la interfaz
estable (`detect_*`/`_detect_*` -> lista de máscaras/bboxes) con una
implementación base funcional por heurística clásica de OpenCV, y puntos de
extensión claros para enchufar modelos entrenados sin cambiar el resto del
pipeline:
  - Placas de autos: `detect_license_plate_boxes` combina un cascade Haar
    (rápido, pero entrenado en placas rusas -- no generaliza bien a otros
    países/formatos) con `_detect_plate_text_rows` (localiza la placa por la
    FORMA de su contenido: una fila de varios caracteres agrupados, vía
    MSER -- funciona sin importar el formato/país de la placa). Reemplazar
    ambos por un detector YOLO entrenado en datasets de placas (ej. YOLOv8 +
    OCR de matrícula) para mayor precisión.
  - Logos/marcas: reemplazar `detect_logos` por matching contra un banco de
    logos conocidos (ej. embeddings CLIP + búsqueda por similitud).
  - Postes/cables: reemplazar `detect_poles_and_wires` por un modelo de
    segmentación semántica (ej. U-Net entrenado en escenas urbanas/aéreas).

Una vez detectada la máscara del objeto, `remove_objects` usa inpainting
(cv2.inpaint / cv2.INPAINT_TELEA) para "borrar" el objeto de forma creíble --
se sigue usando así para logos/postes/cables. Las placas usan
`_reconstruct_plate_region` en su lugar (ver esa función para el porqué:
`cv2.inpaint` propaga color desde el borde de la máscara hacia adentro, y el
borde de una placa suele colindar con contenido muy distinto -- luneta
oscura, parachoques -- así que termina manchando en vez de dejar una
superficie limpia y coherente con la propia placa).
"""
from __future__ import annotations
import numpy as np
import cv2

from app.services.ai.subject_segmentation import estimate_subject_mask


_PLATE_DETECT_WIDTH = 640  # cascada Haar en resolución completa (~10MP) tarda varios segundos por foto


def _detect_plate_boxes_haar(image: np.ndarray, subject_mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Candidatos a placa vía el clasificador Haar preentrenado de OpenCV
    (rápido, pero entrenado en placas rusas -- ver `_detect_plate_text_rows`
    para el detector que de verdad encuentra placas de otros países/formatos;
    este se conserva como señal adicional barata, no como la única fuente).
    Devuelve rectángulos (x0,y0,x1,y1) en resolución completa.

    El cascade Haar genérico da muchos falsos positivos en cualquier zona con
    bordes repetitivos (rejillas, difusores, parrillas) -- si se les hace
    caso, la reconstrucción borra piezas reales del auto. Para evitarlo:
    exige mucha más evidencia (`minNeighbors` alto) y descarta cualquier
    detección cuyo tamaño/proporción no sea plausible para una placa real.

    La detección (Canny + cascada Haar) corre sobre una copia reducida --
    en fotos reales de cámara/celular (~10MP) hacerlo a resolución completa
    tardaba ~5 segundos por foto (medido: es el cuello de botella dominante
    del modo "Automotriz"). Una placa sigue siendo perfectamente detectable
    a 640px de ancho; el rectángulo final se reescala de vuelta a resolución
    completa para la reconstrucción, que sí necesita el detalle real."""
    h, w = image.shape[:2]
    scale = min(1.0, _PLATE_DETECT_WIDTH / w)
    sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
    small = cv2.resize(image, (sw, sh), interpolation=cv2.INTER_AREA) if scale < 1.0 else image

    boxes: list[tuple[int, int, int, int]] = []
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    img_h, img_w = small.shape[:2]
    try:
        plate_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_russian_plate_number.xml"
        )
        plates = plate_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=12)
        for (x, y, pw, ph) in plates:
            aspect = pw / ph if ph else 0
            width_ratio = pw / img_w
            # Una placa real: proporción ancha (~2:1 a 3.5:1) y un tamaño
            # razonable respecto al ancho de la foto (ni un punto, ni medio auto).
            if not (1.8 <= aspect <= 3.5 and 0.03 <= width_ratio <= 0.15):
                continue
            # Rejillas/difusores tienen la misma proporción que una placa pero
            # muchísima más textura (huecos oscuros repetidos): una placa real
            # es una superficie casi lisa con caracteres, así que su densidad
            # de bordes y variación de brillo son mucho más bajas.
            roi_edges = edges[y:y + ph, x:x + pw]
            roi_gray = gray[y:y + ph, x:x + pw]
            if roi_edges.size == 0:
                continue
            edge_density = np.count_nonzero(roi_edges) / roi_edges.size
            if edge_density > 0.035 or float(np.std(roi_gray)) > 30:
                continue
            fx, fy = x / scale, y / scale
            fw, fh = pw / scale, ph / scale
            full_box = (int(fx), int(fy), int(fx + fw), int(fy + fh))
            if _box_on_subject(full_box, subject_mask):
                boxes.append(full_box)
    except cv2.error:
        pass  # Clasificador no disponible en este build de OpenCV; no bloquea el pipeline.
    return boxes


def _boxes_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def detect_license_plate_boxes(
    image: np.ndarray, subject_mask: np.ndarray | None = None
) -> list[tuple[int, int, int, int]]:
    """Combina las dos señales de detección de placa (Haar + bloque de
    texto por contorno, ver `_detect_plate_text_rows`), restringidas al
    vehículo detectado (ver `estimate_subject_mask`, ya usado por el acabado
    profesional de Automotriz -- se reutiliza aquí, no se reimplementa nada
    nuevo) para no confundir texto de fondo (grafiti, rótulos, placas de
    OTROS autos en la escena) con la placa del vehículo protagonista --
    confirmado con una foto real: sin esta restricción, el detector marcaba
    grafiti en una pared y un peatón como "placa". Descarta duplicados que
    se solapen -- devuelve la lista final de rectángulos a reconstruir.

    `cv2.setRNGSeed` antes de segmentar: GrabCut (dentro de
    `estimate_subject_mask`) inicializa su modelo de mezcla de gaussianas
    con el generador de números aleatorios global de OpenCV, que NO es
    determinista por defecto -- confirmado con una foto real: llamar a
    `estimate_subject_mask` 5 veces seguidas sobre la MISMA foto dio 3
    resultados distintos (incluida una vez sin converger en nada), y como
    esta función usa el rectángulo del vehículo como recorte duro para
    buscar la placa (no solo como filtro suave), esa variación cambiaba por
    completo qué placa se encontraba de una corrida a la siguiente. Fijar
    la semilla aquí (no en `subject_segmentation.py`, que no es de este
    módulo y no hace falta tocar) hace que ESTA función dé siempre el mismo
    resultado sobre la misma foto, sin afectar en nada a
    `professional_finish.py` (que sigue llamando a `estimate_subject_mask`
    con el RNG global tal como estaba)."""
    if subject_mask is None or subject_mask.shape[:2] != image.shape[:2]:
        cv2.setRNGSeed(42)
        subject_mask = estimate_subject_mask(image)
    boxes = list(_detect_plate_text_rows(image, subject_mask)) + _detect_plate_boxes_haar(image, subject_mask)
    unique: list[tuple[int, int, int, int]] = []
    for box in boxes:
        if not any(_boxes_overlap(box, existing) for existing in unique):
            unique.append(box)
    return unique


def _box_on_subject(box: tuple[int, int, int, int], subject_mask: np.ndarray, min_coverage: float = 0.35) -> bool:
    """Si GrabCut no logró converger, `estimate_subject_mask` ya devuelve
    una máscara neutra (0.5 en todo) -- en ese caso este chequeo no bloquea
    nada (0.5 > umbral en todos lados), porque no hay evidencia confiable de
    dónde está el vehículo para usarla como filtro."""
    x0, y0, x1, y1 = box
    h, w = subject_mask.shape[:2]
    region = subject_mask[max(0, y0):min(h, y1), max(0, x0):min(w, x1)]
    if region.size == 0:
        return False
    return float(np.mean(region > 0.4)) >= min_coverage


def _subject_bbox(subject_mask: np.ndarray) -> tuple[int, int, int, int]:
    """Rectángulo delimitador del vehículo detectado, con un margen pequeño
    alrededor (la placa puede estar justo en el borde de la máscara). Si
    GrabCut no logró converger (máscara neutra 0.5 en todo -- ver
    `estimate_subject_mask`) o el "sujeto" cubre casi toda la foto (máscara
    no confiable), devuelve la imagen completa: no hay recorte útil que hacer."""
    h, w = subject_mask.shape[:2]
    strong = subject_mask > 0.5
    coverage = float(np.mean(strong))
    if not np.any(strong) or coverage > 0.92:
        return (0, 0, w, h)
    ys, xs = np.where(strong)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    pad_x, pad_y = int((x1 - x0) * 0.05), int((y1 - y0) * 0.05)
    return (max(0, x0 - pad_x), max(0, y0 - pad_y), min(w, x1 + pad_x), min(h, y1 + pad_y))


def _detect_plate_text_rows(image: np.ndarray, subject_mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Localiza placas por la FORMA de su contenido (un bloque de texto
    sobre un fondo uniforme, con alto contraste LOCAL) en vez de un cascade
    Haar entrenado en un país específico -- confirmado con una foto real de
    una placa de Costa Rica claramente visible: el cascade de arriba
    (`haarcascade_russian_plate_number.xml`) da CERO detecciones incluso
    bajando `minNeighbors` a 3, porque la proporción/estilo de la placa rusa
    en la que fue entrenado no se parece a la de otros países.

    Primer intento de este detector (MSER agrupando caracteres individuales
    en "filas") se descartó tras probarlo contra la misma foto real: a la
    compresión/resolución típica de una foto de celular, los caracteres
    individuales de la placa no se separan de forma confiable como regiones
    MSER estables (se fusionan entre sí o con el marco) -- ni un solo grupo
    de >=4 caracteres se formó, aunque los bordes del texto sí eran visibles.

    Segundo intento: el mismo Canny + cierre morfológico ancho (para unir
    los caracteres de la placa en un solo contorno sólido, sin necesitar
    separarlos) -- también falló, incluso recortando ya al vehículo: hay
    suficientes bordes reales del propio auto (molduras, llanta, faros,
    ventanas) para que el cierre una TODO en un solo blob que cubre casi
    todo el recorte (confirmado: `RETR_EXTERNAL` devolvía un único contorno
    del tamaño exacto del recorte del vehículo), tragándose el contorno real
    de la placa adentro en vez de aislarlo.

    Enfoque que sí funciona: en vez de exigir que el texto forme UN
    contorno sólido y conectado (fràgil), se mide la DENSIDAD LOCAL de
    bordes con un filtro de caja (`cv2.boxFilter`, equivalente a un
    promedio móvil 2D) sobre el mapa de bordes -- el resultado es un "mapa
    de calor" continuo, no una forma binaria que pueda fusionarse con nada.
    Una placa real es, por naturaleza, la zona con la densidad de bordes
    MÁS ALTA del vehículo dentro de una ventana del tamaño de una placa
    (texto apretado en poco espacio); el resto de la carrocería, aunque
    tenga sus propios bordes, los tiene mucho más dispersos. Por eso se usa
    un umbral relativo (percentil 97 de densidad dentro del propio
    vehículo) en vez de uno fijo -- se adapta a cuánta textura tenga cada
    foto en particular, sin necesitar calibrar un número absoluto que
    funcione igual en todas las fotos. Recortar primero al rectángulo del
    vehículo (`_subject_bbox`, sobre `estimate_subject_mask` -- ya usado por
    el acabado profesional de Automotriz, no algo nuevo) además descarta
    automáticamente grafiti/rótulos de fondo del cálculo del percentil."""
    bx0, by0, bx1, by1 = _subject_bbox(subject_mask)
    crop = image[by0:by1, bx0:bx1]
    crop_subject = subject_mask[by0:by1, bx0:bx1]
    ch, cw = crop.shape[:2]
    if ch < 20 or cw < 20:
        return []

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    value_channel = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)[:, :, 2]
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    edges = cv2.Canny(enhanced, 60, 160).astype(np.float32)

    # Ventana de suavizado del tamaño de UN carácter (no de la placa entera):
    # una ventana grande (probado primero: ~11% del ancho del vehículo)
    # "esparce" cada carácter en un blob demasiado ancho/impreciso, y el
    # resultado deja de tener la forma rectangular real de la placa. Con una
    # ventana angosta el mapa de densidad conserva la forma, y el cierre
    # morfológico de abajo (kernel ancho) es lo que une los caracteres entre
    # sí -- separando las dos responsabilidades en vez de que una sola
    # ventana intente hacer ambas cosas a la vez.
    win = max(8, int(cw * 0.035))
    density = cv2.boxFilter(edges, -1, (win, win), normalize=True)

    # Restringe tanto la BÚSQUEDA como el cálculo del percentil a la mitad
    # inferior del vehículo, sobre píxeles que de verdad son del auto (no el
    # rectángulo delimitador completo, que en fotos con perspectiva incluye
    # fondo real -- confirmado con una foto real: un rótulo de la calle caía
    # dentro del rectángulo del vehículo y su densidad de bordes dominaba el
    # percentil). Una placa NUNCA está en la mitad superior (techo/vidrios) --
    # descartar esa mitad de entrada también evita que el vidrio trasero o
    # el limpiaparabrisas (con reflejos de alto contraste, medido: más denso
    # que la propia placa) le ganen el percentil a la placa real.
    lower_half = np.zeros((ch, cw), dtype=bool)
    lower_half[int(ch * 0.45):, :] = True
    valid = (crop_subject > 0.4) & lower_half
    if not np.any(valid):
        valid = lower_half  # sin máscara confiable: al menos evita la mitad superior
    density_search = np.where(valid, density, 0.0)

    # Umbral ADAPTATIVO: empieza exigiendo el percentil más alto (más
    # selectivo, evita falsos positivos en la mayoría de fotos) y solo baja
    # el umbral si nada calificó como candidato plausible -- una placa real
    # no siempre es la zona de MÁXIMA densidad del vehículo (medido en una
    # foto real: el limpiaparabrisas/vidrio trasero a veces la supera), pero
    # sigue estando entre las más densas, así que un escaneo descendente la
    # encuentra sin tener que adivinar un solo percentil fijo que funcione
    # igual en todas las fotos.
    plate_boxes: list[tuple[int, int, int, int]] = []
    for percentile in (97, 94, 90, 85):
        threshold = max(float(np.percentile(density[valid], percentile)), 18.0)
        _, binary = cv2.threshold(density_search, threshold, 255, cv2.THRESH_BINARY)
        # Kernel horizontal ancho: une los caracteres de la misma línea de
        # texto (la ventana de densidad de arriba ya NO hace este trabajo).
        binary = cv2.morphologyEx(binary.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 25), np.uint8))
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            if bw < 15 or bh < 6:
                continue
            aspect = bw / bh
            width_ratio = bw / cw
            # Proporción y tamaño plausibles para una placa real (no una
            # palabra cualquiera de un cartel/aviso, ni un panel de grafiti).
            # Nota: el propio cierre a veces solo une PARTE de los caracteres
            # (ej. "510" sin "SYN"), así que el aspecto de un candidato real
            # puede salir más cuadrado que el de la placa completa -- por eso
            # el mínimo es más permisivo que el de una placa ya completa, y
            # el relleno de abajo compensa expandiendo generosamente.
            if not (1.1 <= aspect <= 6.5) or not (0.015 <= width_ratio <= 0.45):
                continue
            roi_gray = gray[y:y + bh, x:x + bw]
            if roi_gray.size == 0:
                continue
            std = float(np.std(roi_gray))
            # Placa real: contraste interno genuino (los caracteres son
            # visiblemente más oscuros/claros que el fondo) -- descarta
            # zonas que el umbral relativo aceptó pero son casi lisas.
            if std < 12:
                continue
            # Placa real: fondo claro (blanco/amarillo -- el caso típico,
            # incluida Costa Rica). Descarta candidatos oscuros que igual
            # tienen bordes densos -- confirmado con una foto real: el
            # farol trasero (cromo + lente rojo) y una sombra del
            # parachoques pasaban los filtros de arriba pero son
            # notablemente más oscuros que la propia placa (130/85/112 de
            # brillo medio contra 162 de la placa real).
            if float(np.mean(value_channel[y:y + bh, x:x + bw])) < 140:
                continue

            # Techo de seguridad sobre la altura CRUDA detectada, antes de
            # rellenar/expandir -- sin esto, un contorno alto por error (ej.
            # se fusionó con algo del propio auto) se multiplica por el
            # relleno y la corrección de proporción de abajo, y termina
            # cubriendo un pedazo enorme de la carrocería en vez de solo la
            # placa (medido: con un contorno de altura 80 -- ya el doble de
            # una fila de caracteres real --, la caja final terminó
            # cubriendo casi medio auto). Una fila de caracteres real mide
            # 3-6% del ancho del vehículo; se acota ahí antes de continuar.
            bh_capped = min(bh, max(6, int(cw * 0.06)))
            if bh_capped < bh:
                y = y + (bh - bh_capped) // 2
                bh = bh_capped

            # Pedido explícito (con foto de referencia): "COSTA RICA" y
            # "CENTROAMERICA" NO son información identificable del vehículo
            # -- son el mismo texto en TODAS las placas del país, como el
            # marco/diseño de la placa -- así que deben quedar visibles. Solo
            # el CÓDIGO alfanumérico (el número de placa real, ej. "SYN-510")
            # debe borrarse. Por eso ya NO se expande la caja a la altura de
            # la placa completa (eso de paso explica por qué el relleno se
            # veía gris/azulado en vez de blanco limpio: al meterse en el
            # marco oscuro/emblema de arriba, la mediana de color usada para
            # rellenar se sesgaba hacia gris) -- se queda ceñida a la fila de
            # números, con un margen modesto solo para no dejar un borde de
            # carácter sin cubrir.
            plate_w = bh * 5.0  # una fila de 6-7 caracteres es bastante más ancha que alta
            cx = x + bw / 2.0
            cy = y + bh / 2.0

            pad_y = bh * 0.25
            ex0 = max(0, int(cx - plate_w / 2))
            ex1 = min(cw, int(cx + plate_w / 2))
            ey0 = max(0, int(cy - bh / 2 - pad_y))
            ey1 = min(ch, int(cy + bh / 2 + pad_y))

            # Techo de seguridad final, sin importar cómo se llegó hasta
            # aquí: dado que `bh` ya viene acotado arriba a ~6% del ancho del
            # vehículo, el código de una placa real derivado de esa altura
            # nunca debería superar ~30% del ancho ni ~12% del alto -- si el
            # resultado lo supera de todos modos (ej. `bw` original venía
            # inflado), se descarta en vez de arriesgarse a reconstruir un
            # pedazo grande de carrocería real (mejor no tocar la placa en un
            # caso raro que borrar de más en la mayoría).
            if (ex1 - ex0) > cw * 0.30 or (ey1 - ey0) > ch * 0.12:
                continue

            full_box = (bx0 + ex0, by0 + ey0, bx0 + ex1, by0 + ey1)
            if _box_on_subject(full_box, subject_mask):
                plate_boxes.append(full_box)

        if plate_boxes:
            break

    return plate_boxes


def _reconstruct_plate_region(image: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    """Reemplaza el recorte de la placa por una superficie limpia y
    coherente con su PROPIO color/textura -- no con el contenido vecino de
    la escena. Pedido explícito: nada de desenfoque/oscurecido/pixelado, y
    "coherente con el área de la placa", no con el parachoques o la luneta
    de al lado. Por eso NO se usa `cv2.inpaint` aquí (que sí se sigue usando
    para logos/postes/cables, sin cambios): TELEA propaga color desde el
    borde de la máscara hacia adentro, y el borde de una placa colinda con
    contenido completamente distinto (luneta oscura, parachoques) -- medido
    en una foto real: arrastra un manchón oscuro desde la luneta hacia
    dentro del hueco de la placa en vez de dejarla limpia.

    En cambio: la MEDIANA de color de la propia placa ya excluye la
    influencia de los caracteres (son la minoría de píxeles frente al fondo
    liso), así que da el tono real del fondo de la placa sin necesidad de
    saber exactamente dónde está cada carácter. Se le suma de vuelta una
    variación de brillo sutil (atenuada) tomada de la textura original de la
    placa, para que la superficie final se sienta como material real y no
    como un rectángulo plano "photoshopeado"."""
    x0, y0, x1, y1 = box
    patch = image[y0:y1, x0:x1]
    if patch.size == 0:
        return image

    gray_patch = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY).astype(np.float32)

    # El fondo real de una placa (blanco/amarillo) es notablemente más
    # CLARO que sus propios caracteres (azules/negros) -- una mediana simple
    # sobre TODO el recorte todavía se deja arrastrar por esos caracteres si
    # ocupan una fracción no trivial del área (medido: dejaba un relleno
    # gris-azulado en vez de blanco limpio). Se promedia solo el 40% de
    # píxeles más claros del recorte (el fondo real, casi por definición la
    # mayoría) para estimar el color base, ignorando los caracteres oscuros
    # sin necesitar saber exactamente dónde están.
    brightness_threshold = float(np.percentile(gray_patch, 60))
    bg_pixels = patch[gray_patch >= brightness_threshold]
    if bg_pixels.size > 0:
        base_color = bg_pixels.reshape(-1, 3).mean(axis=0).astype(np.float32)
    else:
        base_color = np.median(patch.reshape(-1, 3), axis=0).astype(np.float32)

    variation = np.clip(gray_patch - np.median(gray_patch), -15, 15) * 0.25
    filled = np.clip(base_color[None, None, :] + variation[:, :, None], 0, 255).astype(np.uint8)

    # Difumina el propio recorte reconstruido (no la imagen de alrededor):
    # elimina cualquier resto de borde de carácter que la mediana no haya
    # promediado del todo, sin tocar nada fuera del rectángulo de la placa.
    filled = cv2.GaussianBlur(filled, (0, 0), sigmaX=max(1.0, patch.shape[1] * 0.02))

    # Plumeado suave en el borde del rectángulo (no un corte duro) para que
    # la transición con la carrocería/parachoques de alrededor sea invisible:
    # un rectángulo blanco relleno, encogido `feather` px desde cada borde,
    # difuminado -- 1.0 en el centro, cae suave a 0.0 justo en el borde.
    ph, pw = y1 - y0, x1 - x0
    feather = max(3, int(min(pw, ph) * 0.06))
    alpha = np.zeros((ph, pw), dtype=np.float32)
    inset_x1, inset_y1 = max(0, pw - feather), max(0, ph - feather)
    if inset_x1 > feather and inset_y1 > feather:
        cv2.rectangle(alpha, (feather, feather), (inset_x1, inset_y1), 1.0, thickness=-1)
        alpha = cv2.GaussianBlur(alpha, (0, 0), sigmaX=feather * 0.6)
    else:
        alpha[:] = 1.0  # rectángulo demasiado pequeño para plumear -- se rellena entero

    region = image[y0:y1, x0:x1].astype(np.float32)
    blended = region * (1 - alpha[:, :, None]) + filled.astype(np.float32) * alpha[:, :, None]

    result = image.copy()
    result[y0:y1, x0:x1] = np.clip(blended, 0, 255).astype(np.uint8)
    return result


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
    plate_boxes: list[tuple[int, int, int, int]] | None = None,
) -> np.ndarray:
    """Pipeline de conveniencia: detecta y elimina en un solo paso los
    elementos indeseados seleccionados por el usuario.

    `plate_boxes`: rectángulos de placa YA detectados, si el llamador ya los
    tiene (ver batch_processor.py). Importante: la detección de placa se
    calibró y probó corriendo `detect_license_plate_boxes` sobre la foto
    recién leída/con corrección de perspectiva, ANTES de los ajustes de
    tono/color y la limpieza de ruido -- confirmado con una foto real que
    esos ajustes cambian lo suficiente el resultado de GrabCut (usado tanto
    aquí como en el acabado profesional) como para que la MISMA foto dé una
    máscara de vehículo distinta antes y después de ajustarla, y con eso una
    detección de placa distinta (en un caso real, ninguna). Por eso esta
    función ya NO detecta la placa ella misma sobre `image` (que en el
    pipeline real ya llega ajustada) -- si el llamador no pasa `plate_boxes`
    explícitamente, se detecta aquí mismo como red de seguridad (ej. otro
    llamador que no siga este orden), pero lo ideal es detectar temprano y
    pasar el resultado.

    Placas: recorrido aparte, con `_reconstruct_plate_region` en vez del
    `remove_objects`/inpainting genérico de abajo -- pedido explícito
    "eliminación real... conservando apariencia natural y coherente con el
    área de la placa", y `cv2.inpaint` propaga color desde el borde de la
    máscara hacia adentro, que para una placa suele ser la luneta oscura o
    el parachoques de al lado, no un tono plausible de placa (confirmado con
    una foto real: dejaba un manchón oscuro en vez de una placa limpia).
    Logos/postes/cables SIGUEN el camino de siempre (mask + `remove_objects`),
    sin ningún cambio."""
    result = image
    if remove_plates:
        boxes = plate_boxes if plate_boxes is not None else detect_license_plate_boxes(result)
        for box in boxes:
            result = _reconstruct_plate_region(result, box)

    masks = []
    if remove_logos:
        masks.append(detect_logos(result, reference_logos))
    if remove_poles_wires:
        masks.append(detect_poles_and_wires(result))

    if masks:
        final_mask = combine_masks(*masks)
        result = remove_objects(result, final_mask)

    return result
