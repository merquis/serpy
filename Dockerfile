# Usa imagen base oficial de Ubuntu 24.04
FROM ubuntu:24.04

# ════════════════════════════════════════════════════
# 🛠️ Instalar Python, pip y dependencias del sistema
# ════════════════════════════════════════════════════
# Instalamos python3.12 y python3-pip, así como las dependencias necesarias para Playwright
# y otras herramientas como curl, wget, git.
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
    libharbuzz0b \
    fonts-liberation \
    libasound2t64 \
    xdg-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ════════════════════════════════════════════════════
# 🐍 Actualizar pip a la última versión
# ════════════════════════════════════════════════════
# >>> ELIMINADA: No es necesario ni recomendable actualizar pip instalado por el sistema.
# RUN python3.12 -m pip install --upgrade pip --break-system-packages

# ════════════════════════════════════════════════════
# 📁 Establecer el directorio de trabajo
# ════════════════════════════════════════════════════
WORKDIR /app

# ════════════════════════════════════════════════════
# 📦 Instalar las dependencias de Python
# ════════════════════════════════════════════════════
# Usamos el pip del sistema (python3.12 -m pip) para instalar las dependencias de requirements.txt.
# Hemos eliminado el flag --break-system-packages para evitar conflictos con paquetes del sistema.
COPY requirements.txt .
RUN python3.12 -m pip install --no-cache-dir -r requirements.txt

# ════════════════════════════════════════════════════
# 🌍 Instalar navegadores de Playwright
# ════════════════════════════════════════════════════
# Playwright necesita los navegadores para funcionar.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install --with-deps

# ════════════════════════════════════════════════════
# 📄 Copiar el resto del proyecto
# ════════════════════════════════════════════════════
# Copia todos los archivos de tu proyecto al directorio de trabajo en el contenedor.
COPY . .

# ════════════════════════════════════════════════════
# 🌐 Exponer puerto para Streamlit
# ════════════════════════════════════════════════════
# Indica que el contenedor escucha en el puerto 8501.
EXPOSE 8501

# ════════════════════════════════════════════════════
# 🚀 Comando para ejecutar Streamlit
# ════════════════════════════════════════════════════
# Define el comando que se ejecuta cuando el contenedor inicia.
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
