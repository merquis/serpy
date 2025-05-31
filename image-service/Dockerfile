FROM ubuntu:24.04

# Instalar Python, pip y dependencias básicas para Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3-pip \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
