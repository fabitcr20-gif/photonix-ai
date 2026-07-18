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
Esquema de base de datos sugerido (Supabase / Postgres). Crear vía SQL editor
de Supabase o migraciones (alembic si se usa Postgres directo):

-- Tabla de perfiles de usuario (extiende auth.users de Supabase)
create table public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    full_name text,
    email text unique not null,
    role text not null default 'client',              -- 'admin' | 'client'
    accepted_terms boolean not null default false,
    trial_ends_at timestamptz,                          -- fin de prueba gratuita (30 días)
    created_at timestamptz not null default now()
);

-- Tabla de membresías / suscripciones
create table public.memberships (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references public.profiles(id) on delete cascade,
    plan text not null,                                  -- 'trial' | 'starter' | 'pro' | 'studio' | 'founder'
    status text not null default 'pending',              -- 'pending' | 'active' | 'rejected' | 'expired'
    starts_at timestamptz,
    ends_at timestamptz,
    created_at timestamptz not null default now()
);

-- Tabla de comprobantes de pago SINPE Móvil
create table public.sinpe_payments (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references public.profiles(id) on delete cascade,
    plan text not null,
    receipt_image_url text not null,
    status text not null default 'pending',              -- 'pending' | 'approved' | 'rejected'
    reviewed_by uuid references public.profiles(id),
    reviewed_at timestamptz,
    created_at timestamptz not null default now()
);

-- Tabla de proyectos/sesiones fotográficas
create table public.projects (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references public.profiles(id) on delete cascade,
    name text not null,
    session_type text,                                   -- boda, retrato, producto, etc.
    status text not null default 'processing',
    processed_count int not null default 0,              -- fotos ya editadas por la IA
    total_count int not null default 0,                  -- total de fotos a editar (barra de progreso)
    created_at timestamptz not null default now()
);

-- Tabla de fotos por proyecto (para saber qué archivos exportar en ZIP,
-- procesar con IA, etc.)
create table public.project_photos (
    id uuid primary key default gen_random_uuid(),
    project_id uuid references public.projects(id) on delete cascade,
    original_url text not null,
    created_at timestamptz not null default now()
);

-- Tabla de watermarks guardados por usuario (un único config por usuario:
-- user_id es unique para que el "upsert on_conflict=user_id" funcione)
create table public.watermarks (
    id uuid primary key default gen_random_uuid(),
    user_id uuid unique references public.profiles(id) on delete cascade,
    logo_url text not null,
    position text not null default 'south_east',          -- N,S,E,O,center,custom
    pos_x int,
    pos_y int,
    opacity float not null default 0.8,
    scale float not null default 0.2,
    rotation float not null default 0,          -- grados, sentido horario
    created_at timestamptz not null default now()
);

-- Conexión OAuth de Google Drive por usuario (un usuario = una cuenta de
-- Drive conectada; refresh_token permite renovar el acceso sin pedirle a el
-- usuario que vuelva a autorizar cada vez).
create table public.google_drive_connections (
    user_id uuid primary key references public.profiles(id) on delete cascade,
    access_token text not null,
    refresh_token text not null,
    expires_at timestamptz not null,
    created_at timestamptz not null default now()
);
"""
