from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from xarm.wrapper import XArmAPI

from xarm7_driver.errors import XArmConnectionError


@dataclass
class XArmConnectionConfig:
    """Connection settings for the xArm. Used when creating the driver."""

    ip: str
    is_radian: bool = True
    do_not_open: bool = False
    timeout: float | None = None  # command response timeout (seconds), optional


class XArmDriver:
    """
    Thin wrapper around XArmAPI.

    Phase 0: connect + basic reads only.
    Later phases add: prepare(), limits, telemetry, mode switching, send_twist(), stop().
    """

    def __init__(self, config: XArmConnectionConfig) -> None:
        self.config = config
        self._arm: XArmAPI | None = None

    @property
    def arm(self) -> XArmAPI:
        """The underlying SDK object. Raises if not connected."""
        if self._arm is None:
            raise RuntimeError("Not connected: call connect() first")
        return self._arm

    def connect(self) -> None:
        """Open connection to the robot."""
        self._arm = XArmAPI(
            self.config.ip,
            is_radian=self.config.is_radian,
            do_not_open=self.config.do_not_open,
        )
        if self.config.do_not_open:
            self._arm.connect(self.config.ip)
        if self.config.timeout is not None:
            self._arm.set_timeout(self.config.timeout)

    def disconnect(self) -> None:
        """Close connection. Safe to call even if not connected."""
        if self._arm is not None:
            try:
                self._arm.disconnect()
            finally:
                self._arm = None

    def prepare(self) -> None:
        """
        Clear errors/warnings if any, enable motion, set state to ready (0).
        Call after connect() when you want the arm ready to accept commands.
        Raises XArmConnectionError if any step fails.
        """
        arm = self.arm
        code, (err, warn) = arm.get_err_warn_code()
        if code != 0:
            raise XArmConnectionError(f"get_err_warn_code failed: code={code}")
        if err != 0 or warn != 0:
            arm.clean_warn()
            arm.clean_error()
        code = arm.motion_enable(True)
        if code != 0:
            raise XArmConnectionError(f"motion_enable(True) failed: code={code}")
        code = arm.set_state(0)
        if code != 0:
            raise XArmConnectionError(f"set_state(0) failed: code={code}")

    def read_basic_status(self) -> dict[str, Any]:
        """
        Read version, state, error/warn codes, and current pose.
        Returns a dict with 'code' and 'value' for each (for Phase 0 smoke test).
        """
        out: dict[str, Any] = {}
        code, version = self.arm.get_version()
        out["version"] = {"code": code, "value": version}
        code, state = self.arm.get_state()
        out["state"] = {"code": code, "value": state}
        code, ew = self.arm.get_err_warn_code()
        out["err_warn"] = {"code": code, "value": ew}
        code, pos = self.arm.get_position(is_radian=self.config.is_radian)
        out["position"] = {"code": code, "value": pos}
        return out
