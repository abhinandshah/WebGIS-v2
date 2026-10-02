import gzip
import json

import pytest
from flask.sessions import SecureCookieSessionInterface

import app as app_module
from conftest import PARCELS, login


# ---------------------------------------------------------------- auth ----
def test_old_hardcoded_secret_key_cannot_forge_admin(app):
    """S1: the key that shipped in the original ZIP must not work any more."""
    class Old:  # minimal stand-in exposing what the serializer needs
        secret_key = 'your-secret-key-change-in-production'
        config = {'SECRET_KEY_FALLBACKS': None}
    forged = SecureCookieSessionInterface().get_signing_serializer(Old()).dumps(
        {'_user_id': 'admin', '_fresh': True})
    c = app.test_client()
    c.set_cookie('session', forged)
    assert c.get('/dashboard').status_code == 302


def test_weak_or_missing_secret_key_refused(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'your-secret-key-change-in-production')
    with pytest.raises(RuntimeError):
        app_module.create_app()
    monkeypatch.delenv('SECRET_KEY')
    with pytest.raises(RuntimeError):
        app_module.create_app()


def test_default_passwords_no_longer_work(client):
    assert login(client, 'admin', 'admin123').status_code == 401
    assert login(client, 'user', 'user123').status_code == 401


def test_login_success_and_failure(client):
    assert login(client, 'nobody', 'x').status_code == 401
    assert login(client, 'user', 'wrong').status_code == 401
    r = login(client, 'admin', 'admin-test-pass-1')
    assert r.status_code == 200 and r.get_json() == {'success': True, 'role': 'admin'}


@pytest.mark.parametrize('body', ['[]', 'null', '"text"', '{"username":["a"],"password":"x"}',
                                  '{"username":"a"}', '{"username":1,"password":2}', '{not json'])
def test_login_malformed_body_is_400_not_500(client, body):
    r = client.post('/login', data=body, content_type='application/json')
    assert r.status_code == 400


def test_login_form_post_is_400(client):
    assert client.post('/login', data={'username': 'a', 'password': 'b'}).status_code == 400


def test_login_rate_limited_with_json(make_app):
    c = make_app(LOGIN_RATE_LIMIT='3 per minute').test_client()
    codes = [login(c, 'user', f'bad{i}').status_code for i in range(5)]
    assert codes[:3] == [401, 401, 401] and codes[3:] == [429, 429]
    r = login(c, 'user', 'bad')
    assert r.get_json()['success'] is False and 'Too many' in r.get_json()['message']


def test_logout_requires_post(user_client):
    assert user_client.get('/logout').status_code == 302
    assert user_client.get('/dashboard').status_code == 200          # still signed in
    assert user_client.post('/logout').status_code == 302
    assert user_client.get('/dashboard').status_code == 302          # now signed out


def test_pages_redirect_when_anonymous(client):
    for p in ['/dashboard', '/land', '/house', '/survey', '/road', '/weather', '/profile', '/admin']:
        r = client.get(p)
        assert r.status_code == 302 and r.headers['Location'].endswith('/login'), p


def test_api_returns_json_401_when_anonymous(client):
    for p in ['/api/parcels', '/api/roads', '/api/houses', '/api/surveys', '/api/wards',
              '/api/parcel/search?kitta_no=1', '/api/parcel/filter?ward=1']:
        r = client.get(p)
        assert r.status_code == 401 and r.is_json, p


def test_admin_routes_are_role_protected(user_client, admin_client):
    assert user_client.get('/admin').status_code == 403
    r = admin_client.get('/admin')
    assert r.status_code == 200 and b'Total Users' in r.data
    assert b'99.8%' not in r.data and b'>156<' not in r.data      # invented numbers are gone


# ------------------------------------------------------ data exposure -----
def test_geodata_not_served_from_static(client, user_client):
    for p in ['/static/data/land_parcels.geojson', '/static/data/land_parcels.web.geojson',
              '/data/land_parcels.web.geojson', '/static/../data/land_parcels.web.geojson']:
        assert client.get(p).status_code == 404, p
        assert user_client.get(p).status_code == 404, p


def test_no_credentials_in_login_page(client):
    html = client.get('/login').get_data(as_text=True)
    assert 'admin123' not in html and 'user123' not in html and 'Demo Credentials' not in html


def test_security_headers(client):
    r = client.get('/login')
    assert r.headers['X-Content-Type-Options'] == 'nosniff'
    assert r.headers['X-Frame-Options'] == 'DENY'
    assert "frame-ancestors 'none'" in r.headers['Content-Security-Policy']
    assert r.headers['Set-Cookie'] if 'Set-Cookie' in r.headers else True


def test_session_cookie_flags(app):
    assert app.config['SESSION_COOKIE_HTTPONLY'] is True
    assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'


# ---------------------------------------------------------- data API ------
def test_parcels_served_as_file_with_conditional_get(user_client):
    r = user_client.get('/api/parcels')
    assert r.status_code == 200 and r.mimetype == 'application/geo+json'
    assert json.loads(r.data) == PARCELS
    etag = r.headers['ETag']
    r2 = user_client.get('/api/parcels', headers={'If-None-Match': etag})
    assert r2.status_code == 304


def test_large_files_served_pregzipped(user_client, monkeypatch):
    monkeypatch.setattr(app_module, 'GZIP_MIN_BYTES', 10)
    r = user_client.get('/api/parcels', headers={'Accept-Encoding': 'gzip'})
    assert r.headers['Content-Encoding'] == 'gzip' and 'Accept-Encoding' in r.headers['Vary']
    assert json.loads(gzip.decompress(r.data)) == PARCELS
    plain = user_client.get('/api/parcels', headers={'Accept-Encoding': 'identity'})
    assert 'Content-Encoding' not in plain.headers and json.loads(plain.data) == PARCELS


def test_search_and_filter_use_real_property_values(user_client):
    r = user_client.get('/api/parcel/search?kitta_no=12')
    assert [f['properties']['kitta_no'] for f in r.get_json()['features']] == ['12']
    assert user_client.get('/api/parcel/search?kitta_no=999').get_json()['features'] == []
    # numeric ward in the data vs. string in the query, and a feature with null properties
    assert len(user_client.get('/api/parcel/filter?ward=3').get_json()['features']) == 1
    assert len(user_client.get('/api/parcel/filter?ward=4').get_json()['features']) == 1


def test_search_filter_require_parameter(user_client):
    assert user_client.get('/api/parcel/search').status_code == 400
    assert user_client.get('/api/parcel/filter?ward=').status_code == 400


def test_missing_layers_are_503_not_fake_data(user_client):
    for p in ['/api/roads', '/api/houses', '/api/surveys']:
        r = user_client.get(p)
        assert r.status_code == 503 and 'not available' in r.get_json()['error'], p


def test_demo_mode_serves_samples_near_map_centre(make_app):
    c = make_app(DEMO_MODE=True).test_client()
    login(c)
    j = c.get('/api/roads').get_json()
    lon, lat = j['features'][0]['geometry']['coordinates'][0]
    assert abs(lat - 27.4089) < 0.01 and abs(lon - 86.0732) < 0.01   # not 150 km away in Biratnagar


def test_corrupt_layer_file_is_503(make_app, data_dir):
    (data_dir / 'roads.geojson').write_text('{"type": "FeatureColl', encoding='utf-8')
    c = make_app().test_client(); login(c)
    assert c.get('/api/roads').status_code == 503


def test_non_ascii_attributes_read_correctly(make_app, data_dir):
    doc = {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'properties': {'kitta_no': 'क-१'}, 'geometry': None}]}
    (data_dir / 'land_parcels.web.geojson').write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8')
    c = make_app().test_client(); login(c)
    r = c.get('/api/parcel/search?kitta_no=' + 'क-१')
    assert r.get_json()['features'][0]['properties']['kitta_no'] == 'क-१'


def test_geostore_index_reloads_when_file_changes(make_app, data_dir):
    app = make_app(); c = app.test_client(); login(c)
    assert len(c.get('/api/parcel/filter?ward=3').get_json()['features']) == 1
    doc = json.loads((data_dir / 'land_parcels.web.geojson').read_text())
    doc['features'].append({'type': 'Feature', 'properties': {'ward': '3'}, 'geometry': None})
    (data_dir / 'land_parcels.web.geojson').write_text(json.dumps(doc))
    assert len(c.get('/api/parcel/filter?ward=3').get_json()['features']) == 2


def test_wards_from_config(make_app):
    c = make_app(WARD_COUNT=7).test_client(); login(c)
    assert len(c.get('/api/wards').get_json()) == 7


# --------------------------------------------------------- templates ------
@pytest.mark.parametrize('path', ['/dashboard', '/land', '/house', '/survey', '/road', '/weather', '/profile'])
def test_pages_render_with_logo_and_local_assets(user_client, path):
    r = user_client.get(path)
    html = r.get_data(as_text=True)
    assert r.status_code == 200
    assert '/static/image/logo-96.png' in html or '/static/image/logo-256.png' in html, 'logo missing'
    assert 'rel="icon"' in html
    for cdn in ('unpkg.com', 'cdn.jsdelivr.net', 'cdnjs.cloudflare.com', 'code.jquery.com', 'cdn.tailwindcss.com'):
        assert cdn not in html, cdn


def test_login_page_has_logo(client):
    html = client.get('/login').get_data(as_text=True)
    assert '/static/image/logo-256.png' in html


def test_admin_page_has_logo(admin_client):
    assert '/static/image/logo-96.png' in admin_client.get('/admin').get_data(as_text=True)


def test_profile_shows_real_session_time(user_client):
    html = user_client.get('/profile').get_data(as_text=True)
    assert '>now<' not in html and 'Signed in' in html


def test_dashboard_admin_link_only_for_admin(user_client, admin_client):
    assert 'href="/admin"' not in user_client.get('/dashboard').get_data(as_text=True)
    assert 'href="/admin"' in admin_client.get('/dashboard').get_data(as_text=True)


def test_static_assets_exist(client):
    for p in ['/static/image/logo-96.png', '/static/image/logo-256.png', '/static/image/favicon.ico',
              '/static/vendor/leaflet/leaflet.js', '/static/vendor/leaflet/leaflet.css',
              '/static/vendor/bootstrap/bootstrap.min.css', '/static/vendor/bootstrap/bootstrap.bundle.min.js',
              '/static/vendor/fontawesome/css/all.min.css', '/static/vendor/fontawesome/webfonts/fa-solid-900.woff2',
              '/static/js/gis-common.js', '/static/css/style.css']:
        assert client.get(p).status_code == 200, p


def test_store_rejects_path_traversal_but_allows_symlinks(app, data_dir, tmp_path_factory):
    import os
    store = app.extensions['geostore']
    with pytest.raises(FileNotFoundError):
        store.path('../../etc/passwd')
    outside = tmp_path_factory.mktemp('elsewhere') / 'real.geojson'
    outside.write_text(json.dumps(PARCELS))
    os.symlink(outside, data_dir / 'roads.geojson')
    c = app.test_client(); login(c)
    assert c.get('/api/roads').status_code == 200
