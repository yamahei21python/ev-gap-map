"""Custom exceptions"""


class EVChargeError(Exception):
    """Base exception"""

    pass


class ScraperError(EVChargeError):
    """Scraping error"""

    pass


class GeocodingError(EVChargeError):
    """Geocoding error"""

    pass


class FetchError(EVChargeError):
    """Data fetch error"""

    pass


class ConfigurationError(EVChargeError):
    """Configuration error"""

    pass


class DatabaseError(EVChargeError):
    """Database error"""

    pass
