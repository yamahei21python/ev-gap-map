"""Constants - Status values and enumerations"""

from enum import IntEnum


class GeocodingStatus(IntEnum):
    """Geocoding status enumeration"""

    UNPROCESSED = 0
    SUCCESS = 1
    FAILED = 2


class ChargerType:
    """Charger type mappings"""

    CHADEMO = "CHAdeMO"
    TYPE_200V = "200V"
    TYPE_100V = "100V"
    NACS = "NACS"

    MAP = {
        "1": CHADEMO,
        "2": TYPE_200V,
        "3": TYPE_100V,
        "4": NACS,
    }
