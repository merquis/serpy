#!/usr/bin/env python3
"""Script para probar las importaciones del servicio"""

import sys
import traceback

print("=== Probando importaciones del servicio de imágenes ===")
print(f"Python path: {sys.path}")
print()

# Test 1: Importar settings
try:
    print("1. Probando importar settings...")
    from config.settings import settings
    print("   ✓ Settings importado correctamente")
    print(f"   - APP_NAME: {settings.app_name}")
    print(f"   - REDIS_URL: {settings.redis_url}")
except Exception as e:
    print(f"   ✗ Error importando settings: {e}")
    traceback.print_exc()

print()

# Test 2: Importar core
try:
    print("2. Probando importar core...")
    from app.core import settings, logger, setup_logging
    print("   ✓ Core importado correctamente")
except Exception as e:
    print(f"   ✗ Error importando core: {e}")
    traceback.print_exc()

print()

# Test 3: Importar main
try:
    print("3. Probando importar main...")
    from app.main import app
    print("   ✓ Main importado correctamente")
except Exception as e:
    print(f"   ✗ Error importando main: {e}")
    traceback.print_exc()

print()

# Test 4: Importar celery_app
try:
    print("4. Probando importar celery_app...")
    from app.workers.celery_app import celery_app
    print("   ✓ Celery app importado correctamente")
except Exception as e:
    print(f"   ✗ Error importando celery_app: {e}")
    traceback.print_exc()

print()
print("=== Fin de las pruebas ===")
