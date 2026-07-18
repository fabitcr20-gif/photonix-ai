"""
Catálogo de funciones habilitadas por plan (feature gating).
Cada plan desbloquea un subconjunto de funciones del motor de IA y de carga,
para que lo que el cliente puede hacer en la app esté en función de lo que
paga. El plan 'founder' (fundador/administrador) siempre tiene todo desbloqueado
y sin límites, de por vida.
"""
from __future__ import annotations
from typing import TypedDict, Optional


class PlanFeatures(TypedDict):
    max_batch_photos: Optional[int]  # None = ilimitado
    object_removal: bool             # placas, postes/cables (Core Feature #4b)
    watermark_multi: bool            # múltiples logos/plantillas (Fase 5 del roadmap)
    priority_processing: bool        # cola de procesamiento prioritaria


PLAN_FEATURES: dict[str, PlanFeatures] = {
    "trial": {
        "max_batch_photos": 100,
        "object_removal": True,
        "watermark_multi": True,
        "priority_processing": False,
    },
    "starter": {
        "max_batch_photos": 100,
        "object_removal": False,
        "watermark_multi": False,
        "priority_processing": False,
    },
    "pro": {
        "max_batch_photos": 500,
        "object_removal": True,
        "watermark_multi": True,
        "priority_processing": False,
    },
    "studio": {
        "max_batch_photos": None,
        "object_removal": True,
        "watermark_multi": True,
        "priority_processing": True,
    },
    "founder": {
        "max_batch_photos": None,
        "object_removal": True,
        "watermark_multi": True,
        "priority_processing": True,
    },
}

# Plan aplicado por defecto cuando no hay trial vigente ni membresía activa
# (solo se usa para calcular "qué vería el usuario si pagara", nunca para
# otorgar acceso: eso lo decide `require_active_membership`).
DEFAULT_FEATURES: PlanFeatures = PLAN_FEATURES["starter"]


def get_features(plan: Optional[str]) -> PlanFeatures:
    return PLAN_FEATURES.get(plan or "starter", DEFAULT_FEATURES)
