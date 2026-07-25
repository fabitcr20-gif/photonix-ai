"""
Cliente de Supabase (Auth + Postgres + Storage).
Se exponen dos clientes:
  - supabase_public: usa la ANON KEY, respeta Row Level Security (RLS). Úsalo
    para operaciones en nombre del usuario autenticado.
  - supabase_admin: usa la SERVICE ROLE KEY, ignora RLS. Úsalo SOLO en rutas
    de administrador o procesos internos del servidor (nunca se expone al cliente).
"""
from functools import lru_cache
from supabase import create_client, Client
from app.config import get_settings

settings = get_settings()


@lru_cache
def get_supabase_public() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


@lru_cache
def get_supabase_admin() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


"""
El esquema de base de datos (Supabase / Postgres) vive en sql/schema.sql
(fuente de verdad única -- ver sql/README.md para la convención de cómo
versionar cambios de esquema nuevos). Antes vivía duplicado como comentario
aquí mismo, lo que llevó a que se quedara desactualizado silenciosamente
(faltaban columnas y tablas que el código ya usaba en producción, ej.
projects.processing_started_at/processing_completed_at y las tablas
feedback/support_tickets) -- un solo archivo evita que eso vuelva a pasar."""
