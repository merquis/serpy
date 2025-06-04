"""
Core del microservicio - configuración, logging y excepciones
"""
from .config import settings
from .logging import logger, setup_logging
from .exceptions import *

__all__ = ["settings", "logger", "setup_logging"]
