# Despliegue de Photonix AI a producción

Guía paso a paso para publicar Photonix AI en internet bajo un dominio propio
(ej. `photonixai.cr`). Usa **Vercel** para el frontend (Next.js) y **Railway**
para el backend (FastAPI), que es la combinación más simple y económica para
este proyecto.

Nada de esto lo puedo ejecutar yo por ti: registrar el dominio y crear cuentas
en Vercel/Railway requiere que ingreses tus propios datos de pago y credenciales.
Esta guía te deja los pasos exactos para que tú los sigas.

## 0. Antes de empezar (checklist)

- [ ] Cuenta de GitHub (recomendado, para desplegar automáticamente en cada push)
- [ ] Proyecto real de Supabase creado, con Auth (Google/Apple/Email) habilitado
      y el esquema SQL de `backend/app/database.py` ejecutado (ver `README.md`)
- [ ] Cuenta en [vercel.com](https://vercel.com)
- [ ] Cuenta en [railway.com](https://railway.com)
- [ ] Dominio elegido (puede ser `photonixai.cr` u otro — ver paso 1)

## 1. Registrar el dominio

Para un dominio `.cr` (Costa Rica), el registrador oficial es **NIC Costa Rica**
(`dominios.cr` / `nic.cr`). No se requiere residencia en Costa Rica, solo un
correo de contacto válido y funcional. El precio oficial ronda **$70+IVA por
un año** (hay planes de 2 y 5 años, y promociones periódicas — revisa
[nic.cr](https://nic.cr/) para el precio vigente).

Pasos:
1. Entra a [dominios.cr](https://dominios.cr/) y busca disponibilidad de `photonixai.cr`.
2. Crea tu cuenta de contacto/registrante y completa el registro.
3. Paga con tu propio método de pago.
4. Al finalizar, tendrás acceso a un panel de DNS para ese dominio (lo usarás en el paso 5).

Si prefieres no tramitar un `.cr` (por ejemplo, si tu registrador preferido no
lo soporta), cualquier dominio `.com`/`.io`/etc. sirve exactamente igual — el
resto de la guía no cambia, solo el nombre.

## 2. Subir el código a GitHub (recomendado)

Vercel y Railway se conectan directamente a un repositorio y despliegan
automáticamente en cada `git push`. Si el proyecto aún no es un repositorio git:

```bash
cd "photonix-ai 2"
git init
git add .
git commit -m "Versión inicial de Photonix AI"
```

Luego crea un repositorio vacío en GitHub y súbelo:

```bash
git remote add origin https://github.com/tu-usuario/photonix-ai.git
git branch -M main
git push -u origin main
```

(También es posible desplegar sin GitHub usando `vercel` y `railway up` desde
la terminal, pero perderías el auto-despliegue en cada cambio.)

## 3. Backend en Railway

1. En [railway.com](https://railway.com) → **New Project** → **Deploy from GitHub repo** → selecciona tu repositorio.
2. En **Settings → Root Directory**, indica `backend` (Railway detecta el `Dockerfile` automáticamente).
3. En **Variables**, copia todas las claves de `backend/.env.example` con sus valores reales: credenciales de Supabase, `SINPE_PHONE_NUMBER`, `SMTP_*` si vas a enviar recordatorios de verdad, y `FRONTEND_ORIGINS` (por ahora déjalo con la URL que Railway te asigne; lo ajustas en el paso 6).
4. Despliega. Railway te da una URL tipo `photonix-backend-production.up.railway.app` — pruébala en `/health` y `/docs`.
5. Dominio personalizado: **Settings → Networking → Custom Domain** → escribe `api.photonixai.cr`. Railway te mostrará un **CNAME** y un **TXT** exactos que debes copiar tal cual (no son fijos, los genera para tu proyecto) — los agregarás en el paso 5.

## 4. Frontend en Vercel

1. En [vercel.com](https://vercel.com) → **Add New… → Project** → importa el mismo repositorio.
2. En **Root Directory**, indica `frontend` (Vercel detecta Next.js automáticamente).
3. En **Environment Variables**, agrega:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_API_BASE_URL` = `https://api.photonixai.cr/api/v1` (o la URL de Railway si aún no conectas el dominio del backend)
4. Despliega.
5. Dominio personalizado: **Settings → Domains** → agrega `photonixai.cr` (dominio raíz/apex) y `www.photonixai.cr`. Vercel te mostrará:
   - Para el apex (`photonixai.cr`): un registro **A** con una IP específica de tu proyecto.
   - Para `www`: un registro **CNAME** hacia un valor tipo `xxxxx.vercel-dns-xxx.com`.
   Copia los valores exactos que Vercel te muestre — no uses una IP genérica de otra guía.

## 5. Configurar el DNS del dominio

En el panel de DNS de donde registraste el dominio (NIC Costa Rica u otro),
agrega los registros que Vercel y Railway te mostraron en los pasos 3 y 4.
La tabla es solo un ejemplo de qué tipos de registro esperar — los valores
reales los copias del panel de cada plataforma:

| Tipo  | Nombre | Valor                                  | Para qué |
|-------|--------|-----------------------------------------|----------|
| A     | @      | (IP que indique Vercel)                 | `photonixai.cr` → frontend |
| CNAME | www    | (host que indique Vercel)               | `www.photonixai.cr` → frontend |
| CNAME | api    | (host que indique Railway)              | `api.photonixai.cr` → backend |
| TXT   | api (o el nombre que pida Railway) | (valor que indique Railway) | Verificación de dominio en Railway |

La propagación de DNS puede tardar desde minutos hasta un par de horas.

## 6. Últimos ajustes tras conectar el dominio

1. En Railway, actualiza `FRONTEND_ORIGINS` a
   `["https://photonixai.cr","https://www.photonixai.cr"]` y vuelve a desplegar.
2. En Supabase → **Authentication → URL Configuration**, actualiza el **Site URL**
   a `https://photonixai.cr` y agrega `https://photonixai.cr/**` a las **Redirect URLs**
   (necesario para que el login con Google/Apple funcione en producción).
3. En Vercel, confirma que `NEXT_PUBLIC_API_BASE_URL` apunte a `https://api.photonixai.cr/api/v1`.
4. Prueba el flujo completo en el dominio real: registro, login, carga de fotos, panel admin.

## 7. Certificados SSL

Tanto Vercel como Railway emiten y renuevan certificados TLS automáticamente
en cuanto el DNS queda verificado — no hay ninguna acción manual adicional.

## Fuentes consultadas

- [Capítulo 1: Registro de un Nombre de Dominio — NIC Costa Rica](https://nic.cr/capitulo-1-registro-de-un-nombre-de-dominio/)
- [¿Cuánto cuestan los dominios .CR? — Transparencia](https://transparencia.org.ve/cuanto-cuestan-los-dominios-cr-de-costa-rica/)
- [Adding & Configuring a Custom Domain — Vercel Docs](https://vercel.com/docs/domains/working-with-domains/add-a-domain)
- [Can I use my domain on Vercel with A records? — Vercel Knowledge Base](https://vercel.com/kb/guide/a-record-and-caa-with-vercel)
- [Working with Domains — Railway Docs](https://docs.railway.com/networking/domains/working-with-domains)
