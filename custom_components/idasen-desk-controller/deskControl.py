"""
Wrapper for bluetoothctl
"""

import time
import pexpect
import sys

class DeskController:
    """A wrapper for idasen-controller """

    def __init__(self):
        """Initalize shell."""
        print("Init DeskController")


    def scanDevices(self):
        print("Start scanning")
        child = pexpect.spawn('idasen-controller --scan', encoding='utf-8')
        child.expect(".*Found*")
        output = child.read()
        return self.scanOutputToDict(output)

    def clean_output(self, input):
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


    def scanOutputToDict(self, input):
        dict = {}
        outputStrings = self.clean_output(input)
        for outputString in outputStrings[1:]:
            splitedString = outputString.split(": ",1)
            dict[splitedString[1]] = splitedString[0]
        return dict
