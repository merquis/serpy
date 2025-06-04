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
MONGO_URI=mongodb://serpy:esperanza85@serpy_mongodb:27017/?authSource=admin
MONGO_DB_NAME=serpy
API_BASE_URL=https://serpy.videocursosweb.com
ENVIRONMENT=production
```

**IMPORTANTE**: 
- Si MongoDB está en otro servidor, cambia `serpy_mongodb` por la IP o hostname correcto
- Si MongoDB está en el mismo servidor de EasyPanel pero en otro contenedor, usa el nombre del servicio
- Para MongoDB Atlas o remoto, usa la URI completa proporcionada por el servicio

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
Este es el error que estás viendo actualmente. Soluciones:

1. **Verificar la URI de MongoDB**:
   - La URI debe tener el formato: `mongodb://usuario:contraseña@host:puerto/?authSource=admin`
   - Si MongoDB está en Docker en el mismo servidor, usa el nombre del contenedor/servicio
   - Si está en otro servidor, usa la IP pública o hostname

2. **Verificar accesibilidad**:
   - MongoDB debe estar accesible desde el contenedor de la API
   - El puerto 27017 debe estar abierto si es remoto
   - Las credenciales deben ser correctas

3. **Probar la conexión**:
   - Accede a `/health` para ver el estado de la conexión
   - Los logs mostrarán detalles del error de conexión

### La API no responde
- Verifica los logs en EasyPanel
- Asegúrate de que el puerto 8000 esté configurado correctamente
- Comprueba que las variables de entorno estén configuradas

## Verificación

Una vez desplegado, puedes verificar que funciona correctamente:

1. **Verificar estado de salud**: 
   - Accede a `https://serpy.videocursosweb.com/health`
   - Deberías ver un JSON con el estado de la API y la conexión a MongoDB

2. **Si la base de datos está conectada**:
   - Prueba listar colecciones: `https://serpy.videocursosweb.com/collections`
   - Prueba obtener un post: `https://serpy.videocursosweb.com/posts/68407473fc91e2815c748b71-los-mejores-hoteles-lanzarote-guia-completa-2024`

3. **Si hay problemas de conexión**:
   - Revisa los logs en EasyPanel
   - El endpoint `/health` mostrará detalles del error
   - La API seguirá respondiendo pero sin acceso a datos

4. **Documentación** (solo en modo development):
   - Swagger UI: `https://serpy.videocursosweb.com/docs`
   - ReDoc: `https://serpy.videocursosweb.com/redoc`
