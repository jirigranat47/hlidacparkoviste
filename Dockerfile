FROM python:3.11-slim

# Instalace systémových závislostí pro OpenCV a psycopg2
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Nejdříve zkopírujeme requirements a nainstalujeme je
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Poté zkopírujeme zbytek aplikace
# Poté zkopírujeme zbytek aplikace
COPY . .

# Nastavení pro Railway a YOLO
ENV YOLO_CONFIG_DIR=/tmp/Ultralytics
ENV PORT=8000

# Výchozí příkaz necháme prázdný nebo nastavíme na spuštění API,
# ale Railway by mělo použít Procfile. Pro jistotu zde dáme spuštění API.
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]