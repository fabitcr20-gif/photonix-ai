"""Esquemas Pydantic (request/response) para autenticación."""
from __future__ import annotations
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    accepted_terms: bool = Field(
        ..., description="Debe ser True: checkbox obligatorio de Términos y Condiciones"
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OAuthCallbackRequest(BaseModel):
    """Usado tras el redirect de Google/Apple OAuth manejado por Supabase Auth."""
    provider: str  # 'google' | 'apple'
    access_token: str
    accepted_terms: bool = True


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    user_id: str
    email: str
    role: str
    trial_ends_at: str | None = None
