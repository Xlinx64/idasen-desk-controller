from .ble_control import BLEController

MIN_HEIGHT = 620
MAX_HEIGHT = 1270
TOLERANCE = 10

TASKTYPE_MONITORING = "MONITORING"
TASKTYPE_MOVE = "MOVE"


class DeskController:
    """A wrapper for idasen-controller """

    def __init__(self, name=None, address=None):
        """Initalize DeskController"""
        print("Init DeskController")
        self.name = name
        self.address = address
        self.height = 0
        self.speed = 0
        self._callbacks = set()
        self._ble_controller = BLEController(mac_address=address,
                                             height_speed_callback=self.height_speed_callback,
                                             connection_change_callback=self.publish_updates)

    @property
    def height_percentage(self):
        """Return if the cover is closed, same as position 0."""
        return int(self.height-MIN_HEIGHT)/((MAX_HEIGHT-MIN_HEIGHT)/100)

    @property
    def is_on_highest(self):
        """Return if the desk is on its highest position"""
        return MAX_HEIGHT-self.height-TOLERANCE < 0

    @property
    def is_on_lowest(self):
        """Return if the desk is on its lowest position"""
        return MIN_HEIGHT-self.height-TOLERANCE < 0

    @property
    def is_connected(self):
        """Return if the desk is connected"""
        return self._ble_controller.client.is_connected

    def set_device(self, name, mac_address):
        self.name = name
        self.address = mac_address
        self._ble_controller.mac_address = mac_address

    def height_speed_callback(self, height, speed):
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
            if string_contains(name, "desk"):
                filtered_devices[name] = devices[name]
        #print(filtered_devices)
        return filtered_devices

    async def get_device_state(self):
        """Get desk status"""
        print("Get status")
        height, speed = await self._ble_controller.get_current_state()
        self.height = height
        self.speed = speed
        return height, speed

    async def start_monitoring(self):
        await self._ble_controller.start_monitoring()

    async def move_to_position(self, percentage):
        height = int(percentage*((MAX_HEIGHT-MIN_HEIGHT)/100) + MIN_HEIGHT)
        print(height)
        if height < 620:
            height = 620
        elif height > 1270:
            height = 1270
        await self._ble_controller.move_to_position(height)

    async def stop_movement(self):
        print("STOP MOVEMENT")
        await self._ble_controller.stop_movement()

    async def disconnect(self):
        await self._ble_controller.disconnect()

    #HOME ASSISTNAT Callbacks
    def register_callback(self, callback) -> None:
        """Register callback, called when Roller changes state."""
        self._callbacks.add(callback)

    def remove_callback(self, callback) -> None:
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    def publish_updates(self) -> None:
        """Schedule call all registered callbacks."""
        for callback in self._callbacks:
            callback()


def string_contains(str1, str2):
    if str1 is None:
        return False
    return str1.lower().find(str2.lower()) != -1
