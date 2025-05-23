# SERPY - Herramienta SEO y Scraping

## 🔐 Configuración de Secretos en Easypanel

Para mantener los secretos seguros y seguir las mejores prácticas, SERPY utiliza variables de entorno para gestionar las credenciales y configuraciones sensibles.

### Configuración en Easypanel

1. En tu panel de Easypanel, ve a la sección "Entorno" de tu aplicación SERPY
2. Añade una variable de entorno llamada `STREAMLIT_SECRETS_TOML` 
3. Como valor, copia todo el contenido de tu archivo `secrets.toml` original

El formato debe ser similar a este ejemplo:

```
STREAMLIT_SECRETS_TOML='
[openai]
api_key = "sk-..."

[drive_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = """-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
"""
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

[brightdata]
token = "..."
'
```

### Importante:
- No actives la opción "Crear archivo .env"
- Asegúrate de incluir las comillas simples al inicio y final del valor
- Después de guardar, implementa los cambios para que se apliquen

### Ejecución local (para desarrollo)

Si necesitas ejecutar la aplicación localmente durante el desarrollo:

1. Crea un directorio `.streamlit` en la raíz del proyecto
2. Dentro de él, crea un archivo `secrets.toml` con tus credenciales
3. Ejecuta el proyecto con `streamlit run streamlit_app.py`

Este archivo `.streamlit/secrets.toml` está incluido en `.gitignore` para evitar que se suba a git.