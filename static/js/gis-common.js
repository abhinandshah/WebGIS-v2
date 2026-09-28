/* Shared helpers for the Spatial Wings pages.
 *
 * - esc / popupTable: build popup HTML safely (feature attributes are data,
 *   never markup).
 * - fetchJSON: fetch with clear errors; sends the user to /login on 401.
 * - notify: small non-blocking messages (replaces alert()).
 * - initMap: one place that sets up base maps (with attribution), the layer
 *   control, scale bar and fullscreen button for every map page.
 */
(function (global) {
    'use strict';

    /* ------------------------------------------------------------------ */
    /* Text safety                                                         */
    /* ------------------------------------------------------------------ */
    const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

    /** Escape a value for use inside HTML. null / undefined / '' -> fallback. */
    function esc(value, fallback) {
        const empty = value === null || value === undefined || value === '';
        const text = empty ? (fallback === undefined ? 'N/A' : fallback) : String(value);
        return text.replace(/[&<>"']/g, function (c) { return ESCAPES[c]; });
    }

    function humanizeKey(key) {
        return String(key).replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
    }

    /** [[label, value], ...] for every attribute of a feature. */
    function propertiesRows(props) {
        props = props || {};
        return Object.keys(props).map(function (k) { return [humanizeKey(k), props[k]]; });
    }

    /** Popup HTML with every label and value escaped. */
    function popupTable(title, iconClass, rows) {
        let html = '<div class="popup-content"><h6><i class="fas ' + esc(iconClass, '') + '"></i> ' +
            esc(title, '') + '</h6><table>';
        rows.forEach(function (r) {
            html += '<tr><td>' + esc(r[0], '') + ':</td><td>' + esc(r[1]) + '</td></tr>';
        });
        return html + '</table></div>';
    }

    /* ------------------------------------------------------------------ */
    /* Notifications                                                       */
    /* ------------------------------------------------------------------ */
    function notify(message, kind, timeoutMs) {
        let host = document.getElementById('gis-notify');
        if (!host) {
            host = document.createElement('div');
            host.id = 'gis-notify';
            host.className = 'gis-notify';
            host.setAttribute('role', 'status');
            host.setAttribute('aria-live', 'polite');
            document.body.appendChild(host);
        }
        const item = document.createElement('div');
        item.className = 'gis-notify-item gis-notify-' + (kind || 'info');
        const text = document.createElement('span');
        text.textContent = message;                       // textContent: never parsed as HTML
        const close = document.createElement('button');
        close.type = 'button';
        close.setAttribute('aria-label', 'Dismiss');
        close.textContent = '\u00d7';
        item.appendChild(text);
        item.appendChild(close);
        host.appendChild(item);

        const remove = function () { if (item.parentNode) { item.parentNode.removeChild(item); } };
        close.addEventListener('click', remove);
        if (timeoutMs !== 0) {
            setTimeout(remove, timeoutMs || (kind === 'error' ? 10000 : 5000));
        }
        return item;
    }

    /* ------------------------------------------------------------------ */
    /* Networking                                                          */
    /* ------------------------------------------------------------------ */
    async function fetchJSON(url) {
        const res = await fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
        if (res.status === 401) {
            window.location.href = '/login';
            throw new Error('Your session has expired. Redirecting to the login page...');
        }
        const type = res.headers.get('content-type') || '';
        if (!res.ok) {
            let message = 'The server returned HTTP ' + res.status + '.';
            if (type.indexOf('json') !== -1) {
                try {
                    const body = await res.json();
                    if (body && body.error) { message = body.error; }
                } catch (e) { /* keep the generic message */ }
            }
            throw new Error(message);
        }
        try {
            return await res.json();
        } catch (e) {
            throw new Error('The data could not be read (invalid JSON).');
        }
    }

    /** Resolve after the browser has painted, so a loading overlay is visible
     *  before heavy synchronous work (e.g. drawing thousands of polygons). */
    function nextPaint() {
        return new Promise(function (resolve) {
            requestAnimationFrame(function () { setTimeout(resolve, 0); });
        });
    }

    function isPlainObject(v) { return v !== null && typeof v === 'object' && !Array.isArray(v); }

    /** Features array from a FeatureCollection, or [] . */
    function featuresOf(data) {
        return isPlainObject(data) && Array.isArray(data.features)
            ? data.features.filter(function (f) { return isPlainObject(f); })
            : [];
    }

    /* ------------------------------------------------------------------ */
    /* Map setup                                                           */
    /* ------------------------------------------------------------------ */
    const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
    const OSM = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    const TOPO = 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png';

    function createBaseLayers() {
        return {
            satellite: L.tileLayer(ESRI, {
                maxZoom: 19,
                attribution: 'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community'
            }),
            street: L.tileLayer(OSM, {
                maxZoom: 19,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'
            }),
            terrain: L.tileLayer(TOPO, {
                maxZoom: 17,
                attribution: 'Map data &copy; OpenStreetMap contributors, SRTM | Style &copy; <a href="https://opentopomap.org" target="_blank" rel="noopener">OpenTopoMap</a> (CC-BY-SA)'
            })
        };
    }

    function createFullscreenControl() {
        return L.Control.extend({
            options: { position: 'topleft' },
            onAdd: function (map) {
                const btn = L.DomUtil.create('button', 'leaflet-bar leaflet-control');
                btn.type = 'button';
                btn.title = 'Toggle fullscreen';
                btn.setAttribute('aria-label', 'Toggle fullscreen');
                btn.style.cssText = 'background:white; width:34px; height:34px; border:2px solid rgba(0,0,0,0.2); ' +
                    'cursor:pointer; font-size:16px; display:flex; align-items:center; justify-content:center;';
                L.DomEvent.disableClickPropagation(btn);

                const container = map.getContainer();
                const sync = function () {
                    const on = document.fullscreenElement === container;
                    btn.innerHTML = '<i class="fas fa-' + (on ? 'compress' : 'expand') + '"></i>';
                    setTimeout(function () { map.invalidateSize(); }, 150);
                };
                sync();
                document.addEventListener('fullscreenchange', sync);   // also fires when the user presses Esc

                btn.addEventListener('click', function (e) {
                    e.preventDefault();
                    const action = document.fullscreenElement ? document.exitFullscreen() : container.requestFullscreen();
                    Promise.resolve(action).catch(function (err) { console.error('Fullscreen error:', err); });
                });
                return btn;
            }
        });
    }

    /** Create a Leaflet map with the standard base layers and controls.
     *  Returns { map, basemaps }. */
    function initMap(elementId, options) {
        options = options || {};
        if (typeof L === 'undefined') {
            notify('The map library failed to load. Please refresh the page.', 'error', 0);
            throw new Error('Leaflet is not loaded');
        }
        const cfg = global.APP_CONFIG || {};
        const map = L.map(elementId, {
            center: options.center || cfg.center || [27.4089, 86.0732],
            zoom: options.zoom || cfg.zoom || 13,
            zoomControl: true,
            preferCanvas: options.preferCanvas !== false     // canvas scales far better than SVG
        });
        const basemaps = createBaseLayers();
        (basemaps[options.basemap] || basemaps.satellite).addTo(map);
        L.control.layers({
            'Satellite': basemaps.satellite,
            'Street': basemaps.street,
            'Terrain': basemaps.terrain
        }, null, { position: 'topright' }).addTo(map);
        L.control.scale({ position: 'bottomleft', imperial: false }).addTo(map);
        if (document.fullscreenEnabled) {
            const Fullscreen = createFullscreenControl();
            map.addControl(new Fullscreen());
        }
        setTimeout(function () { map.invalidateSize(); }, 100);
        window.addEventListener('resize', function () { map.invalidateSize(); });
        return { map: map, basemaps: basemaps };
    }

    /** Show / hide a centred loading box on top of a map. */
    function setLoading(map, on, text) {
        const container = map.getContainer();
        let el = container.querySelector('.map-loading');
        if (!on) {
            if (el) { el.remove(); }
            return;
        }
        if (!el) {
            el = document.createElement('div');
            el.className = 'map-loading';
            el.innerHTML = '<div class="spinner"></div><div class="map-loading-text"></div>';
            container.appendChild(el);
        }
        el.querySelector('.map-loading-text').textContent = text || 'Loading...';
    }

    global.GIS = {
        esc: esc,
        humanizeKey: humanizeKey,
        propertiesRows: propertiesRows,
        popupTable: popupTable,
        notify: notify,
        fetchJSON: fetchJSON,
        nextPaint: nextPaint,
        featuresOf: featuresOf,
        isPlainObject: isPlainObject,
        initMap: initMap,
        setLoading: setLoading
    };
})(window);
