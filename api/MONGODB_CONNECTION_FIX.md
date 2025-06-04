# Solución para "Colección 'posts' no disponible"

## El problema

La API está funcionando pero no puede conectarse a MongoDB. Por eso muestra el error "Colección 'posts' no disponible".

## Verificación rápida

1. Accede a: `https://api.videocursosweb.com/health`
   - Verás el estado de la conexión a MongoDB
   - Si dice "database": "disconnected", confirma el problema

## Soluciones

### 1. Verificar el nombre del servicio MongoDB en EasyPanel

La variable `MONGO_URI` actual usa `serpy_mongodb` como host:
```
mongodb://serpy:esperanza85@serpy_mongodb:27017/?authSource=admin
```

**Verifica en EasyPanel**:
- ¿Cuál es el nombre exacto del servicio/contenedor de MongoDB?
- Podría ser: `mongodb`, `serpy-mongodb`, `mongo`, etc.

**Actualiza la variable** con el nombre correcto:
```
MONGO_URI=mongodb://serpy:esperanza85@NOMBRE_CORRECTO:27017/?authSource=admin
```

### 2. Si MongoDB está en otro servidor

Usa la IP pública o hostname:
```
MONGO_URI=mongodb://serpy:esperanza85@IP_PUBLICA:27017/?authSource=admin
```

### 3. Verificar las credenciales

Las credenciales por defecto son:
- Usuario: `serpy`
- Contraseña: `esperanza85`
- Base de datos de autenticación: `admin`

Si cambiaste las credenciales, actualiza la URI.

### 4. Verificar en los logs

En EasyPanel, revisa los logs del servicio API. Busca mensajes como:
```
Error conectando a MongoDB: [detalles del error]
```

Esto te dará pistas específicas del problema.

## Configuración correcta en EasyPanel

### Si MongoDB está en el mismo servidor (Docker):

1. Encuentra el nombre exacto del servicio MongoDB
2. Actualiza la variable:
   ```
   MONGO_URI=mongodb://serpy:esperanza85@[NOMBRE_SERVICIO]:27017/?authSource=admin
   ```

### Si MongoDB está en MongoDB Atlas:

1. Obtén la cadena de conexión de Atlas
2. Actualiza la variable:
   ```
   MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net/?retryWrites=true&w=majority
   ```

## Prueba de conexión

Después de actualizar la configuración:

1. Guarda y redeploy en EasyPanel
2. Accede a: `https://api.videocursosweb.com/health`
3. Deberías ver: `"database": "connected"`
4. Luego prueba: `https://api.videocursosweb.com/posts`

## Nombres comunes de servicios MongoDB en EasyPanel

Prueba estos nombres si no estás seguro:
- `mongodb`
- `mongo`
- `serpy-mongodb`
- `serpy_mongo`
- `database`
- `db`

La clave es que el nombre en la URI coincida exactamente con el nombre del servicio en EasyPanel.
