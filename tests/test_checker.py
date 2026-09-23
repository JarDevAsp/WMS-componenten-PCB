from datetime import date, timedelta

from voorraadwacht.checker import build_change_email, classify_change, run_check
from voorraadwacht.models import Component, PurchaseOrder, StockSnapshot, Watch, db
from voorraadwacht.providers import StockInfo


def test_classify_change():
    assert classify_change(None, 100) is None  # eerste meting
    assert classify_change(100, 100) is None
    assert classify_change(100, 0) == "Uitverkocht"
    assert classify_change(0, 5) == "Terug op voorraad"
    assert classify_change(100, 90, min_pct=20) is None
    assert classify_change(100, 70, min_pct=20) == "Gedaald (-30%)"
    assert classify_change(100, 150, min_pct=20) == "Gestegen (+50%)"
    assert classify_change(510, 495, threshold=500) == "Onder drempel (500)"
    assert classify_change(495, 510, threshold=500) == "Terug boven drempel (500)"


class FakeProvider:
    key, name = "fake", "Fake"

    def __init__(self, stocks):
        self.stocks = list(stocks)

    def is_configured(self):
        return True

    def fetch(self, mpn, supplier_sku=None):
        return StockInfo(stock=self.stocks.pop(0), unit_price=0.5, currency="EUR", supplier_sku="F-1")


def test_run_check_records_and_notifies(app, monkeypatch):
    sent = []
    monkeypatch.setattr("voorraadwacht.checker.send_email", lambda cfg, s, b: sent.append((s, b)))
    app.extensions["providers"]["fake"] = FakeProvider([1000, 1000, 0])

    comp = Component(mpn="NE555P", manufacturer="TI")
    watch = Watch(component=comp, supplier="fake")
    db.session.add_all([comp, watch, PurchaseOrder(component=comp, supplier="Mouser", quantity=250,
                                                   order_date=date.today(), lead_time_days=14)])
    db.session.commit()

    assert run_check() == []  # eerste meting: geen melding
    assert run_check() == []  # ongewijzigd
    changes = run_check()
    assert [c.reason for c in changes] == ["Uitverkocht"]
    assert watch.stock == 0 and watch.supplier_sku == "F-1"
    assert StockSnapshot.query.count() == 2
    assert len(sent) == 1
    subject, body = sent[0]
    assert "NE555P" in body and "1000 → 0" in body and "250 st. bij Mouser" in body


def test_unconfigured_provider_sets_error(app):
    comp = Component(mpn="X")
    watch = Watch(component=comp, supplier="mouser")
    db.session.add_all([comp, watch])
    db.session.commit()
    run_check(notify=False)
    assert "niet geconfigureerd" in watch.last_error


def test_order_expected_and_overdue():
    order = PurchaseOrder(quantity=1, supplier="x", status="besteld",
                          order_date=date.today() - timedelta(days=20), lead_time_days=10)
    assert order.expected == date.today() - timedelta(days=10)
    assert order.is_overdue
    order.expected_date = date.today() + timedelta(days=3)
    assert not order.is_overdue
    order.status = "ontvangen"
    assert not order.is_open
