"""
Phase 0 smoke test: connect to the robot and print version, state, error/warn codes, and pose.
"""
import argparse
import json
import os

from xarm7_driver import XArmConnectionConfig, XArmDriver


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 0: connect and read basic status")
    parser.add_argument("--ip", default=os.getenv("XARM_IP"), help="Robot IP (or set XARM_IP)")
    parser.add_argument("--timeout", type=float, default=None, help="SDK command timeout (seconds)")
    parser.add_argument("--degrees", action="store_true", help="Use degrees instead of radians for RPY")
    args = parser.parse_args()

    if not args.ip:
        raise SystemExit("No IP provided. Use --ip or set XARM_IP environment variable.")

    cfg = XArmConnectionConfig(
        ip=args.ip,
        is_radian=not args.degrees,
        timeout=args.timeout,
    )
    driver = XArmDriver(cfg)

    driver.connect()
    try:
        status = driver.read_basic_status()
        print(json.dumps(status, indent=2))
    finally:
        driver.disconnect()


if __name__ == "__main__":
    main()
