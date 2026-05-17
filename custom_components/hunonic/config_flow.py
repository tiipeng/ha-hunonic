from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HunonicAuthError, HunonicClient, HunonicError
from .const import CONF_BASE_URL, CONF_HOME_ID, CONF_TOKEN_ID, DEFAULT_BASE_URL, DOMAIN


class HunonicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = HunonicClient(session, user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL))
            try:
                login = await client.login(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
                token_id = (login.get("data") or {}).get("token_id")
                profile = await client.profile(token_id)
                profile_data = profile.get("data") or {}
                home_id = profile_data.get("home_default_id")
                if not token_id or not home_id:
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(str(profile_data.get("id") or user_input[CONF_USERNAME]))
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=profile_data.get("name") or "Hunonic",
                        data={
                            CONF_USERNAME: user_input[CONF_USERNAME],
                            CONF_BASE_URL: user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL),
                            CONF_TOKEN_ID: token_id,
                            CONF_HOME_ID: str(home_id),
                        },
                    )
            except HunonicAuthError:
                errors["base"] = "invalid_auth"
            except HunonicError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
