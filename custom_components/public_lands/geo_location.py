"""Map markers for nearby open public land.

One entity per nearby result, keyed by unit name, kept in step with the
coordinator's latest result (including the one restored at startup).

Refreshes apply a delta rather than removing everything and rebuilding: units
that are still in range are updated in place, units that dropped out are
removed, and only genuinely new units create entities. Removing and recreating
would reuse the same entity_id within one refresh, and the removal lands after
the new entity has claimed that id, blanking its state.

Entities are created without a unique_id: they are transient, so keeping them
out of the entity registry means a shrinking result list cannot strand orphaned
markers on the map.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_MAX_RESULTS, DOMAIN
from .coordinator import PublicLandsCoordinator
from .nearby import get_options

_LOGGER = logging.getLogger(__name__)

SOURCE = "public_lands"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PublicLandsCoordinator = hass.data[DOMAIN][entry.entry_id]
    markers = MarkerSync(hass, coordinator, async_add_entities)
    markers.sync()
    entry.async_on_unload(coordinator.async_add_listener(markers.sync))


class MarkerSync:
    """Brings markers in line with the coordinator's nearby results."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: PublicLandsCoordinator,
        add_entities: AddEntitiesCallback,
    ) -> None:
        self._hass = hass
        self._coordinator = coordinator
        self._add_entities = add_entities
        self._current: dict[str, PublicLandsGeoLocation] = {}

    @callback
    def sync(self) -> None:
        data = self._coordinator.data or {}
        limit = get_options(self._coordinator.entry)[CONF_MAX_RESULTS]
        wanted = {r["name"]: r for r in (data.get("nearby") or [])[:limit]}

        # Units that are no longer in range
        for name in list(self._current):
            if name not in wanted:
                entity = self._current.pop(name)
                if entity.hass is not None:
                    self._hass.async_create_task(entity.async_remove(force_remove=True))

        # Units still in range keep their entity and just get new numbers
        added = []
        for name, result in wanted.items():
            if (entity := self._current.get(name)) is None:
                entity = self._current[name] = PublicLandsGeoLocation(result)
                added.append(entity)
            else:
                entity.update_result(result)
        if added:
            self._add_entities(added)
        _LOGGER.debug("USPL markers: %d total, %d added", len(self._current), len(added))


class PublicLandsGeoLocation(GeolocationEvent):
    """A single nearby public land unit, shown as a marker on the map."""

    _attr_should_poll = False
    _attr_icon = "mdi:tree"
    _attr_source = SOURCE
    _attr_unit_of_measurement = UnitOfLength.MILES

    def __init__(self, result: dict[str, Any]) -> None:
        # source/distance/latitude/longitude are cached properties on the base
        # class, so set the backing attributes rather than overriding them.
        self._attr_name = result["name"]
        self._apply(result)

    def _apply(self, result: dict[str, Any]) -> None:
        self._result = result
        self._attr_distance = result["distance_miles"]
        self._attr_latitude = result["latitude"]
        self._attr_longitude = result["longitude"]

    def update_result(self, result: dict[str, Any]) -> None:
        """Refresh this marker's position and distance in place."""
        self._apply(result)
        if self.hass is not None:
            self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            key: self._result.get(key)
            for key in (
                "manager",
                "management_type",
                "designation",
                "public_access",
                "bearing_degrees",
                "bearing_compass",
                "google_maps_url",
                "apple_maps_url",
            )
        }
