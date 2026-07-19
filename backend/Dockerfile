FROM python:3.11-slim

# Dependencias del sistema requeridas por OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# numpy/OpenCV usan BLAS (OpenBLAS/MKL) internamente para operaciones de
# arreglos, y esa librería detecta el número de CPUs del HOST subyacente
# (via /proc/cpuinfo), no el límite real de vCPU del contenedor -- en un
# host con muchos núcleos pero un contenedor limitado a 1-2 vCPU (ej.
# Railway), esto crea muchísimos más hilos BLAS de los que la cuota de CPU
# real puede atender, y la contención resultante puede hacer que el
# procesamiento de una sola foto tarde muchísimo o parezca colgado (CPU
# medida cerca de 0% porque cada hilo solo recibe una porción mínima de
# tiempo de CPU). cv2.setNumThreads(1) en batch_processor.py limita el
# paralelismo INTERNO de OpenCV, pero no toca el pool de hilos de BLAS que
# usa numpy por separado -- de ahí que haga falta fijarlo aparte, y hacerlo
# aquí (antes de que arranque Python) para que tome efecto en el momento en
# que numpy inicializa su backend BLAS, no después.
ENV OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    VECLIB_MAXIMUM_THREADS=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# La mayoría de plataformas de hosting (ej. Railway) inyectan el puerto real
# a través de la variable de entorno PORT; se usa 8000 como valor por defecto
# para correr el contenedor localmente sin configuración adicional.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
