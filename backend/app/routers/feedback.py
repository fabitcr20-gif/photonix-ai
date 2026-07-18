"""Rutas del cliente para dejar retroalimentación tras una sesión editada."""
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.rate_limit import rate_limiter, reject_missing_user_agent
from app.core.security import AuthUser, get_current_user
from app.services import feedback_service

router = APIRouter(prefix="/feedback", tags=["Retroalimentación"])


class CreateFeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=2000)
    project_id: Optional[str] = None


@router.post(
    "",
    dependencies=[Depends(reject_missing_user_agent), Depends(rate_limiter(max_requests=10, window_seconds=300))],
)
async def submit_feedback(payload: CreateFeedbackRequest, user: AuthUser = Depends(get_current_user)):
    return feedback_service.create_feedback(user.id, payload.rating, payload.comment, payload.project_id)
