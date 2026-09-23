import pytest

from voorraadwacht.providers.base import parse_int, parse_price
from voorraadwacht.providers.tme import sign


@pytest.mark.parametrize("raw, expected", [
    ("€0,123", 0.123), ("1.234,56 €", 1234.56), ("$1,234.56", 1234.56),
    ("0.45", 0.45), (1.5, 1.5), (None, None), ("", None), ("1.234.5", 1234.5),
])
def test_parse_price(raw, expected):
    assert parse_price(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("1.234 In Stock", 1234), ("0", 0), (57, 57), (None, None), ("Geen", None),
])
def test_parse_int(raw, expected):
    assert parse_int(raw) == expected


def test_tme_signature_is_stable_and_order_independent():
    a = sign("https://api.tme.eu/x.json", {"b": "2", "a": "1"}, "secret")
    b = sign("https://api.tme.eu/x.json", {"a": "1", "b": "2"}, "secret")
    assert a == b and len(a) == 28


def test_connection_error_hides_api_key(monkeypatch):
    import requests
    from voorraadwacht.providers.base import ProviderError
    from voorraadwacht.providers.mouser import MouserProvider

    def boom(*a, **kw):
        raise requests.ConnectionError("Max retries exceeded with url: /api/v1/search?apiKey=GEHEIM123 (x)")
    monkeypatch.setattr(requests, "request", boom)
    with pytest.raises(ProviderError) as exc:
        MouserProvider({"MOUSER_API_KEY": "GEHEIM123"}).fetch("NE555P")
    assert "GEHEIM123" not in str(exc.value)
