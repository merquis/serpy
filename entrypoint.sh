#!/bin/bash

# Salir inmediatamente si un comando falla
set -e

# Muestra los comandos que se ejecutan (muy útil para depurar)
set -x

# Iniciar Xvfb (servidor gráfico virtual)
export DISPLAY=:99
echo "▶️ Iniciando Xvfb..."
if command -v Xvfb &>/dev/null; then
    # Inicia Xvfb en segundo plano
    Xvfb :99 -screen 0 1280x1024x24 -ac +extension GLX +render -noreset &
    PID_XVFB=$!
    echo "✅ Xvfb iniciado con PID: $PID_XVFB en display $DISPLAY"
else
    echo "❌ Xvfb no está instalado o no se encuentra en PATH"; exit 1
fi

# Espera un poco más para asegurar que Xvfb esté listo
sleep 5

# Iniciar Fluxbox (gestor de ventanas minimalista)
echo "▶️ Iniciando Fluxbox..."
if command -v fluxbox &>/dev/null; then
    # Inicia Fluxbox en segundo plano
    fluxbox &
    PID_FLUXBOX=$!
    echo "✅ Fluxbox iniciado con PID: $PID_FLUXBOX"
else
    echo "⚠️ Fluxbox no está instalado. Continuando sin gestor de ventanas..."
fi

# Crear .streamlit/secrets.toml desde variable de entorno
mkdir -p /app/.streamlit
if [ -n "$STREAMLIT_SECRETS_TOML" ]; then
    # Tu lógica de limpieza parece diseñada para quitar ' al inicio y fin.
    # Asegúrate de que la variable se pasa exactamente así.
    CLEANED_SECRETS="${STREAMLIT_SECRETS_TOML#\'}"
    CLEANED_SECRETS="${CLEANED_SECRETS%\'}"
    echo "$CLEANED_SECRETS" > /app/.streamlit/secrets.toml
    echo "✅ Archivo secrets.toml creado con éxito"
else
    echo "# Placeholder - no secrets configured" > /app/.streamlit/secrets.toml
    echo "⚠️ STREAMLIT_SECRETS_TOML no definido. Usando configuración vacía."
fi

# Ejecutar Streamlit
echo "🚀 Iniciando Streamlit en 0.0.0.0..."
# AÑADIDO: --server.address=0.0.0.0
exec streamlit run streamlit_app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
