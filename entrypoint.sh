#!/bin/bash

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
exec streamlit run streamlit_app.py --server.port=8501 --server.enableCORS=false --server.enableXsrfProtection=false 
