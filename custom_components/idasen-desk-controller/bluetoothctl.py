# Based on ReachView code from Egor Fedorov (egor.fedorov@emlid.com) and @castis (https://gist.github.com/castis/0b7a162995d0b465ba9c84728e60ec01)


import time
import pexpect
import logging

logger = logging.getLogger("btctl")


class Bluetoothctl:
    """A wrapper for bluetoothctl utility."""

    def __init__(self):
        self.process = pexpect.spawnu("bluetoothctl", echo=False)

    def send(self, command, pause=0):
        self.process.send(f"{command}\n")
        time.sleep(pause)
        if self.process.expect(["#", "not available", pexpect.EOF, pexpect.TIMEOUT]):
            raise Exception(f"failed after {command}")

    def get_output(self, *args, **kwargs):
        """Run a command in bluetoothctl prompt, return output as a list of lines."""
        self.send(*args, **kwargs)
        return self.process.before.split("\r\n")

    def start_scan(self, pause):
        """Start bluetooth scanning process."""
        try:
            self.send("scan off")
            time.sleep(2)
            self.send("scan on")
            time.sleep(pause)
        except Exception as e:
            logger.error(e)

    def parse_device_info(self, info_string):
        """Parse a string corresponding to a device."""
        device = {}
        block_list = ["[\x1b[0;", "removed"]
        if not any(keyword in info_string for keyword in block_list):
            try:
                device_position = info_string.index("Device")
            except ValueError:
                pass
            else:
                if device_position > -1:
                    attribute_list = info_string[device_position:].split(" ", 2)
                    device = {
                        "mac_address": attribute_list[1],
                        "name": attribute_list[2],
                    }
        return device

    def get_paired_devices(self):
        """Return a list of tuples of paired devices."""
        paired_devices = []
        try:
            out = self.get_output("paired-devices")
        except Exception as e:
            logger.error(e)
        else:
            for line in out:
                device = self.parse_device_info(line)
                if device:
                    paired_devices.append(device)
        return paired_devices

    def pairing_process(self, mac_address, attempt=0):
        """Try to pair with a device by mac address."""
        try:
            self.send(f"pair {mac_address}", 4)
        except Exception as e:
            logger.error(e)
            return False
        else:
            result_list = ["Failed to pair", "Pairing successful", "not available", pexpect.EOF]
            result = self.process.expect(result_list)
            print(f"Pairing result: {result_list[result]}")
            return result == 1

    def pair(self, mac_address):
        print("Checking paired devices")
        for device in self.get_paired_devices():
            if device["mac_address"] == mac_address:
                print("Device already paired")
                return True

        print("Device is not paired yet! Start pairing")
        self.start_scan(5)
        for attempt in range(3):
            print(f"attempt {attempt}")
            if self.pairing_process(mac_address, attempt):
                return True
        return False


# ctl = Bluetoothctl()
# success = ctl.pair("F4:E5:29:13:6A:3C")
# print(f"SUCCESS: {success}")
