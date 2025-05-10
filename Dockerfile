# Usa imagen base oficial de Ubuntu 24.04
FROM ubuntu:24.04

# ════════════════════════════════════════════════════
# 🛠️ Instalar Python, pip y dependencias del sistema
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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ════════════════════════════════════════════════════
# 🐍 Actualizar pip a la última versión
# ════════════════════════════════════════════════════
RUN python3.12 -m pip install --upgrade pip --break-system-packages

# ════════════════════════════════════════════════════
# 📁 Establecer el directorio de trabajo
# ════════════════════════════════════════════════════
WORKDIR /app

# ════════════════════════════════════════════════════
# 📦 Instalar las dependencias de Python
# ════════════════════════════════════════════════════
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# ════════════════════════════════════════════════════
# 🌍 Instalar navegadores de Playwright
# ════════════════════════════════════════════════════
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install --with-deps

# ════════════════════════════════════════════════════
# 📄 Copiar el resto del proyecto
# ════════════════════════════════════════════════════
COPY . .

# ════════════════════════════════════════════════════
# 🌐 Exponer puerto para Streamlit
# ════════════════════════════════════════════════════
EXPOSE 8501

# ════════════════════════════════════════════════════
# 🚀 Comando para ejecutar Streamlit
# ════════════════════════════════════════════════════
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
