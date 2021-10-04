# Linak DPG Desk Panel Integration
Home Assistant integration to control Linak DPG Desk Panels (eg. IKEA IDÅSEN or DENCON) with adjustable heights. The integration uses a custom bluetoothctl wrapper and does not require pybluez. The integration is developed with focus on Home Assistant OS and is not requiring other server tools.

The project is work in progress.

### Features
- Pair and connect
- Current height

### Pending
- Device selection under installation
- Offset
- Move up/move down
- Stop moving
- Save favorites

## Installation
### Installation with hacs
1. Make sure the HACS component is installed and working.
2. Add https://github.com/Laeborg/hass-linak-dpg as a custom repository
3.  Install component and reboot

### Manual Installation
Upload the custom component to Home Assistant's custom_components directory and restart the service.

## Configuration

### Recommended configuration
Add the integration though interface of Home Assistant

### Manual configuration
Add the sensor to your configuration.yaml:
```
sensor:
  - platform: linak_dpg
    name: Linak Desk
    address: 00:11:22:33:44:55
```

## Notable projects
Open Source is awesome! This integration is inspired by the following projects:
- nconrad's [idasen-desk-controller](https://github.com/nconrad/idasen-desk-controller)
- kosme's [bluetoothctl_lib](https://github.com/kosme/bluetoothctl_lib)
