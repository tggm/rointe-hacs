"""Rointe app data model."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

import homeassistant.util.dt as dt_util


class DeviceMode(Enum):
    """Device working mode."""

    AUTO = "auto"
    MAN = "manual"


class ScheduleMode(Enum):
    """Schedule mode."""

    COMFORT = "C"
    ECO = "E"
    NONE = "O"


class RointeDevice:
    """Represent a Rointe device from the API."""

    id: str
    name: str
    serialnumber: str
    type: str
    product_version: str

    nominal_power: int
    power: bool

    # Describes the preset: ICE, ECO, Comfort, None
    preset: str
    mode: str

    temp: float
    temp_calc: float
    temp_probe: float

    # preset temperatures
    comfort_temp: float
    eco_temp: float
    ice_temp: float

    # User mode
    um_max_temp: float
    um_min_temp: float
    user_mode: bool
    ice_mode: bool

    # Schedule
    schedule: list[str]
    schedule_day: int
    schedule_hour: int

    last_sync_datetime_app: datetime
    last_sync_datetime_device: datetime

    def __init__(self, device_id: str, device_info: dict) -> None:
        """Initialize the device from the rointe's json blob."""
        self.id = device_id
        self.type = device_info["data"]["type"]
        self.product_version = str.lower(device_info["data"]["product_version"])
        self.serialnumber = device_info["serialnumber"]

        self.update_data(device_info)

    def update_data(self, device_info: dict) -> None:
        """Update the device data from a Json object."""

        data = device_info["data"]

        self.name = data["name"]
        self.nominal_power = int(data["nominal_power"])
        self.power = bool(data["power"])
        self.preset = data["status"]
        self.mode = data["mode"]

        self.temp = float(data["temp"])
        self.temp_calc = float(data["temp_calc"])
        self.temp_probe = float(data["temp_probe"])

        self.comfort_temp = float(data["comfort"])
        self.eco_temp = float(data["eco"])
        self.ice_temp = float(data["ice"])

        # User mode settings are only valid for V2 radiators.
        if self.product_version == "v2":
            self.um_max_temp = float(data["um_max_temp"])
            self.um_min_temp = float(data["um_min_temp"])
            self.user_mode = bool(data["user_mode"])
        else:
            self.user_mode = False

        self.ice_mode = bool(data["ice_mode"])
        self.schedule = data["schedule"]
        self.schedule_day = data["schedule_day"]
        self.schedule_hour = data["schedule_hour"]

        self.last_sync_datetime_app = datetime.fromtimestamp(
            int(data["last_sync_datetime_app"]) / 1000.0
        )

        self.last_sync_datetime_device = datetime.fromtimestamp(
            int(data["last_sync_datetime_device"]) / 1000.0
        )

    def get_current_schedule_mode(self) -> ScheduleMode:
        """Return the current schedule mode for the device.

        Returns C for Comfort, E for Eco, O for no-schedule
        """
        day_time = dt_util.now()
        day_of_week = day_time.weekday()  # 0 is Monday
        hour_index = day_time.hour

        current_mode = self.schedule[day_of_week][hour_index]

        if current_mode == "C":
            return ScheduleMode.COMFORT
        elif current_mode == "E":
            return ScheduleMode.ECO
        else:
            return ScheduleMode.NONE

    def user_mode_supported(self) -> bool:
        """Return True if this device supports user mode."""
        return self.product_version == "v2"
