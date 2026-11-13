"""Pure geometry and query-building helpers.

Kept free of Home Assistant and third-party imports so the standalone script in
scripts/ can exercise the same code from a plain Python install.

Nearest point is the closest polygon *vertex* rather than the closest point on
the polygon edge. With server-side geometry simplification the difference is a
few hundred feet on a number used to decide which way to drive, and avoiding
shapely keeps manifest requirements empty so the integration installs cleanly
on HA OS.
"""

import math

from .const import MANAGER_GROUPS

EARTH_RADIUS_MI = 3958.7613
METERS_PER_MILE = 1609.344

COMPASS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def haversine_miles(lat1, lon1, lat2, lon2):
    """Great-circle distance in miles."""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(a))


def bearing_degrees(lat1, lon1, lat2, lon2):
    """Initial compass bearing from point 1 to point 2, in degrees."""
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(
        math.radians(lat1)
    ) * math.cos(math.radians(lat2)) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def compass_point(degrees):
    """16-point compass label for a bearing."""
    return COMPASS[int((degrees + 11.25) % 360 // 22.5)]


def build_where(managers, open_access_only):
    """Build the where clause from selected manager groups.

    This layer has no coded manager fields -- only the *_Desc text fields -- so
    the clause matches on full description strings.
    """
    names = []
    for group in managers:
        for name in MANAGER_GROUPS.get(group, []):
            if name not in names:
                names.append(name)

    clauses = []
    if open_access_only:
        clauses.append("Pub_Access='OA'")
    if names:
        quoted = ",".join("'{}'".format(n.replace("'", "''")) for n in names)
        clauses.append(f"MngNm_Desc IN ({quoted})")
    return " AND ".join(clauses) if clauses else "1=1"


def nearest_vertex(lat, lon, geometry):
    """Closest polygon vertex to (lat, lon). Returns (miles, lat, lon) or None."""
    best = None
    for ring in (geometry or {}).get("rings", []):
        for point in ring:
            # ArcGIS rings are [x, y] i.e. [lon, lat]
            plon, plat = point[0], point[1]
            miles = haversine_miles(lat, lon, plat, plon)
            if best is None or miles < best[0]:
                best = (miles, plat, plon)
    return best


def maps_urls(lat, lon):
    """Turn-by-turn navigation links to a destination."""
    return (
        f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}",
        f"https://maps.apple.com/?daddr={lat},{lon}",
    )


def summarize(lat, lon, features, max_results=None):
    """Turn raw ArcGIS features into sorted, deduplicated result dicts."""
    closest = {}
    for feature in features:
        attrs = feature.get("attributes", {})
        name = attrs.get("Unit_Nm")
        if not name:
            continue
        found = nearest_vertex(lat, lon, feature.get("geometry"))
        if found is None:
            continue
        miles, plat, plon = found
        if name not in closest or miles < closest[name]["distance_miles"]:
            degrees = bearing_degrees(lat, lon, plat, plon)
            google, apple = maps_urls(plat, plon)
            closest[name] = {
                "name": name,
                "distance_miles": round(miles, 1),
                "bearing_degrees": round(degrees),
                "bearing_compass": compass_point(degrees),
                "manager": attrs.get("MngNm_Desc"),
                "management_type": attrs.get("MngTp_Desc"),
                "designation": attrs.get("DesTp_Desc"),
                "public_access": attrs.get("Pub_Access"),
                "latitude": round(plat, 5),
                "longitude": round(plon, 5),
                "google_maps_url": google,
                "apple_maps_url": apple,
            }

    results = sorted(closest.values(), key=lambda r: r["distance_miles"])
    return results[:max_results] if max_results else results


def query_params(lat, lon, radius_miles, where, out_fields):
    """ArcGIS query parameters for the nearby lookup."""
    return {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "distance": str(radius_miles * METERS_PER_MILE),
        "units": "esriSRUnit_Meter",
        "spatialRel": "esriSpatialRelIntersects",
        "where": where,
        "outFields": out_fields,
        "returnGeometry": "true",
        "outSR": "4326",
        "geometryPrecision": "5",
        # Simplify server-side. Without this a dense area returns several MB of
        # vertices per press; ~0.002 degrees cuts that by roughly 10x and moves
        # the nearest-point answer by about a tenth of a mile.
        "maxAllowableOffset": "0.002",
        "f": "json",
        "resultRecordCount": "200",
    }
