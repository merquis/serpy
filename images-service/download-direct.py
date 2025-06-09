#!/usr/bin/env python3
"""
Script directo de descarga de imágenes
Este archivo existe para compatibilidad con el Dockerfile pero no se usa actualmente.
Toda la funcionalidad de descarga está implementada en app/services/download/
"""

import sys

if __name__ == "__main__":
    print("Este script no se usa actualmente. Use la API REST del servicio.")
    print("Endpoint: POST /api/v1/download/from-collection")
    print("Documentación: http://localhost:8001/docs")
    sys.exit(0)
