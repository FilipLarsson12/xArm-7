# Architecture & Code Organization

## Design goals
1. **Safety-first**: always support stop(), watchdog timeouts, and error/state monitoring.
2. **Single abstraction layer**: controller code never talks to XArmAPI directly.
3. **Config-driven**: IP, limits, telemetry mode, and speed clamps live in config/env.
4. **Testable logic**: pure helpers (clamp, rate, config parsing) are isolated from hardware I/O.
5. **Same code for real robot**: no “if simulation” branches in the driver API; only configuration changes.

## Repo layout

### `src/xarm7_driver/` (library code)
- `__init__.py`
  - Exposes the public API (`XArmDriver`, config types).
- `config.py`
  - Dataclasses for configuration:
    - connection (ip, timeout)
    - units (is_radian)
    - telemetry mode (`off|poll|callback`, hz)
    - clamps (max linear mm/s, max angular rad/s)
    - limits (reduced mode + boundary values)
- `driver.py`
  - Main entry point class: `XArmDriver`
  - Responsibilities:
    - connect/disconnect
    - prepare (clear errors, motion_enable, set_state)
    - apply limits (reduced mode, boundary)
    - enter cartesian velocity mode (mode 5)
    - `send_twist()` with clamping + duration watchdog
    - `stop()` and `shutdown()`
    - optional fault monitor integration
- `telemetry.py`
  - Pose streaming implementation:
    - `telemetry=off`: no background work
    - `telemetry=poll`: thread polling `get_position()`
    - `telemetry=callback`: uses SDK report callbacks (when enabled_report)
  - Provides `latest_pose()` and timestamps.
- `limits.py`
  - Helpers to configure/query:
    - reduced mode settings (max tcp speed, max joint speed, joint ranges)
    - safety boundary/fence settings (xyz min/max) if enabled in controller
  - Contains validation (ordering of max/min, units, etc).
- `errors.py`
  - Exception classes:
    - `XArmConnectionError`, `XArmCommandError`, `XArmSafetyError`
  - Utilities to format common error/warn/state into readable messages.
- `utils.py`
  - Pure utilities:
    - clamp helpers
    - rate loop helper (sleep-to-hz)
    - timing / monotonic timestamps
    - thread stop events

### `scripts/` (runnable steps; thin wrappers)
- `phase0_smoke_test.py`
  - Connect → print version/state/error codes/pose → disconnect.
- `phase1_prepare.py`
  - Clear errors/warns if present → motion_enable → set_state(0).
- `phase4_velocity_pulse.py`
  - Enter mode 5 → send tiny velocity for short duration → stop.
- (Later) `log_pose_csv.py`
  - Run telemetry and dump to CSV.

Rules:
- scripts should be **thin**: parse args + call into `xarm7_driver`.
- no business logic in scripts.

### `config/`
- `config.example.yaml`
  - Template config file checked into git.
- `local.yaml`
  - Your real config (ignored by git). Stores IP and workspace bounds.

### `notebooks/` (optional)
- `quick_debug.ipynb`
  - Imports `xarm7_driver`
  - Shows pose stream, quick plots, and manual command experiments.

### Root docs
- `README.md`
  - What it is, prerequisites, quickstart commands.
- `PLAN.md`
  - Phase roadmap and completion criteria.
- `ARCHITECTURE.md`
  - This file.

## Public API (intended)
- `XArmDriver.connect()`, `disconnect()`
- `XArmDriver.prepare()`
- `XArmDriver.apply_limits()`
- `XArmDriver.set_telemetry(mode=..., hz=...)`
- `XArmDriver.enter_cartesian_velocity_mode()`
- `XArmDriver.send_twist(vx, vy, vz, wx, wy, wz, frame="base|tool")`
- `XArmDriver.stop()`
- `XArmDriver.latest_pose()`

## Non-goals (for now)
- Trajectory planning
- IK/FK utilities beyond what the SDK gives
- ROS integration (later possible)