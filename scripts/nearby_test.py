#!/usr/bin/env python3
"""Standalone sanity check for the nearby public land query.

Runs the same query and the same geometry code the integration uses, without
needing Home Assistant or aiohttp installed.

    python3 scripts/nearby_test.py LAT LON [RADIUS_MILES] [--managers BLM,USFS]
                                            [--any-access] [--json]

Examples:
    python3 scripts/nearby_test.py 36.2 -115.0 25
    python3 scripts/nearby_test.py 31.22 -85.39 100 --managers BLM,USFS,State
"""

import argparse
import importlib.machinery
import json
import os
import sys
import urllib.parse
import urllib.request

# Load the integration's dependency-free modules directly by path. Importing the
# package normally would execute __init__.py, which needs Home Assistant.
import importlib.util  # noqa: E402

_PKG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                        "custom_components", "public_lands")


def _load(name):
    """Load public_lands.<name> without running the package __init__."""
    full = f"public_lands.{name}"
    if full in sys.modules:
        return sys.modules[full]
    if "public_lands" not in sys.modules:
        pkg = importlib.util.module_from_spec(
            importlib.machinery.ModuleSpec("public_lands", None, is_package=True)
        )
        pkg.__path__ = [_PKG_DIR]
        sys.modules["public_lands"] = pkg
    spec = importlib.util.spec_from_file_location(
        full, os.path.join(_PKG_DIR, f"{name}.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


_const = _load("const")
_geo = _load("geo")

ARCGIS_URL = _const.ARCGIS_URL
DEFAULT_MANAGERS = _const.DEFAULT_MANAGERS
DEFAULT_RADIUS = _const.DEFAULT_RADIUS
MANAGER_GROUPS = _const.MANAGER_GROUPS
NON_PADUS = _const.NON_PADUS
OUT_FIELDS = _const.OUT_FIELDS
build_where = _geo.build_where
query_params = _geo.query_params
summarize = _geo.summarize


def fetch(url, timeout=20):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lat", type=float)
    p.add_argument("lon", type=float)
    p.add_argument("radius", type=float, nargs="?", default=DEFAULT_RADIUS,
                   help=f"search radius in miles (default {DEFAULT_RADIUS})")
    p.add_argument("--managers", default=",".join(DEFAULT_MANAGERS),
                   help="comma-separated groups: " + ", ".join(MANAGER_GROUPS))
    p.add_argument("--any-access", action="store_true",
                   help="do not restrict to open-access land")
    p.add_argument("--json", action="store_true", help="print raw JSON results")
    args = p.parse_args()

    managers = [m.strip() for m in args.managers.split(",") if m.strip()]
    unknown = [m for m in managers if m not in MANAGER_GROUPS]
    if unknown:
        p.error(f"unknown manager group(s): {', '.join(unknown)}")

    # Point query first -- this is what decides whether the nearby query runs.
    point = {
        "geometry": f"{args.lon},{args.lat}", "geometryType": "esriGeometryPoint",
        "inSR": "4326", "outFields": OUT_FIELDS, "returnGeometry": "false", "f": "json",
    }
    pdata = json.loads(fetch(f"{ARCGIS_URL}?{urllib.parse.urlencode(point)}"))
    pfeatures = pdata.get("features") or []
    unit = (pfeatures[0].get("attributes", {}).get("Unit_Nm") if pfeatures else None)
    print(f"Point query: {unit or '(no feature returned)'}")

    if unit and unit != NON_PADUS:
        print("-> On public land. The integration would SKIP the nearby query.")
        return

    where = build_where(managers, not args.any_access)
    print(f"-> Not on public land. Nearby query within {args.radius:g} mi")
    print(f"   where: {where}\n")

    params = query_params(args.lat, args.lon, args.radius, where, OUT_FIELDS)
    raw = fetch(f"{ARCGIS_URL}?{urllib.parse.urlencode(params)}")
    data = json.loads(raw)
    if "error" in data:
        print(f"ArcGIS error: {data['error']}")
        return 1

    features = data.get("features", [])
    results = summarize(args.lat, args.lon, features)
    print(f"{len(raw)/1024:.0f} KB, {len(features)} features, "
          f"{len(results)} unique units\n")

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    if not results:
        print("No matches within range. Try a larger radius or more managers.")
        return 0

    for r in results:
        print(f"{r['distance_miles']:6.1f} mi {r['bearing_compass']:<3} "
              f"{r['name'][:42]:<42} {(r['manager'] or '')[:26]:<26} "
              f"{(r['designation'] or '')[:24]}")
    print(f"\nNearest: {results[0]['name']}\n  {results[0]['google_maps_url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
