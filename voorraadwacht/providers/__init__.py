from .base import Provider, ProviderError, StockInfo
from .demo import DemoProvider
from .digikey import DigikeyProvider
from .farnell import FarnellProvider
from .mouser import MouserProvider
from .tme import TmeProvider

PROVIDER_CLASSES = [MouserProvider, FarnellProvider, TmeProvider, DigikeyProvider, DemoProvider]


def build_providers(config):
    """Alle leveranciers, ook niet-geconfigureerde (die geven een foutmelding bij controle)."""
    return {cls.key: cls(config) for cls in PROVIDER_CLASSES}


__all__ = ["Provider", "ProviderError", "StockInfo", "build_providers", "PROVIDER_CLASSES"]
