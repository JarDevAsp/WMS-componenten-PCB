from .base import Provider, ProviderError, StockInfo, parse_int

URL = "https://api.element14.com/catalog/products"


class FarnellProvider(Provider):
    """Farnell / element14 Product Search API – sleutel via partner.element14.com."""

    key = "farnell"
    name = "Farnell"

    def is_configured(self):
        return bool(self.config.get("FARNELL_API_KEY"))

    def fetch(self, mpn, supplier_sku=None):
        term = f"id:{supplier_sku}" if supplier_sku else f"manuPartNum:{mpn}"
        store = self.config.get("FARNELL_STORE", "be.farnell.com")
        data = self._request("GET", URL, params={
            "term": term,
            "storeInfo.id": store,
            "resultsSettings.offset": 0,
            "resultsSettings.numberOfResults": 5,
            "resultsSettings.responseGroup": "large",
            "callInfo.responseDataFormat": "json",
            "callInfo.apiKey": self.config["FARNELL_API_KEY"],
        })
        # Het antwoord heet bv. 'manufacturerPartNumberSearchReturn' of 'premierFarnellPartNumberReturn'
        result = next((v for k, v in data.items() if k.endswith("Return")), None) or {}
        products = result.get("products") or []
        if not products:
            raise ProviderError(f"Farnell: '{supplier_sku or mpn}' niet gevonden")
        product = products[0]

        stock = product.get("stock") or {}
        level = stock.get("level", product.get("inv"))
        prices = product.get("prices") or []
        first = min(prices, key=lambda p: p.get("from", 0)) if prices else {}
        lead = stock.get("leastLeadTime")
        return StockInfo(
            stock=parse_int(level) or 0,
            unit_price=first.get("cost"),
            currency=self.config.get("CURRENCY", "EUR"),
            lead_time=f"{lead} dagen" if lead else None,
            product_url=f"https://{store}/{product['sku']}" if product.get("sku") else None,
            supplier_sku=product.get("sku"),
        )
