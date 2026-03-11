"""
Run phase scripts in order for a repeatable full test.

Runs: phase0 (smoke) -> phase1 (prepare) -> phase4 (velocity pulse).
Uses the same --ip (and optional --timeout, --degrees) for all.
Exits with the first failing script's exit code.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

# Directory containing this script and the phase scripts
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PHASES = [
    ("phase0_smoke_test.py", "Smoke test"),
    ("phase1_prepare.py", "Prepare"),
    ("phase4_velocity_pulse.py", "Velocity pulse"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run phase0 -> phase1 -> phase4 with same config")
    parser.add_argument("--ip", default=os.getenv("XARM_IP"), help="Robot IP (or set XARM_IP)")
    parser.add_argument("--timeout", type=float, default=None, help="SDK timeout (seconds)")
    parser.add_argument("--degrees", action="store_true", help="Use degrees instead of radians")
    args = parser.parse_args()

    if not args.ip:
        print("No IP provided. Use --ip or set XARM_IP.", file=sys.stderr)
        return 1

    cmd_base = [sys.executable]
    if args.timeout is not None:
        cmd_base.extend(["--timeout", str(args.timeout)])
    if args.degrees:
        cmd_base.append("--degrees")

    for script, label in PHASES:
        path = os.path.join(SCRIPT_DIR, script)
        cmd = cmd_base + [path, "--ip", args.ip]
        print(f"Run: {label} ({script})")
        ret = subprocess.run(cmd, cwd=os.path.dirname(SCRIPT_DIR))
        if ret.returncode != 0:
            print(f"Failed: {script} exited {ret.returncode}", file=sys.stderr)
            return ret.returncode

    print("All phases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
