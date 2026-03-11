"""
Phase 4: Enter Cartesian velocity mode (5), send a small velocity pulse, then stop.
"""
import argparse
import os
import time

from xarm7_driver import XArmConnectionConfig, XArmDriver
from xarm7_driver.errors import XArmCommandError, XArmConnectionError


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 4: enter mode 5, send small velocity pulse, stop"
    )
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
        driver.enter_cartesian_velocity_mode()

        # Small velocity pulse: 5 mm/s in x for 0.2 s (duration=0.2 in send_twist)
        code = driver.send_twist(5.0, 0.0, 0.0, 0.0, 0.0, 0.0, duration=0.2)
        if code != 0:
            print("send_twist returned code:", code)
        time.sleep(0.25)
        driver.stop()
        print("Velocity pulse done, stopped.")
    except (XArmConnectionError, XArmCommandError) as e:
        raise SystemExit(f"Failed: {e}") from e
    finally:
        driver.shutdown()
    print("Done.")


if __name__ == "__main__":
    main()
