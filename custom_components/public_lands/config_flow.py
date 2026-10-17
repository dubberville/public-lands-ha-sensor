import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_MANAGERS,
    CONF_MAX_RESULTS,
    CONF_OPEN_ONLY,
    CONF_RADIUS,
    DEFAULT_MANAGERS,
    DEFAULT_MAX_RESULTS,
    DEFAULT_OPEN_ONLY,
    DEFAULT_RADIUS,
    DOMAIN,
    MANAGER_GROUPS,
    MAX_RADIUS,
    MIN_RADIUS,
)


class PublicLandsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Public Lands."""

    async def async_step_user(self, user_input=None):
        return self.async_create_entry(title="Public Lands", data={})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PublicLandsOptionsFlow()


class PublicLandsOptionsFlow(config_entries.OptionsFlow):
    """Options for the nearby open public land lookup."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_RADIUS,
                    default=options.get(CONF_RADIUS, DEFAULT_RADIUS),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_RADIUS,
                        max=MAX_RADIUS,
                        step=5,
                        unit_of_measurement="mi",
                        mode=NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Required(
                    CONF_MANAGERS,
                    default=options.get(CONF_MANAGERS, DEFAULT_MANAGERS),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=list(MANAGER_GROUPS),
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_OPEN_ONLY,
                    default=options.get(CONF_OPEN_ONLY, DEFAULT_OPEN_ONLY),
                ): BooleanSelector(),
                vol.Required(
                    CONF_MAX_RESULTS,
                    default=options.get(CONF_MAX_RESULTS, DEFAULT_MAX_RESULTS),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=50, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
