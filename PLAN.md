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

## Progress
- **Phase 0** — Complete
- **Phase 1** — Complete
- **Phase 2** — Complete
- **Phase 3** — Complete
- **Phase 4** — Complete
- **Phase 5** — Complete
- **Phase 6** — Complete

## Phases

### Phase 0 — Environment + smoke test ✅ Complete
**Done when:**
- SDK installs and imports
- Script can connect to robot and print: version/state/error codes/pose

**Deliverables:**
- `pyproject.toml` dependencies
- `scripts/phase0_smoke_test.py`

### Phase 1 — Connect + prepare ✅ Complete
**Done when:**
- Can clear errors/warnings (if any)
- Can enable motion and set state to ready safely

**Deliverables:**
- `XArmDriver.connect()`, `prepare()`
- `scripts/phase1_prepare.py`

### Phase 2 — Limits / safety configuration ✅ Complete
**Done when:**
- Reduced mode and bounds can be configured from config
- (Optional) safety boundary/fence config supported
- Driver can query current reduced states

**Deliverables:**
- `XArmDriver.apply_limits()` (limit logic in driver only; no separate limits.py)

### Phase 3 — Telemetry (pose streaming on/off) ✅ Complete
**Done when:**
- telemetry=off: no background work
- telemetry=poll: background polling provides latest pose
- telemetry=callback: (when enabled_report) callback provides latest pose

**Deliverables:**
- `telemetry.py` PoseStream
- `XArmDriver.get_pose()` / `latest_pose()`

### Phase 4 — Enter Cartesian velocity mode (mode 5) ✅ Complete
**Done when:**
- Driver switches mode/state reliably
- A tiny velocity pulse works and stops cleanly

**Deliverables:**
- `XArmDriver.enter_cartesian_velocity_mode()`
- `scripts/phase4_velocity_pulse.py`

### Phase 5 — Safe velocity command pipeline ✅ Complete
**Done when:**
- `send_twist()` clamps + uses duration watchdog
- `stop()` zeros velocity immediately
- fault monitor stops on error/state changes

**Deliverables:**
- `XArmDriver.send_twist()`, `stop()`, `shutdown()`

### Phase 6 — Testing + logging ✅ Complete
**Done when:**
- Basic logging of pose/time to CSV works
- Repeatable run scripts exist

**Deliverables:**
- `scripts/log_pose_to_csv.py` — pose + timestamp to CSV; background writer thread so the sampling loop never blocks on I/O; timestamps are those returned with each pose (accurate pose–time alignment).
- `scripts/run_phases.py` — runs phase0 → phase1 → phase4 with the same config.

## Config
Use environment variable `XARM_IP` or a YAML config in `config/local.yaml` (ignored by git).
`config/config.example.yaml` shows the expected keys.

## How to run (examples)
- `python scripts/phase0_smoke_test.py --ip $XARM_IP`
- `python scripts/phase1_prepare.py --ip $XARM_IP`
- `python scripts/run_phases.py --ip $XARM_IP` — repeatable full test (phase0 → phase1 → phase4)
- `python scripts/log_pose_to_csv.py --ip $XARM_IP --output pose_log.csv --duration 10` — log pose at 50 Hz to CSV