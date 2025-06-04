# Solución para el conflicto de dominios

## El problema

Actualmente tienes dos servicios compitiendo por el mismo dominio:
- **Streamlit** (scraper) en `serpy.videocursosweb.com`
- **API** (FastAPI) en `serpy.videocursosweb.com`

Cuando accedes a `https://serpy.videocursosweb.com/posts/...`, el servidor está enviando la petición a Streamlit en lugar de a la API, por eso ves una página en blanco.

## Solución recomendada: Usar un subdominio

### Opción 1: Subdominio para la API (RECOMENDADO)

1. En EasyPanel, configura el servicio API con:
   - **Dominio**: `api.serpy.videocursosweb.com`
   - **Puerto**: 8000
   - **Sin Path Prefix**

2. Actualiza la variable de entorno:
   ```
   API_BASE_URL=https://api.serpy.videocursosweb.com
   ```

3. Las URLs serán:
   - `https://api.serpy.videocursosweb.com/health`
   - `https://api.serpy.videocursosweb.com/collections`
   - `https://api.serpy.videocursosweb.com/posts`
   - `https://api.serpy.videocursosweb.com/posts/68407473fc91e2815c748b71-los-mejores-hoteles-lanzarote-guia-completa-2024`

### Opción 2: Subdominio para Streamlit

1. Mueve Streamlit a `app.serpy.videocursosweb.com`
2. Deja la API en `serpy.videocursosweb.com`
3. Actualiza las configuraciones correspondientes

## Configuración en EasyPanel

### Para la API con subdominio:

1. Ve a la configuración del servicio `serpy-api`
2. En la sección de dominios:
   - Elimina el dominio actual
   - Añade nuevo dominio: `api.serpy.videocursosweb.com`
3. En variables de entorno:
   ```
   API_BASE_URL=https://api.serpy.videocursosweb.com
   ```
4. Guarda y redeploy

### Verificación

Después de configurar el subdominio:

1. Espera que el DNS se propague (puede tardar unos minutos)
2. Prueba: `https://api.serpy.videocursosweb.com/health`
3. Si funciona, prueba: `https://api.serpy.videocursosweb.com/posts/68407473fc91e2815c748b71-los-mejores-hoteles-lanzarote-guia-completa-2024`

## Alternativa: Usar rutas específicas

Si no puedes usar subdominios, configura rutas específicas que no entren en conflicto:

- Streamlit: rutas que NO empiecen con palabras reservadas
- API: rutas específicas como `/posts`, `/hoteles`, `/urls-google`, etc.

Pero esto es más complejo y propenso a errores. **El subdominio es la solución más limpia**.
