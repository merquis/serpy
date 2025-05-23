FROM ubuntu:24.04

# ════════════════════════════════════════════════════
# 🛠️ Instalar dependencias básicas + Tesseract OCR + Xvfb
# ════════════════════════════════════════════════════
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3-pip \
    curl \
    wget \
    git \
    nano \
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
    libgl1 \
    libegl1 \
    libdrm2 \
    libpangocairo-1.0-0 \
    libicu74 \
    tesseract-ocr \
    xvfb \
    fluxbox \
    x11vnc \
    net-tools \
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
# 📄 Copiar el código fuente y el entrypoint
COPY . .
COPY entrypoint.sh /app/entrypoint.sh

# ════════════════════════════════════════════════════
# 🌐 Exponer puertos
EXPOSE 8501 # Streamlit
EXPOSE 5900 # VNC (opcional)

# ════════════════════════════════════════════════════
# 📝 Permisos y ejecución del entrypoint
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
