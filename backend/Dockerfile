FROM python:3.11-slim

# Dependencias del sistema requeridas por OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# La mayoría de plataformas de hosting (ej. Railway) inyectan el puerto real
# a través de la variable de entorno PORT; se usa 8000 como valor por defecto
# para correr el contenedor localmente sin configuración adicional.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
