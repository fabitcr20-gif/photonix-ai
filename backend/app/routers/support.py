"""Rutas del cliente para soporte técnico: crear tickets y ver los propios."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.rate_limit import rate_limiter, reject_missing_user_agent
from app.core.security import AuthUser, get_current_user
from app.services import support_service

router = APIRouter(prefix="/support", tags=["Soporte"])


class CreateTicketRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=5000)


@router.post(
    "/tickets",
    dependencies=[Depends(reject_missing_user_agent), Depends(rate_limiter(max_requests=5, window_seconds=300))],
)
async def create_ticket(payload: CreateTicketRequest, user: AuthUser = Depends(get_current_user)):
    return support_service.create_ticket(user.id, payload.subject, payload.message)


@router.get("/tickets")
async def list_my_tickets(user: AuthUser = Depends(get_current_user)):
    return support_service.list_tickets_for_user(user.id)
