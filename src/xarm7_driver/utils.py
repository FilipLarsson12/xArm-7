"""
Pure helpers: rate loop, timing. No SDK or I/O.
"""
import time


class RateLoop:
    """
    Sleep so that consecutive sleep() calls run at roughly the given rate (Hz).
    Use in a loop: do work, then rate.sleep().
    """
    __slots__ = ("_interval", "_next_ts")

    def __init__(self, rate_hz: float) -> None:
        if rate_hz <= 0:
            raise ValueError("rate_hz must be positive")
        self._interval = 1.0 / rate_hz
        self._next_ts = 0.0

    def sleep(self) -> None:
        now = time.monotonic()
        if self._next_ts > 0:
            delay = self._next_ts - now
            if delay > 0:
                time.sleep(delay)
        self._next_ts = (self._next_ts or now) + self._interval
        if self._next_ts <= now:
            self._next_ts = now + self._interval
