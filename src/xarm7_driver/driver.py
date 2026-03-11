from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal

from xarm.wrapper import XArmAPI

from xarm7_driver.errors import XArmConnectionError, XArmCommandError, XArmLimitError
from xarm7_driver.telemetry import LatestPoseStore, PoseStream
from xarm7_driver.utils import clamp_twist


@dataclass
class XArmConnectionConfig:
    """Connection settings for the xArm. Used when creating the driver."""

    ip: str
    is_radian: bool = True
    do_not_open: bool = False
    timeout: float | None = None  # command response timeout (seconds), optional
    enable_report: bool = False  # True required for telemetry mode "callback"


@dataclass
class LimitsConfig:
    """
    Limit-related config: reduced-mode boundary/speeds (apply_limits) and velocity
    clamp/watchdog (send_twist). Pass to apply_limits() and/or driver at init.
    Boundary order: [x_max, x_min, y_max, y_min, z_max, z_min] in mm.
    """

    tcp_boundary: list[float]  # 6 values: x_max, x_min, y_max, y_min, z_max, z_min (mm)
    max_tcp_speed_mm_s: float = 100.0  # reduced mode + send_twist linear clamp
    max_joint_speed_rad_s: float | None = None  # optional; reduced mode only
    max_angular_speed_rad_s: float = 1.0  # send_twist angular clamp (rad/s)
    velocity_duration_s: float = 0.15  # send_twist watchdog when duration=None


class XArmDriver:
    """
    Thin wrapper around XArmAPI.

    Phase 0: connect + basic reads only.
    Later phases add: prepare(), limits, telemetry, mode switching, send_twist(), stop().
    """

    def __init__(
        self,
        config: XArmConnectionConfig,
        limits: LimitsConfig | None = None,
    ) -> None:
        self.config = config
        self._limits = limits
        self._arm: XArmAPI | None = None
        self._pose_store = LatestPoseStore()
        self._telemetry_mode: Literal["off", "poll", "callback"] = "off"
        self._poll_hz: float = 50.0
        self._pose_stream: PoseStream | None = None
        self._report_callback_ref: Any = None  # for release_report_location_callback

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
            enable_report=self.config.enable_report,
        )
        if self.config.do_not_open:
            self._arm.connect(self.config.ip)
        if self.config.timeout is not None:
            self._arm.set_timeout(self.config.timeout)

    def disconnect(self) -> None:
        """Close connection. Stops telemetry first, then disconnects."""
        self.stop_telemetry()
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

    def apply_limits(self, limits: LimitsConfig) -> None:
        """
        Set reduced-mode boundary and speeds, then enable reduced mode.
        Call after connect() (and optionally after prepare()).
        Raises XArmLimitError if any SDK call fails.
        """
        if len(limits.tcp_boundary) != 6:
            raise XArmLimitError("tcp_boundary must have 6 values: x_max, x_min, y_max, y_min, z_max, z_min")
        arm = self.arm
        code = arm.set_reduced_tcp_boundary(limits.tcp_boundary)
        if code != 0:
            raise XArmLimitError(f"set_reduced_tcp_boundary failed: code={code}")
        code = arm.set_reduced_max_tcp_speed(limits.max_tcp_speed_mm_s)
        if code != 0:
            raise XArmLimitError(f"set_reduced_max_tcp_speed failed: code={code}")
        if limits.max_joint_speed_rad_s is not None:
            code = arm.set_reduced_max_joint_speed(
                limits.max_joint_speed_rad_s, is_radian=self.config.is_radian
            )
            if code != 0:
                raise XArmLimitError(f"set_reduced_max_joint_speed failed: code={code}")
        code = arm.set_reduced_mode(True)
        if code != 0:
            raise XArmLimitError(f"set_reduced_mode(True) failed: code={code}")

    def get_reduced_states(self) -> tuple[int, Any]:
        """
        Query current reduced-mode state (boundary, speeds, joint ranges, etc.).
        Returns (code, states) from the SDK; 0 means success.
        """
        return self.arm.get_reduced_states(is_radian=self.config.is_radian)

    def enter_cartesian_velocity_mode(self) -> None:
        """
        Set controller to Cartesian velocity mode (5) and state to ready (0).
        Call after connect() and prepare() when you want to send twist commands.
        Raises XArmCommandError if mode or state change fails.
        """
        arm = self.arm
        code = arm.set_mode(5)
        if code != 0:
            raise XArmCommandError(f"set_mode(5) failed: code={code}")
        code = arm.set_state(0)
        if code != 0:
            raise XArmCommandError(f"set_state(0) failed: code={code}")

    def send_twist(
        self,
        vx: float,
        vy: float,
        vz: float,
        wx: float,
        wy: float,
        wz: float,
        duration: float | None = None,
    ) -> int:
        """
        Send Cartesian velocity (mm/s for vx,vy,vz; rad/s for wx,wy,wz in base frame).
        Speeds are clamped using limits (max_tcp_speed_mm_s, max_angular_speed_rad_s) if set.
        duration: max seconds this speed is applied; None = use limits.velocity_duration_s (watchdog);
        0 = until next command. Returns SDK code.
        """
        if self._limits is not None:
            lim = self._limits
            speeds = clamp_twist(
                vx, vy, vz, wx, wy, wz,
                lim.max_tcp_speed_mm_s,
                lim.max_angular_speed_rad_s,
            )
            d = duration if duration is not None else lim.velocity_duration_s
        else:
            speeds = [vx, vy, vz, wx, wy, wz]
            d = duration if duration is not None else 0.15
        return self.arm.vc_set_cartesian_velocity(
            speeds,
            is_radian=self.config.is_radian,
            is_tool_coord=False,
            duration=d,
        )

    def stop(self) -> int:
        """Send zero velocity immediately. Returns SDK code."""
        return self.arm.vc_set_cartesian_velocity(
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            is_radian=self.config.is_radian,
            is_tool_coord=False,
            duration=0,
        )

    def check_fault(self) -> tuple[bool, int, int]:
        """
        Read error/warn codes. If error != 0, calls stop() and returns (False, err, warn).
        Otherwise returns (True, err, warn). Call in your control loop to react to controller faults.
        """
        code, (err, warn) = self.arm.get_err_warn_code()
        if code != 0:
            return (False, err, warn)
        if err != 0:
            self.stop()
            return (False, err, warn)
        return (True, err, warn)

    def shutdown(self) -> None:
        """Stop telemetry, send zero velocity, disconnect. Safe to call anytime."""
        self.stop_telemetry()
        self.stop()
        self.disconnect()

    def set_telemetry(
        self,
        mode: Literal["off", "poll", "callback"],
        poll_hz: float = 50.0,
    ) -> None:
        """
        Set telemetry mode. Does not start streaming; call start_telemetry() after connect().
        Use "callback" only if XArmConnectionConfig had enable_report=True.
        """
        self.stop_telemetry()
        self._telemetry_mode = mode
        self._poll_hz = poll_hz

    def start_telemetry(self) -> None:
        """
        Start pose streaming (poll thread or SDK callback). No-op if mode is "off".
        Call after connect(). For callback mode, enable_report must have been True at connect.
        """
        if self._telemetry_mode == "off":
            return
        if self._telemetry_mode == "poll":
            get_position_fn = lambda: self.arm.get_position(is_radian=self.config.is_radian)
            self._pose_stream = PoseStream(get_position_fn, self._poll_hz, self._pose_store)
            self._pose_stream.start()
        elif self._telemetry_mode == "callback":
            if not self.config.enable_report:
                raise XArmConnectionError(
                    "telemetry mode 'callback' requires enable_report=True in connection config"
                )
            self._report_callback_ref = self._on_report
            self.arm.register_report_location_callback(
                self._report_callback_ref,
                report_cartesian=True,
                report_joints=False,
            )

    def stop_telemetry(self) -> None:
        """Stop pose streaming. Safe to call anytime; called automatically on disconnect()."""
        if self._pose_stream is not None:
            self._pose_stream.stop()
            self._pose_stream = None
        if self._arm is not None and self._report_callback_ref is not None:
            self._arm.release_report_location_callback(self._report_callback_ref)
            self._report_callback_ref = None

    def _on_report(self, data: dict) -> None:
        """SDK report callback; updates pose store. Called from SDK thread."""
        cartesian = data.get("cartesian") or []
        if cartesian:
            self._pose_store.update(cartesian, time.monotonic())

    def get_pose(self) -> tuple[int, list[float]]:
        """One-shot read: (code, pose). Pose is [x, y, z, roll, pitch, yaw]."""
        return self.arm.get_position(is_radian=self.config.is_radian)

    def latest_pose(self) -> tuple[list[float], float]:
        """
        Best available pose now: (pose, timestamp).
        If streaming (poll/callback), returns cached; if off, one-shot read. Timestamp is monotonic.
        """
        if self._telemetry_mode == "off":
            code, pose = self.get_pose()
            return (list(pose) if code == 0 and pose else [], time.monotonic())
        return self._pose_store.get()

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
