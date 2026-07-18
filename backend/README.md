# Photonix AI — Backend

API en **FastAPI** (Python) para el motor de edición automatizada con IA, autenticación, pagos SINPE y panel de administración.

## Instalación

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # completar con tus credenciales de Supabase
uvicorn app.main:app --reload
```

La API queda disponible en `http://localhost:8000` y la documentación interactiva (Swagger) en `http://localhost:8000/docs`.

## Estructura

```
app/
  main.py            # Registro de la app y routers
  config.py          # Variables de entorno / settings
  database.py        # Cliente Supabase + esquema SQL sugerido
  core/               # Seguridad (JWT), roles (RBAC), dependencias
  models/             # Estructuras de dominio
  schemas/            # Contratos Pydantic de request/response
  routers/            # Endpoints HTTP agrupados por módulo
  services/
    ai/                # Motor de IA: entorno, perspectiva, ajustes, limpieza, object removal, batch
    sinpe_service.py    # Lógica de pagos SINPE
    storage_service.py  # Abstracción de almacenamiento
    watermark_service.py# Composición de marca de agua
```

## Base de datos

El esquema SQL sugerido (tablas `profiles`, `memberships`, `sinpe_payments`, `projects`, `watermarks`) está documentado como comentario en `app/database.py`. Ejecutarlo en el SQL Editor de Supabase antes de iniciar la app.

## Notas de producción

- Reemplazar `BackgroundTasks` de FastAPI por una cola real (Celery + Redis o RQ) para procesar sesiones de miles de fotos con reintentos y persistencia de progreso.
- Los detectores de `object_removal.py` (placas, logos, postes/cables) están implementados con heurísticas clásicas de OpenCV; están listos para sustituirse por modelos entrenados sin cambiar la interfaz.
- Para RAW nativo (CR2, NEF, ARW, etc.) integrar `rawpy` antes de pasar la imagen a los módulos de IA (ya incluido en `requirements.txt`).
