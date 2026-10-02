<div align="center">

# 🌍 Spatial Wings WebGIS

### A Municipal GIS Platform for Spatial Data, Land Management & Urban Infrastructure

A Flask + Leaflet web mapping application featuring a municipal GIS dashboard, land management, house numbering, digital survey, road network, and a Nepal weather map.

<br>

![Python](https://img.shields.io/badge/Python-Flask-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Maps](https://img.shields.io/badge/Web_Mapping-Leaflet-199900?style=for-the-badge&logo=leaflet&logoColor=white)
![GIS](https://img.shields.io/badge/Domain-Municipal_GIS-2E8B57?style=for-the-badge)
![Data](https://img.shields.io/badge/Data-GeoJSON-4285F4?style=for-the-badge)
![Status](https://img.shields.io/badge/Project-Under_Development-orange?style=for-the-badge)

**Built by Spatial Wings** · GIS · WebGIS · Spatial Analysis · Urban Planning

[Features](#-features) · [Preview](#-screenshots--demo) · [Installation](#-installation) · [Configuration](#-configuration) · [Data](#-data-layers) · [Deployment](#-deployment)

</div>

---

## 📌 Overview

**Spatial Wings WebGIS** is a web-based municipal GIS application built with **Flask** and **Leaflet**. It brings municipal spatial-data workflows into a single web interface, with pages for land management, house numbering, digital survey, road networks, and a Nepal weather map.

This repository contains a patched version of the original project, including the Spatial Wings logo across the application pages.

> **Project status:** Some modules are not yet connected to supporting data or backend functionality. Their current limitations are documented below.

## ✨ Features

- 🗺️ **Interactive WebGIS maps** powered by Leaflet
- 🏘️ **Land management** interface and parcel layer
- 🏠 **House numbering** module
- 📐 **Digital survey** module
- 🛣️ **Road network** module
- 🌦️ **Nepal weather map**
- 🔐 **Admin and user sign-in** with environment-based password hashes
- 🧩 **Shared GIS helpers** for map interactions, popups, and data requests
- 📦 **GeoJSON data support** with an optimization utility for large files
- 🎨 **Spatial Wings branding** throughout the application
- 🧪 **Test support** through pytest

## 📸 Screenshots & Demo

Add screenshots or a short GIF of the running application to the `screenshots/` directory, then update the paths below.

<div align="center">

| Municipal Dashboard | Interactive GIS Map |
|---|---|
| ![Dashboard placeholder](screenshots/dashboard.png) | ![Map placeholder](screenshots/webgis-map.png) |

| Land Management | House Numbering |
|---|---|
| ![Land management placeholder](screenshots/land-management.png) | ![House numbering placeholder](screenshots/house-numbering.png) |

</div>

**Demo GIF placeholder:** Save a screen recording as `screenshots/demo.gif` and embed it here:

```markdown
![Spatial Wings WebGIS demo](screenshots/demo.gif)
```

> The screenshot paths above are placeholders. Add the corresponding image files to the repository before expecting them to display on GitHub.

## 🧰 Technology Stack

| Technology | Role |
|---|---|
| **Python** | Application programming language |
| **Flask** | Web application framework |
| **Leaflet** | Interactive web maps |
| **GeoJSON** | Web-ready spatial data |
| **HTML templates** | Application pages |
| **JavaScript** | Map interactions and client-side behavior |
| **Bootstrap** | Interface components |
| **Font Awesome** | Icons |
| **pytest** | Automated tests |

The project keeps Leaflet, Bootstrap, and Font Awesome assets locally under `static/vendor/`.

## 🚀 Installation

### Prerequisites

- Python installed and available from your terminal
- Git, if cloning the repository
- The project source code and its required data files

### 1. Clone the repository

Replace `YOUR-USERNAME` with your GitHub username:

```bash
git clone https://github.com/abhinandshah/WebGIS-v2.git
cd WebGIS-v2
```

Alternatively, download the repository as a ZIP file and extract it.

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

**Windows — Command Prompt**

```bat
.venv\Scripts\activate
```

**Windows — PowerShell**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS**

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize application credentials

Run the environment setup utility:

```bash
python tools/init_env.py
```

The script creates a `.env` file with a random `SECRET_KEY` and hashed passwords for the `admin` and `user` accounts. It prompts you to choose passwords. You can use `--random` to generate credentials and print them once:

```bash
python tools/init_env.py --random
```

**Important:** The application requires the secret key and password hashes to be configured. It does not use built-in default credentials. Keep your `.env` file private and do not commit it to Git.

### 5. Start the application

```bash
python app.py
```

Open the local address in your browser:

**http://127.0.0.1:5000**

## 🪟 Local Development Configuration

For local development over plain HTTP, you may set the following values in `.env`:

```dotenv
FLASK_DEBUG=1
COOKIE_SECURE=0
```

Use these settings only for local development. Do not use the Flask debugger on a public-facing deployment.

## 🗂️ Project Structure

```text
.
├── app.py                       # Flask application
├── templates/                   # HTML templates
│   └── _macros.html             # Shared logo and user menu
│   ├── admin.html
│   ├── base.html
│   ├── dashboard.html
│   ├── house.html
│   ├── land.html
│   ├── login.html
│   ├── profile.html                 
│   ├── road.html            
│   ├── survey.html       
│   └── weather.html
├── static/
│   ├── js/
│   │   └── gis-common.js        # Shared map, popup, and fetch helpers
│   ├── vendor/                  # Local Leaflet, Bootstrap, Font Awesome
│   └── image/                   # Web logo, favicon, and touch icon
├── image/                       # Original artwork (not served)
├── data/
│   ├── land_parcels.web.geojson # Web-ready parcel layer
│   └── source/                  # Original GeoJSON and shapefiles
├── tools/
│   ├── init_env.py              # Creates local environment configuration
│   └── optimize_geojson.py      # Optimizes GeoJSON for web use
├── tests/                       # Automated tests
├── requirements.txt             # Runtime dependencies
├── requirements-dev.txt         # Development/test dependencies
└── README.md
```

## ⚙️ Configuration

Application configuration can be supplied through environment variables or the `.env` file.

| Variable | Default / Requirement | Purpose |
|---|---|---|
| `SECRET_KEY` | Required; 32+ random characters recommended | Flask secret key |
| `ADMIN_PASSWORD_HASH` | Required | Hashed admin password |
| `USER_PASSWORD_HASH` | Required | Hashed user password |
| `MUNICIPALITY_NAME` | `Biratnagar Municipality` | Municipality name shown in the interface |
| `MAP_CENTER` | `27.4089,86.0732` | Map center for the parcel data |
| `MAP_ZOOM` | `13` | Initial map zoom |
| `WARD_COUNT` | `20` | Number of entries in ward dropdowns |
| `DATA_DIR` | `./data` | Directory containing GeoJSON layers |
| `DEMO_MODE` | Off | Set to `1` to show small built-in sample features when a layer is missing |
| `COOKIE_SECURE` | On; off when `FLASK_DEBUG=1` | Cookie security setting; use `0` only for local plain-HTTP development |
| `LOGIN_RATE_LIMIT` | `5 per minute;30 per hour` | Login rate limit per client IP |
| `BEHIND_PROXY` | Off | Set to `1` when running behind one reverse proxy |
| `RATELIMIT_STORAGE_URI` | `memory://` | Rate-limit storage; consider Redis for multiple workers |

Use the initialization script to configure required credentials rather than manually inventing password hashes.

## 🗺️ Data Layers

The application reads spatial data from `DATA_DIR` (by default, `./data`).

### Included

- `land_parcels.web.geojson`
- The application can fall back to `land_parcels.geojson` if the web-ready parcel file is not available.

### Additional data expected

These files are **not included in the original project ZIP**:

- `roads.geojson`
- `houses.geojson`
- `surveys.geojson`

Until the required files are added, the corresponding pages display a data-unavailable message rather than fabricated features.

### Expected GeoJSON properties

| Layer | Expected properties |
|---|---|
| Roads | `road_name`, `road_type`, `status` |
| Houses | `house_no`, `ward`, `street`, `owner`, `floors` |
| Surveys | `survey_id`, `date`, `surveyor`, `status` |

Expected values include:

- Road type: `primary`, `secondary`, `tertiary`
- Road status: `paved`, `gravel`, `under construction`
- Survey status: `completed`, `pending`, `in progress`

Ensure that your GeoJSON feature properties match the expected names and values when adding new data.

### Optimize a large GeoJSON file

Use the included utility to generate a web-optimized copy:

```bash
python tools/optimize_geojson.py data/source/big.geojson data/big.web.geojson
```

The example input and output paths should be replaced with the paths for your own data.

## 🧪 Run Tests

Install development dependencies and run the test suite:

```bash
pip install -r requirements-dev.txt
python -m pytest tests
```

## 🌐 Deployment

For a production-style WSGI launch, install Gunicorn:

```bash
pip install gunicorn
```

Start the application with:

```bash
gunicorn -w 2 -b 127.0.0.1:8000 app:app
```

For a public deployment:

1. Put the application behind an HTTPS reverse proxy, such as Nginx or Caddy.
2. Set `BEHIND_PROXY=1` when using one trusted reverse proxy.
3. Keep `FLASK_DEBUG` unset.
4. Set secure production environment variables and keep `.env` out of version control.
5. For multiple workers, configure shared rate-limit storage such as Redis instead of relying on in-memory storage.

**Never expose the Flask debugger to the public internet.** Review proxy and cookie settings for your deployment environment.

## 🚧 Current Limitations

The following limitations are intentional in the current version:

- The parcel layer does not contain `ward` or `kitta_no` attributes, so ward and Kitta search is disabled with an explanation. Add the relevant attributes to enable that workflow.
- Province/District selection, cadastral sheets, drone layer, street layer, admin actions, and profile editing are marked as coming soon because the required backend functionality or data is not yet available.
- The English/Nepali language toggle on the dashboard is a placeholder.
- `static/js/main.js` is an unused original file and is not loaded because it would affect the dashboard layout.
- User accounts are currently represented by the two configured accounts in `.env`. A database-backed user-management system would be needed for more extensive account management.

## 🛣️ Potential Next Steps

Possible future enhancements include:

- [ ] Add and validate road, house, and survey datasets
- [ ] Implement ward and Kitta search after adding the required parcel attributes
- [ ] Connect the disabled modules to their data and backend workflows
- [ ] Implement database-backed user management
- [ ] Complete English/Nepali language switching
- [ ] Add more application screenshots and a workflow demo
- [ ] Expand automated test coverage

These are potential improvements, not features currently guaranteed by the application.

## 🤝 Contributing

Suggestions and improvements are welcome.

1. Fork the repository.
2. Create a branch for your change.
3. Make and test your updates.
4. Submit a pull request describing the change.

For bug reports, include relevant error messages, steps to reproduce the issue, and details about your local environment. Avoid sharing secrets, passwords, or private spatial data.

## 🔐 Security Notes

- Do not commit `.env`, passwords, secret keys, or other credentials.
- Use strong, unique passwords for configured accounts.
- Keep `FLASK_DEBUG` disabled in production.
- Use HTTPS for public deployments.
- Configure trusted proxy and rate-limit settings according to your hosting environment.

## 👨‍💻 About Spatial Wings

**Spatial Wings** focuses on practical geospatial workflows, including GIS, spatial analysis, Remote Sensing, WebGIS, urban planning, land management, and drone/UAV mapping.

This project explores how web technologies can make municipal spatial data easier to view and manage through an interactive mapping interface.

## 📄 License

This project is released under the **MIT License**.<br>
See [License](LICENSE) for details..


---
<div align="center">

(screenshorts/logo.png)<br>




**Spatial Wings WebGIS**


*Connecting spatial data with practical municipal workflows.*

Built with Python, Flask, Leaflet, and GeoJSON.

</div>

