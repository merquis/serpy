# Configuración de SERPY API en EasyPanel

## Configuración del Servicio

### 1. Información General
- **Nombre del servicio**: serpy-api
- **Tipo**: App (Docker)

### 2. Configuración de GitHub
- **Repository**: Tu repositorio de GitHub
- **Branch**: main (o la rama que uses)
- **Build Context**: `./api` (MUY IMPORTANTE: debe apuntar al directorio api)

### 3. Variables de Entorno
Configura las siguientes variables en EasyPanel:

```
MONGO_URI=mongodb://serpy:tu_password@tu_host:27017/?authSource=admin
MONGO_DB_NAME=serpy
API_BASE_URL=https://serpy.videocursosweb.com
ENVIRONMENT=production
```

### 4. Configuración de Red
- **Puerto interno**: 8000
- **Dominio**: serpy.videocursosweb.com (o el que prefieras)
- **HTTPS**: Activar

### 5. Configuración de Build
- **Dockerfile Path**: `Dockerfile` (relativo al Build Context)
- **Build Args**: No necesarios

### 6. Recursos (opcional)
- **CPU**: 0.5 - 1 core
- **RAM**: 512MB - 1GB (dependiendo del tráfico)

## Solución de Problemas

### Error: "path not found" o "unable to prepare context"
Este es el error más común en EasyPanel. Soluciones:

1. **Configurar Build Context correctamente**:
   - En la configuración de GitHub en EasyPanel, establece Build Context como `./api`
   - NO dejes el Build Context vacío o como `/`

2. **Usar Dockerfile alternativo**:
   - Si el error persiste, usa `Dockerfile.easypanel` en lugar de `Dockerfile`
   - En EasyPanel, cambia el Dockerfile Path a `Dockerfile.easypanel`

3. **Verificar la estructura del repositorio**:
   ```
   tu-repositorio/
   ├── api/
   │   ├── Dockerfile
   │   ├── main.py
   │   ├── requirements.txt
   │   └── config/
   │       ├── __init__.py
   │       └── settings.py
   └── otros-directorios/
   ```

### Error de conexión a MongoDB
- Verifica que la URI de MongoDB sea correcta
- Asegúrate de que MongoDB sea accesible desde EasyPanel
- Si usas MongoDB en Docker, usa el nombre del servicio en lugar de localhost

### La API no responde
- Verifica los logs en EasyPanel
- Asegúrate de que el puerto 8000 esté configurado correctamente
- Comprueba que las variables de entorno estén configuradas

## Verificación

Una vez desplegado, puedes verificar que funciona correctamente:

1. Accede a `https://tu-dominio.com/health`
2. Deberías ver un JSON con el estado de la API
3. Si configuraste `ENVIRONMENT=development`, puedes acceder a `/docs` para ver la documentación Swagger
