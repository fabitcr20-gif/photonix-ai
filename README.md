# Photonix AI

Plataforma de edición fotográfica automatizada con IA para fotógrafos y diseñadores profesionales.

## Contenido de este proyecto

- `backend/` — API en FastAPI (Python): autenticación, roles, pagos SINPE, panel admin, carga de archivos y motor de IA (análisis de entorno, perspectiva, ajustes, limpieza, eliminación de objetos) + marca de agua. Ver `backend/README.md`.
- `frontend/` — Aplicación en Next.js 14 + Tailwind CSS (tema oscuro): registro/login, dashboard de cliente (carga, membresía, marca de agua) y panel de administrador (estadísticas + validación SINPE).
- `ROADMAP_MAESTRO.md` — Visión de producto completa a largo plazo, organizada en fases, más allá de este MVP.
- `DEPLOYMENT.md` — Guía paso a paso para publicar la app en internet bajo un dominio propio (ej. `photonixai.cr`) usando Vercel + Railway.

## Puesta en marcha rápida

### 1. Supabase

Crea un proyecto en [supabase.com](https://supabase.com), habilita los proveedores de Auth (Google, Apple, Email), y ejecuta el esquema SQL documentado en `backend/app/database.py` desde el SQL Editor. Copia la URL, la ANON KEY, la SERVICE ROLE KEY y el JWT SECRET.

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completa con tus credenciales de Supabase
uvicorn app.main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # completa con tus credenciales de Supabase
npm run dev
```

La app queda disponible en `http://localhost:3000` y la API en `http://localhost:8000/docs`.

### 4. Cuenta de fundador/administrador

El correo definido en `FOUNDER_ADMIN_EMAIL` (backend) recibe automáticamente rol `admin` y membresía `founder` gratuita e ilimitada al registrarse por primera vez desde la app.

Si prefieres no esperar al registro manual, puedes aprovisionar la cuenta directamente (crea el usuario en Supabase Auth con contraseña + perfil admin + membresía founder, todo de una vez):

```bash
cd backend
source venv/bin/activate
export FOUNDER_ADMIN_PASSWORD="una-contraseña-segura"   # opcional; si se omite se genera una aleatoria
python -m scripts.bootstrap_founder_admin
```

El script imprime el correo y la contraseña una sola vez al final — guárdalos en un lugar seguro. Es idempotente: se puede volver a correr sin duplicar el usuario ni la membresía (por ejemplo para restablecer la contraseña).

### 5. Recordatorios de pago

Desde el Panel de Administrador → "Recordatorios" se listan los clientes cuya prueba gratuita o membresía vence pronto o ya venció, con botones para enviarles un correo individualmente o a todos a la vez. Configura `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD` en `backend/.env` para enviarlos de verdad (si se dejan vacíos, los correos solo se registran en logs). Para que se envíen automáticamente todos los días sin acción manual, activa `ENABLE_REMINDER_SCHEDULER=true` en `backend/.env`.

### 6. Funciones según el plan

Lo que un cliente puede hacer en la app depende de su plan activo (ver `backend/app/core/plans.py`): la eliminación de objetos (placas, postes, cables) requiere Pro o Studio, y el número máximo de fotos por carga masiva crece con el plan. El backend valida esto en cada request (no solo la interfaz), y el frontend deshabilita las opciones no incluidas mostrando un enlace para actualizar el plan.

### 7. Exportación de sesiones (ZIP, Google Drive, Instagram)

Después de cargar fotos, la página "Cargar Fotos" muestra una barra de progreso real durante la subida y, una vez creado el proyecto, botones para **descargar en ZIP** (funciona de inmediato, sin configuración) y para **subir a Google Drive** / **Instagram** (requieren credenciales propias — ver más abajo).

Esta función necesita la tabla `project_photos`, que registra qué fotos pertenecen a cada sesión. Si tu base de datos es anterior a esta versión, corre en el SQL Editor de Supabase:

```sql
create table public.project_photos (
    id uuid primary key default gen_random_uuid(),
    project_id uuid references public.projects(id) on delete cascade,
    original_url text not null,
    created_at timestamptz not null default now()
);
```

Para habilitar Google Drive/Instagram, agrega en `backend/.env`:
- `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` — de un proyecto en [Google Cloud Console](https://console.cloud.google.com) con la Drive API habilitada.
- `INSTAGRAM_ACCESS_TOKEN` — de una app en [Meta for Developers](https://developers.facebook.com) con el Instagram Graph API habilitado (requiere cuenta de Instagram Business/Creator y, para publicar contenido real, revisión de la app por parte de Meta).

Sin esas credenciales, los botones muestran un aviso claro en vez de fallar en silencio.

### 8. Barra de progreso de la edición automática

Al iniciar la edición, la página consulta cada 2 segundos cuántas fotos ya procesó la IA y muestra una barra de avance real (no solo un mensaje fijo). Necesita dos columnas nuevas en `projects`. Si tu base de datos es anterior a esta versión, corre en el SQL Editor de Supabase:

```sql
alter table public.projects add column processed_count int not null default 0;
alter table public.projects add column total_count int not null default 0;
```

## Marca

El logo se recreó en formato vectorial (`frontend/public/logo.svg` y `logo-mark.svg`) a partir de la imagen proporcionada. Para una réplica exacta pixel a pixel, sustituye estos archivos por el asset original de la marca cuando esté disponible en alta resolución.

## Siguientes pasos sugeridos

Revisa `ROADMAP_MAESTRO.md` para la hoja de ruta completa: importación inteligente desde tarjetas SD, aprendizaje del estilo del fotógrafo ("Mi Estilo"), revisión antes/después, exportación multi-formato, galería web para clientes, backup automático a Google Drive y escalabilidad internacional.
