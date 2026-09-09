"""Map markers for nearby open public land.

One entity per nearby result, recreated on every refresh. The entities are
deliberately created without a unique_id: they are transient, so leaving them
out of the entity registry means a shrinking result list cannot strand orphaned
markers on the map.
"""

import logging

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SOURCE = "public_lands"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Hold on to the add-entities callback so refreshes can create markers."""
    data = hass.data.setdefault(DOMAIN, {})
    data["geo_add_entities"] = async_add_entities
    data.setdefault("geo_entities", [])

    # A refresh may have already run before this platform finished setting up.
    pending = data.get("nearby") or []
    if pending:
        max_results = (data.get("nearby_options") or {}).get("max_results")
        await async_sync_geo_locations(hass, pending[:max_results] if max_results else pending)


async def async_sync_geo_locations(hass: HomeAssistant, results=None):
    """Replace all markers with the given results. No results clears the map."""
    data = hass.data.setdefault(DOMAIN, {})
    existing = data.get("geo_entities") or []

    for entity in existing:
        if entity.hass is not None:
            await entity.async_remove(force_remove=True)
    data["geo_entities"] = []

    if not results:
        _LOGGER.debug("Cleared USPL map markers")
        return

    add_entities = data.get("geo_add_entities")
    if add_entities is None:
        # Platform not set up yet; async_setup_entry will pick these up.
        _LOGGER.debug("geo_location platform not ready, deferring %d marker(s)", len(results))
        return

    entities = [PublicLandsGeoLocation(result) for result in results]
    data["geo_entities"] = entities
    add_entities(entities)
    _LOGGER.debug("Added %d USPL map marker(s)", len(entities))


class PublicLandsGeoLocation(GeolocationEvent):
    """A single nearby public land unit, shown as a marker on the map."""

    _attr_should_poll = False
    _attr_icon = "mdi:tree"
    _attr_source = SOURCE
    _attr_unit_of_measurement = UnitOfLength.MILES

    def __init__(self, result: dict):
        # source/distance/latitude/longitude are cached properties on the base
        # class, so set the backing attributes rather than overriding them.
        self._result = result
        self._attr_name = result["name"]
        self._attr_distance = result["distance_miles"]
        self._attr_latitude = result["latitude"]
        self._attr_longitude = result["longitude"]

    @property
    def extra_state_attributes(self):
        return {
            "manager": self._result["manager"],
            "management_type": self._result["management_type"],
            "designation": self._result["designation"],
            "public_access": self._result["public_access"],
            "bearing_degrees": self._result["bearing_degrees"],
            "bearing_compass": self._result["bearing_compass"],
            "google_maps_url": self._result["google_maps_url"],
            "apple_maps_url": self._result["apple_maps_url"],
        }
