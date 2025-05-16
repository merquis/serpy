# SERPY - Herramienta SEO y Scraping

## 🔐 Configuración de Secretos

### Configuración en GitHub

Para mantener los secretos seguros y seguir las mejores prácticas, se ha implementado un sistema que utiliza los secretos de GitHub en lugar de incluir el archivo `.streamlit/secrets.toml` directamente en el repositorio.

1. En tu repositorio de GitHub, ve a "Settings" > "Secrets and variables" > "Actions"
2. Crea un nuevo secreto llamado `STREAMLIT_SECRETS` 
3. Copia todo el contenido de tu archivo `secrets.toml` y pégalo como valor del secreto

El contenido debe tener este formato (ejemplo):

```toml
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
```

### Construcción de Docker con Secretos

Al construir la imagen Docker con GitHub Actions, ahora se incluirá automáticamente el secreto en la imagen:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: |
          docker build \
            --build-arg STREAMLIT_SECRETS="${{ secrets.STREAMLIT_SECRETS }}" \
            -t serpy:latest .
```

### Ejecución local

Si ejecutas Docker localmente, puedes pasar los secretos de dos formas:

1. **Opción 1**: Pasar todo el archivo como argumento de construcción:
   ```bash
   docker build --build-arg STREAMLIT_SECRETS="$(cat .streamlit/secrets.toml)" -t serpy:latest .
   ```

2. **Opción 2**: Montar el directorio .streamlit al ejecutar:
   ```bash
   docker run -p 8501:8501 -v $(pwd)/.streamlit:/app/.streamlit serpy:latest
   ```

Con estas opciones, no es necesario subir el archivo `.streamlit/secrets.toml` al repositorio Git, manteniendo tus credenciales seguras.