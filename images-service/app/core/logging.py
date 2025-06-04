"""
Sistema de logging estructurado para el microservicio
"""
import structlog
import logging
import sys
from typing import Any, Dict
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_file: Path = None) -> None:
    """
    Configura el sistema de logging estructurado
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Archivo opcional para guardar logs
    """
    # Configurar el nivel de logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Procesadores para structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Añadir procesador JSON para producción
    if log_level != "DEBUG":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Configurar structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Obtiene un logger configurado
    
    Args:
        name: Nombre del logger (generalmente __name__)
        
    Returns:
        Logger configurado con structlog
    """
    return structlog.get_logger(name)


class LoggerAdapter:
    """Adaptador para añadir contexto consistente a los logs"""
    
    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger
        self._context: Dict[str, Any] = {}
    
    def bind(self, **kwargs) -> "LoggerAdapter":
        """Añade contexto permanente al logger"""
        self._context.update(kwargs)
        self.logger = self.logger.bind(**self._context)
        return self
    
    def unbind(self, *keys) -> "LoggerAdapter":
        """Elimina contexto del logger"""
        for key in keys:
            self._context.pop(key, None)
        self.logger = structlog.get_logger().bind(**self._context)
        return self
    
    def with_context(self, **kwargs):
        """Context manager para contexto temporal"""
        class ContextManager:
            def __init__(self, adapter, context):
                self.adapter = adapter
                self.context = context
                self.original_logger = None
            
            def __enter__(self):
                self.original_logger = self.adapter.logger
                self.adapter.logger = self.adapter.logger.bind(**self.context)
                return self.adapter
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.adapter.logger = self.original_logger
        
        return ContextManager(self, kwargs)
    
    # Métodos de logging
    def debug(self, msg: str, **kwargs):
        self.logger.debug(msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        self.logger.info(msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        self.logger.warning(msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        self.logger.error(msg, **kwargs)
    
    def exception(self, msg: str, **kwargs):
        self.logger.exception(msg, **kwargs)


# Logger global para el servicio
logger = LoggerAdapter(get_logger("images-service"))
