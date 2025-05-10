# Usa una imagen base de Python oficial.
# Usamos la etiqueta python:3.12, que es una imagen estándar y robusta,
# generalmente basada en Debian.
FROM python:3.12

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de requisitos e instala las dependencias de Python
# Usamos --no-cache-dir para no guardar archivos temporales de pip, reduciendo el tamaño de la imagen.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# --- Configuración para Playwright ---
# Playwright necesita ciertas dependencias del sistema operativo para funcionar,
# incluso en modo headless. Las siguientes son comunes para imágenes basadas en Debian/Ubuntu.
# La imagen python:3.12 ya podría incluir algunas de estas, pero las listamos
# por si acaso y para claridad. Si encuentras errores durante la construcción o ejecución,
# puede que necesites añadir o ajustar las dependencias aquí.
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Librerías gráficas básicas (necesarias para navegadores headless)
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
    libgbm0 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libdbus-1-3 \
    libexpat1 \
    libffi7 \
    libgcc1 \
    libstdc++6 \
    libuuid1 \
    libxcb1 \
    libxkbcommon0 \
    libxrandr2 \
    libfreetype6 \
    libharfbuzz0b \
    # Limpieza para reducir el tamaño de la imagen
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instala los navegadores de Playwright dentro del contenedor.
# PLAYWRIGHT_BROWSERS_PATH=/ms-playwright es una variable de entorno recomendada por Playwright
# para instalar los navegadores en una ubicación conocida y accesible dentro del contenedor.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install --with-deps

# Copia el resto de los archivos de tu aplicación al contenedor
# Asegúrate de que tu script principal y otros módulos estén en la misma carpeta.
COPY . .

# Expone el puerto en el que Streamlit se ejecuta por defecto (8501)
EXPOSE 8501

# Comando para ejecutar la aplicación Streamlit
# Reemplaza 'your_main_script.py' con el nombre real de tu archivo principal de Streamlit.
# Los flags --server.port, --server.enableCORS, --server.enableXsrfProtection son comunes
# para despliegues en entornos como Docker/EasyPanel.
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
