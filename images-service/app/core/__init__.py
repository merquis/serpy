"""
Core del microservicio - configuración, logging y excepciones
"""
import sys
from pathlib import Path

# Añadir el directorio raíz al path para importar config
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from config.settings import settings
from .logging import logger, setup_logging
from .exceptions import *

__all__ = ["settings", "logger", "setup_logging"]
