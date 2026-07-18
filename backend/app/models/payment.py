"""Modelo de dominio para comprobantes de pago SINPE Móvil."""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

PaymentStatus = Literal["pending", "approved", "rejected"]


@dataclass
class SinpePayment:
    id: str
    user_id: str
    plan: str
    receipt_image_url: str
    status: PaymentStatus
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime
