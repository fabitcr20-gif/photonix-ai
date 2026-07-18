"""Esquemas Pydantic para el perfil de usuario."""
from pydantic import BaseModel
from typing import Optional


class PlanFeaturesResponse(BaseModel):
    max_batch_photos: Optional[int]
    object_removal: bool
    watermark_multi: bool
    priority_processing: bool


class ProfileResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    role: str
    accepted_terms: bool
    trial_ends_at: Optional[str]
    membership_plan: Optional[str] = None
    membership_status: Optional[str] = None
    # Plan realmente vigente ahora mismo (considera trial y expiración) y las
    # funciones que desbloquea, para que el frontend habilite/deshabilite
    # opciones del motor de IA según el plan del cliente.
    active_plan: Optional[str] = None
    plan_features: Optional[PlanFeaturesResponse] = None


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
