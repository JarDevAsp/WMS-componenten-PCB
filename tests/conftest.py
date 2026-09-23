import pytest

from voorraadwacht import create_app
from voorraadwacht.models import db


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        "SMTP_HOST": "",
        "BASIC_AUTH_USER": "",
        "BASIC_AUTH_PASSWORD": "",
    })
    with app.app_context():
        yield app
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()
