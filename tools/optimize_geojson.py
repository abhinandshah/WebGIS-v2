#!/usr/bin/env python3
"""Shrink a GeoJSON file for web delivery.

Rounds coordinates to N decimal places (default 6 = ~0.11 m, far finer than
any web map can show) and writes compact JSON. The original file is never
modified.

    python tools/optimize_geojson.py data/source/land_parcels.geojson \
                                     data/land_parcels.web.geojson

On the bundled parcel layer this takes the file from 62 MB to about 37 MB
(about 8.5 MB gzipped). The app also creates a .gz copy next to the file
automatically the first time a browser asks for it.
"""
import argparse
import json
import os
import sys


def round_coords(c, n):
    if c and isinstance(c[0], (int, float)):
        return [round(v, n) for v in c]
    return [round_coords(i, n) for i in c]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--precision', type=int, default=6)
    args = ap.parse_args()

    if os.path.abspath(args.src) == os.path.abspath(args.dst):
        sys.exit('Refusing to overwrite the source file; choose a different destination.')

    with open(args.src, encoding='utf-8') as f:
        doc = json.load(f)

    for feat in doc.get('features', []):
        geom = feat.get('geometry')
        if geom and 'coordinates' in geom:
            geom['coordinates'] = round_coords(geom['coordinates'], args.precision)

    with open(args.dst, 'w', encoding='utf-8') as f:
        json.dump(doc, f, separators=(',', ':'), ensure_ascii=False)

    before, after = os.path.getsize(args.src), os.path.getsize(args.dst)
    print(f'{args.src}: {before/1e6:.1f} MB -> {args.dst}: {after/1e6:.1f} MB '
          f'({100 * (1 - after / before):.0f}% smaller, {len(doc.get("features", []))} features)')


if __name__ == '__main__':
    main()
