"""
Pose streaming: thread-safe store and poll-based updater. No SDK dependency.
"""
from __future__ import annotations

import threading
import time
from typing import Callable

from xarm7_driver.utils import RateLoop


class LatestPoseStore:
    """
    Thread-safe store for one pose and timestamp.
    Updated by a poll thread or SDK callback; read by latest_pose().
    """
    __slots__ = ("_pose", "_timestamp", "_lock")

    def __init__(self) -> None:
        self._pose: list[float] = []
        self._timestamp: float = 0.0
        self._lock = threading.Lock()

    def update(self, pose: list[float], timestamp: float) -> None:
        with self._lock:
            self._pose = list(pose)
            self._timestamp = timestamp

    def get(self) -> tuple[list[float], float]:
        with self._lock:
            return (list(self._pose), self._timestamp)


class PoseStream:
    """
    Background thread that polls get_position_fn at poll_hz and updates store.
    Call start() after connect; call stop() before disconnect.
    """
    __slots__ = ("_get_position_fn", "_poll_hz", "_store", "_thread", "_stop")

    def __init__(
        self,
        get_position_fn: Callable[[], tuple[int, list[float]]],
        poll_hz: float,
        store: LatestPoseStore,
    ) -> None:
        self._get_position_fn = get_position_fn
        self._poll_hz = poll_hz
        self._store = store
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run(self) -> None:
        rate = RateLoop(self._poll_hz)
        while not self._stop.is_set():
            try:
                code, pose = self._get_position_fn()
                if code == 0 and pose:
                    self._store.update(pose, time.monotonic())
            except Exception:
                pass  # arm may be disconnected; ignore and keep loop alive until stop
            rate.sleep()
