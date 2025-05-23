#!/bin/bash

# Iniciar Xvfb en segundo plano
export DISPLAY=:99
Xvfb :99 -screen 0 1280x1024x24 -ac +extension GLX +render -noreset &
PID_XVFB=$!
echo "Xvfb iniciado con PID: $PID_XVFB en display $DISPLAY"

sleep 2

# Iniciar Fluxbox
fluxbox & 
PID_FLUXBOX=$!
echo "Fluxbox iniciado con PID: $PID_FLUXBOX"

# secrets.toml
mkdir -p /app/.streamlit
if [ ! -z "$STREAMLIT_SECRETS_TOML" ]; then
    CLEANED_SECRETS="${STREAMLIT_SECRETS_TOML#\'}"
    CLEANED_SECRETS="${CLEANED_SECRETS%\'}"
    echo "$CLEANED_SECRETS" > /app/.streamlit/secrets.toml
    echo "Archivo secrets.toml creado con éxito"
else
    echo "# Placeholder - no secrets configured" > /app/.streamlit/secrets.toml
fi

# Ejecutar Streamlit
echo "Iniciando Streamlit..."
exec streamlit run streamlit_app.py --server.port=8501 --server.enableCORS=false --server.enableXsrfProtection=false
