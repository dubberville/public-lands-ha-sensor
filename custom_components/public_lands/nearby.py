"""Nearby open public land lookup.

Runs a second ArcGIS query when the point query says we are not on PAD-US land.
All geometry and query-building logic lives in geo.py.
"""

import logging
from urllib.parse import urlencode

import aiohttp
import async_timeout

from .const import (
    ARCGIS_URL,
    CONF_MANAGERS,
    CONF_MAX_RESULTS,
    CONF_OPEN_ONLY,
    CONF_RADIUS,
    DEFAULT_MANAGERS,
    DEFAULT_MAX_RESULTS,
    DEFAULT_OPEN_ONLY,
    DEFAULT_RADIUS,
    OUT_FIELDS,
)
from .geo import build_where, query_params, summarize

_LOGGER = logging.getLogger(__name__)

TIMEOUT = 20


def get_options(entry):
    """Read options at query time so changes apply without a restart."""
    opts = dict(entry.options) if entry else {}
    # NumberSelector hands back floats; max_results is used as a slice index.
    return {
        CONF_RADIUS: float(opts.get(CONF_RADIUS, DEFAULT_RADIUS)),
        CONF_MANAGERS: opts.get(CONF_MANAGERS) or DEFAULT_MANAGERS,
        CONF_OPEN_ONLY: bool(opts.get(CONF_OPEN_ONLY, DEFAULT_OPEN_ONLY)),
        CONF_MAX_RESULTS: int(opts.get(CONF_MAX_RESULTS, DEFAULT_MAX_RESULTS)),
    }


async def async_query_nearby(lat, lon, options):
    """Query nearby open public land. Returns a sorted list of result dicts."""
    where = build_where(options[CONF_MANAGERS], options[CONF_OPEN_ONLY])
    params = query_params(lat, lon, options[CONF_RADIUS], where, OUT_FIELDS)
    url = f"{ARCGIS_URL}?{urlencode(params)}"
    _LOGGER.debug("USPL nearby query: %s", url)

    async with async_timeout.timeout(TIMEOUT):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json(content_type=None)

    if "error" in data:
        raise RuntimeError(f"ArcGIS error: {data['error']}")

    features = data.get("features", [])
    results = summarize(lat, lon, features)
    _LOGGER.debug(
        "USPL nearby: %d features -> %d unique units", len(features), len(results)
    )
    return results
