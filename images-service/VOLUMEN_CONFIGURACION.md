# Configuración del Volumen de Imágenes

## Resumen de cambios

Se ha configurado un volumen Docker para que las imágenes descargadas se almacenen directamente en el VPS en lugar de dentro del contenedor Docker.

### Cambios realizados:

1. **docker-compose.yml**: Actualizado el volumen de `/var/www/images:/images` a `/root/images:/images`
2. **Scripts creados**:
   - `setup-images-volume.sh`: Configura el volumen y reinicia el servicio
   - `descargar-imagenes-vps.sh`: Script mejorado para descargar imágenes con verificación
   - `verificar-volumen-imagenes.sh`: Verifica el estado del volumen y la configuración

## Estructura de almacenamiento

Las imágenes ahora se guardan en:
- **En el VPS**: `/root/images/`
- **Dentro del contenedor**: `/images/` (mapeado al directorio del VPS)

La estructura de carpetas será:
```
/root/images/
├── serpy_db/
│   ├── hotels/
│   │   ├── {document_id}-{search_field}/
│   │   │   ├── image1.jpg
│   │   │   ├── image2.jpg
│   │   │   └── ...
│   └── other_collections/
└── other_databases/
```

## Instrucciones de uso

### 1. Aplicar la nueva configuración (ejecutar en el VPS):

```bash
# Navegar al directorio donde está tu proyecto
# Por ejemplo, si está en /root/app:
cd /root/app/images-service

# O si está en otra ubicación, ajusta la ruta:
# cd /ruta/a/tu/proyecto/images-service

# Hacer el script ejecutable y ejecutarlo
chmod +x setup-images-volume.sh
./setup-images-volume.sh
```

### 2. Verificar que el volumen está configurado correctamente:

```bash
chmod +x verificar-volumen-imagenes.sh
./verificar-volumen-imagenes.sh
```

### 3. Descargar imágenes:

```bash
chmod +x descargar-imagenes-vps.sh
./descargar-imagenes-vps.sh
```

### 4. Verificar las imágenes descargadas:

```bash
# Ver estructura de carpetas
tree -L 3 /root/images/

# Contar total de imágenes
find /root/images -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.webp" \) | wc -l

# Ver tamaño total
du -sh /root/images/

# Ver las últimas imágenes descargadas
find /root/images -type f -mmin -10 -ls
```

## Comandos útiles

### Ver logs del servicio:
```bash
docker logs -f serpy-images-service
```

### Reiniciar el servicio:
```bash
cd /root/serpy/images-service
docker-compose restart
```

### Limpiar imágenes antiguas (opcional):
```bash
# Eliminar imágenes de más de 30 días
find /root/images -type f -mtime +30 -delete
```

## Ventajas de esta configuración

1. **Persistencia**: Las imágenes no se pierden si se elimina o recrea el contenedor
2. **Acceso directo**: Puedes acceder a las imágenes directamente desde el VPS sin entrar al contenedor
3. **Gestión simplificada**: Facilita hacer backups, mover archivos, etc.
4. **Espacio**: Las imágenes no ocupan espacio dentro del contenedor Docker

## Notas importantes

- El directorio `/root/images` debe tener permisos adecuados (755)
- El servicio debe reiniciarse después de cambiar la configuración del volumen
- Las imágenes descargadas anteriormente dentro del contenedor no se migran automáticamente
