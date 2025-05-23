FROM ubuntu:24.04

# ════════════════════════════════════════════════════
# 🛠️ Instalar dependencias del sistema y entorno gráfico virtual
# ════════════════════════════════════════════════════
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3-pip curl wget git nano ca-certificates \
    # Playwright y entorno headless
    libnss3 libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxi6 libxtst6 \
    libatk1.0-0 libcairo2 libcups2 libfontconfig1 libgbm1 libgdk-pixbuf2.0-0 libglib2.0-0 \
    libgtk-3-0 libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libdbus-1-3 libexpat1 libffi8 \
    libgcc-s1 libstdc++6 libuuid1 libxcb1 libxkbcommon0 libxrandr2 libfreetype6 libharfbuzz0b \
    fonts-liberation libasound2t64 xdg-utils libxshmfence1 libxss1 libxt6 libxrender1 \
    libx11-xcb1 libatspi2.0-0 libxinerama1 libgl1 libegl1 libdrm2 libpangocairo-1.0-0 libicu74 \
    # OCR y headless
    tesseract-ocr xvfb fluxbox \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ════════════════════════════════════════════════════
# 📁 Crear directorio de trabajo
WORKDIR /app

# ════════════════════════════════════════════════════
# 📦 Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# ════════════════════════════════════════════════════
# 🌍 Instalar navegadores Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install chromium

# ════════════════════════════════════════════════════
# 📄 Copiar código fuente y entrypoint
COPY . .
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# ════════════════════════════════════════════════════
# 🌐 Exponer puerto para Streamlit
EXPOSE 8501

# ════════════════════════════════════════════════════
# 🚀 Lanzar Streamlit + Xvfb + entorno headless
ENTRYPOINT ["/app/entrypoint.sh"]
