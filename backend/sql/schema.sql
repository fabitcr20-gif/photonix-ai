-- Photonix AI — Esquema base de datos (Supabase / Postgres)
--
-- Este archivo es la fuente de verdad del esquema, reconstruida a partir del
-- uso REAL en el código (cada .table(...)/.select(...)/.insert(...)/.update(...)
-- en backend/app/), no solo de lo que alguna vez se documentó. Hasta ahora
-- el esquema vivía SOLO como un comentario en app/database.py que ya estaba
-- desactualizado -- por ejemplo, projects.processing_started_at/
-- processing_completed_at y las tablas feedback/support_tickets ya las usa
-- el código en producción pero no aparecían documentadas en ningún lado.
--
-- Este proyecto no usa un framework de migraciones (Alembic, etc.) -- los
-- cambios de esquema se corren manualmente en el SQL Editor de Supabase.
-- Convención a partir de ahora: este archivo es el esquema base ya aplicado;
-- CUALQUIER cambio nuevo va en un archivo nuevo dentro de sql/migrations/
-- (ej. 0001_add_x_column.sql), nunca editando este archivo directamente --
-- así queda un historial real y reproducible en el repo, en vez de SQL que
-- se corrió una vez a mano y se perdió.
--
-- Para reconstruir un ambiente desde cero: correr este archivo completo en
-- el SQL Editor de Supabase, y luego cada archivo de sql/migrations/ en
-- orden numérico.

-- ============================================================================
-- profiles -- extiende auth.users de Supabase con los datos propios de la app
-- ============================================================================
create table public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    full_name text,
    email text unique not null,
    role text not null default 'client',              -- 'admin' | 'client'
    accepted_terms boolean not null default false,
    trial_ends_at timestamptz,                          -- fin de prueba gratuita (ver TRIAL_DAYS)
    is_blocked boolean not null default false,          -- bloqueo manual por un admin (ver admin.py)
    created_at timestamptz not null default now()
);

-- ============================================================================
-- memberships -- historial de membresías/suscripciones. Un usuario puede
-- tener varias filas (trial, luego pago aprobado, luego renovación...);
-- resolve_active_plan() (core/dependencies.py) toma la que tenga ends_at más
-- lejano entre las 'active'.
-- ============================================================================
create table public.memberships (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references public.profiles(id) on delete cascade,
    plan text not null,                                  -- 'trial' | 'starter' | 'pro' | 'studio' | 'founder'
    status text not null default 'pending',              -- 'pending' | 'active' | 'rejected' | 'expired'
    starts_at timestamptz,
    ends_at timestamptz,                                  -- null = sin expiración (ej. founder)
    created_at timestamptz not null default now()
);

-- ============================================================================
-- sinpe_payments -- comprobantes de pago SINPE Móvil subidos por el cliente
-- y revisados manualmente por un admin (ver sinpe_service.py).
-- ============================================================================
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

-- ============================================================================
-- projects -- sesiones/lotes fotográficos de un usuario.
-- ============================================================================
create table public.projects (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references public.profiles(id) on delete cascade,
    name text not null,
    session_type text,                                   -- boda, retrato, producto, etc.
                                                           -- declarado pero NO usado por el código
                                                           -- todavía (ver models/project.py) -- se
                                                           -- deja por si ya hay datos reales con
                                                           -- valor en producción.
    status text not null default 'processing',           -- 'processing' | 'review' | 'error' | 'cancelled'
    processed_count int not null default 0,              -- fotos ya editadas por la IA
    total_count int not null default 0,                  -- total de fotos a editar (barra de progreso)
    qa_fallback_count int,                                -- cuántas fotos no pasaron el control de
                                                           -- calidad y se entregaron sin editar (ver
                                                           -- qa_check.py / batch_processor.py)
    processing_started_at timestamptz,                    -- ver ai_engine._run_batch_job
    processing_completed_at timestamptz,                  -- usado en /admin/stats/photos para el
                                                           -- tiempo promedio de procesamiento
    created_at timestamptz not null default now()
);

-- ============================================================================
-- project_photos -- fotos individuales de un proyecto (para saber qué
-- archivos exportar en ZIP, procesar con IA, etc.)
-- ============================================================================
create table public.project_photos (
    id uuid primary key default gen_random_uuid(),
    project_id uuid references public.projects(id) on delete cascade,
    original_url text not null,
    created_at timestamptz not null default now()
);

-- ============================================================================
-- watermarks -- config de marca de agua guardada por usuario (un único
-- config por usuario: user_id es unique para que el "upsert
-- on_conflict=user_id" de watermark.py funcione).
-- ============================================================================
create table public.watermarks (
    id uuid primary key default gen_random_uuid(),
    user_id uuid unique references public.profiles(id) on delete cascade,
    logo_url text not null,
    position text not null default 'south',                -- 'north'|'south'|'east'|'west'|'center'|'custom'
                                                             -- (ver VALID_POSITIONS en routers/watermark.py)
    pos_x int,
    pos_y int,
    opacity float not null default 0.8,
    scale float not null default 0.2,
    rotation float not null default 0,          -- grados, sentido horario
    created_at timestamptz not null default now()
);

-- ============================================================================
-- google_drive_connections -- conexión OAuth de Google Drive por usuario
-- (un usuario = una cuenta de Drive conectada; refresh_token permite renovar
-- el acceso sin pedirle al usuario que vuelva a autorizar cada vez).
-- ============================================================================
create table public.google_drive_connections (
    user_id uuid primary key references public.profiles(id) on delete cascade,
    access_token text not null,
    refresh_token text not null,
    expires_at timestamptz not null,
    created_at timestamptz not null default now()
);

-- ============================================================================
-- feedback -- calificación (1-5) + comentario opcional que el cliente deja
-- sobre una sesión ya editada (ver feedback_service.py).
-- ============================================================================
create table public.feedback (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references public.profiles(id) on delete cascade,
    project_id uuid references public.projects(id) on delete set null,
    rating int not null check (rating between 1 and 5),
    comment text,
    status text not null default 'pending',    -- 'pending' | 'in_review' | 'implemented' | 'discarded'
    created_at timestamptz not null default now()
);

-- ============================================================================
-- support_tickets -- tickets de soporte técnico (ver support_service.py).
-- ============================================================================
create table public.support_tickets (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references public.profiles(id) on delete cascade,
    subject text not null,
    message text not null,
    status text not null default 'open',       -- 'open' | 'in_progress' | 'closed'
    admin_reply text,
    updated_at timestamptz,
    created_at timestamptz not null default now()
);

-- ============================================================================
-- Índices -- las columnas más consultadas con .eq()/.order() en el código
-- (ver backend/app/routers/*.py, backend/app/services/*.py) no tenían ningún
-- índice explícito documentado; Postgres ya indexa las primary keys, pero
-- estas son las foreign keys y columnas de filtro/orden reales del código.
-- ============================================================================
create index if not exists idx_memberships_user_id on public.memberships(user_id);
create index if not exists idx_sinpe_payments_user_id on public.sinpe_payments(user_id);
create index if not exists idx_sinpe_payments_status on public.sinpe_payments(status);
create index if not exists idx_projects_user_id on public.projects(user_id);
create index if not exists idx_projects_created_at on public.projects(created_at desc);
create index if not exists idx_project_photos_project_id on public.project_photos(project_id);
create index if not exists idx_feedback_user_id on public.feedback(user_id);
create index if not exists idx_feedback_project_id on public.feedback(project_id);
create index if not exists idx_support_tickets_user_id on public.support_tickets(user_id);
