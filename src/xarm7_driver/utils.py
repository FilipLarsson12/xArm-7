"""
Pure helpers: rate loop, timing, clamp. No SDK or I/O.
"""
import time


def clamp(value: float, low: float, high: float) -> float:
    """Clamp value to [low, high]."""
    return max(low, min(high, value))


def clamp_twist(
    vx: float,
    vy: float,
    vz: float,
    wx: float,
    wy: float,
    wz: float,
    max_linear_mm_s: float,
    max_angular_rad_s: float,
) -> list[float]:
    """
    Clamp linear components to ±max_linear_mm_s and angular to ±max_angular_rad_s.
    Returns [vx, vy, vz, wx, wy, wz].
    """
    return [
        clamp(vx, -max_linear_mm_s, max_linear_mm_s),
        clamp(vy, -max_linear_mm_s, max_linear_mm_s),
        clamp(vz, -max_linear_mm_s, max_linear_mm_s),
        clamp(wx, -max_angular_rad_s, max_angular_rad_s),
        clamp(wy, -max_angular_rad_s, max_angular_rad_s),
        clamp(wz, -max_angular_rad_s, max_angular_rad_s),
    ]


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
