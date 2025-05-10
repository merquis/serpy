# 📦 Imagen base: Ubuntu 24.04
FROM ubuntu:24.04

# ════════════════════════════════════════════════════
# 🛠️ Instalar dependencias básicas y Playwright
# ════════════════════════════════════════════════════
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3-pip \
    curl \
    wget \
    git \
    ca-certificates \
    libnss3 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxtst6 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libfontconfig1 \
    libgbm1 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libdbus-1-3 \
    libexpat1 \
    libffi8 \
    libgcc-s1 \
    libstdc++6 \
    libuuid1 \
    libxcb1 \
    libxkbcommon0 \
    libxrandr2 \
    libfreetype6 \
    libharfbuzz0b \
    fonts-liberation \
    libasound2t64 \
    xdg-utils \
    libxshmfence1 \
    libxss1 \
    libxt6 \
    libxrender1 \
    libx11-xcb1 \
    libatspi2.0-0 \
    libxinerama1 \
    libgl1 \    # <-- CORREGIDO AQUI
    libegl1 \
    libdrm2 \
    libpangocairo-1.0-0 \
    libicu74 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ════════════════════════════════════════════════════
# 📁 Crear carpeta de trabajo
WORKDIR /app

# ════════════════════════════════════════════════════
# 📦 Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# ════════════════════════════════════════════════════
# 🌍 Instalar navegadores Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install

# ════════════════════════════════════════════════════
# 📄 Copiar tu código
COPY . .

# ════════════════════════════════════════════════════
# 🌐 Exponer puerto 8501
EXPOSE 8501

# ════════════════════════════════════════════════════
# 🚀 Ejecutar Streamlit
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
