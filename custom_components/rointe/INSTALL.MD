# Description
This is an integration for Rointe connected radiators. It uses the official web app REST API for retrieving and updating the devices.

## Warning
This code is still under development. You can add it to your live HomeAssistant but don't leave it running for extended periods of time.

## Changelog
> Please see the file CHANGELOG.MD in this repository.


# How to Install as a Custom Component
Before you begin please remove the existing integration (if you have installed it before).
To install the code as a custom integration on your existing HomeAssistant follow these steps:

> **Warning:** Perform a full backup of your installation before proceeding.

## 1. Uploading the code to your HomeAssistant
_Note:_ You can use whatever method you prefer to upload the code.

1. Download the folder `homeasisstant/components/rointe` from this repository.
    * Ensure you're at the `rointe-integration` branch.
2. Create a ZIP archive with the contents. (For example `rointe.zip`)
3. Using the file editor add-on, create a folder called `custom_components/` under `config/`
4. Upload your zip to `custom_components`
5. Using the terminal Add-on execute:
    * `cd /config/custom_components`
    * `unzip rointe.zip`

    **Ensure your files end up in a structure like**

    ```
    /config/custom_components/rointe/manigest.json
    /config/custom_components/rointe/__init__.py
    /config/custom_components/rointe/climate.py
    etc....
    ```
## 2. Configuration
Using the file editor add-on edit the file `homeasisstant/components/rointe/manifest.json` and add a version parameter at the end:

> **Note**: Pay attention to the commas in the last and second to last lines.

```
{
  "domain": "rointe",
  "name": "Rointe Heaters",
  "config_flow": true,
  "documentation": "https://www.home-assistant.io/integrations/rointe",
  "requirements": [],
  "ssdp": [],
  "zeroconf": [],
  "homekit": {},
  "dependencies": [],
  "codeowners": ["@tggm"],
  "iot_class": "cloud_polling",
  "version": "1.0.6"
}
```

## 3. Cleanups
If you're updating the code (ie. you installed it before) you'll need to remove the __pycache__ folders.
Run the following in the terminal Add-On:

> **Be careful here. Type the comands by hand. Do not use copy/paste.**

```
rm -rf /config/custom_components/rointe/__pycache__
rm -rf /config/custom_components/rointe/api/__pycache__
```

## 4. Running
1. Restart Home Assistant
2. After restart, you should be able to add an integration called **Rointe**
3. Add your RointeConnect credentials and pick an installation.
4. Good luck!