FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copiar los archivos de requerimientos
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip3 install -r requirements.txt

# Copiar el resto del código
COPY . .

# Exponer el puerto que usa Streamlit
EXPOSE 8501

# Configurar el comando para ejecutar la aplicación
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
