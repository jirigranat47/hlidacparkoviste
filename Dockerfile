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
COPY . .

CMD ["python", "main.py"]