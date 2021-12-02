"""Handles communications with rointe's API."""
from datetime import datetime, timedelta
import logging
import time
from typing import Any, Dict, Optional

import requests

from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
)

from ..api.exceptions import APIError, CannotConnect, InvalidAuth
from ..api.rointe_device import RointeDevice, ScheduleMode
from ..const import (
    AUTH_ACCT_INFO_URL,
    AUTH_HOST,
    AUTH_TIMEOUT_SECONDS,
    AUTH_VERIFY_URL,
    FIREBASE_APP_KEY,
    FIREBASE_DEFAULT_URL,
    FIREBASE_DEVICE_DATA_PATH_BY_ID,
    FIREBASE_DEVICES_PATH_BY_ID,
    FIREBASE_INSTALLATIONS_PATH,
)

_LOGGER = logging.getLogger(__name__)


def get_local_id(auth_token: str) -> str:
    """Retrieve user local_id value."""

    if not auth_token:
        _LOGGER.error("No ID token. Call login() first")
        raise CannotConnect

    payload = {"idToken": auth_token}

    response = requests.post(
        f"{AUTH_HOST}{AUTH_ACCT_INFO_URL}?key={FIREBASE_APP_KEY}",
        data=payload,
    )

    if not response:
        _LOGGER.error("No response from %s while authenticating", AUTH_HOST)
        raise CannotConnect

    if response.status_code != 200:
        _LOGGER.error("Get account info returned %s", response.status_code)
        raise APIError

    response_json = response.json()

    return response_json["users"][0]["localId"]


def login_user(username: str, password: str):
    """Log the user in."""

    payload = {"email": username, "password": password, "returnSecureToken": True}

    response = requests.post(
        f"{AUTH_HOST}{AUTH_VERIFY_URL}?key={FIREBASE_APP_KEY}",
        data=payload,
        timeout=AUTH_TIMEOUT_SECONDS,
    )

    if not response:
        raise CannotConnect

    if response.status_code != 200:
        raise InvalidAuth

    response_json = response.json()

    if not response_json or "idToken" not in response_json:
        raise APIError

    data = {
        "auth_token": response_json["idToken"],
        "expires": datetime.now() + timedelta(seconds=int(response_json["expiresIn"])),
    }

    return data


def get_installation_by_id(
    installation_id: str, local_id: str, auth_token: str
) -> Dict[Any, Any]:
    """Retrieve a specific installation by ID."""

    args = {"auth": auth_token, "orderBy": '"userid"', "equalTo": f'"{local_id}"'}
    url = f"{FIREBASE_DEFAULT_URL}{FIREBASE_INSTALLATIONS_PATH}"

    response = requests.get(url, params=args)

    if not response:
        _LOGGER.error("No response from %s while retrieving installations", url)
        raise CannotConnect

    if response.status_code != 200:
        _LOGGER.error("Get installations returned %s", response.status_code)
        raise InvalidAuth

    reponse_json = response.json()

    if len(reponse_json) == 0 or installation_id not in reponse_json:
        _LOGGER.error("No Rointe installations found")
        raise APIError

    return reponse_json[installation_id]


def get_installations(local_id: str, auth_token: str) -> Dict[str, str]:
    """Retrieve the client's installations."""

    args = {"auth": auth_token, "orderBy": '"userid"', "equalTo": f'"{local_id}"'}
    url = f"{FIREBASE_DEFAULT_URL}{FIREBASE_INSTALLATIONS_PATH}"

    response = requests.get(url, params=args)

    if not response:
        _LOGGER.error("No response from %s while retrieving installations", url)
        raise CannotConnect

    if response.status_code != 200:
        _LOGGER.error("Get installations returned %s", response.status_code)
        raise InvalidAuth

    reponse_json = response.json()

    if len(reponse_json) == 0:
        _LOGGER.error("No Rointe installations found")
        raise APIError

    installations = {}

    for key in reponse_json.keys():
        installations[key] = reponse_json[key]["location"]

    return installations


def get_device(device_id: str, auth_token: str) -> object:
    """Retrieve device data."""

    args = {"auth": auth_token}

    response = requests.get(
        "{}{}".format(
            FIREBASE_DEFAULT_URL, FIREBASE_DEVICES_PATH_BY_ID.format(device_id)
        ),
        params=args,
    )

    if not response:
        _LOGGER.error(
            "No response from %s while retrieving device %s", AUTH_HOST, device_id
        )
        return None

    if response.status_code != 200:
        _LOGGER.error("Get device returned %s", response.status_code)
        return None

    return response.json()


def set_device_temp(device: RointeDevice, auth_token: str, new_temp: float) -> bool:
    """Set the device target temperature."""

    device_id = device.id
    args = {"auth": auth_token}
    body = {"temp": new_temp, "mode": "manual"}

    url = "{}{}".format(
        FIREBASE_DEFAULT_URL, FIREBASE_DEVICE_DATA_PATH_BY_ID.format(device_id)
    )

    return _send_patch_request(device_id, url, args, body)


def set_device_preset(device: RointeDevice, auth_token: str, preset_mode: str) -> bool:
    """Set the preset."""

    device_id = device.id
    args = {"auth": auth_token}
    body: Dict[str, Any] = {}

    url = "{}{}".format(
        FIREBASE_DEFAULT_URL, FIREBASE_DEVICE_DATA_PATH_BY_ID.format(device_id)
    )

    if preset_mode == HVAC_MODE_OFF:
        body = {"power": False, "mode": "manual"}
        return _send_patch_request(device_id, url, args, body)

    elif preset_mode == HVAC_MODE_HEAT:
        body = {"mode": "manual", "power": True, "status": "none"}
        return _send_patch_request(device_id, url, args, body)

    elif preset_mode == HVAC_MODE_AUTO:
        current_mode: ScheduleMode = device.get_current_schedule_mode()

        # For reasons unknown when changing modes we need to send the proper
        # temperature also.
        if current_mode == ScheduleMode.COMFORT:
            body = {"temp": device.comfort_temp}
        elif current_mode == ScheduleMode.ECO:
            body = {"temp": device.eco_temp}
        elif device.ice_mode:
            body = {"temp": device.ice_temp}
        else:
            body = {"temp": 20}

        request_power_status = _send_patch_request(device_id, url, args, body)

        # and then set AUTO mode.
        request_mode_status = _send_patch_request(
            device_id, url, args, {"mode": "auto", "power": True}
        )

        return request_power_status and request_mode_status

    else:
        _LOGGER.error("Invalid HVAC_MODE: %s", preset_mode)
        return False


def _send_patch_request(
    device_id: str,
    url: str,
    params: Optional[Dict[str, Any]] = None,
    body=None,
) -> bool:
    """Send a patch request."""

    body["last_sync_datetime_app"] = round(time.time() * 1000)

    _LOGGER.debug("Sending patch request body: %s", body)

    response = requests.patch(
        url,
        params=params,
        json=body,
    )

    if not response:
        _LOGGER.error(
            "No response from %s while setting sending %s to %s",
            AUTH_HOST,
            str(body),
            device_id,
        )
        return False

    if response.status_code != 200:
        _LOGGER.error(
            "Got response %s from %s while setting sending %s to %s",
            response.status_code,
            AUTH_HOST,
            str(body),
            device_id,
        )
        return False

    return True
