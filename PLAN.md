# xArm7 Cartesian Velocity Driver — Plan

## Goal
Build a small, safe Python driver layer for xArm7 Cartesian velocity control (mode 5) that:
- Connects/prepares the robot reliably
- Configures safety limits (reduced mode + safety boundary/fence when enabled)
- Optionally streams TCP pose (off/poll/callback)
- Sends Cartesian velocity commands with clamping + watchdog duration
- Provides a reliable stop() and safe shutdown()
- Monitors errors/state and fails safe

## Repo Structure
- `src/xarm7_driver/` reusable driver package
- `scripts/` runnable phase scripts
- `config/` example config (IP, limits, telemetry)
- `notebooks/` optional interactive debug notebook

## Phases

### Phase 0 — Environment + smoke test
**Done when:**
- SDK installs and imports
- Script can connect to robot and print: version/state/error codes/pose

**Deliverables:**
- `pyproject.toml` dependencies
- `scripts/phase0_smoke_test.py`

### Phase 1 — Connect + prepare
**Done when:**
- Can clear errors/warnings (if any)
- Can enable motion and set state to ready safely

**Deliverables:**
- `XArmDriver.connect()`, `prepare()`
- `scripts/phase1_prepare.py`

### Phase 2 — Limits / safety configuration
**Done when:**
- Reduced mode and bounds can be configured from config
- (Optional) safety boundary/fence config supported
- Driver can query current reduced states

**Deliverables:**
- `limits.py` helpers
- `XArmDriver.apply_limits()`

### Phase 3 — Telemetry (pose streaming on/off)
**Done when:**
- telemetry=off: no background work
- telemetry=poll: background polling provides latest pose
- telemetry=callback: (when enabled_report) callback provides latest pose

**Deliverables:**
- `telemetry.py` PoseStream
- `XArmDriver.get_pose()` / `latest_pose()`

### Phase 4 — Enter Cartesian velocity mode (mode 5)
**Done when:**
- Driver switches mode/state reliably
- A tiny velocity pulse works and stops cleanly

**Deliverables:**
- `XArmDriver.enter_cartesian_velocity_mode()`
- `scripts/phase4_velocity_pulse.py`

### Phase 5 — Safe velocity command pipeline
**Done when:**
- `send_twist()` clamps + uses duration watchdog
- `stop()` zeros velocity immediately
- fault monitor stops on error/state changes

**Deliverables:**
- `XArmDriver.send_twist()`, `stop()`, `shutdown()`

### Phase 6 — Testing + logging
**Done when:**
- Basic logging of pose/time to CSV works
- Repeatable run scripts exist

## Config
Use environment variable `XARM_IP` or a YAML config in `config/local.yaml` (ignored by git).
`config/config.example.yaml` shows the expected keys.

## How to run (examples)
- `python scripts/phase0_smoke_test.py --ip $XARM_IP`
- `python scripts/phase1_prepare.py --ip $XARM_IP`