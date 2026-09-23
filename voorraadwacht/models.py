from datetime import date, datetime, timedelta

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

ORDER_STATUSES = ["besteld", "bevestigd", "verzonden", "ontvangen", "geannuleerd"]
CLOSED_STATUSES = {"ontvangen", "geannuleerd"}


class Component(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mpn = db.Column(db.String(120), nullable=False)  # fabrikant-artikelnummer
    manufacturer = db.Column(db.String(120))
    description = db.Column(db.String(255))
    alert_threshold = db.Column(db.Integer)  # mail als voorraad hieronder zakt
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

    watches = db.relationship("Watch", back_populates="component", cascade="all, delete-orphan")
    orders = db.relationship("PurchaseOrder", back_populates="component", cascade="all, delete-orphan")

    @property
    def open_orders(self):
        return [o for o in self.orders if o.is_open]

    @property
    def incoming_quantity(self):
        return sum(o.quantity for o in self.open_orders)


class Watch(db.Model):
    """Een component opgevolgd bij één leverancier."""

    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey("component.id"), nullable=False)
    supplier = db.Column(db.String(40), nullable=False)  # sleutel van de provider
    supplier_sku = db.Column(db.String(120))  # bestelnummer bij leverancier (optioneel)
    active = db.Column(db.Boolean, default=True, nullable=False)

    stock = db.Column(db.Integer)
    unit_price = db.Column(db.Float)
    currency = db.Column(db.String(8))
    lead_time = db.Column(db.String(80))
    product_url = db.Column(db.String(500))
    last_checked = db.Column(db.DateTime)
    last_changed = db.Column(db.DateTime)
    last_error = db.Column(db.String(500))

    component = db.relationship("Component", back_populates="watches")
    snapshots = db.relationship(
        "StockSnapshot", back_populates="watch", cascade="all, delete-orphan",
        order_by="StockSnapshot.checked_at.desc()",
    )


class StockSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    watch_id = db.Column(db.Integer, db.ForeignKey("watch.id"), nullable=False)
    checked_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    stock = db.Column(db.Integer)
    unit_price = db.Column(db.Float)
    currency = db.Column(db.String(8))

    watch = db.relationship("Watch", back_populates="snapshots")


class PurchaseOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey("component.id"), nullable=False)
    supplier = db.Column(db.String(120), nullable=False)
    order_number = db.Column(db.String(120))
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float)
    currency = db.Column(db.String(8), default="EUR")
    shipping_cost = db.Column(db.Float)
    order_date = db.Column(db.Date, default=date.today, nullable=False)
    lead_time_days = db.Column(db.Integer)
    expected_date = db.Column(db.Date)  # overschrijft order_date + levertermijn
    status = db.Column(db.String(20), default="besteld", nullable=False)
    received_date = db.Column(db.Date)
    notes = db.Column(db.Text)

    component = db.relationship("Component", back_populates="orders")

    @property
    def is_open(self):
        return self.status not in CLOSED_STATUSES

    @property
    def expected(self):
        if self.expected_date:
            return self.expected_date
        if self.order_date and self.lead_time_days is not None:
            return self.order_date + timedelta(days=self.lead_time_days)
        return None

    @property
    def is_overdue(self):
        return self.is_open and self.expected is not None and self.expected < date.today()

    @property
    def total_cost(self):
        if self.unit_price is None:
            return None
        return self.unit_price * self.quantity + (self.shipping_cost or 0)
