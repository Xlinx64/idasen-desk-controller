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

print(f"PLATFORM: {sys.platform}")

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
        self.count = 0

    async def run_command(self, action):
        """Begin the action specified by command line arguments and config"""
        # Always print current height
        self.client = await self.connect()
        initial_height, speed = struct.unpack("<Hh", await self.client.read_gatt_char(UUID_HEIGHT))
        print("Height: {:4.0f}mm".format(self._raw_to_mm(initial_height)))
        target = None
        if action == "monitor":
            # Print changes to height data
            await self.subscribe(self.client, UUID_HEIGHT, self._height_data_callback)
            loop = asyncio.get_event_loop()
            wait = loop.create_future()
            await wait

        elif action == "move":
            # Move to custom height
            target = self._mm_to_raw(config['move_to'])
            await self.move_to(self.client, target)
        if target:
            # If we were moving to a target height, wait, then print the actual final height
            await asyncio.sleep(1)
            final_height_raw, speed_raw = struct.unpack("<Hh", await self.client.read_gatt_char(UUID_HEIGHT))
            height = self._raw_to_mm(final_height_raw)
            speed = self._raw_to_speed(speed_raw)
            if self.height_speed_callback is not None:
                self.height_speed_callback(height, speed)
            print("Final height: {:4.0f}mm (Target: {:4.0f}mm)".format(height, self._raw_to_mm(target)))

    async def scan(self, mac_address=None):
        """Scan for a bluetooth device with the configured address and return it or return all devices if no address specified"""
        print('Scanning')
        scanner = BleakScanner()
        devices = await scanner.discover(device=config['adapter_name'], timeout=config['scan_timeout'])
        if not mac_address:
            print(f"Found {len(devices)} devices using {config['adapter_name']}")
            for device in devices:
                print(device)
            return devices
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
            await self.stop()
            if self.client.is_connected:
                await self.client.disconnect()
            print('Disconnected')

    async def connect(self, attempt=0):
        """Attempt to connect to the desk"""
        # Attempt to load and connect to the pickled desk
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

    def _mm_to_raw(self, mm):
        return (mm - BASE_HEIGHT) * 10

    def _raw_to_mm(self, raw):
        return (raw / 10) + BASE_HEIGHT

    def _raw_to_speed(self, raw):
        return (raw / 100)

    def _height_data_callback(self, sender, data):
        height, speed = struct.unpack("<Hh", data)
        print("Height: {:4.0f}mm Speed: {:2.0f}mm/s".format(self._raw_to_mm(height), self._raw_to_speed(speed)))
        if self.height_speed_callback is not None:
            self.height_speed_callback(height, speed)

    def has_reached_target(self, height, target):
        # The notified height values seem a bit behind so try to stop before
        # reaching the target value to prevent overshooting
        return (abs(height - target) <= 10 * config['height_tolerance'])

    async def move_up(self):
        await self.client.write_gatt_char(UUID_COMMAND, COMMAND_UP)

    async def move_down(self):
        await self.client.write_gatt_char(UUID_COMMAND, COMMAND_DOWN)

    async def stop(self):
        # This emulates the behaviour of the app. Stop commands are sent to both
        # Reference Input and Command characteristics.
        await self.client.write_gatt_char(UUID_COMMAND, COMMAND_STOP)
        if IS_LINUX:
            # It doesn't like this on windows
            await self.client.write_gatt_char(UUID_REFERENCE_INPUT, COMMAND_REFERENCE_INPUT_STOP)

    async def subscribe(self, client, uuid, callback):
        """Listen for notifications on a characteristic"""
        await self.client.start_notify(uuid, callback)

    async def unsubscribe(self, client, uuid):
        try:
            await self.client.stop_notify(uuid)
        except KeyError:
            # This happens on windows, I don't know why
            pass

    async def move_to(self, client, target):
        """Move the desk to a specified height"""

        initial_height, speed = struct.unpack("<Hh", await self.client.read_gatt_char(UUID_HEIGHT))

        # Initialise by setting the movement direction
        direction = "UP" if target > initial_height else "DOWN"

        # Set up callback to run when the desk height changes. It will resend
        # movement commands until the desk has reached the target height.
        loop = asyncio.get_event_loop()
        move_done = loop.create_future()
        self.count = 0

        def _move_to_callback(sender, data):

            height, speed = struct.unpack("<Hh", data)
            height_final = self._raw_to_mm(height)
            speed_final = self._raw_to_speed(speed)
            self.count = self.count + 1
            self.height_speed_callback(height_final, speed_final)
            print("Height: {:4.0f}mm Target: {:4.0f}mm Speed: {:2.0f}mm/s".format(height_final, self._raw_to_mm(target), speed_final))

            # Stop if we have reached the target OR
            # If you touch desk control while the script is running then movement
            # callbacks stop. The final call will have speed 0 so detect that
            # and stop.
            if speed == 0 or self.has_reached_target(height, target):
                asyncio.create_task(self.stop())
                asyncio.create_task(self.unsubscribe(UUID_HEIGHT))
                try:
                    move_done.set_result(True)
                except asyncio.exceptions.InvalidStateError:
                    # This happens on windows, I dont know why
                    pass
            # Or resend the movement command if we have not yet reached the
            # target.
            # Each movement command seems to run the desk motors for about 1
            # second if uninterrupted and the height value is updated about 16
            # times.
            # Resending the command on the 6th update seems a good balance
            # between helping to avoid overshoots and preventing stutterinhg
            # (the motor seems to slow if no new move command has been sent)
            elif direction == "UP" and self.count == 6:
                asyncio.create_task(self.move_up())
                self.count = 0
            elif direction == "DOWN" and self.count == 6:
                asyncio.create_task(self.move_down())
                self.count = 0

        # Listen for changes to desk height and send first move command (if we are
        # not already at the target height).
        if not self.has_reached_target(initial_height, target):
            await self.subscribe(UUID_HEIGHT, _move_to_callback)
            if direction == "UP":
                asyncio.create_task(self.move_up())
            elif direction == "DOWN":
                asyncio.create_task(self.move_down())
            try:
                await asyncio.wait_for(move_done, timeout=config['movement_timeout'])
            except asyncio.TimeoutError as e:
                print('Timed out while waiting for desk')
                print(e)
                await self.unsubscribe(UUID_HEIGHT)

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
