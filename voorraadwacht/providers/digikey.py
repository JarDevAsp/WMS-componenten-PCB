import time
from urllib.parse import quote

from .base import Provider, ProviderError, StockInfo, parse_int

TOKEN_URL = "https://api.digikey.com/v1/oauth2/token"
DETAILS_URL = "https://api.digikey.com/products/v4/search/{}/productdetails"


class DigikeyProvider(Provider):
    """DigiKey Product Information API v4 – app aanmaken via developer.digikey.com."""

    key = "digikey"
    name = "DigiKey"

    def __init__(self, config):
        super().__init__(config)
        self._token = None
        self._token_expires = 0

    def is_configured(self):
        return bool(self.config.get("DIGIKEY_CLIENT_ID") and self.config.get("DIGIKEY_CLIENT_SECRET"))

    def _access_token(self):
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        data = self._request("POST", TOKEN_URL, data={
            "client_id": self.config["DIGIKEY_CLIENT_ID"],
            "client_secret": self.config["DIGIKEY_CLIENT_SECRET"],
            "grant_type": "client_credentials",
        })
        self._token = data["access_token"]
        self._token_expires = time.time() + int(data.get("expires_in", 600))
        return self._token

    def fetch(self, mpn, supplier_sku=None):
        part = supplier_sku or mpn
        data = self._request("GET", DETAILS_URL.format(quote(part, safe="")), headers={
            "Authorization": f"Bearer {self._access_token()}",
            "X-DIGIKEY-Client-Id": self.config["DIGIKEY_CLIENT_ID"],
            "X-DIGIKEY-Locale-Site": self.config.get("COUNTRY", "BE"),
            "X-DIGIKEY-Locale-Language": "en",
            "X-DIGIKEY-Locale-Currency": self.config.get("CURRENCY", "EUR"),
        })
        product = data.get("Product")
        if not product:
            raise ProviderError(f"DigiKey: '{part}' niet gevonden")
        variations = product.get("ProductVariations") or []
        pricing = (variations[0].get("StandardPricing") if variations else None) or []
        first = min(pricing, key=lambda p: p.get("BreakQuantity", 0)) if pricing else {}
        lead = product.get("ManufacturerLeadWeeks")
        return StockInfo(
            stock=parse_int(product.get("QuantityAvailable")) or 0,
            unit_price=first.get("UnitPrice", product.get("UnitPrice")),
            currency=self.config.get("CURRENCY", "EUR"),
            lead_time=f"{lead} weken" if lead else None,
            product_url=product.get("ProductUrl"),
            supplier_sku=variations[0].get("DigiKeyProductNumber") if variations else None,
        )
