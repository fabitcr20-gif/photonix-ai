"""Esquemas Pydantic para pagos SINPE y membresías."""
from pydantic import BaseModel
from typing import Optional, Literal


class SinpePaymentCreateResponse(BaseModel):
    id: str
    plan: str
    status: str
    receipt_image_url: str
    created_at: str


class SinpePaymentReviewRequest(BaseModel):
    action: Literal["approve", "reject"]
    admin_note: Optional[str] = None


class SinpePaymentAdminView(BaseModel):
    id: str
    user_id: str
    user_email: Optional[str]
    plan: str
    receipt_image_url: str
    status: str
    created_at: str


class PlanInfo(BaseModel):
    id: str
    name: str
    price_crc: int
    duration_days: Optional[int]


class SinpePaymentHistoryItem(BaseModel):
    id: str
    plan: str
    status: str
    created_at: str
    reviewed_at: Optional[str]
