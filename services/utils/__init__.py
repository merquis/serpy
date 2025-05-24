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

from .httpx_service import (
    HttpxService,
    HttpxConfig,
    create_fast_httpx_config,
    create_stealth_httpx_config,
    create_aggressive_httpx_config
)

__all__ = [
    'PlaywrightService',
    'PlaywrightConfig',
    'create_booking_config',
    'create_generic_config',
    'create_fast_config',
    'HttpxService',
    'HttpxConfig',
    'create_fast_httpx_config',
    'create_stealth_httpx_config',
    'create_aggressive_httpx_config'
]
