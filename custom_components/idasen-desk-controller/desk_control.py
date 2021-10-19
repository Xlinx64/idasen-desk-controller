"""
DeskController handles Home Assistant communication
"""

from .ble_control import BLEController
from .const import HEIGHT_TOLERANCE, MIN_HEIGHT, MAX_HEIGHT, LOGGER

TASKTYPE_MONITORING = "MONITORING"
TASKTYPE_MOVE = "MOVE"

DESK_NAME = "desk"


class DeskController:

    def __init__(self, name=None, address=None):
        """Initalize DeskController"""
        LOGGER.debug("Init DeskController")
        self.name = name
        self.address = address
        self.height = 0
        self.speed = 0
        self._callbacks = set()
        self._ble_controller = BLEController(address=address,
                                             height_speed_callback=self.height_speed_callback,
                                             connection_change_callback=self.publish_updates)

    @property
    def height_percentage(self):
        """Return the height of the desk in percentage, it is used for the cover"""
        return int(self.height-MIN_HEIGHT)/((MAX_HEIGHT-MIN_HEIGHT)/100)

    @property
    def is_on_highest(self):
        """Return if the desk is on its highest position"""
        return MAX_HEIGHT-self.height-HEIGHT_TOLERANCE < 0

    @property
    def is_on_lowest(self):
        """Return if the desk is on its lowest position"""
        return MIN_HEIGHT-self.height-HEIGHT_TOLERANCE < 0

    @property
    def is_connected(self):
        """Return if the desk is connected"""
        return self._ble_controller.is_connected

    def set_device(self, name, address):
        self.name = name
        self.address = address
        self._ble_controller.address = address

    def height_speed_callback(self, height, speed):
        """Callback for the BLEController"""
        print(f"Height: {height}mm Speed: {speed}mm/s")
        self.speed = speed
        self.height = height
        self.publish_updates()

    async def scan_devices(self):
        """Scan devices"""
        print("Start scanning")
        filtered_devices = {}
        devices = await self._ble_controller.scan()
        for name in devices:
            if string_contains(name, DESK_NAME):
                filtered_devices[name] = devices[name]
        return filtered_devices

    async def initial_device_setup(self):
        """Pair device"""

    async def get_device_state(self):
        """Get desk state"""
        print("Get status")
        height, speed = await self._ble_controller.get_current_state()
        self.height = height
        self.speed = speed
        return height, speed

    async def start_monitoring(self):
        """Start monitoring the state characteristic and get initial values"""
        await self._ble_controller.start_monitoring()

    async def move_to_position(self, percentage):
        """Move to percentage"""
        height = int(percentage*((MAX_HEIGHT-MIN_HEIGHT)/100) + MIN_HEIGHT)
        if height < MIN_HEIGHT:
            height = MIN_HEIGHT
        elif height > MAX_HEIGHT:
            height = MAX_HEIGHT
        await self._ble_controller.move_to_position(height)

    async def stop_movement(self):
        """Stop movement"""
        await self._ble_controller.stop_movement()

    async def disconnect(self):
        """Disconnect the ble client"""
        await self._ble_controller.disconnect()

    #HOME ASSISTNAT Callbacks
    def register_callback(self, callback) -> None:
        """Register callback, called when the desk changes state."""
        self._callbacks.add(callback)

    def remove_callback(self, callback) -> None:
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    def publish_updates(self) -> None:
        """Call all registered callbacks."""
        for callback in self._callbacks:
            callback()


def string_contains(str1, str2):
    if str1 is None or str2 is None:
        return False
    return str1.lower().find(str2.lower()) != -1
