"""
Utilidades compartidas para servicios
"""
from .playwright_service import (
    PlaywrightService,
    PlaywrightConfig,
    create_booking_config,
    create_generic_config,
    create_fast_config
)

__all__ = [
    'PlaywrightService',
    'PlaywrightConfig',
    'create_booking_config',
    'create_generic_config',
    'create_fast_config'
]
