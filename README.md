# Idasen Desk Controller Integration
Home Assistant integration to control the IKEA IDÅSEN standing desk. This integration might also work with other tables/controllers (DENCON). I tested this integration on MacOS and Linux. 

This project is work in progress. It is also my first python and open source project.

### Features
- Connect
- Device selection in configuration
- Monitors current height and speed
- Move up/down/position

### Pending features and known issues
- Pairing on Linux.  
    - The used bluetooth library "bleak" doesnt allow to pair before connecting.
    - On MacOS and Windows pairing happens automatically.
    - I will try to add a workaround (bluetoothctl wrapper)
- The bluetooth connection is sometimes a little bit flaky. The integration will try to reconnect (sometimes this fails)
    - Will hopefully be improved with the next "bleak" version
- Doesnt play well with other bluetooth integrations (Switchbot)
- Code quality needs to be improved (help wanted)

## Installation
### Installation with hacs
1. Make sure the HACS component is installed and working.
2. Add https://github.com/Xilinx64/idasen-desk-controller as a custom repository
3. Install component and reboot

### Manual Installation
Upload the custom component to Home Assistant's custom_components directory and restart the service.

## Configuration
### Pairing
Pairing needs to be done via terminal for now.  
Instuctions:
1. Start bluetoothctl: ```bluetoothctl```  
2. Start scan: ```scan on```
3. Wait until you see the mac address of the desk
4. Pair desk: ```pair 00:00:00:00:00:00```
5. Disconnect: ```disconnect 00:00:00:00:00:00```

### Home Assistant configuration
Add the integration through the Home Assistant interface.

## Awesome projects
- **idasen-controller** from rhyst (https://github.com/rhyst/idasen-controller) \
I use a stripped down and heavily modified version of this library.
- **hass-linak-dpg** from Laeborg (https://github.com/Laeborg/hass-linak-dpg) \
I used this project as a starting point.
- **bleak** from hbldh (https://github.com/hbldh/bleak) \
Bluetooth library

