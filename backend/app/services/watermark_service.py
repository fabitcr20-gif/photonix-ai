"""
Módulo de Marca de Agua (Watermark).
Permite componer un logo PNG transparente sobre cada foto procesada, con
posicionamiento por punto cardinal (Norte, Sur, Este, Oeste, Centro) o por
coordenadas X/Y personalizadas (arrastradas libremente en la vista previa del
frontend), además de opacidad y escala configurables. Implementado con Pillow
(maneja canal alpha de forma nativa y sencilla).
"""
from dataclasses import dataclass
from typing import Literal, Optional
from PIL import Image

Position = Literal["north", "south", "east", "west", "center", "custom"]


@dataclass
class WatermarkConfig:
    position: Position = "south"
    opacity: float = 0.8       # 0.0 (invisible) a 1.0 (totalmente opaco)
    scale: float = 0.18        # ancho del logo relativo al ancho de la foto (0-1)
    margin_px: int = 24        # margen respecto al borde cuando no es 'custom'
    # Posición del CENTRO del logo cuando position == 'custom', como
    # porcentaje (0-100) del ancho/alto de la foto — no píxeles absolutos, así
    # la posición que el usuario arrastra en la vista previa se ve igual sin
    # importar el tamaño real de cada foto que se procese después.
    custom_x: Optional[float] = None
    custom_y: Optional[float] = None
    rotation: float = 0.0      # grados, sentido horario


def _resize_logo(logo: Image.Image, target_width: int) -> Image.Image:
    ratio = target_width / logo.width
    target_height = int(logo.height * ratio)
    return logo.resize((max(1, target_width), max(1, target_height)), Image.LANCZOS)


def _apply_opacity(logo: Image.Image, opacity: float) -> Image.Image:
    if logo.mode != "RGBA":
        logo = logo.convert("RGBA")
    alpha = logo.split()[3].point(lambda p: int(p * opacity))
    logo.putalpha(alpha)
    return logo


def _compute_position(base_size: tuple[int, int], logo_size: tuple[int, int], config: WatermarkConfig) -> tuple[int, int]:
    bw, bh = base_size
    lw, lh = logo_size
    m = config.margin_px

    positions = {
        "north": ((bw - lw) // 2, m),
        "south": ((bw - lw) // 2, bh - lh - m),
        "east": (bw - lw - m, (bh - lh) // 2),
        "west": (m, (bh - lh) // 2),
        "center": ((bw - lw) // 2, (bh - lh) // 2),
    }

    if config.position == "custom":
        # custom_x/custom_y son el CENTRO del logo como % del ancho/alto;
        # se convierten a la esquina superior izquierda que espera Pillow.
        pct_x = config.custom_x if config.custom_x is not None else 50.0
        pct_y = config.custom_y if config.custom_y is not None else 50.0
        x = int(bw * (pct_x / 100)) - lw // 2
        y = int(bh * (pct_y / 100)) - lh // 2
        x = max(0, min(x, bw - lw))
        y = max(0, min(y, bh - lh))
        return x, y

    return positions[config.position]


def apply_watermark(base_image_path: str, logo_png_path: str, config: WatermarkConfig, output_path: str) -> str:
    """Compone el logo transparente sobre la foto base y guarda el resultado."""
    base = Image.open(base_image_path).convert("RGBA")
    logo = Image.open(logo_png_path).convert("RGBA")

    target_width = int(base.width * config.scale)
    logo = _resize_logo(logo, target_width)
    logo = _apply_opacity(logo, config.opacity)
    if config.rotation:
        # expand=True agranda el lienzo para no recortar las esquinas al girar.
        logo = logo.rotate(-config.rotation, expand=True, resample=Image.BICUBIC)

    position = _compute_position(base.size, logo.size, config)

    composed = base.copy()
    composed.alpha_composite(logo, dest=position)
    composed.convert("RGB").save(output_path, quality=95)
    return output_path


def apply_watermark_batch(image_paths: list[str], logo_png_path: str, config: WatermarkConfig, output_dir: str) -> list[str]:
    """Aplica la misma marca de agua a una lista de fotos (uso típico: al
    final del procesamiento por lotes de una sesión completa)."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    outputs = []
    for path in image_paths:
        filename = os.path.basename(path)
        output_path = os.path.join(output_dir, filename)
        outputs.append(apply_watermark(path, logo_png_path, config, output_path))
    return outputs
