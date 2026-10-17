import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_RADIUS, DOMAIN
from .nearby import get_options

_LOGGER = logging.getLogger(__name__)

SENSOR_DEFINITIONS = {
    "Unit_Nm": ("Unit Name", "mdi:map-marker-radius"),
    "Pub_Access": ("Public Access", "mdi:key"),
    "MngTp_Desc": ("Management Type", "mdi:account-tie-hat"),
    "MngNm_Desc": ("Management Name", "mdi:domain"),
    "DesTp_Desc": ("Designation", "mdi:pine-tree"),
}

ACCESS_MAP = {
    "OA": "Open to the Public",
    "RA": "Restricted Access",
    "XA": "Closed to the Public",
    "PA": "Public Access by Permit",
    "TA": "Temporary Access Allowed",
    "UK": "Unknown"
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    hass.data.setdefault(DOMAIN, {}).setdefault("sensors", [])
    entities: list = []

    # Create standard USPL data sensors
    for key, (name, icon) in SENSOR_DEFINITIONS.items():
        sensor = PublicLandsSensor(hass, name, icon, key)
        hass.data[DOMAIN]["sensors"].append(sensor)
        entities.append(sensor)

    # Create and register the status and last_success sensors
    status_sensor = PublicLandsStatusBinarySensor(hass)
    last_success_sensor = LastSuccessSensor(hass)

    hass.data[DOMAIN]["status_sensor"] = status_sensor
    hass.data[DOMAIN]["last_success_sensor"] = last_success_sensor

    entities.append(last_success_sensor)
    entities.append(status_sensor)

    # Nearby open public land, populated when not currently on public land
    nearest_sensor = NearestOpenLandSensor(hass, entry)
    count_sensor = NearbyCountSensor(hass)
    hass.data[DOMAIN]["nearby_sensors"] = [nearest_sensor, count_sensor]
    entities.append(nearest_sensor)
    entities.append(count_sensor)

    # Register all sensors at once
    async_add_entities(entities, True)


class PublicLandsSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, name: str, icon: str, key: str):
        self.hass = hass
        self._attr_name = f"USPL {name}"
        self._attr_icon = icon
        self._key = key
        self._attr_unique_id = f"uspl_{key}"

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def state(self):
        raw_data = self.hass.data.get(DOMAIN, {}).get("latest_api_data", {})
        attributes = (raw_data.get("features") or [{}])[0].get("attributes", {})
        value = attributes.get(self._key)

        if self._key == "Unit_Nm" and value == "Non-PAD-US Area":
            return "Non-Protected Area"
        if self._key == "Pub_Access":
            return ACCESS_MAP.get(value, "Unknown Access Type")
        return value or "Unavailable"


class LastSuccessSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._attr_name = "USPL Last Successful Refresh"
        self._attr_unique_id = "uspl_last_success"
        self._attr_icon = "mdi:clock-outline"
        self._attr_device_class = "timestamp"

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def state(self):
        # device_class=timestamp must be a valid datetime/ISO string or None —
        # "Never" makes the frontend throw (Intl.RelativeTimeFormat) and freeze the
        # page, which breaks the iOS companion app. Use None instead.
        return self.hass.data.get(DOMAIN, {}).get("last_success") or None


class PublicLandsStatusBinarySensor(BinarySensorEntity):
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._attr_name = "USPL API Status"
        self._attr_unique_id = "uspl_api_status"
        self._attr_icon = "mdi:check-network"
        self._attr_device_class = "connectivity"

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def is_on(self) -> bool:
        return self.hass.data.get(DOMAIN, {}).get("status") == "ok"

    @property
    def extra_state_attributes(self):
        return {
            "last_success": self.hass.data.get(DOMAIN, {}).get("last_success", "Never")
        }


class NearestOpenLandSensor(SensorEntity):
    """Closest open public land unit when the van is not already on one."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self._entry = entry
        self._attr_name = "USPL Nearest Open Land"
        self._attr_unique_id = "uspl_nearest_open_land"
        self._attr_icon = "mdi:tree"

    @property
    def should_poll(self) -> bool:
        return False

    def _nearest(self):
        results = self.hass.data.get(DOMAIN, {}).get("nearby") or []
        return results[0] if results else None

    @property
    def state(self):
        nearest = self._nearest()
        return nearest["name"] if nearest else "None within range"

    @property
    def extra_state_attributes(self):
        data = self.hass.data.get(DOMAIN, {})
        results = data.get("nearby") or []
        options = get_options(self._entry)
        attrs = {
            "result_count": len(results),
            "search_radius_miles": options[CONF_RADIUS],
            "nearby_status": data.get("nearby_status", "unknown"),
        }
        nearest = self._nearest()
        if nearest:
            attrs.update({
                "distance_miles": nearest["distance_miles"],
                "bearing_degrees": nearest["bearing_degrees"],
                "bearing_compass": nearest["bearing_compass"],
                "manager": nearest["manager"],
                "management_type": nearest["management_type"],
                "designation": nearest["designation"],
                "public_access": nearest["public_access"],
                "latitude": nearest["latitude"],
                "longitude": nearest["longitude"],
                "google_maps_url": nearest["google_maps_url"],
                "apple_maps_url": nearest["apple_maps_url"],
            })
        return attrs


class NearbyCountSensor(SensorEntity):
    """How many matching units are within the search radius."""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._attr_name = "USPL Nearby Count"
        self._attr_unique_id = "uspl_nearby_count"
        self._attr_icon = "mdi:map-search"

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def state(self):
        return len(self.hass.data.get(DOMAIN, {}).get("nearby") or [])
