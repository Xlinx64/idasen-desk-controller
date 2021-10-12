# Idasen Desk Controller Integration
Home Assistant integration to control the IKEA IDÅSEN standing desk. This integration might also work with other tables/controllers (DENCON). I tested this integration on MacOS and Linux. 

This project is work in progress. It is also my first python and open source projekt.

### Features
- Pair and connect
- Device selection in configuration
- Current height and speed
- Move up/down/position

## Installation
### Installation with hacs
1. Make sure the HACS component is installed and working.
2. Add https://github.com/Xilinx64/idasen-desk-controller as a custom repository
3. Install component and reboot

### Manual Installation
Upload the custom component to Home Assistant's custom_components directory and restart the service.

## Configuration
Add the integration through the Home Assistant interface.

## Awesome projects
- **idasen-controller** from rhyst (https://github.com/rhyst/idasen-controller) \
I use a stripped down and heavily modified version of this library.
- **hass-linak-dpg** from Laeborg (https://github.com/Laeborg/hass-linak-dpg) \
I used this project as a starting point.

