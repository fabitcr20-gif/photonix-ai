"""Modelo de dominio para membresías/suscripciones."""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

PlanId = Literal["trial", "starter", "pro", "studio", "founder"]
MembershipStatus = Literal["pending", "active", "rejected", "expired"]

# Catálogo de planes: fuente única de verdad para precios y beneficios.
PLAN_CATALOG = {
    "trial": {"name": "Prueba Gratuita", "price_crc": 0, "duration_days": 30},
    "starter": {"name": "Photonix Starter", "price_crc": 3500, "duration_days": 30},
    "pro": {"name": "Photonix Pro", "price_crc": 7000, "duration_days": 30},
    "studio": {"name": "Photonix Studio", "price_crc": 12000, "duration_days": 30},
    "founder": {"name": "Fundador (Admin)", "price_crc": 0, "duration_days": None},  # ilimitado
}


@dataclass
class Membership:
    id: str
    user_id: str
    plan: PlanId
    status: MembershipStatus
    starts_at: Optional[datetime]
    ends_at: Optional[datetime]
