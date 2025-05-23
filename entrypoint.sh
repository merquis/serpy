#!/bin/bash

# Iniciar Xvfb en segundo plano
export DISPLAY=:99
Xvfb :99 -screen 0 1280x1024x24 -ac +extension GLX +render -noreset & 
PID_XVFB=$!
echo "Xvfb iniciado con PID: $PID_XVFB en display $DISPLAY"

# Esperar un momento para que Xvfb se inicie completamente
sleep 2

# Iniciar Fluxbox (gestor de ventanas ligero) en segundo plano
fluxbox & 
PID_FLUXBOX=$!
echo "Fluxbox iniciado con PID: $PID_FLUXBOX"

# (Opcional) Iniciar x11vnc para acceso remoto al escritorio virtual
# x11vnc -display :99 -nopw -forever -quiet -bg
# echo "x11vnc iniciado en el puerto 5900 (sin contraseña)"

# Crear directorio .streamlit si no existe
mkdir -p /app/.streamlit

# Verificar si existe la variable de entorno STREAMLIT_SECRETS_TOML
if [ ! -z "$STREAMLIT_SECRETS_TOML" ]; then
    # Eliminar las comillas simples del inicio y final si existen
    CLEANED_SECRETS="${STREAMLIT_SECRETS_TOML#\'}"
    CLEANED_SECRETS="${CLEANED_SECRETS%\'}"
    
    # Escribir al archivo secrets.toml
    echo "$CLEANED_SECRETS" > /app/.streamlit/secrets.toml
    echo "Archivo secrets.toml creado con éxito"
else
    echo "No se encontró la variable STREAMLIT_SECRETS_TOML"
    echo "# Placeholder - no secrets configured" > /app/.streamlit/secrets.toml
fi

# Ejecutar streamlit
echo "Iniciando Streamlit..."
exec streamlit run streamlit_app.py --server.port=8501 --server.enableCORS=false --server.enableXsrfProtection=false

# Limpieza al salir (esto no se ejecutará si Streamlit toma el control con exec)
# trap "echo 'Deteniendo Xvfb y Fluxbox...'; kill $PID_XVFB $PID_FLUXBOX; exit" SIGINT SIGTERM 