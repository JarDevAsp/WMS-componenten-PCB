import logging
import os

import click
from dotenv import load_dotenv
from flask import Flask, Response, request

load_dotenv()

from .config import Config  # noqa: E402  (na load_dotenv)
from .models import db  # noqa: E402
from .providers import build_providers  # noqa: E402


def create_app(overrides=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)
    os.makedirs(app.instance_path, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    db.init_app(app)
    app.extensions["providers"] = build_providers(app.config)

    from .views import bp
    app.register_blueprint(bp)
    _setup_basic_auth(app)

    with app.app_context():
        db.create_all()

    @app.cli.command("check")
    @click.option("--no-mail", is_flag=True, help="Geen e-mail versturen")
    def check_command(no_mail):
        """Controleer nu de voorraad bij alle leveranciers."""
        from .checker import run_check
        changes = run_check(notify=not no_mail)
        click.echo(f"{len(changes)} melding(en)")

    if app.config["SCHEDULER_ENABLED"] and not app.config.get("TESTING"):
        _start_scheduler(app)
    return app


def _setup_basic_auth(app):
    user, password = app.config["BASIC_AUTH_USER"], app.config["BASIC_AUTH_PASSWORD"]
    if not (user and password):
        return

    @app.before_request
    def require_login():
        auth = request.authorization
        if not auth or auth.username != user or auth.password != password:
            return Response("Login vereist", 401, {"WWW-Authenticate": 'Basic realm="Voorraadwacht"'})


def _start_scheduler(app):
    # Bij 'flask run --debug' start de reloader twee processen; enkel het kindproces plant.
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    from apscheduler.schedulers.background import BackgroundScheduler
    from .checker import run_check

    def job():
        with app.app_context():
            run_check()

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(job, "interval", minutes=app.config["CHECK_INTERVAL_MINUTES"],
                      id="stock-check", max_instances=1, coalesce=True)
    scheduler.start()
    app.extensions["scheduler"] = scheduler
