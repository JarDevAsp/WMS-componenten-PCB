from voorraadwacht.models import Component, PurchaseOrder, Watch


def test_full_flow(client):
    assert client.get("/").status_code == 200

    r = client.post("/componenten/nieuw", data={"mpn": "LM358", "manufacturer": "TI",
                                                  "alert_threshold": "100", "suppliers": ["demo"]})
    assert r.status_code == 302
    comp = Component.query.one()
    assert [w.supplier for w in comp.watches] == ["demo"]

    client.post(f"/componenten/{comp.id}/controleren")
    assert Watch.query.one().stock is not None

    page = client.get(f"/componenten/{comp.id}").get_data(as_text=True)
    assert "Demo-leverancier" in page

    r = client.post("/bestellingen/nieuw", data={
        "component_id": comp.id, "supplier": "Farnell", "quantity": "500", "unit_price": "0,21",
        "order_date": "2026-09-01", "lead_time_days": "10", "status": "besteld"})
    assert r.status_code == 302
    order = PurchaseOrder.query.one()
    assert order.unit_price == 0.21 and str(order.expected) == "2026-09-11"
    assert "LM358" in client.get("/").get_data(as_text=True)

    client.post(f"/bestellingen/{order.id}/ontvangen")
    assert PurchaseOrder.query.one().status == "ontvangen"
    assert "LM358" not in client.get("/bestellingen").get_data(as_text=True)


def test_invalid_edit_does_not_crash(client):
    client.post("/componenten/nieuw", data={"mpn": "A1"})
    comp = Component.query.one()
    r = client.post(f"/componenten/{comp.id}/bewerken", data={"mpn": ""})
    assert r.status_code == 200 and "verplicht" in r.get_data(as_text=True)

    client.post("/bestellingen/nieuw", data={"component_id": comp.id, "supplier": "x", "quantity": "1"})
    order = PurchaseOrder.query.one()
    r = client.post(f"/bestellingen/{order.id}/bewerken", data={"component_id": "", "supplier": "", "quantity": ""})
    assert r.status_code == 200
    assert PurchaseOrder.query.one().supplier == "x"


def test_basic_auth(tmp_path):
    from voorraadwacht import create_app
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'a.db'}",
                      "BASIC_AUTH_USER": "inkoop", "BASIC_AUTH_PASSWORD": "geheim"})
    c = app.test_client()
    assert c.get("/").status_code == 401
    assert c.get("/", auth=("inkoop", "geheim")).status_code == 200
