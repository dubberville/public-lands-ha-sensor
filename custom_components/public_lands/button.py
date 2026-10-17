import aiohttp
import async_timeout
import logging
from datetime import datetime

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util

from .const import CONF_MAX_RESULTS, DOMAIN, NON_PADUS
from .geo_location import async_sync_geo_locations
from .nearby import async_query_nearby, get_options

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    # Ensure the shared sensor list exists
    hass.data.setdefault(DOMAIN, {}).setdefault("sensors", [])

    # Create and register the refresh button
    button = RefreshUSPLButton(hass, entry, hass.data[DOMAIN]["sensors"])
    async_add_entities([button], True)


class RefreshUSPLButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, sensors: list):
        """Initialize the button with a handle to hass and the sensor list."""
        self.hass = hass
        self._entry = entry
        self._sensors = sensors
        self._attr_name = "Refresh USPL"
        self._attr_unique_id = "refresh_uspl"
        self._attr_icon = "mdi:refresh"

    async def async_press(self) -> None:
        _LOGGER.debug("USPL refresh button pressed")

        # Get location from zone.home or fallback to configured lat/lon
        zone = self.hass.states.get("zone.home")
        if zone:
            lat = round(zone.attributes.get("latitude"), 4)
            lon = round(zone.attributes.get("longitude"), 4)
        else:
            _LOGGER.warning("zone.home not found, using configured coords")
            lat = round(self.hass.config.latitude, 4)
            lon = round(self.hass.config.longitude, 4)

        url = (
            f"https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/"
            f"PADUS_Public_Access/FeatureServer/0/query?"
            f"geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326"
            f"&outFields=Unit_Nm,Pub_Access,MngTp_Desc,MngNm_Desc,DesTp_Desc"
            f"&returnGeometry=false&f=json"
        )

        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        data = await resp.json()

                        # Store data and update status
                        self.hass.data[DOMAIN]["latest_api_data"] = data
                        self.hass.data[DOMAIN]["last_success"] = dt_util.now().isoformat(timespec="seconds")
                        self.hass.data[DOMAIN]["status"] = "ok"
                        _LOGGER.info("USPL data refreshed successfully")

        except Exception as e:
            self.hass.data[DOMAIN]["status"] = "fail"
            _LOGGER.error(f"Failed to fetch public lands data: {e}")
            return

        await self._async_update_nearby(lat, lon)

        #  Refresh main USPL sensors
        for sensor in self._sensors:
            sensor.async_schedule_update_ha_state()

        #  Also refresh status/last_success sensors if available
        if "last_success_sensor" in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN]["last_success_sensor"].async_schedule_update_ha_state()

        if "status_sensor" in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN]["status_sensor"].async_schedule_update_ha_state()

        #  And the nearby sensors
        for sensor in self.hass.data[DOMAIN].get("nearby_sensors", []):
            sensor.async_schedule_update_ha_state()

    async def _async_update_nearby(self, lat: float, lon: float) -> None:
        """Look up nearby open public land, but only when not already on it.

        Only ever called after a successful point query, so a failure here is
        partial: keep API Status on, keep whatever nearby results we already
        had, and mark them stale.
        """
        data = self.hass.data[DOMAIN]
        features = (data.get("latest_api_data") or {}).get("features") or []
        unit = features[0].get("attributes", {}).get("Unit_Nm") if features else None

        if unit and unit != NON_PADUS:
            # On public land -- clear nearby results and remove map markers.
            _LOGGER.debug("On public land (%s), skipping nearby query", unit)
            data["nearby"] = []
            data["nearby_status"] = "on_public_land"
            await async_sync_geo_locations(self.hass)
            return

        options = get_options(self._entry)
        try:
            results = await async_query_nearby(lat, lon, options)
        except Exception as err:  # noqa: BLE001 - partial failure, keep prior data
            data["nearby_status"] = "stale"
            _LOGGER.warning("Nearby public lands query failed, keeping prior results: %s", err)
            return

        data["nearby"] = results
        data["nearby_status"] = "ok"
        data["nearby_options"] = options
        _LOGGER.info("USPL nearby refreshed: %d unit(s) within %s mi",
                     len(results), options["search_radius_miles"])
        await async_sync_geo_locations(self.hass, results[:options[CONF_MAX_RESULTS]])
