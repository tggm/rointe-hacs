# V1.0.5
* Further fixes initialization error for V1 devices.

# V1.0.5
* Fixes initialization error for V1 devices.

# V1.0.4
* Fixed error in import that prevented the integration from being run as a custom_component.
* Add instructions for updating in INSTALL.MD

# V1.0.3
* Device status is optimistically updated after successfully sending a command.
* Setting automode takes into account anti-frost mode.
* Error handling for radiator actions.
* Sensor entity now shows the current (probe) temperature, not the target one.

# V1.0.2
* Setting Auto mode takes the schedule into account.

# V1.0.1
* Added the CT.2 thermostat (experimental support)
* Setting Auto mode now works if the schedule is not currently active.
* User mode limits are now taken into account (limits max and min temperatures)