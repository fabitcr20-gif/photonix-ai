"""Rutas de gestión de perfil de usuario."""
from fastapi import APIRouter, Depends
from app.core.security import AuthUser, get_current_user
from app.database import get_supabase_admin
from app.schemas.user import ProfileResponse, ProfileUpdateRequest

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.patch("/me", response_model=ProfileResponse)
async def update_profile(
    payload: ProfileUpdateRequest, user: AuthUser = Depends(get_current_user)
):
    db = get_supabase_admin()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if updates:
        db.table("profiles").update(updates).eq("id", user.id).execute()
    profile = db.table("profiles").select("*").eq("id", user.id).single().execute()
    return ProfileResponse(**profile.data)
