from datetime import date, datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from .checker import run_check
from .models import ORDER_STATUSES, Component, PurchaseOrder, Watch, db

bp = Blueprint("main", __name__)


# ---------- hulpfuncties voor formulieren ----------

def _str(name):
    value = request.form.get(name, "").strip()
    return value or None


def _int(name):
    value = _str(name)
    return int(value) if value is not None else None


def _float(name):
    value = _str(name)
    return float(value.replace(",", ".")) if value is not None else None


def _date(name):
    value = _str(name)
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


@bp.app_context_processor
def inject_globals():
    providers = current_app.extensions["providers"]
    return {
        "providers": providers,
        "supplier_name": lambda key: providers[key].name if key in providers else key,
        "order_statuses": ORDER_STATUSES,
        "today": date.today(),
    }


@bp.app_template_filter("dt")
def format_datetime(value):
    return value.strftime("%d/%m/%Y %H:%M") if value else "–"


@bp.app_template_filter("d")
def format_date(value):
    return value.strftime("%d/%m/%Y") if value else "–"


@bp.app_template_filter("money")
def format_money(value, currency=""):
    if value is None:
        return "–"
    return f"{value:,.4f}".rstrip("0").rstrip(".").replace(",", " ").replace(".", ",") + (f" {currency}" if currency else "")


# ---------- dashboard ----------

@bp.route("/")
def dashboard():
    components = Component.query.order_by(Component.mpn).all()
    open_orders = [o for o in PurchaseOrder.query.all() if o.is_open]
    open_orders.sort(key=lambda o: (o.expected is None, o.expected or date.max))
    errors = Watch.query.filter(Watch.last_error.isnot(None), Watch.active.is_(True)).count()
    used = {w.supplier for c in components for w in c.watches if w.active}
    columns = [key for key in current_app.extensions["providers"] if key in used]
    return render_template("dashboard.html", components=components, open_orders=open_orders,
                           errors=errors, columns=columns)


@bp.post("/controleren")
def check_all():
    changes = run_check()
    flash(f"Controle uitgevoerd: {len(changes)} melding(en).", "ok")
    return redirect(request.referrer or url_for("main.dashboard"))


# ---------- componenten ----------

def _fill_component(component):
    component.mpn = _str("mpn")
    component.manufacturer = _str("manufacturer")
    component.description = _str("description")
    component.alert_threshold = _int("alert_threshold")
    component.notes = _str("notes")


@bp.route("/componenten/nieuw", methods=["GET", "POST"])
def component_new():
    component = Component()
    if request.method == "POST":
        _fill_component(component)
        if not component.mpn:
            flash("Artikelnummer is verplicht.", "error")
        else:
            db.session.add(component)
            for key in request.form.getlist("suppliers"):
                db.session.add(Watch(component=component, supplier=key))
            db.session.commit()
            flash("Component toegevoegd.", "ok")
            return redirect(url_for("main.component_detail", component_id=component.id))
    return render_template("component_form.html", component=component)


@bp.route("/componenten/<int:component_id>")
def component_detail(component_id):
    component = db.get_or_404(Component, component_id)
    return render_template("component_detail.html", component=component)


@bp.route("/componenten/<int:component_id>/bewerken", methods=["GET", "POST"])
def component_edit(component_id):
    component = db.get_or_404(Component, component_id)
    if request.method == "POST":
        _fill_component(component)
        if not component.mpn:
            db.session.rollback()
            flash("Artikelnummer is verplicht.", "error")
        else:
            db.session.commit()
            flash("Component bijgewerkt.", "ok")
            return redirect(url_for("main.component_detail", component_id=component.id))
    return render_template("component_form.html", component=component)


@bp.post("/componenten/<int:component_id>/verwijderen")
def component_delete(component_id):
    component = db.get_or_404(Component, component_id)
    db.session.delete(component)
    db.session.commit()
    flash(f"{component.mpn} verwijderd.", "ok")
    return redirect(url_for("main.dashboard"))


@bp.post("/componenten/<int:component_id>/controleren")
def component_check(component_id):
    component = db.get_or_404(Component, component_id)
    changes = run_check([w for w in component.watches if w.active])
    flash(f"Voorraad opgehaald ({len(changes)} melding(en)).", "ok")
    return redirect(url_for("main.component_detail", component_id=component.id))


@bp.post("/componenten/<int:component_id>/leveranciers")
def watch_add(component_id):
    component = db.get_or_404(Component, component_id)
    supplier = _str("supplier")
    if supplier not in current_app.extensions["providers"]:
        abort(400)
    db.session.add(Watch(component=component, supplier=supplier, supplier_sku=_str("supplier_sku")))
    db.session.commit()
    return redirect(url_for("main.component_detail", component_id=component.id))


@bp.post("/opvolgingen/<int:watch_id>/aan-uit")
def watch_toggle(watch_id):
    watch = db.get_or_404(Watch, watch_id)
    watch.active = not watch.active
    db.session.commit()
    return redirect(url_for("main.component_detail", component_id=watch.component_id))


@bp.post("/opvolgingen/<int:watch_id>/verwijderen")
def watch_delete(watch_id):
    watch = db.get_or_404(Watch, watch_id)
    component_id = watch.component_id
    db.session.delete(watch)
    db.session.commit()
    return redirect(url_for("main.component_detail", component_id=component_id))


# ---------- bestellingen ----------

def _fill_order(order):
    order.component_id = _int("component_id")
    order.supplier = _str("supplier")
    order.order_number = _str("order_number")
    order.quantity = _int("quantity")
    order.unit_price = _float("unit_price")
    order.currency = _str("currency") or "EUR"
    order.shipping_cost = _float("shipping_cost")
    order.order_date = _date("order_date") or date.today()
    order.lead_time_days = _int("lead_time_days")
    order.expected_date = _date("expected_date")
    order.status = _str("status") or "besteld"
    order.received_date = _date("received_date")
    order.notes = _str("notes")
    if order.status == "ontvangen" and not order.received_date:
        order.received_date = date.today()


def _save_order(order, is_new):
    try:
        _fill_order(order)
    except ValueError:
        db.session.rollback()
        flash("Controleer de ingevulde getallen en datums.", "error")
        return None
    if not (order.component_id and order.supplier and order.quantity):
        db.session.rollback()
        flash("Component, leverancier en aantal zijn verplicht.", "error")
        return None
    if is_new:
        db.session.add(order)
    db.session.commit()
    flash("Bestelling opgeslagen.", "ok")
    return redirect(url_for("main.orders"))


@bp.route("/bestellingen")
def orders():
    show = request.args.get("toon", "open")
    query = PurchaseOrder.query.order_by(PurchaseOrder.order_date.desc())
    items = query.all()
    if show == "open":
        items = [o for o in items if o.is_open]
    return render_template("orders.html", orders=items, show=show)


@bp.route("/bestellingen/nieuw", methods=["GET", "POST"])
def order_new():
    order = PurchaseOrder(order_date=date.today(), status="besteld", currency="EUR",
                          component_id=request.args.get("component_id", type=int))
    if request.method == "POST":
        response = _save_order(order, is_new=True)
        if response:
            return response
    return render_template("order_form.html", order=order,
                           components=Component.query.order_by(Component.mpn).all())


@bp.route("/bestellingen/<int:order_id>/bewerken", methods=["GET", "POST"])
def order_edit(order_id):
    order = db.get_or_404(PurchaseOrder, order_id)
    if request.method == "POST":
        response = _save_order(order, is_new=False)
        if response:
            return response
    return render_template("order_form.html", order=order,
                           components=Component.query.order_by(Component.mpn).all())


@bp.post("/bestellingen/<int:order_id>/ontvangen")
def order_received(order_id):
    order = db.get_or_404(PurchaseOrder, order_id)
    order.status = "ontvangen"
    order.received_date = date.today()
    db.session.commit()
    flash("Bestelling gemarkeerd als ontvangen.", "ok")
    return redirect(request.referrer or url_for("main.orders"))


@bp.post("/bestellingen/<int:order_id>/verwijderen")
def order_delete(order_id):
    order = db.get_or_404(PurchaseOrder, order_id)
    db.session.delete(order)
    db.session.commit()
    flash("Bestelling verwijderd.", "ok")
    return redirect(url_for("main.orders"))
