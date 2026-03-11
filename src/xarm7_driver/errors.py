"""Exceptions for the driver. Scripts can catch these to report failures clearly."""


class XArmDriverError(Exception):
    """Base exception for driver errors."""


class XArmConnectionError(XArmDriverError):
    """Raised when connection or prepare step fails."""
