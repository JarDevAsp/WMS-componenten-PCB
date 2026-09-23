import re
from dataclasses import dataclass

import requests

TIMEOUT = 20


@dataclass
class StockInfo:
    stock: int | None
    unit_price: float | None = None  # prijs bij de kleinste afnamehoeveelheid
    currency: str | None = None
    lead_time: str | None = None
    product_url: str | None = None
    supplier_sku: str | None = None


class ProviderError(Exception):
    pass


class Provider:
    key = ""
    name = ""

    def __init__(self, config):
        self.config = config

    def is_configured(self) -> bool:
        return True

    def fetch(self, mpn: str, supplier_sku: str | None = None) -> StockInfo:
        raise NotImplementedError

    def _request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", TIMEOUT)
        try:
            response = requests.request(method, url, **kwargs)
        except requests.RequestException as exc:
            # querystring weglaten: die kan de API-sleutel bevatten
            detail = re.sub(r"\?[^\s)'\"]*", "", str(exc))
            raise ProviderError(f"{self.name}: verbinding mislukt ({detail})") from exc
        if response.status_code >= 400:
            raise ProviderError(f"{self.name}: HTTP {response.status_code} – {response.text[:200]}")
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderError(f"{self.name}: onverwacht antwoord (geen JSON)") from exc


def parse_int(value):
    """'1.234 In Stock' -> 1234, None/'' -> None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r"\d[\d.,\s]*", str(value))
    if not match:
        return None
    return int(re.sub(r"\D", "", match.group()))


def parse_price(value):
    """Leest prijzen zoals '€0,123', '1.234,56 €' of '$1,234.56'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = re.sub(r"[^\d.,]", "", str(value))
    if not text:
        return None
    if "," in text and "." in text:
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        text = text.replace(thousands, "").replace(decimal, ".")
    else:
        text = text.replace(",", ".")
        if text.count(".") > 1:
            head, _, tail = text.rpartition(".")
            text = head.replace(".", "") + "." + tail
    try:
        return float(text)
    except ValueError:
        return None
