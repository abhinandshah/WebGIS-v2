# Spatial Wings WebGIS (patched)

Flask + Leaflet municipal WebGIS: dashboard, land management, house numbering,
digital survey, road network and a Nepal weather map. This is the patched
version of the original `again.zip`, with the Spatial Wings logo on every page.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python tools/init_env.py             # creates .env: random SECRET_KEY + hashed passwords
python app.py                        # http://127.0.0.1:5000
```

`tools/init_env.py` asks you to choose the `admin` and `user` passwords (or use
`--random` to have it generate and print them once). **The app refuses to start
without them** - there are no built-in default credentials any more.

For local development over plain http you may also want, in `.env`:

```
FLASK_DEBUG=1
COOKIE_SECURE=0
```

Run the tests with `pip install -r requirements-dev.txt && python -m pytest tests`.

## Where things are

| Path | What |
|---|---|
| `app.py` | Flask app (config from environment / `.env`) |
| `templates/` | Pages. `_macros.html` holds the shared logo + user menu |
| `static/js/gis-common.js` | Shared map/popup/fetch helpers used by every map page |
| `static/vendor/` | Leaflet, Bootstrap, Font Awesome - self-hosted, version-pinned |
| `static/image/` | Web-sized logo, favicon, touch icon (generated from `image/logo.png`) |
| `image/` | Original artwork (not served) |
| `data/land_parcels.web.geojson` | Parcel layer the app serves (6-decimal coordinates) |
| `data/source/` | Original GeoJSON + shapefiles (**never served**) |
| `tools/` | `init_env.py`, `optimize_geojson.py` |

## Configuration (environment or `.env`)

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | *required* | 32+ random characters |
| `ADMIN_PASSWORD_HASH`, `USER_PASSWORD_HASH` | *required* | Set by `tools/init_env.py` |
| `MUNICIPALITY_NAME` | `Biratnagar Municipality` | Shown in headers and on the login page |
| `MAP_CENTER`, `MAP_ZOOM` | `27.4089,86.0732`, `13` | Centre of the parcel data |
| `WARD_COUNT` | `20` | Entries in the ward dropdowns |
| `DATA_DIR` | `./data` | Where the GeoJSON layers live |
| `DEMO_MODE` | off | `1` = show tiny built-in sample features when a layer file is missing |
| `COOKIE_SECURE` | on (off if `FLASK_DEBUG=1`) | Set `0` only for plain-http local use |
| `LOGIN_RATE_LIMIT` | `5 per minute;30 per hour` | Per client IP |
| `BEHIND_PROXY` | off | `1` when behind one reverse proxy (so rate limiting sees real IPs) |
| `RATELIMIT_STORAGE_URI` | `memory://` | Use Redis when running several workers |

## Data layers

The app expects these files in `DATA_DIR`:

* `land_parcels.web.geojson` (included; falls back to `land_parcels.geojson`)
* `roads.geojson`, `houses.geojson`, `surveys.geojson` - **not included in the
  original ZIP.** Until you add them, those pages show a clear "data is not
  available" message instead of inventing features.

Expected properties: roads `road_name`, `road_type` (primary/secondary/tertiary),
`status` (paved/gravel/under construction); houses `house_no`, `ward`, `street`,
`owner`, `floors`; surveys `survey_id`, `date`, `surveyor`, `status`
(completed/pending/in progress). To slim down a new large layer:

```bash
python tools/optimize_geojson.py data/source/big.geojson data/big.web.geojson
```

## Deploying

```bash
pip install gunicorn
gunicorn -w 2 -b 127.0.0.1:8000 app:app
```

Put it behind an HTTPS reverse proxy (nginx, Caddy), set `BEHIND_PROXY=1`, and
keep `FLASK_DEBUG` unset. Never expose the Flask debugger.

## Known limits (deliberate)

* The parcel layer has no `ward` or `kitta_no` attribute, so ward/kitta search
  is switched off with an explanation. Add those columns and it turns on by itself.
* Province/District, cadastral sheets, drone layer, street layer, admin actions and
  profile editing are shown disabled ("coming soon") because nothing backs them yet.
* The EN/NP toggle on the dashboard is still a placeholder.
* `static/js/main.js` is the original, unused file. It is not loaded (it would
  shift the dashboard layout).
* Users are the two accounts in `.env`. For real user management, move to a database.





python tools/optimize_geojson.py "C:\Computer\WebGIS\New WebGIS\data\source\land parcels.geojson" "C:\Computer\WebGIS\New WebGIS\data\land_parcels.web.geojson"
