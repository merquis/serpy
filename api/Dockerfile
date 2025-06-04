FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos necesarios
# Nota: En EasyPanel, asegúrate de que el Build Context esté configurado como ./api
COPY requirements.txt .
COPY main.py .
COPY config/ ./config/

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Crear directorio para logs si es necesario
RUN mkdir -p /app/logs

# Exponer puerto
EXPOSE 8000

# Variables de entorno por defecto
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Comando para ejecutar la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
