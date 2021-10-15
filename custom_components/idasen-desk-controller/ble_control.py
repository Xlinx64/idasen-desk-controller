"""
BLEController handles BLE communication
"""

import sys
import os
import struct
import asyncio
import pickle
from bleak import BleakClient, BleakError, BleakScanner
from bleak.backends.service import BleakGATTServiceCollection
from .const import HEIGHT_TOLERANCE, MIN_HEIGHT, ADAPTER_NAME, SCAN_TIMEOUT, CONNECTION_TIMEOUT, LOGGER

IS_LINUX = sys.platform == "linux" or sys.platform == "linux2"
IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

# GATT CHARACTERISTIC AND COMMAND DEFINITIONS
UUID_HEIGHT = '99fa0021-338a-1024-8a49-009c0215f78a'
UUID_COMMAND = '99fa0002-338a-1024-8a49-009c0215f78a'
UUID_REFERENCE_INPUT = '99fa0031-338a-1024-8a49-009c0215f78a'


# COMMAND_UP = bytearray(struct.pack("<H", 71))
# COMMAND_DOWN = bytearray(struct.pack("<H", 70))
# COMMAND_STOP = bytearray(struct.pack("<H", 255))
#
# COMMAND_REFERENCE_INPUT_STOP = bytearray(struct.pack("<H", 32769))
# COMMAND_REFERENCE_INPUT_UP = bytearray(struct.pack("<H", 32768))
# COMMAND_REFERENCE_INPUT_DOWN = bytearray(struct.pack("<H", 32767))

COMMAND_REFERENCE_INPUT_STOP = bytearray([0x01, 0x80])
COMMAND_UP = bytearray([0x47, 0x00])
COMMAND_DOWN = bytearray([0x46, 0x00])
COMMAND_STOP = bytearray([0xFF, 0x00])

PICKLE_FILE = os.path.join(os.getcwd(), 'desk.pickle')


class BLEController:
    def __init__(self, mac_address=None,
                 height_speed_callback=None,
                 connection_change_callback=None):
        """Set up the async event loop and signal handlers"""
        print("Init BLEController")
        self.client = None
        self.mac_address = mac_address
        self.height_speed_callback = height_speed_callback
        self.connection_change_callback = connection_change_callback
        self._reconnect = True

        self._is_moving = False
        self._target_height = None
        self._movement_count = 0
        self._direction = None
        self._move_done = None

    @property
    def is_connected(self):
        """Return if the client is connected"""
        return self.client is not None and self.client.is_connected

    async def start_monitoring(self):
        print("START MONITORING")
        self.client = await self.connect(self.mac_address, self.client)
        if self.client is None:
            print(f'Cannot start monitoring for address: {self.mac_address}')
            return
        await self._read_state(self.client)

    async def get_current_state(self):
        print("GET CURRENT STATE")
        self.client = await self.connect(self.mac_address, self.client)
        if self.client is None:
            print(f'Cannot start monitoring for address: {self.mac_address}')
            return None, None
        return await self._read_state(self.client)

    async def _read_state(self, client):
        if client is None:
            print(f'Could not get client: {self.mac_address}')
            LOGGER.error(f'Could not connect to client: {self.mac_address}')
            return None, None
        height_raw, speed_raw = await self._read_gatt_char()
        height, speed = self._format_height_speed(height_raw, speed_raw)
        print("Height: {:4.0f}mm Speed: {:2.0f}mm/s".format(height, speed))
        if self.height_speed_callback is not None:
            self.height_speed_callback(height, speed)
        return height, speed

    async def scan(self, mac_address=None):
        """Scan for a bluetooth device with the configured address
        return it or return all devices if no address specified"""
        print('Scanning')
        scanner = BleakScanner()
        devices = await scanner.discover(device=ADAPTER_NAME, timeout=SCAN_TIMEOUT)
        if not mac_address:
            print(f"Found {len(devices)} devices using {ADAPTER_NAME}")
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
        print("Disconnect called")
        self._reconnect = False
        if self.client:
            print('Disconnecting')
            await self.stop_movement()
            if self.client.is_connected:
                await self.client.disconnect()
                self.client.services = BleakGATTServiceCollection()
            print('Disconnected')

    async def pair_device(self):  # TODO
        if IS_LINUX:
            print("Try pairing")

    async def connect(self, mac_address, current_client):
        """Attempt to connect to the desk"""
        # Attempt to load and connect to the pickled desk
        if current_client is not None and current_client.is_connected:
            self._reconnect = True
            return current_client

        pickled_Desk = self._unpickle_desk(mac_address)

        if current_client is not None:
            print("Client available! Try connecting")
            if (await self._connect_client(current_client)):
                return current_client
            else:
                print("Stored client invalid! Remove self.client")
                self.client = None

        if pickled_Desk is not None:
            print("Pickled desk available! Try connecting")
            client = BleakClient(pickled_Desk, device=ADAPTER_NAME)
            if (await self._connect_client(client)):
                return client

        found_desk = await self.scan(mac_address)
        if found_desk is None:
            print(f'Could not find desk {self.mac_address}')
            LOGGER.error(f'Could not find desk {self.mac_address}')
            return None

        self._remove_pickled_desk()
        client = BleakClient(found_desk, device=ADAPTER_NAME)
        if (await self._connect_client(client)):
            self._pickle_desk(found_desk)
            return client
        return None

    async def _connect_client(self, client):
        if client is None:
            print("Cannot connect, client is None")
            return False

        for attempt in range(3):
            try:
                print(f'Connecting - attempt {attempt}')
                if client.is_connected:
                    await self._setup_connection(client)
                    return True
                client.services = BleakGATTServiceCollection()
                await client.connect(timeout=CONNECTION_TIMEOUT)
                if client.is_connected:
                    await self._setup_connection(client)
                    return True
            except BleakError as e:
                print(f'Bluetooth Error {e}')
                LOGGER.error(f'Bluetooth Error {e}')
            await asyncio.sleep(3)
        return False

    async def _setup_connection(self, client):
        self._connection_change(client)
        client.set_disconnected_callback(self._connection_change)
        await self._subscribe(client, UUID_HEIGHT, self._height_data_callback)
        print(f"Connected {self.mac_address}")
        self._reconnect = True

    def _connection_change(self, client):
        if not client.is_connected:
            client.services = BleakGATTServiceCollection()
            self.connection_change_callback()
            if self._reconnect:
                LOGGER.error('Client did disconnect. Try reconnecting!')
                asyncio.create_task(self.connect(self.mac_address, self.client))
        self.connection_change_callback()

    async def move_to_position(self, position):
        self.client = await self.connect(self.mac_address, self.client)
        if self.client is None:
            print(f'Could not get Client {self.mac_address}')
            LOGGER.error(f'Could not connect to {self.mac_address}')
            return
        self._target_height = self._mm_to_raw(position)
        await self._move_to()
        if self._target_height:
            # If we were moving to a target height, wait, then print the actual final height
            await asyncio.sleep(1)
            height_raw, speed_raw = await self._read_gatt_char()
            height, speed = self._format_height_speed(height_raw, speed_raw)
            if self.height_speed_callback is not None:
                self.height_speed_callback(height, speed)

    async def _move_to(self):
        """Move the desk to a specified height"""
        initial_height, speed = await self._read_gatt_char()
        self._direction = "UP" if self._target_height > initial_height else "DOWN"
        self._movement_count = 0

        # loop = asyncio.get_event_loop()
        # self._move_done = loop.create_future()

        if not self._has_reached_target(initial_height):
            self._is_moving = True
            if self._direction == "UP":
                asyncio.create_task(self._move_up())
            elif self._direction == "DOWN":
                asyncio.create_task(self._move_down())
            # try:
            #     await asyncio.wait_for(self._move_done, timeout=MOVEMENT_TIMEOUT)
            # except asyncio.TimeoutError as e:
            #     print('Timed out while waiting for desk')
            #     print(e)
                #await self._unsubscribe(UUID_HEIGHT)

    def _height_data_callback(self, sender, data):
        height_raw, speed_raw = struct.unpack("<Hh", data)
        height, speed = self._format_height_speed(height_raw, speed_raw)

        if self._is_moving:
            self._movement_count = self._movement_count + 1
            if self.height_speed_callback is not None:
                self.height_speed_callback(height, speed)
            print("Height: {:4.0f}mm Target: {:4.0f}mm Speed: {:2.0f}mm/s".format(height, self._raw_to_mm(self._target_height), speed))

            # Stop if we have reached the target OR
            # If you touch desk control while the script is running then movement
            # callbacks stop. The final call will have speed 0 so detect that
            # and stop.
            if speed == 0 or self._has_reached_target(height_raw):
                asyncio.create_task(self.stop_movement())
                self._is_moving = False
                self._direction = None
                # try:
                #     self._move_done.set_result(True)
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
            elif self._direction == "UP" and self._movement_count == 6:
                asyncio.create_task(self._move_up())
                self._movement_count = 0
            elif self._direction == "DOWN" and self._movement_count == 6:
                asyncio.create_task(self._move_down())
                self._movement_count = 0

        if self.height_speed_callback is not None:
            self.height_speed_callback(height, speed)

    async def stop_movement(self):
        self._is_moving = False
        self._direction = None
        await self.client.write_gatt_char(UUID_COMMAND, COMMAND_STOP)
        if not IS_WINDOWS:
            # Doesnt work on windows
            await self.client.write_gatt_char(UUID_REFERENCE_INPUT, COMMAND_REFERENCE_INPUT_STOP)

    async def _read_gatt_char(self):
        return struct.unpack("<Hh", await self.client.read_gatt_char(UUID_HEIGHT))

    def _has_reached_target(self, height):
        # The notified height values seem a bit behind so try to stop before
        # reaching the target value to prevent overshooting
        return (abs(height - self._target_height) <= 10 * HEIGHT_TOLERANCE)

    async def _move_up(self):
        await self.client.write_gatt_char(UUID_COMMAND, COMMAND_UP)

    async def _move_down(self):
        await self.client.write_gatt_char(UUID_COMMAND, COMMAND_DOWN)

    async def _subscribe(self, client, uuid, callback):
        """Listen for notifications on a characteristic"""
        try:
            await client.start_notify(uuid, callback)
        except ValueError:
            pass

    async def _unsubscribe(self, uuid):
        try:
            await self.client.stop_notify(uuid)
        except KeyError:
            # This happens on windows
            pass

    def _unpickle_desk(self, mac_address):
        """Load a Bleak device config from a pickle file and check that it is the correct device"""
        if IS_LINUX:
            try:
                with open(PICKLE_FILE, 'rb') as f:
                    desk = pickle.load(f)
                    if desk is not None and desk.address == mac_address:
                        return desk
            except Exception:
                pass
        return None

    def _pickle_desk(self, desk):
        """Attempt to pickle the desk"""
        if IS_LINUX and desk is not None:
            with open(PICKLE_FILE, 'wb') as f:
                pickle.dump(desk, f)

    def _remove_pickled_desk(self):
        """Attempt to pickle the desk"""
        if IS_LINUX:
            try:
                os.remove(PICKLE_FILE)
                print('desk pickle removed')
            except OSError:
                pass

    def _mm_to_raw(self, mm):
        return (mm - MIN_HEIGHT) * 10

    def _raw_to_mm(self, raw):
        return (raw / 10) + MIN_HEIGHT

    def _raw_to_speed(self, raw):
        return (raw / 100)

    def _format_height_speed(self, height, speed):
        return int(self._raw_to_mm(height)), int(self._raw_to_speed(speed))
