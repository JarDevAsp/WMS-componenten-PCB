import os


def _bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "ja", "on")


def _float(name, default):
    value = os.environ.get(name)
    return float(value) if value else default


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "verander-mij")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///voorraadwacht.db")

    # Optionele login (HTTP Basic Auth) voor de webinterface
    BASIC_AUTH_USER = os.environ.get("BASIC_AUTH_USER", "")
    BASIC_AUTH_PASSWORD = os.environ.get("BASIC_AUTH_PASSWORD", "")

    # Automatische controle
    SCHEDULER_ENABLED = _bool("SCHEDULER_ENABLED", True)
    CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "60"))
    # Meld een wijziging pas vanaf dit percentage (uitverkocht / terug op voorraad /
    # drempel overschreden wordt altijd gemeld)
    NOTIFY_MIN_CHANGE_PCT = _float("NOTIFY_MIN_CHANGE_PCT", 20.0)

    # E-mail
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_SSL = _bool("SMTP_USE_SSL", False)  # True voor poort 465
    MAIL_FROM = os.environ.get("MAIL_FROM", "")
    MAIL_TO = [a.strip() for a in os.environ.get("MAIL_TO", "").split(",") if a.strip()]

    # Leveranciers (API-sleutels)
    COUNTRY = os.environ.get("COUNTRY", "BE")
    CURRENCY = os.environ.get("CURRENCY", "EUR")
    MOUSER_API_KEY = os.environ.get("MOUSER_API_KEY", "")
    FARNELL_API_KEY = os.environ.get("FARNELL_API_KEY", "")
    FARNELL_STORE = os.environ.get("FARNELL_STORE", "be.farnell.com")
    TME_TOKEN = os.environ.get("TME_TOKEN", "")
    TME_SECRET = os.environ.get("TME_SECRET", "")
    DIGIKEY_CLIENT_ID = os.environ.get("DIGIKEY_CLIENT_ID", "")
    DIGIKEY_CLIENT_SECRET = os.environ.get("DIGIKEY_CLIENT_SECRET", "")
    DEMO_PROVIDER_ENABLED = _bool("DEMO_PROVIDER_ENABLED", True)
