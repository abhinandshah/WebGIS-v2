import json
import os
import sys

import pytest
from werkzeug.security import generate_password_hash

# Configure the environment BEFORE app.py is imported (it builds `app` at import time).
os.environ['SECRET_KEY'] = 'test-secret-key-' + 'x' * 32
os.environ['ADMIN_PASSWORD_HASH'] = generate_password_hash('admin-test-pass-1')
os.environ['USER_PASSWORD_HASH'] = generate_password_hash('user-test-pass-1')
os.environ['COOKIE_SECURE'] = '0'
os.environ['FLASK_DEBUG'] = '0'
os.environ['RATELIMIT_STORAGE_URI'] = 'memory://'
os.environ['LOGIN_RATE_LIMIT'] = '1000 per minute'

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_module  # noqa: E402

PARCELS = {
    'type': 'FeatureCollection',
    'features': [
        {'type': 'Feature', 'properties': {'kitta_no': '12', 'ward': 3, 'zone': 'Residential'},
         'geometry': {'type': 'Polygon', 'coordinates': [[[86.0, 27.4], [86.1, 27.4], [86.1, 27.5], [86.0, 27.4]]]}},
        {'type': 'Feature', 'properties': {'kitta_no': '13', 'ward': '4', 'zone': 'Agricultural'},
         'geometry': {'type': 'Polygon', 'coordinates': [[[86.0, 27.4], [86.1, 27.4], [86.1, 27.5], [86.0, 27.4]]]}},
        {'type': 'Feature', 'properties': None,
         'geometry': {'type': 'Point', 'coordinates': [86.0, 27.4]}},
    ],
}


@pytest.fixture()
def data_dir(tmp_path):
    (tmp_path / 'land_parcels.web.geojson').write_text(json.dumps(PARCELS), encoding='utf-8')
    return tmp_path


@pytest.fixture()
def make_app(data_dir):
    def _make(**overrides):
        cfg = {'DATA_DIR': str(data_dir), 'TESTING': True}
        cfg.update(overrides)
        return app_module.create_app(cfg)
    return _make


@pytest.fixture()
def app(make_app):
    return make_app()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, username='user', password='user-test-pass-1'):
    return client.post('/login', json={'username': username, 'password': password})


@pytest.fixture()
def user_client(client):
    assert login(client).status_code == 200
    return client


@pytest.fixture()
def admin_client(app):
    c = app.test_client()
    assert login(c, 'admin', 'admin-test-pass-1').status_code == 200
    return c
