"""Map markers for nearby open public land.

One entity per nearby result, keyed by unit name.

Refreshes apply a delta rather than removing everything and rebuilding: units
that are still in range are updated in place, units that dropped out are
removed, and only genuinely new units create entities. Removing and recreating
would reuse the same entity_id within one refresh, and the removal lands after
the new entity has claimed that id, blanking its state.

Entities are created without a unique_id: they are transient, so keeping them
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
    data.setdefault("geo_entities", {})

    # A refresh may have already run before this platform finished setting up.
    pending = data.get("nearby") or []
    if pending:
        max_results = (data.get("nearby_options") or {}).get("max_results")
        await async_sync_geo_locations(
            hass, pending[:max_results] if max_results else pending
        )


async def async_sync_geo_locations(hass: HomeAssistant, results=None):
    """Bring markers in line with the given results. No results clears the map."""
    data = hass.data.setdefault(DOMAIN, {})
    current = data.setdefault("geo_entities", {})
    wanted = {result["name"]: result for result in (results or [])}

    # Units that are no longer in range
    for name in list(current):
        if name not in wanted:
            entity = current.pop(name)
            if entity.hass is not None:
                await entity.async_remove(force_remove=True)

    # Units still in range keep their entity and just get new numbers
    added = []
    for name, result in wanted.items():
        entity = current.get(name)
        if entity is None:
            entity = PublicLandsGeoLocation(result)
            current[name] = entity
            added.append(entity)
        else:
            entity.update_result(result)

    if added:
        add_entities = data.get("geo_add_entities")
        if add_entities is None:
            # Platform not set up yet; async_setup_entry will pick these up.
            for entity in added:
                current.pop(entity.unit_name, None)
            _LOGGER.debug(
                "geo_location platform not ready, deferring %d marker(s)", len(added)
            )
            return
        add_entities(added)

    _LOGGER.debug(
        "USPL markers: %d total, %d added", len(current), len(added)
    )


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
        self._apply(result)

    @property
    def unit_name(self) -> str:
        return self._result["name"]

    def _apply(self, result: dict) -> None:
        self._result = result
        self._attr_distance = result["distance_miles"]
        self._attr_latitude = result["latitude"]
        self._attr_longitude = result["longitude"]

    def update_result(self, result: dict) -> None:
        """Refresh this marker's position and distance in place."""
        self._apply(result)
        if self.hass is not None:
            self.async_write_ha_state()

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
