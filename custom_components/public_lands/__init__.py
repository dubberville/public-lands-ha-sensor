from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS = ["sensor", "button", "geo_location"]


async def async_setup(hass: HomeAssistant, config: dict):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("sensors", [])
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("sensors", [])
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    """Options are read at query time, so a change only needs a state refresh."""
    for sensor in hass.data.get(DOMAIN, {}).get("nearby_sensors", []):
        sensor.async_schedule_update_ha_state()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        for key in ("geo_add_entities", "geo_entities", "nearby_sensors"):
            hass.data.get(DOMAIN, {}).pop(key, None)
    return unload_ok
