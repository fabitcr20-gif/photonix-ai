"""
Integración con Google Drive: conecta la cuenta de Drive del cliente vía
OAuth 2.0 y sube ahí las fotos de una sesión (en una carpeta con el nombre
del proyecto). Implementado con llamadas HTTP directas (via httpx) a las APIs
de Google, sin depender del SDK oficial (más pesado), ya que solo se necesitan
tres operaciones: intercambiar el código por tokens, refrescar el access token
y subir archivos.

Requiere un proyecto en Google Cloud Console con la Drive API habilitada y
credenciales OAuth "Web application" — ver README.md para los pasos exactos.
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.database import get_supabase_admin

settings = get_settings()

AUTH_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"


def build_authorization_url(state: str) -> str:
    """URL a la que se redirige al usuario para que autorice el acceso a su
    Google Drive. `drive.file` limita el acceso solo a los archivos que la
    app crea (no a todo el Drive del usuario), lo cual es más seguro y más
    fácil de aprobar en la pantalla de consentimiento de Google."""
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": DRIVE_SCOPE,
        "access_type": "offline",  # necesario para recibir refresh_token
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_BASE_URL}?{urlencode(params)}"


def _store_tokens(user_id: str, token_data: dict) -> None:
    db = get_supabase_admin()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=token_data.get("expires_in", 3600))

    row = {
        "user_id": user_id,
        "access_token": token_data["access_token"],
        "expires_at": expires_at.isoformat(),
    }
    # Google solo devuelve refresh_token la PRIMERA vez que se autoriza; si no
    # viene (reconexión posterior), conservamos el que ya teníamos guardado.
    if token_data.get("refresh_token"):
        row["refresh_token"] = token_data["refresh_token"]

    db.table("google_drive_connections").upsert(row, on_conflict="user_id").execute()


def exchange_code_for_tokens(user_id: str, code: str) -> None:
    """Intercambia el código de autorización de Google por access/refresh
    tokens y los guarda asociados al usuario."""
    response = httpx.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Google rechazó la autorización: {response.text}",
        )
    _store_tokens(user_id, response.json())


def _refresh_access_token(user_id: str, refresh_token: str) -> str:
    response = httpx.post(
        TOKEN_URL,
        data={
            "refresh_token": refresh_token,
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="No se pudo renovar el acceso a Google Drive. Vuelve a conectar tu cuenta.",
        )
    token_data = response.json()
    _store_tokens(user_id, token_data)
    return token_data["access_token"]


def get_valid_access_token(user_id: str) -> str:
    """Devuelve un access_token vigente para el usuario, renovándolo con el
    refresh_token si ya expiró. Lanza 400 si el usuario no ha conectado Drive."""
    db = get_supabase_admin()
    connection = (
        db.table("google_drive_connections")
        .select("access_token, refresh_token, expires_at")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not connection.data:
        raise HTTPException(
            status_code=400,
            detail="Todavía no has conectado tu cuenta de Google Drive.",
        )

    row = connection.data[0]
    expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
    if expires_at > datetime.now(timezone.utc) + timedelta(seconds=30):
        return row["access_token"]

    return _refresh_access_token(user_id, row["refresh_token"])


def is_connected(user_id: str) -> bool:
    db = get_supabase_admin()
    result = (
        db.table("google_drive_connections").select("user_id").eq("user_id", user_id).limit(1).execute()
    )
    return bool(result.data)


def disconnect(user_id: str) -> None:
    db = get_supabase_admin()
    db.table("google_drive_connections").delete().eq("user_id", user_id).execute()


def _create_folder(access_token: str, folder_name: str) -> str:
    response = httpx.post(
        FILES_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        json={"name": folder_name, "mimeType": "application/vnd.google-apps.folder"},
        timeout=30,
    )
    if response.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"No se pudo crear la carpeta en Drive: {response.text}")
    return response.json()["id"]


def _upload_file(access_token: str, folder_id: str, filename: str, content: bytes, mime_type: str) -> None:
    metadata = {"name": filename, "parents": [folder_id]}
    files = {
        "metadata": (None, json.dumps(metadata), "application/json"),
        "file": (filename, content, mime_type),
    }
    response = httpx.post(
        f"{UPLOAD_URL}?uploadType=multipart",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files,
        timeout=120,
    )
    if response.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"No se pudo subir '{filename}' a Drive: {response.text}")


def upload_project_photos(user_id: str, project_name: str, photos: list[tuple[str, bytes]]) -> str:
    """Crea una carpeta con el nombre del proyecto en el Drive del usuario y
    sube ahí cada foto. `photos` es una lista de (nombre_archivo, contenido).
    Devuelve el link web de la carpeta creada."""
    access_token = get_valid_access_token(user_id)
    folder_id = _create_folder(access_token, project_name)

    for filename, content in photos:
        mime_type = "image/jpeg"
        if filename.lower().endswith(".png"):
            mime_type = "image/png"
        _upload_file(access_token, folder_id, filename, content, mime_type)

    return f"https://drive.google.com/drive/folders/{folder_id}"
