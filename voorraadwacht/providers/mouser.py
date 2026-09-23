from .base import Provider, ProviderError, StockInfo, parse_int, parse_price

URL = "https://api.mouser.com/api/v1/search/partnumber"


class MouserProvider(Provider):
    """Mouser Search API – sleutel aanvragen via mouser.be > My Account > APIs."""

    key = "mouser"
    name = "Mouser"

    def is_configured(self):
        return bool(self.config.get("MOUSER_API_KEY"))

    def fetch(self, mpn, supplier_sku=None):
        part = supplier_sku or mpn
        data = self._request(
            "POST", URL,
            params={"apiKey": self.config["MOUSER_API_KEY"]},
            json={"SearchByPartRequest": {"mouserPartNumber": part, "partSearchOptions": "Exact"}},
        )
        if data.get("Errors"):
            raise ProviderError(f"Mouser: {data['Errors'][0].get('Message', data['Errors'])}")
        parts = (data.get("SearchResults") or {}).get("Parts") or []
        match = _pick(parts, part)
        if match is None:
            raise ProviderError(f"Mouser: '{part}' niet gevonden")

        breaks = match.get("PriceBreaks") or []
        first = min(breaks, key=lambda b: b.get("Quantity", 0)) if breaks else {}
        return StockInfo(
            stock=parse_int(match.get("AvailabilityInStock")) or 0,
            unit_price=parse_price(first.get("Price")),
            currency=first.get("Currency"),
            lead_time=match.get("LeadTime"),
            product_url=match.get("ProductDetailUrl"),
            supplier_sku=match.get("MouserPartNumber"),
        )


def _pick(parts, wanted):
    wanted = wanted.upper()
    for p in parts:
        if wanted in ((p.get("MouserPartNumber") or "").upper(), (p.get("ManufacturerPartNumber") or "").upper()):
            return p
    return parts[0] if parts else None
