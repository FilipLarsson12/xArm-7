"""Exceptions for the driver. Scripts can catch these to report failures clearly."""


class XArmDriverError(Exception):
    """Base exception for driver errors."""


class XArmConnectionError(XArmDriverError):
    """Raised when connection or prepare step fails."""


class XArmCommandError(XArmDriverError):
    """Raised when a controller command fails (e.g. set_mode, set_state, velocity command)."""


class XArmLimitError(XArmDriverError):
    """Raised when applying or querying limits fails."""
