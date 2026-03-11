"""
Phase 1: Connect, clear errors/warnings if any, enable motion, set state to ready.
"""
import argparse
import os

from xarm7_driver import XArmConnectionConfig, XArmDriver
from xarm7_driver.errors import XArmConnectionError


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 1: connect and prepare (motion enable, state=0)")
    parser.add_argument("--ip", default=os.getenv("XARM_IP"), help="Robot IP (or set XARM_IP)")
    parser.add_argument("--timeout", type=float, default=None, help="SDK command timeout (seconds)")
    parser.add_argument("--degrees", action="store_true", help="Use degrees instead of radians")
    args = parser.parse_args()

    if not args.ip:
        raise SystemExit("No IP provided. Use --ip or set XARM_IP environment variable.")

    cfg = XArmConnectionConfig(
        ip=args.ip,
        is_radian=not args.degrees,
        timeout=args.timeout,
    )
    driver = XArmDriver(cfg)

    try:
        driver.connect()
        driver.prepare()
        code, state = driver.arm.get_state()
        print("Prepared. get_state:", code, state)
    except XArmConnectionError as e:
        raise SystemExit(f"Prepare failed: {e}") from e
    finally:
        driver.disconnect()
    print("Disconnected.")


if __name__ == "__main__":
    main()
