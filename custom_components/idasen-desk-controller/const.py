"""
Constants for Idasen Desk Controller Integration
"""

import logging

LOGGER = logging.getLogger(__package__)
DOMAIN = 'idasen-desk-controller'
PLATFORMS = ["cover", "sensor", "switch"]

MIN_HEIGHT = 620
MAX_HEIGHT = 1270  # 6500
HEIGHT_TOLERANCE = 2.0
ADAPTER_NAME = 'hci0'
SCAN_TIMEOUT = 5
CONNECTION_TIMEOUT = 20
MOVEMENT_TIMEOUT = 30
