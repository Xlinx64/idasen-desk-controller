import time
import pexpect
import threading

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
        self._callbacks = set()
        self._current_task = None
        self.current_task_type = None

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

    def scan_devices(self):
        """Scan devices"""
        print("Start scanning")
        child = pexpect.spawn('python3 /config/custom_components/idasen-desk-controller/main.py --scan', encoding='utf-8')
        child.expect(".*Found*")
        output = child.read()
        child.close()
        return self._scan_output_to_dict(output)

    def check_Connection(self):
        """Get desk status"""
        print("Get status")
        child = pexpect.spawn(self._build_command_string({}), encoding='utf-8')
        index = child.expect(["Height: ", "was not found"])
        ret = False
        if index == 0:
            height = self._height_output_to_int(self._clean_output(child.read())[0])
            ret = type(height) == int
        child.close()
        return ret

    def start_monitoring(self):
        self._start_background_thread(self.monitoring_task)

    def monitoring_task(self):
        print("Start monitoring")
        self._kill_current_task(TASKTYPE_MONITORING)
        self._current_task = pexpect.spawn(self._build_command_string({'monitor': ""}), encoding='utf-8')
        self._current_task.expect("Connected", timeout=None)
        print("Monitoring started")
        while self.current_task_type == TASKTYPE_MONITORING:
            if self._current_task is None:
                continue
            self._current_task.expect(["\n", pexpect.EOF], timeout=None)
            output = ""
            if self._current_task is not None:
                output = self._current_task.before
            if string_contains(output, "height:"):
                self._height_output_to_int(output)
                self.publish_updates()

    def move_to_position(self, percentage):
        height = int(percentage*((MAX_HEIGHT-MIN_HEIGHT)/100) + MIN_HEIGHT)
        print(height)
        if height < 620:
            height = 620
        elif height > 1270:
            height = 1270
        self._start_background_thread(self._move_task, (height,))

    def _move_task(self, height):
        print(f"_move_task height: {height}")
        self._kill_current_task(TASKTYPE_MOVE)
        self._current_task = pexpect.spawn(self._build_command_string({'move-to': height}), encoding='utf-8')
        isMoving = True
        while isMoving:
            if self._current_task is None:
                isMoving = False
                continue
            self._current_task.expect(["\n", pexpect.EOF], timeout=None)
            output = ""
            if self._current_task is None:
                isMoving = False
                continue
            else:
                output = self._current_task.before
            if string_contains(output, "height:"):
                self._height_output_to_int(output)
                self.publish_updates()
            elif string_contains(output, "Disconnected"):
                print("Movement finsished")
                isMoving = False
                if self.current_task_type == TASKTYPE_MOVE:
                    self.start_monitoring()

    def stop_movement(self):
        print("STOP MOVEMENT")
        if self.current_task_type == TASKTYPE_MOVE:
            self.start_monitoring()

    def _build_command_string(self, dict):
        cmdString = "python3 /config/custom_components/idasen-desk-controller/main.py "
        cmdString += f"--mac-address {self.address} "
        cmdString += "--scan-timeout 2 "
        for key in dict:
            entry = dict[key]
            cmdString += f"--{key} {entry} "
        print(cmdString)
        return cmdString

    #Task management
    def _kill_current_task(self, newTaskType):
        print("Kill current task")
        if self._current_task is not None:
            print("Task found")
            self._current_task.terminate()
            self._current_task = None
            time.sleep(1)
        self.current_task_type = newTaskType

    def kill_tasks(self):
        self._kill_current_task(None)

    def _start_background_thread(self, task, args=[]):
        self.currentThread = threading.Thread(target=task, args=args)
        self.currentThread.start()

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

    #FORMAT OUTPUT
    def _clean_output(self, input):
        """Split the output and strip unwanted characters"""
        formatting = [
            "\xc2\xa0"
        ]
        output = []

        for substring in input.splitlines():
            for format in formatting:
                substring = substring.replace(format, "")
            substring = substring.strip()
            output.append(substring)
        return output

    def _scan_output_to_dict(self, input):
        """Format scan output"""
        dict = {}
        output_strings = self._clean_output(input)
        for output_string in output_strings[1:]:
            splited_string = output_string.split(": ", 1)
            name = splited_string[1]
            mac_address = splited_string[0]
            if string_contains(name, "desk"):
                dict[name] = mac_address
        return dict

    def _height_output_to_int(self, input):
        """Format height output"""
        if string_contains(input, "mm"):
            self.height = int(''.join(filter(str.isdigit, input.split("mm", 1)[0])))
            print(f'Height: {self.height}mm')
            return self.height
        return None


def string_contains(str1, str2):
    if str1 is None:
        return False
    return str1.lower().find(str2.lower()) != -1
