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
    max_batch_photos: Optional[int]       # None = ilimitado (límite por SESIÓN/lote)
    max_photos_per_month: Optional[int]   # None = ilimitado (límite ACUMULADO del mes)
    object_removal: bool             # placas, postes/cables (Core Feature #4b)
    watermark_multi: bool            # múltiples logos/plantillas (Fase 5 del roadmap)
    priority_processing: bool        # cola de procesamiento prioritaria


# Techo mensual real de fotos (Core Feature de control de costo -- cada foto
# procesada tiene un costo de cómputo de IA real, y hasta ahora NINGÚN plan
# tenía un límite acumulado por mes, solo un límite por lote individual --
# un cliente podía subir lotes ilimitados uno tras otro sin ningún freno de
# costo). Pedido explícito: solo aplica a los planes pensados para clientes
# nuevos con uso acotado (trial/starter/studio) -- Photonix Pro y el plan
# Fundador deben seguir siendo ilimitados. Los valores de abajo son
# SUGERIDOS (documentados como tal): no hay datos de costo/margen real de
# Photonix AI en este repo para calcular el número "correcto" -- ajustar
# según el costo real de cómputo por foto y el margen de cada plan.
PLAN_FEATURES: dict[str, PlanFeatures] = {
    "trial": {
        "max_batch_photos": 100,
        "max_photos_per_month": 300,   # sugerido: prueba gratuita, tope conservador anti-abuso
        "object_removal": True,
        "watermark_multi": True,
        "priority_processing": False,
    },
    "starter": {
        "max_batch_photos": 100,
        "max_photos_per_month": 500,   # sugerido: plan de entrada
        "object_removal": False,
        "watermark_multi": False,
        "priority_processing": False,
    },
    "pro": {
        "max_batch_photos": 500,
        "max_photos_per_month": None,  # Photonix Pro: ilimitado -- pedido explícito
        "object_removal": True,
        "watermark_multi": True,
        "priority_processing": False,
    },
    "studio": {
        "max_batch_photos": None,
        "max_photos_per_month": 3000,  # sugerido: alto volumen real (bodas/estudios) pero con techo
        "object_removal": True,
        "watermark_multi": True,
        "priority_processing": True,
    },
    "founder": {
        "max_batch_photos": None,
        "max_photos_per_month": None,  # fundador: ilimitado -- pedido explícito
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
