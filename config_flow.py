"""Config flow for Rointe Heaters integration."""
from __future__ import annotations

import logging
from typing import Any

from rointesdk.rointe_api import RointeAPI
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

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
        rointe_api: RointeAPI

        if user_input is not None:
            try:
                rointe_api = RointeAPI(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )

                login_error_code = await self.hass.async_add_executor_job(
                    rointe_api.initialize_authentication
                )

                if not rointe_api.is_logged_in():
                    raise Exception(login_error_code)

                local_id_response = await self.hass.async_add_executor_job(
                    rointe_api.get_local_id
                )

                if not local_id_response.success:
                    raise Exception(local_id_response.error_message)

                local_id = local_id_response.data

                installations_response = await self.hass.async_add_executor_job(
                    rointe_api.get_installations, local_id
                )

                if not installations_response.success:
                    raise Exception(installations_response.error_message)

                installations = installations_response.data

                # If we get this far then we have logged in and determined the local_id. Go the next step.
                self.step_user_data = user_input
                self.step_user_local_id = local_id
                self.step_user_installations = installations

                return await self.async_step_installation(None)

            except Exception as ex:
                errors["base"] = str(ex)

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
