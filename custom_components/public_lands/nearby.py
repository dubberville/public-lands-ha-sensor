"""Nearby open public land lookup.

Runs a second ArcGIS query when the point lookup found no PAD-US area here.
All geometry and query-building logic lives in geo.py.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry

from .api import get_json
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
    NON_PROTECTED_AREA,
    OUT_FIELDS,
    PRIVATE_LAND,
)
from .geo import build_where, query_params, summarize

_LOGGER = logging.getLogger(__name__)


def get_options(entry: ConfigEntry | None) -> dict[str, Any]:
    """Nearby options with defaults filled in."""
    opts = dict(entry.options) if entry else {}
    # NumberSelector hands back floats; max_results is used as a slice index.
    return {
        CONF_RADIUS: float(opts.get(CONF_RADIUS, DEFAULT_RADIUS)),
        CONF_MANAGERS: opts.get(CONF_MANAGERS) or DEFAULT_MANAGERS,
        CONF_OPEN_ONLY: bool(opts.get(CONF_OPEN_ONLY, DEFAULT_OPEN_ONLY)),
        CONF_MAX_RESULTS: int(opts.get(CONF_MAX_RESULTS, DEFAULT_MAX_RESULTS)),
    }


def needs_nearby(result: dict[str, Any]) -> bool:
    """True when the point lookup found no public land here."""
    return not result.get("areas") and result.get("unit_name") in (
        NON_PROTECTED_AREA,
        PRIVATE_LAND,
    )


async def async_query_nearby(
    session: aiohttp.ClientSession, lat: float, lon: float, options: dict[str, Any]
) -> list[dict[str, Any]]:
    """Nearby open public land, nearest first. Raises PublicLandsError."""
    where = build_where(options[CONF_MANAGERS], options[CONF_OPEN_ONLY])
    params = query_params(lat, lon, options[CONF_RADIUS], where, OUT_FIELDS)
    data = await get_json(session, ARCGIS_URL, params)
    features = data.get("features") or []
    results = summarize(lat, lon, features)
    _LOGGER.debug(
        "USPL nearby: %d features -> %d unique units", len(features), len(results)
    )
    return results
