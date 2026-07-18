"""
Catálogo de Perfiles de Estilo IA (Fase 3 del Roadmap Maestro: "Perfiles de
Edición"). Cada perfil traduce el tipo de sesión fotográfica a un preset real
de `AdjustmentParams` — no es solo una etiqueta visual: al elegir un perfil en
el frontend, estos valores se envían como `custom_adjustments` al motor de IA
(ver batch_processor.py) y SÍ cambian el resultado de la edición.

El perfil 'automatico' es especial: no trae `params`, así el motor sigue
usando el análisis de entorno por foto (hora/clima/luz) como hasta ahora.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class StyleProfile:
    id: str
    label: str
    emoji: str
    description: str
    estimated_seconds_per_photo: int
    improvement_level: str  # 'adaptativo' | 'sutil' | 'moderado' | 'alto'
    params: Optional[dict] = None  # campos de AdjustmentParams a aplicar
    suggest_remove_plates: bool = False
    suggest_remove_poles_wires: bool = False


STYLE_PROFILES: list[StyleProfile] = [
    StyleProfile(
        id="automatico",
        label="Automático IA",
        emoji="✨",
        description="La IA decide el mejor ajuste según la hora, el clima y la luz de cada foto.",
        estimated_seconds_per_photo=3,
        improvement_level="adaptativo",
        params=None,
    ),
    StyleProfile(
        id="retrato",
        label="Retrato",
        emoji="👤",
        description="Piel suave, tonos cálidos y luces levantadas para resaltar al sujeto.",
        estimated_seconds_per_photo=3,
        improvement_level="moderado",
        params={"exposure": 0.05, "highlights": -0.1, "shadows": 0.15, "clarity": 0.1, "saturation": 0.05, "temperature": 0.1, "contrast": 0.05},
    ),
    StyleProfile(
        id="automotriz",
        label="Automotriz",
        emoji="🚗",
        description="Colores vibrantes, alto contraste y máxima nitidez para carrocerías y detalles.",
        estimated_seconds_per_photo=4,
        improvement_level="alto",
        params={"clarity": 0.35, "contrast": 0.2, "saturation": 0.25, "dehaze": 0.1, "shadows": 0.1},
        suggest_remove_plates=True,
    ),
    StyleProfile(
        id="paisaje",
        label="Paisaje",
        emoji="🏔",
        description="Desvanece la neblina y realza cielo, texturas y profundidad.",
        estimated_seconds_per_photo=4,
        improvement_level="alto",
        params={"dehaze": 0.25, "clarity": 0.3, "saturation": 0.15, "contrast": 0.15},
    ),
    StyleProfile(
        id="arquitectura",
        label="Arquitectura",
        emoji="🏠",
        description="Líneas limpias, blancos puros y contraste controlado para interiores y fachadas.",
        estimated_seconds_per_photo=4,
        improvement_level="moderado",
        params={"contrast": 0.15, "whites": 0.1, "clarity": 0.2, "temperature": -0.05},
        suggest_remove_poles_wires=True,
    ),
    StyleProfile(
        id="food",
        label="Food",
        emoji="🍔",
        description="Colores apetitosos, cálidos y con buen brillo para fotografía gastronómica.",
        estimated_seconds_per_photo=3,
        improvement_level="moderado",
        params={"exposure": 0.1, "saturation": 0.2, "temperature": 0.15, "clarity": 0.15, "contrast": 0.1},
    ),
    StyleProfile(
        id="wedding",
        label="Wedding",
        emoji="💍",
        description="Look suave y romántico, con sombras levantadas y tonos cálidos.",
        estimated_seconds_per_photo=3,
        improvement_level="sutil",
        params={"exposure": 0.05, "shadows": 0.2, "highlights": -0.15, "saturation": 0.05, "temperature": 0.08, "contrast": -0.05},
    ),
    StyleProfile(
        id="mascotas",
        label="Mascotas",
        emoji="🐶",
        description="Realza el pelaje y la mirada, con contraste y nitidez equilibrados.",
        estimated_seconds_per_photo=3,
        improvement_level="moderado",
        params={"clarity": 0.25, "contrast": 0.1, "saturation": 0.1, "shadows": 0.1},
    ),
    StyleProfile(
        id="producto",
        label="Producto",
        emoji="📦",
        description="Blancos puros y máximo detalle para catálogos y e-commerce.",
        estimated_seconds_per_photo=3,
        improvement_level="moderado",
        params={"whites": 0.15, "blacks": -0.05, "clarity": 0.2, "contrast": 0.1, "temperature": -0.05},
    ),
    StyleProfile(
        id="nocturna",
        label="Nocturna",
        emoji="🌃",
        description="Levanta sombras y reduce ruido en tomas nocturnas o de poca luz.",
        estimated_seconds_per_photo=5,
        improvement_level="alto",
        params={"shadows": 0.4, "exposure": 0.15, "dehaze": 0.2, "clarity": 0.15, "saturation": 0.1},
    ),
    StyleProfile(
        id="drone",
        label="Drone",
        emoji="🚁",
        description="Corrige la neblina atmosférica típica de tomas aéreas y realza el contraste.",
        estimated_seconds_per_photo=4,
        improvement_level="alto",
        params={"dehaze": 0.35, "clarity": 0.25, "contrast": 0.15, "saturation": 0.15},
    ),
]

_BY_ID = {p.id: p for p in STYLE_PROFILES}


def get_style_profile(profile_id: str) -> Optional[StyleProfile]:
    return _BY_ID.get(profile_id)


def list_style_profiles_public() -> list[dict]:
    """Catálogo serializable para exponer en la API (frontend: tarjetas de perfil)."""
    return [asdict(p) for p in STYLE_PROFILES]
