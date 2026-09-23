import base64
import hashlib
import hmac
from urllib.parse import quote, urlencode

from .base import Provider, ProviderError, StockInfo, parse_int

URL = "https://api.tme.eu/Products/GetPricesAndStocks.json"


def sign(url, params, secret):
    """HMAC-SHA1 handtekening zoals beschreven in de TME API-documentatie."""
    query = urlencode(sorted(params.items()), quote_via=quote)
    base = "&".join(["POST", quote(url, safe=""), quote(query, safe="")])
    digest = hmac.new(secret.encode(), base.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


class TmeProvider(Provider):
    """TME (Polen) – token en secret via developers.tme.eu."""

    key = "tme"
    name = "TME"

    def is_configured(self):
        return bool(self.config.get("TME_TOKEN") and self.config.get("TME_SECRET"))

    def fetch(self, mpn, supplier_sku=None):
        symbol = supplier_sku or mpn  # TME werkt met eigen 'symbolen'
        params = {
            "Token": self.config["TME_TOKEN"],
            "Country": self.config.get("COUNTRY", "BE"),
            "Currency": self.config.get("CURRENCY", "EUR"),
            "Language": "EN",
            "SymbolList[0]": symbol,
        }
        params["ApiSignature"] = sign(URL, params, self.config["TME_SECRET"])
        data = self._request("POST", URL, data=params)
        if data.get("Status") != "OK":
            raise ProviderError(f"TME: {data.get('Status')} {data.get('Error', '')}".strip())
        products = (data.get("Data") or {}).get("ProductList") or []
        if not products:
            raise ProviderError(f"TME: '{symbol}' niet gevonden")
        product = products[0]
        prices = product.get("PriceList") or []
        first = min(prices, key=lambda p: p.get("Amount", 0)) if prices else {}
        return StockInfo(
            stock=parse_int(product.get("Amount")) or 0,
            unit_price=first.get("PriceValue"),
            currency=data["Data"].get("Currency"),
            product_url=f"https://www.tme.eu/be/nl/details/{quote(product.get('Symbol', symbol).lower())}/",
            supplier_sku=product.get("Symbol"),
        )
