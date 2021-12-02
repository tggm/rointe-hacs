"""Config flow for Rointe Heaters integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .api.api_wrapper import get_installations, get_local_id, login_user
from .api.exceptions import APIError, CannotConnect, InvalidAuth
from .const import (
    CONF_INSTALLATION,
    CONF_LOCAL_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_USERNAME,
        ): str,
        vol.Required(
            CONF_PASSWORD,
        ): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Rointe Heaters."""

    VERSION = 1

    def __init__(self) -> None:
        """Config flow init."""
        super().__init__()
        self.step_user_data: dict[str, Any] | None = None
        self.step_user_local_id: str | None = None
        self.step_user_installations: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step: User credentials validation."""

        errors = {}

        if user_input is not None:
            try:
                login_data = await self.hass.async_add_executor_job(
                    login_user, user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )

                local_id = await self.hass.async_add_executor_job(
                    get_local_id, login_data["auth_token"]
                )

                installations = await self.hass.async_add_executor_job(
                    get_installations, local_id, login_data["auth_token"]
                )

                # If we get this far then we have logged in and determined the local_id. Go the next step.
                self.step_user_data = user_input
                self.step_user_local_id = local_id
                self.step_user_installations = installations

                return await self.async_step_installation(login_data)

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except APIError:
                errors["base"] = "unknown"

        # TODO -> ?
        if user_input is None:
            user_input = {}
        # TODO -> ?

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_installation(self, user_input=None) -> FlowResult:
        """Select the installation."""

        errors: dict[str, str] = {}

        if user_input and CONF_INSTALLATION in user_input:
            assert self.step_user_data is not None
            assert self.step_user_installations is not None

            user_data = {
                CONF_INSTALLATION: user_input[CONF_INSTALLATION],
                CONF_USERNAME: self.step_user_data[CONF_USERNAME],
                CONF_PASSWORD: self.step_user_data[CONF_PASSWORD],
                CONF_LOCAL_ID: self.step_user_local_id,
            }

            return self.async_create_entry(
                title=self.step_user_installations[user_input[CONF_INSTALLATION]],
                description="Rointe",
                data=user_data,
            )

        step_schema = vol.Schema(
            {vol.Required(CONF_INSTALLATION): vol.In(self.step_user_installations)}
        )

        return self.async_show_form(
            step_id="installation", data_schema=step_schema, errors=errors
        )
