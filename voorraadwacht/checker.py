import logging
from dataclasses import dataclass
from datetime import datetime

from flask import current_app

from .models import Watch, db, StockSnapshot
from .notifier import send_email
from .providers import ProviderError

log = logging.getLogger(__name__)


@dataclass
class StockChange:
    watch: Watch
    old_stock: int
    new_stock: int
    reason: str


def classify_change(old, new, threshold=None, min_pct=20.0):
    """Geeft een reden terug als de wijziging gemeld moet worden, anders None."""
    if old is None or new is None or old == new:
        return None
    if new == 0:
        return "Uitverkocht"
    if old == 0:
        return "Terug op voorraad"
    if threshold is not None:
        if old >= threshold > new:
            return f"Onder drempel ({threshold})"
        if old < threshold <= new:
            return f"Terug boven drempel ({threshold})"
    pct = (new - old) / old * 100
    if abs(pct) >= min_pct:
        return f"{'Gestegen' if pct > 0 else 'Gedaald'} ({pct:+.0f}%)"
    return None


def check_watch(watch, providers, min_pct):
    """Haalt de actuele voorraad op en bewaart die. Geeft een StockChange of None."""
    provider = providers.get(watch.supplier)
    now = datetime.now()
    watch.last_checked = now
    if provider is None or not provider.is_configured():
        watch.last_error = "Leverancier niet geconfigureerd (API-sleutel ontbreekt)"
        return None
    try:
        info = provider.fetch(watch.component.mpn, watch.supplier_sku)
    except ProviderError as exc:
        watch.last_error = str(exc)[:500]
        return None
    except Exception as exc:  # een fout bij één leverancier mag de rest niet stoppen
        log.exception("Onverwachte fout bij %s", watch.supplier)
        watch.last_error = f"Onverwachte fout: {exc}"[:500]
        return None

    old = watch.stock
    watch.last_error = None
    watch.stock = info.stock
    watch.unit_price = info.unit_price
    watch.currency = info.currency
    watch.lead_time = info.lead_time
    watch.product_url = info.product_url or watch.product_url
    if info.supplier_sku and not watch.supplier_sku:
        watch.supplier_sku = info.supplier_sku

    if old != info.stock:
        watch.last_changed = now
        db.session.add(StockSnapshot(
            watch=watch, checked_at=now, stock=info.stock,
            unit_price=info.unit_price, currency=info.currency,
        ))

    reason = classify_change(old, info.stock, watch.component.alert_threshold, min_pct)
    return StockChange(watch, old, info.stock, reason) if reason else None


def run_check(watches=None, notify=True):
    """Controleert alle actieve opvolgingen (of de meegegeven lijst) en mailt de wijzigingen."""
    config = current_app.config
    providers = current_app.extensions["providers"]
    if watches is None:
        watches = Watch.query.filter_by(active=True).all()

    changes = []
    for watch in watches:
        change = check_watch(watch, providers, config["NOTIFY_MIN_CHANGE_PCT"])
        if change:
            changes.append(change)
    db.session.commit()

    if changes and notify:
        try:
            send_email(config, *build_change_email(changes, providers))
        except Exception:
            log.exception("E-mail versturen mislukt")
    log.info("Controle klaar: %d opvolgingen, %d meldingen", len(watches), len(changes))
    return changes


def build_change_email(changes, providers):
    subject = f"Voorraadwijziging: {len(changes)} component(en)"
    lines = ["De voorraad bij leveranciers is gewijzigd:", ""]
    for c in changes:
        comp = c.watch.component
        supplier = providers[c.watch.supplier].name if c.watch.supplier in providers else c.watch.supplier
        lines.append(f"• {comp.mpn} ({comp.manufacturer or '-'}) bij {supplier}: "
                     f"{c.old_stock} → {c.new_stock} stuks – {c.reason}")
        if c.watch.unit_price is not None:
            lines.append(f"    Prijs: {c.watch.unit_price:.4f} {c.watch.currency or ''}"
                         f"   Levertermijn: {c.watch.lead_time or '-'}")
        if c.watch.product_url:
            lines.append(f"    {c.watch.product_url}")
        for order in comp.open_orders:
            expected = order.expected.strftime("%d/%m/%Y") if order.expected else "onbekend"
            lines.append(f"    Openstaande bestelling: {order.quantity} st. bij {order.supplier}, verwacht {expected}")
        lines.append("")
    return subject, "\n".join(lines)
