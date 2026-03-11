# xArm 7 — Cartesian Velocity Driver (Python)

A small, safety-first Python driver layer for controlling an **xArm7** using **Cartesian velocity control** (xArm mode **5**) via the **xArm Python SDK**.

This repo is organized so your controller code never talks to `XArmAPI` directly — it talks to a stable wrapper (`XArmDriver`) that handles:
- connect/prepare (enable motors, set state)
- safety limits (reduced mode + optional boundary/fence)
- optional TCP pose streaming (off / polling / callback)
- safe velocity sending (`send_twist`) with clamping + watchdog duration
- stop + shutdown

## Prerequisites
- Python 3.10+ recommended
- Network access to the xArm controller (same subnet)
- xArm Python SDK (`xarm-python-sdk`)

## Install (recommended: editable)
Create and activate a virtual environment, then install:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .