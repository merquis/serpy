# Usa una imagen base oficial de Ubuntu 24.04
FROM ubuntu:24.04

# Evita preguntas interactivas durante la instalación de paquetes
ENV DEBIAN_FRONTEND=noninteractive

# Establece usuario root y directorio de trabajo inicial
USER root
WORKDIR /root
SHELL [ "/bin/bash", "-c" ]

# ════════════════════════════════════════════════════
# 🛠️ Instalar Python 3.12, pip y dependencias del sistema para Playwright y otras herramientas
# ════════════════════════════════════════════════════
# Esta lista de dependencias se basa en la documentación de Playwright para Ubuntu
# y se complementa con herramientas comunes y Python/pip.
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    python3.12 \
    python3-pip \
    # Dependencias de Playwright para navegadores headless en Ubuntu
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libgbm1 \
    libgtk-3-0 \
    libnss3 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxkbcommon0 \
    libxrandr2 \
    libxtst6 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libffi8 \
    libfontconfig1 \
    libgcc-s1 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libharfbuzz-icu0 \
    libnspr4 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libuuid1 \
    libxcb1 \
    xdg-utils \
    # Herramientas adicionales
    curl \
    wget \
    git \
    build-essential \
    gcc \
    g++ \
    make \
    sudo \
    bash-completion \
    tree \
    vim \
    software-properties-common && \
    # Limpieza de caché de apt
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ════════════════════════════════════════════════════
# 👤 Crear usuario "docker" con sudo (según tu snippet)
# ════════════════════════════════════════════════════
# Este paso se adapta de tu snippet para crear un usuario no-root.
RUN useradd -m docker && \
    usermod -aG sudo docker && \
    echo '%sudo ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers && \
    # Copiar bashrc y crear directorio data para el usuario docker
    cp /root/.bashrc /home/docker/ && \
    mkdir /home/docker/data && \
    chown -R docker:docker /home/docker

# Evitar primer uso de sudo warning (según tu snippet)
RUN touch /home/docker/.sudo_as_admin_successful && chown docker:docker /home/docker/.sudo_as_admin_successful

# ════════════════════════════════════════════════════
# 🚪 Cambiar a usuario "docker" y establecer directorio de trabajo
# ════════════════════════════════════════════════════
# Ejecutaremos el resto de los comandos y la aplicación como este usuario.
USER docker
WORKDIR /code

# ════════════════════════════════════════════════════
# 🌐 Configurar variables de entorno (según tu snippet)
# ════════════════════════════════════════════════════
# Configura locale y PATH para el usuario 'docker'.
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8 \
    LC_ALL="C.UTF-8" \
    PYTHONPATH="/code" \
    PATH=/home/docker/.local/bin:$PATH

# ════════════════════════════════════════════════════
# 📦 Instalar las dependencias de Python de requirements.txt
# ════════════════════════════════════════════════════
# Copia tu archivo requirements.txt e instala las dependencias.
# Usamos python3.12 -m pip para asegurar que usamos el pip correcto.
COPY requirements.txt .
RUN python3.12 -m pip install --no-cache-dir -r requirements.txt

# ════════════════════════════════════════════════════
# 🌍 Instalar navegadores de Playwright
# ════════════════════════════════════════════════════
# Instala los binarios de los navegadores necesarios para Playwright.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install --with-deps

# ════════════════════════════════════════════════════
# 📄 Copiar el resto del proyecto
# ════════════════════════════════════════════════════
# Copia todos los archivos de tu proyecto al directorio de trabajo en el contenedor (/code).
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
# Se ejecuta como el usuario 'docker' en el directorio '/code'.
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
