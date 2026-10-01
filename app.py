"""Spatial Wings WebGIS - Flask application.

Configuration comes from environment variables (optionally loaded from a
`.env` file next to this file - run `python tools/init_env.py` to create one).
See README.md for the full list.
"""
import gzip
import json
import logging
import os
import secrets
import shutil
import threading
from datetime import datetime, timedelta, timezone
from functools import wraps

from dotenv import load_dotenv
from flask import (Flask, Response, abort, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

GEOJSON_MIME = 'application/geo+json'
NEPAL_TZ = timezone(timedelta(hours=5, minutes=45))
KNOWN_BAD_KEYS = {'your-secret-key-change-in-production', 'changeme', 'secret'}

# Files at or above GZIP_MIN_BYTES are served pre-gzipped; files at or below
# VALIDATE_LIMIT are parsed once so a corrupt file gives a clean 503.
GZIP_MIN_BYTES = 1_000_000
VALIDATE_LIMIT = 5_000_000


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def env_flag(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


def env_float_pair(name, default):
    try:
        a, b = (float(x) for x in os.environ[name].split(','))
        return (a, b)
    except (KeyError, ValueError):
        return default


def prop(props, *names):
    """First non-empty property value (as stripped text) among `names`."""
    if not isinstance(props, dict):
        return ''
    for name in names:
        value = props.get(name)
        if value not in (None, ''):
            return str(value).strip()
    return ''


# --------------------------------------------------------------------------- #
# GeoJSON store: parse each file once, keep features as compact JSON text
# --------------------------------------------------------------------------- #
class GeoStore:
    """Serves and queries GeoJSON files from a data directory.

    * Whole files are streamed straight from disk (conditional/ETag, gzip) and
      never re-parsed or re-serialised per request.
    * Attribute queries use an index built once per file version. Each feature
      is kept as (properties, compact JSON text), so memory stays close to the
      size of the file rather than the size of the parsed Python objects.
    """

    def __init__(self, data_dir):
        self.data_dir = os.path.abspath(data_dir)
        self._lock = threading.Lock()
        self._index = {}
        self._valid = {}

    def path(self, name):
        # abspath (not realpath) so a symlinked data file still works, while
        # '..' segments can never climb out of the data directory.
        p = os.path.abspath(os.path.join(self.data_dir, name))
        if not p.startswith(self.data_dir + os.sep):
            raise FileNotFoundError(name)
        return p

    @staticmethod
    def _stamp(path):
        st = os.stat(path)
        return (st.st_mtime_ns, st.st_size)

    def index(self, name):
        path = self.path(name)
        stamp = self._stamp(path)
        with self._lock:
            hit = self._index.get(name)
            if hit and hit['stamp'] == stamp:
                return hit['items']
            with open(path, encoding='utf-8') as f:
                doc = json.load(f)
            features = doc.get('features') if isinstance(doc, dict) else None
            if not isinstance(features, list):
                raise ValueError(f'{name} is not a GeoJSON FeatureCollection')
            items = []
            for feat in features:
                if not isinstance(feat, dict):
                    continue
                props = feat.get('properties')
                items.append((props if isinstance(props, dict) else {},
                              json.dumps(feat, separators=(',', ':'), ensure_ascii=False)))
            self._index[name] = {'stamp': stamp, 'items': items}
            return items

    def validate(self, name):
        """Parse small files once per version; raise ValueError if corrupt."""
        path = self.path(name)
        if os.path.getsize(path) > VALIDATE_LIMIT:
            return
        stamp = self._stamp(path)
        if self._valid.get(name) == stamp:
            return
        self.index(name)
        self._valid[name] = stamp

    def ensure_gzip(self, path):
        """Return a .gz sibling of `path`, (re)building it when stale."""
        gz = path + '.gz'
        with self._lock:
            if os.path.isfile(gz) and os.path.getmtime(gz) >= os.path.getmtime(path):
                return gz
            tmp = f'{gz}.{os.getpid()}.tmp'
            with open(path, 'rb') as src, gzip.open(tmp, 'wb', compresslevel=6) as dst:
                shutil.copyfileobj(src, dst)
            os.replace(tmp, gz)
            return gz

    @staticmethod
    def collection(items):
        return ('{"type":"FeatureCollection","features":['
                + ','.join(text for _, text in items) + ']}')


# --------------------------------------------------------------------------- #
# Demo data (only ever served when DEMO_MODE=1)
# --------------------------------------------------------------------------- #
def _fc(features):
    return {'type': 'FeatureCollection', 'features': features}


def sample_parcels(c):
    lat, lon = c

    def box(dx, dy, w=0.0007, h=0.0005):
        return [[[lon + dx, lat + dy], [lon + dx + w, lat + dy], [lon + dx + w, lat + dy + h],
                 [lon + dx, lat + dy + h], [lon + dx, lat + dy]]]
    return _fc([
        {'type': 'Feature', 'properties': {'kitta_no': '1001', 'ward': '1', 'zone': 'Residential', 'area': '500 sq.m'},
         'geometry': {'type': 'Polygon', 'coordinates': box(0, 0)}},
        {'type': 'Feature', 'properties': {'kitta_no': '1002', 'ward': '1', 'zone': 'Commercial', 'area': '800 sq.m'},
         'geometry': {'type': 'Polygon', 'coordinates': box(0.0007, 0)}},
    ])


def sample_houses(c):
    lat, lon = c
    return _fc([{'type': 'Feature',
                 'properties': {'house_no': 'H-001', 'ward': '1', 'street': 'Main Road', 'floors': 2},
                 'geometry': {'type': 'Point', 'coordinates': [lon + 0.0002, lat + 0.0002]}}])


def sample_surveys(c):
    lat, lon = c
    return _fc([{'type': 'Feature',
                 'properties': {'survey_id': 'S-001', 'date': '2025-01-15', 'surveyor': 'GIS Team', 'status': 'Completed'},
                 'geometry': {'type': 'Point', 'coordinates': [lon + 0.0004, lat + 0.0003]}}])


def sample_roads(c):
    lat, lon = c
    return _fc([{'type': 'Feature',
                 'properties': {'road_name': 'Main Road', 'road_type': 'Primary', 'width': '12m', 'status': 'Paved'},
                 'geometry': {'type': 'LineString',
                              'coordinates': [[lon - 0.001, lat - 0.001], [lon + 0.001, lat + 0.0005]]}}])


# --------------------------------------------------------------------------- #
# Configuration loading
# --------------------------------------------------------------------------- #
def load_secret_key(debug):
    key = os.environ.get('SECRET_KEY', '').strip()
    if key:
        if key in KNOWN_BAD_KEYS or len(key) < 32:
            raise RuntimeError('SECRET_KEY is too weak. Use at least 32 random characters '
                               '(python -c "import secrets; print(secrets.token_hex(32))").')
        return key
    if debug:
        logging.getLogger(__name__).warning(
            'SECRET_KEY not set - using a temporary key (sessions reset on restart). '
            'Run `python tools/init_env.py` to create a permanent one.')
        return secrets.token_hex(32)
    raise RuntimeError('SECRET_KEY is not set. Run `python tools/init_env.py` or set it in the environment.')


def load_users():
    spec = (('admin', 'admin', 'Admin User', 'ADMIN_PASSWORD_HASH'),
            ('user', 'user', 'Regular User', 'USER_PASSWORD_HASH'))
    users = {}
    for username, role, name, var in spec:
        pw_hash = os.environ.get(var, '').strip()
        if pw_hash:
            users[username] = {'password_hash': pw_hash, 'role': role, 'name': name}
    if not users:
        raise RuntimeError('No users configured. Run `python tools/init_env.py` '
                           '(sets ADMIN_PASSWORD_HASH / USER_PASSWORD_HASH).')
    return users


class User(UserMixin):
    def __init__(self, username, role, name):
        self.id = username
        self.role = role
        self.name = name


# --------------------------------------------------------------------------- #
# Application factory
# --------------------------------------------------------------------------- #
def create_app(overrides=None):
    app = Flask(__name__)
    debug = env_flag('FLASK_DEBUG')

    app.config.update(
        SECRET_KEY=load_secret_key(debug),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        # Secure cookies need HTTPS. Default: on, except in debug (plain http).
        SESSION_COOKIE_SECURE=env_flag('COOKIE_SECURE', default=not debug),
        SEND_FILE_MAX_AGE_DEFAULT=timedelta(hours=1),
        MAX_CONTENT_LENGTH=1 * 1024 * 1024,
        COMPRESS_MIMETYPES=['text/html', 'text/css', 'text/xml', 'text/javascript',
                            'application/json', 'application/javascript',
                            'application/manifest+json', 'image/svg+xml', GEOJSON_MIME],
        LOGIN_RATE_LIMIT=os.environ.get('LOGIN_RATE_LIMIT', '5 per minute;30 per hour'),
        DATA_DIR=os.environ.get('DATA_DIR', os.path.join(BASE_DIR, 'data')),
        PARCELS_FILE=os.environ.get('PARCELS_FILE', ''),
        DEMO_MODE=env_flag('DEMO_MODE'),
        MUNICIPALITY_NAME=os.environ.get('MUNICIPALITY_NAME', 'Biratnagar Municipality'),
        PRODUCT_NAME='Spatial Wings WebGIS',
        MAP_CENTER=env_float_pair('MAP_CENTER', (27.4089, 86.0732)),
        MAP_ZOOM=int(os.environ.get('MAP_ZOOM', '13')),
        WARD_COUNT=int(os.environ.get('WARD_COUNT', '20')),
    )
    if overrides:
        app.config.update(overrides)
    if 'USERS' not in app.config:
        app.config['USERS'] = load_users()

    if env_flag('BEHIND_PROXY'):
        # Trust one reverse proxy so rate limiting sees real client IPs.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    Compress(app)
    limiter = Limiter(get_remote_address, app=app, default_limits=[],
                      storage_uri=os.environ.get('RATELIMIT_STORAGE_URI', 'memory://'))
    store = GeoStore(app.config['DATA_DIR'])
    app.extensions['geostore'] = store
    dummy_hash = generate_password_hash('not-a-real-password')

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(username):
        rec = app.config['USERS'].get(username)
        return User(username, rec['role'], rec['name']) if rec else None

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith('/api/'):
            return jsonify(error='Authentication required'), 401
        return redirect(url_for('login'))

    def admin_required(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role != 'admin':
                abort(403)
            return f(*args, **kwargs)
        return wrapper

    def authenticate(username, password):
        rec = app.config['USERS'].get(username)
        # Always run one hash check so unknown users cost the same as known ones.
        ok = check_password_hash(rec['password_hash'] if rec else dummy_hash, password)
        return rec if (rec and ok) else None

    # ----------------------------------------------------------------- #
    # Template context / security headers / errors
    # ----------------------------------------------------------------- #
    @app.context_processor
    def inject_site():
        lat, lon = app.config['MAP_CENTER']
        return {
            'site_name': app.config['MUNICIPALITY_NAME'],
            'product_name': app.config['PRODUCT_NAME'],
            'app_config': {'center': [lat, lon], 'zoom': app.config['MAP_ZOOM']},
        }

    csp = ("default-src 'self'; "
           "script-src 'self' 'unsafe-inline'; "
           "style-src 'self' 'unsafe-inline'; "
           "img-src 'self' data: blob: https://server.arcgisonline.com "
           "https://*.tile.openstreetmap.org https://*.tile.opentopomap.org; "
           "connect-src 'self' https://api.open-meteo.com; "
           "font-src 'self'; object-src 'none'; base-uri 'self'; "
           "form-action 'self'; frame-ancestors 'none'")

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('X-Frame-Options', 'DENY')
        resp.headers.setdefault('Referrer-Policy', 'same-origin')
        resp.headers.setdefault('Content-Security-Policy', csp)
        if request.is_secure:
            resp.headers.setdefault('Strict-Transport-Security', 'max-age=31536000')
        return resp

    @app.errorhandler(HTTPException)
    def http_error(err):
        wants_json = request.path.startswith('/api/') or (request.path == '/login' and request.method == 'POST')
        if not wants_json:
            return err
        message = err.description
        if err.code == 429:
            message = 'Too many attempts. Please wait a few minutes and try again.'
        return jsonify(success=False, error=message, message=message), err.code

    # ----------------------------------------------------------------- #
    # Pages
    # ----------------------------------------------------------------- #
    @app.route('/')
    def index():
        return redirect(url_for('dashboard' if current_user.is_authenticated else 'login'))

    @app.route('/login', methods=['GET', 'POST'])
    @limiter.limit(lambda: app.config['LOGIN_RATE_LIMIT'], methods=['POST'])
    def login():
        if request.method == 'POST':
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return jsonify(success=False, message='Invalid request'), 400
            username, password = data.get('username'), data.get('password')
            if not isinstance(username, str) or not isinstance(password, str):
                return jsonify(success=False, message='Invalid request'), 400
            username = username.strip()
            rec = authenticate(username, password)
            if rec:
                session.clear()
                user = User(username, rec['role'], rec['name'])
                login_user(user)
                session['login_at'] = datetime.now(NEPAL_TZ).isoformat(timespec='seconds')
                return jsonify(success=True, role=user.role)
            return jsonify(success=False, message='Invalid credentials'), 401
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('login.html')

    @app.route('/logout', methods=['GET', 'POST'])
    def logout():
        # Logging out must be a POST so other sites cannot trigger it.
        if request.method == 'POST':
            logout_user()
            session.clear()
            return redirect(url_for('login'))
        return redirect(url_for('dashboard' if current_user.is_authenticated else 'login'))

    def add_page(endpoint):
        def view():
            return render_template(f'{endpoint}.html', user=current_user)
        view.__name__ = endpoint
        app.add_url_rule('/' + endpoint, endpoint, login_required(view))

    for name in ('dashboard', 'land', 'house', 'survey', 'road', 'weather'):
        add_page(name)

    @app.route('/profile')
    @login_required
    def profile():
        try:
            signed_in = datetime.fromisoformat(session['login_at']).strftime('%Y-%m-%d %I:%M %p')
        except (KeyError, ValueError):
            signed_in = 'Unknown'
        return render_template('profile.html', user=current_user, signed_in_at=signed_in)

    @app.route('/admin')
    @login_required
    @admin_required
    def admin():
        try:
            layers = sum(1 for f in os.listdir(store.data_dir)
                         if f.lower().endswith(('.geojson', '.json')))
        except OSError:
            layers = 0
        stats = {'users': len(app.config['USERS']), 'layers': layers}
        return render_template('admin.html', user=current_user, stats=stats)

    @app.route('/favicon.ico')
    def favicon():
        return redirect(url_for('static', filename='image/favicon.ico'))

    # ----------------------------------------------------------------- #
    # API
    # ----------------------------------------------------------------- #
    def send_geojson(name):
        """Stream a GeoJSON file (gzip + ETag). Raises FileNotFoundError/ValueError."""
        path = store.path(name)
        if not os.path.isfile(path):
            raise FileNotFoundError(name)
        store.validate(name)
        directory, filename = os.path.dirname(path), os.path.basename(path)
        wants_gzip = 'gzip' in request.headers.get('Accept-Encoding', '').lower()
        if wants_gzip and os.path.getsize(path) >= GZIP_MIN_BYTES:
            try:
                gz = store.ensure_gzip(path)
            except OSError:
                app.logger.warning('Cannot write gzip copy of %s; serving uncompressed', name)
            else:
                resp = send_from_directory(directory, os.path.basename(gz), mimetype=GEOJSON_MIME,
                                           conditional=True, max_age=0)
                resp.headers['Content-Encoding'] = 'gzip'
                resp.headers.add('Vary', 'Accept-Encoding')
                return resp
        resp = send_from_directory(directory, filename, mimetype=GEOJSON_MIME, conditional=True, max_age=0)
        resp.headers.add('Vary', 'Accept-Encoding')
        return resp

    def layer_response(label, name, sample_fn):
        try:
            return send_geojson(name)
        except FileNotFoundError:
            app.logger.warning('%s data file %s not found in %s', label, name, store.data_dir)
        except (OSError, ValueError):
            app.logger.exception('%s data file %s could not be read', label, name)
        if app.config['DEMO_MODE']:
            return jsonify(sample_fn(app.config['MAP_CENTER']))
        return jsonify(error=f'{label} data is not available on the server.'), 503

    def parcels_file():
        configured = app.config['PARCELS_FILE']
        if configured:
            return configured
        for candidate in ('land_parcels.web.geojson', 'land_parcels.geojson'):
            if os.path.isfile(os.path.join(store.data_dir, candidate)):
                return candidate
        return 'land_parcels.web.geojson'

    def parcel_query(predicate):
        try:
            items = store.index(parcels_file())
        except FileNotFoundError:
            return jsonify(error='Parcel data is not available on the server.'), 503
        except (OSError, ValueError):
            app.logger.exception('Parcel data could not be read')
            return jsonify(error='Parcel data could not be read.'), 503
        return Response(store.collection([it for it in items if predicate(it[0])]),
                        mimetype=GEOJSON_MIME)

    @app.route('/api/wards')
    @login_required
    def get_wards():
        return jsonify([{'id': i, 'name': f'Ward {i}'} for i in range(1, app.config['WARD_COUNT'] + 1)])

    @app.route('/api/parcels')
    @login_required
    def get_parcels():
        return layer_response('Parcel', parcels_file(), sample_parcels)

    @app.route('/api/parcel/search')
    @login_required
    def search_parcel():
        kitta_no = (request.args.get('kitta_no') or '').strip()[:32]
        if not kitta_no:
            return jsonify(error='kitta_no is required'), 400
        return parcel_query(lambda p: prop(p, 'kitta_no', 'KITTA_NO') == kitta_no)

    @app.route('/api/parcel/filter')
    @login_required
    def filter_parcel():
        ward = (request.args.get('ward') or '').strip()[:8]
        if not ward:
            return jsonify(error='ward is required'), 400
        return parcel_query(lambda p: prop(p, 'ward', 'WARD') == ward)

    @app.route('/api/houses')
    @login_required
    def get_houses():
        return layer_response('House', 'houses.geojson', sample_houses)

    @app.route('/api/surveys')
    @login_required
    def get_surveys():
        return layer_response('Survey', 'surveys.geojson', sample_surveys)

    @app.route('/api/roads')
    @login_required
    def get_roads():
        return layer_response('Road', 'roads.geojson', sample_roads)

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host=os.environ.get('HOST', '127.0.0.1'),
            port=int(os.environ.get('PORT', '5000')),
            debug=env_flag('FLASK_DEBUG'))
