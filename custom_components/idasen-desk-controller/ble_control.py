#!python3
import os
import sys
import struct
import asyncio
from bleak import BleakClient, BleakError, BleakScanner
import pickle
from appdirs import user_config_dir

IS_LINUX = sys.platform == "linux" or sys.platform == "linux2"
IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

# GATT CHARACTERISTIC AND COMMAND DEFINITIONS
UUID_HEIGHT = '99fa0021-338a-1024-8a49-009c0215f78a'
UUID_COMMAND = '99fa0002-338a-1024-8a49-009c0215f78a'
UUID_REFERENCE_INPUT = '99fa0031-338a-1024-8a49-009c0215f78a'

COMMAND_UP = bytearray(struct.pack("<H", 71))
COMMAND_DOWN = bytearray(struct.pack("<H", 70))
COMMAND_STOP = bytearray(struct.pack("<H", 255))

COMMAND_REFERENCE_INPUT_STOP = bytearray(struct.pack("<H", 32769))
COMMAND_REFERENCE_INPUT_UP = bytearray(struct.pack("<H", 32768))
COMMAND_REFERENCE_INPUT_DOWN = bytearray(struct.pack("<H", 32767))

# OTHER DEFINITIONS
DEFAULT_CONFIG_DIR = user_config_dir('idasen-controller')
PICKLE_FILE = os.path.join(DEFAULT_CONFIG_DIR, 'desk.pickle')

# CONFIGURATION SETUP

# Height of the desk at it's lowest (in mm)
# I assume this is the same for all Idasen desks
BASE_HEIGHT = 620
MAX_HEIGHT = 1270  # 6500

# Default config
# if not os.path.isfile(DEFAULT_CONFIG_PATH):
#     os.makedirs(os.path.dirname(DEFAULT_CONFIG_PATH), exist_ok=True)
#     shutil.copyfile(os.path.join(os.path.dirname(__file__), 'example', 'config.yaml'), DEFAULT_CONFIG_PATH)

config = {
    "mac_address": "D3C7A6E9-0AF3-408E-B1C4-9EA3FC6C280A",
    "height_tolerance": 2.0,
    "adapter_name": 'hci0',
    "scan_timeout": 5,
    "connection_timeout": 20,
    "movement_timeout": 30,
    "sit": False,
    "stand": False,
    "monitor": False,
    "move_to": None
}


class BLEController:
    def __init__(self, height_speed_callback=None):
        """Set up the async event loop and signal handlers"""
        print("Init BLEController")
        self.client = None
        self.height_speed_callback = height_speed_callback
        self.is_moving = False
        self.target_height = None
        self.count = 0
        self.direction = None
        self.move_done = None

    async def start_monitoring(self):
        await self.get_current_state()
        await self._subscribe(UUID_HEIGHT, self._height_data_callback)

    async def get_current_state(self):
        self.client = await self.connect()
        height_raw, speed_raw = struct.unpack("<Hh", await self.client.read_gatt_char(UUID_HEIGHT))
        height, speed = self._format_height_speed(height_raw, speed_raw)
        print("Height: {:4.0f}mm Speed: {:2.0f}mm/s".format(height, speed))
        if self.height_speed_callback is not None:
            self.height_speed_callback(height, speed)
        return height, speed

    async def _read_state(self):  # REPLACE ALL
        return struct.unpack("<Hh", await self.client.read_gatt_char(UUID_HEIGHT))

    async def scan(self, mac_address=None):
        """Scan for a bluetooth device with the configured address and return it or return all devices if no address specified"""
        print('Scanning')
        scanner = BleakScanner()
        devices = await scanner.discover(device=config['adapter_name'], timeout=config['scan_timeout'])
        if not mac_address:
            print(f"Found {len(devices)} devices using {config['adapter_name']}")
            device_dict = {}
            for device in devices:
                print(device)
                device_dict[device.name] = device.address
            return device_dict
        for device in devices:
            if (device.address == mac_address):
                print('Scanning - Desk Found')
                return device
        print(f'Scanning - Desk {mac_address} Not Found')
        return None

    async def disconnect(self):
        print("disconnect called")
        if self.client:
            print('Disconnecting')
            await self.stop_movement()
            if self.client.is_connected:
                await self.client.disconnect()
            print('Disconnected')

    async def connect(self, attempt=0):
        """Attempt to connect to the desk"""
        # Attempt to load and connect to the pickled desk
        if self.client is not None and self.client.is_connected:
            return self.client
        desk = self.unpickle_desk()
        if desk:
            pickled = True
        if not desk:
            # If that fails then rescan for the desk
            desk = await self.scan(config['mac_address'])
        if not desk:
            print('Could not find desk {}'.format(config['mac_address']))
            os._exit(1)
        # Cache the Bleak device config to connect more quickly in future
        self.pickle_desk(desk)
        try:
            print('Connecting')
            if not self.client:
                self.client = BleakClient(desk, device=config['adapter_name'])
                if not IS_MAC:
                    print("TRY PAIRING")
                    ret = await self.client.pair()
                    print(f"RET: {ret}")
            await self.client.connect(timeout=config['connection_timeout'])
            print("Connected {}".format(config['mac_address']))
            return self.client
        except BleakError as e:
            if attempt == 0 and pickled:
                # Could be a bad pickle so remove it and try again
                try:
                    os.remove(PICKLE_FILE)
                    print('Connecting failed - Retrying without cached connection')
                except OSError:
                    pass
                return await self.connect(attempt=attempt + 1)
            else:
                print('Connecting failed')
                print(e)
                os._exit(1)

    async def move_to_position(self, position):
        self.client = await self.connect()
        self.target_height = self._mm_to_raw(position)
        await self.move_to()
        if self.target_height:
            # If we were moving to a target height, wait, then print the actual final height
            await asyncio.sleep(1)
            height_raw, speed_raw = struct.unpack("<Hh", await self.client.read_gatt_char(UUID_HEIGHT))
            height, speed = self._format_height_speed(height_raw, speed_raw)
            #print("Final height: {:4.0f}mm (Target: {:4.0f}mm)".format(height, self._raw_to_mm(target)))
            if self.height_speed_callback is not None:
                self.height_speed_callback(height, speed)

    async def stop_movement(self):
        # This emulates the behaviour of the app. Stop commands are sent to both
        # Reference Input and Command characteristics.
        await self.client.write_gatt_char(UUID_COMMAND, COMMAND_STOP)
        if IS_LINUX:
            # It doesn't like this on windows
            await self.client.write_gatt_char(UUID_REFERENCE_INPUT, COMMAND_REFERENCE_INPUT_STOP)

    async def move_to(self):
        """Move the desk to a specified height"""

        initial_height, speed = struct.unpack("<Hh", await self.client.read_gatt_char(UUID_HEIGHT))

        # Initialise by setting the movement direction
        self.direction = "UP" if self.target_height > initial_height else "DOWN"

        # Set up callback to run when the desk height changes. It will resend
        # movement commands until the desk has reached the target height.
        # loop = asyncio.get_event_loop()
        # self.move_done = loop.create_future()
        self.count = 0
        self.is_moving = True

        # Listen for changes to desk height and send first move command (if we are
        # not already at the target height).
        if not self._has_reached_target(initial_height):
            #await self._subscribe(UUID_HEIGHT, _move_to_callback)
            if self.direction == "UP":
                asyncio.create_task(self._move_up())
            elif self.direction == "DOWN":
                asyncio.create_task(self._move_down())
            # try:
            #     await asyncio.wait_for(self.move_done, timeout=config['movement_timeout'])
            # except asyncio.TimeoutError as e:
            #     print('Timed out while waiting for desk')
            #     print(e)
                #await self._unsubscribe(UUID_HEIGHT)

    def _height_data_callback(self, sender, data):
        height_raw, speed_raw = struct.unpack("<Hh", data)
        height, speed = self._format_height_speed(height_raw, speed_raw)
        #print("Height: {:4.0f}mm Speed: {:2.0f}mm/s".format(height, speed))

        if self.is_moving:
            self.count = self.count + 1
            if self.height_speed_callback is not None:
                self.height_speed_callback(height, speed)
            print("Height: {:4.0f}mm Target: {:4.0f}mm Speed: {:2.0f}mm/s".format(height, self._raw_to_mm(self.target_height), speed))

            # Stop if we have reached the target OR
            # If you touch desk control while the script is running then movement
            # callbacks stop. The final call will have speed 0 so detect that
            # and stop.
            if speed == 0 or self._has_reached_target(height_raw):
                asyncio.create_task(self.stop_movement())
                self.is_moving = False
                #asyncio.create_task(self._unsubscribe(UUID_HEIGHT))
                # try:
                #     self.move_done.set_result(True)
                # except asyncio.exceptions.InvalidStateError:
                #     # This happens on windows, I dont know why
                #     pass
            # Or resend the movement command if we have not yet reached the
            # target.
            # Each movement command seems to run the desk motors for about 1
            # second if uninterrupted and the height value is updated about 16
            # times.
            # Resending the command on the 6th update seems a good balance
            # between helping to avoid overshoots and preventing stutterinhg
            # (the motor seems to slow if no new move command has been sent)
            elif self.direction == "UP" and self.count == 6:
                asyncio.create_task(self._move_up())
                self.count = 0
            elif self.direction == "DOWN" and self.count == 6:
                asyncio.create_task(self._move_down())
                self.count = 0

        if self.height_speed_callback is not None:
            self.height_speed_callback(height, speed)

    def _has_reached_target(self, height):
        # The notified height values seem a bit behind so try to stop before
        # reaching the target value to prevent overshooting
        return (abs(height - self.target_height) <= 10 * config['height_tolerance'])

    async def _move_up(self):
        await self.client.write_gatt_char(UUID_COMMAND, COMMAND_UP)

    async def _move_down(self):
        await self.client.write_gatt_char(UUID_COMMAND, COMMAND_DOWN)

    async def _subscribe(self, uuid, callback):
        """Listen for notifications on a characteristic"""
        await self.client.start_notify(uuid, callback)

    async def _unsubscribe(self, uuid):
        try:
            await self.client.stop_notify(uuid)
        except KeyError:
            # This happens on windows, I don't know why
            pass

    def _mm_to_raw(self, mm):
        return (mm - BASE_HEIGHT) * 10

    def _raw_to_mm(self, raw):
        return (raw / 10) + BASE_HEIGHT

    def _raw_to_speed(self, raw):
        return (raw / 100)

    def _format_height_speed(self, height, speed):
        return int(self._raw_to_mm(height)), int(self._raw_to_speed(speed))

    def unpickle_desk(self):
        """Load a Bleak device config from a pickle file and check that it is the correct device"""
        try:
            if IS_LINUX:
                with open(PICKLE_FILE, 'rb') as f:
                    desk = pickle.load(f)
                    if desk.address == config['mac_address']:
                        return desk
        except Exception:
            pass
        return None

    def pickle_desk(self, desk):
        """Attempt to pickle the desk"""
        if IS_LINUX:
            with open(PICKLE_FILE, 'wb') as f:
                pickle.dump(desk, f)
