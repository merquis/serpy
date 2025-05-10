# Usa imagen base oficial de Ubuntu 24.04
FROM ubuntu:24.04

# Establece usuario root y directorio de trabajo inicial
USER ubuntu
WORKDIR /home/ubuntu
SHELL [ "/bin/bash", "-c" ]

# ════════════════════════════════════════════════════
# 🛠️ Instalar Python, pip y dependencias del sistema
# ════════════════════════════════════════════════════
# Instalamos python3.12, python3-pip y las dependencias necesarias para Playwright
# y otras herramientas comunes del snippet.
RUN apt-get -qq -y update && \
    DEBIAN_FRONTEND=noninteractive apt-get -qq -y install \
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
        libharfbuzz-icu0 \
        fonts-liberation \
        libasound2t64 \
        xdg-utils \
        # Dependencias adicionales del snippet:
        build-essential \
        gcc \
        g++ \
        zlib1g-dev \
        libssl-dev \
        libbz2-dev \
        libsqlite3-dev \
        libncurses5-dev \
        libgdbm-dev \
        libgdbm-compat-dev \
        liblzma-dev \
        libreadline-dev \
        uuid-dev \
        libffi-dev \
        tk-dev \
        make \
        sudo \
        bash-completion \
        tree \
        vim \
        software-properties-common && \
    # Limpieza para reducir el tamaño de la imagen
    apt-get -y autoclean && \
    apt-get -y autoremove && \
    rm -rf /var/lib/apt/lists/*

# Nota: Se omite la instalación de Python desde install_python.sh
# ya que instalamos python3.12 y python3-pip directamente con apt-get.

# ════════════════════════════════════════════════════
# 👤 Crear usuario "docker" con sudo (según snippet)
# ════════════════════════════════════════════════════
# Este paso sigue la estructura del snippet proporcionado.
RUN useradd -m docker && \
    usermod -aG sudo docker && \
    echo '%sudo ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers && \
    # Copiar bashrc y crear directorio data para el usuario docker
    cp /root/.bashrc /home/docker/ && \
    mkdir /home/docker/data && \
    chown -R docker:docker /home/docker

# Nota: Se omite la modificación de bashrc para tab completion
# ya que no es esencial para la ejecución de la aplicación.

# Evitar primer uso de sudo warning (según snippet)
RUN touch /home/docker/.sudo_as_admin_successful && chown docker:docker /home/docker/.sudo_as_admin_successful

# ════════════════════════════════════════════════════
# 🚪 Cambiar a usuario "docker" y establecer directorio de trabajo
# ════════════════════════════════════════════════════
USER docker
WORKDIR /code

# ════════════════════════════════════════════════════
# 🌐 Configurar variables de entorno (según snippet)
# ════════════════════════════════════════════════════
# Configura locale y PATH para el usuario 'docker'.
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8 \
    LC_ALL="C.UTF-8" \
    PYTHONPATH="/code" \
    PATH=/home/docker/.local/bin:$PATH

# ════════════════════════════════════════════════════
# 📦 Instalar las dependencias de Python
# ════════════════════════════════════════════════════
# Usamos el pip del sistema (python3.12 -m pip) para instalar las dependencias de requirements.txt.
# No usamos --break-system-packages para evitar conflictos.
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
