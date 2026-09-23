import hashlib
import time

from .base import Provider, StockInfo


class DemoProvider(Provider):
    """Nepleverancier om de app zonder API-sleutels uit te proberen.

    De voorraad verandert elk uur op een voorspelbare manier en is soms 0.
    """

    key = "demo"
    name = "Demo-leverancier"

    def is_configured(self):
        return bool(self.config.get("DEMO_PROVIDER_ENABLED", True))

    def fetch(self, mpn, supplier_sku=None):
        hour = int(time.time() // 3600)
        seed = int(hashlib.sha256(f"{mpn}:{hour}".encode()).hexdigest(), 16)
        stock = 0 if seed % 7 == 0 else seed % 5000
        return StockInfo(
            stock=stock,
            unit_price=round(0.05 + (seed % 300) / 100, 3),
            currency="EUR",
            lead_time=f"{seed % 20 + 1} weken",
            product_url=None,
            supplier_sku=supplier_sku or f"DEMO-{mpn}",
        )
