"""
Phase 6: Log pose + timestamp to CSV for testing/analysis.

Accuracy design:
- Each row uses the timestamp returned with the pose (time when pose was received
  in the telemetry layer), not the time when the row is written. That keeps
  pose–time alignment correct.
- File I/O runs in a dedicated writer thread. The sampling loop only calls
  latest_pose(), enqueues (timestamp, pose), check_fault(), and rate.sleep().
  So sampling is never delayed by disk and stays at a fixed rate.
- Log rate equals telemetry poll rate (e.g. 50 Hz) so we capture every update
  once and stay in lockstep with the pose stream.
"""
from __future__ import annotations

import argparse
import csv
import os
import queue
import signal
import sys
import threading
import time

from xarm7_driver import XArmConnectionConfig, XArmDriver
from xarm7_driver.errors import XArmConnectionError
from xarm7_driver.utils import RateLoop

# Sentinel for "stop writing"
_STOP = object()

# Defaults aligned with config.example.yaml telemetry
DEFAULT_POLL_HZ = 50.0
CSV_HEADER = ("timestamp_monotonic", "x", "y", "z", "roll", "pitch", "yaw")
QUEUE_MAXSIZE = 10000
FLUSH_EVERY_ROWS = 100


def _writer_thread(
    out_path: str,
    log_queue: queue.Queue,
    flush_every: int,
) -> None:
    """Drain queue and write CSV rows. Stops on _STOP sentinel."""
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        n = 0
        while True:
            try:
                item = log_queue.get()
            except Exception:
                break
            if item is _STOP:
                break
            ts, pose = item
            if len(pose) >= 6:
                w.writerow([ts, pose[0], pose[1], pose[2], pose[3], pose[4], pose[5]])
                n += 1
                if n % flush_every == 0:
                    f.flush()
        f.flush()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Log pose + timestamp to CSV (telemetry poll mode, accurate timing)"
    )
    parser.add_argument("--ip", default=os.getenv("XARM_IP"), help="Robot IP (or set XARM_IP)")
    parser.add_argument("--output", default="pose_log.csv", help="Output CSV path")
    parser.add_argument("--rate", type=float, default=DEFAULT_POLL_HZ, help="Poll/log rate (Hz)")
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Run for N seconds (0 = until Ctrl+C)",
    )
    parser.add_argument("--timeout", type=float, default=None, help="SDK command timeout (s)")
    parser.add_argument("--degrees", action="store_true", help="Use degrees instead of radians")
    args = parser.parse_args()

    if not args.ip:
        print("No IP provided. Use --ip or set XARM_IP.", file=sys.stderr)
        return 1

    if args.rate <= 0:
        print("--rate must be positive.", file=sys.stderr)
        return 1

    cfg = XArmConnectionConfig(
        ip=args.ip,
        is_radian=not args.degrees,
        timeout=args.timeout,
    )
    driver = XArmDriver(cfg)

    log_queue: queue.Queue = queue.Queue(maxsize=QUEUE_MAXSIZE)
    writer = threading.Thread(
        target=_writer_thread,
        args=(args.output, log_queue, FLUSH_EVERY_ROWS),
        daemon=False,
    )
    writer.start()

    stop_requested = threading.Event()

    def _on_signal(_sig: int, _frame: object) -> None:
        stop_requested.set()

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    try:
        driver.connect()
        driver.prepare()
        driver.set_telemetry("poll", poll_hz=args.rate)
        driver.start_telemetry()

        rate = RateLoop(args.rate)
        deadline = time.monotonic() + args.duration if args.duration > 0 else None

        while not stop_requested.is_set():
            if deadline is not None and time.monotonic() >= deadline:
                break
            pose, ts = driver.latest_pose()
            if pose and len(pose) >= 6:
                # Block on put so we never drop samples; queue is large enough for normal use.
                log_queue.put((ts, list(pose)))
            ok, err, warn = driver.check_fault()
            if not ok:
                print(f"Fault: err={err} warn={warn}", file=sys.stderr)
                break
            rate.sleep()

    except XArmConnectionError as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        return 1
    finally:
        driver.shutdown()
        log_queue.put(_STOP)
        writer.join(timeout=5.0)

    print(f"Logged to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
