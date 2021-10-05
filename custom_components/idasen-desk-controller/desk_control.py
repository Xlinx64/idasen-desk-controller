"""
Wrapper for idasen-controller
"""

import time
import pexpect


class DeskController:
    """A wrapper for idasen-controller """

    def __init__(self):
        """Initalize DeskController"""
        print("Init DeskController")
        self.name = None
        self.address = None

    def scan_devices(self):
        """Scan devices"""
        print("Start scanning")
        child = pexpect.spawn('idasen-controller --scan', encoding='utf-8')
        child.expect(".*Found*")
        output = child.read()
        child.close()
        return self._scan_output_to_dict(output)

    def get_status(self):
        """Get desk status"""
        print("Get status")
        mac_address = self.address
        child = pexpect.spawn(f'idasen-controller --mac-address {mac_address}', encoding='utf-8')
        index = child.expect(["was not found"])
        print(child.before)
        if index == 0:
            child.close()
            return None
        else:
            output = child.read()
            child.close()
            return output
        #child.expect(".*Found*")
        #output = child.read()
        #return ""#self._scan_output_to_dict(output)

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
        dict = {}
        output_strings = self._clean_output(input)
        for output_string in output_strings[1:]:
            splited_string = output_string.split(": ", 1)
            name = splited_string[1]
            mac_address = splited_string[0]
            if name.lower().find("desk") != -1:
                dict[name] = mac_address
        return dict
