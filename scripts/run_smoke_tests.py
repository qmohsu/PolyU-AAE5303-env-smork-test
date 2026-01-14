#!/usr/bin/env python3
"""
AAE5303 one-command smoke test runner.

Run:
  python scripts/run_smoke_tests.py

Optional:
  python scripts/run_smoke_tests.py --ros2-colcon-build

Notes:
- This runner is intentionally conservative: it executes existing test scripts in subprocesses
  so native crashes (SIGSEGV) are captured as a readable failure rather than killing the runner.
- ROS 2 workspace build is optional because it requires the ROS 2 environment to be sourced.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    args = _parse_args()
    root = Path(__file__).resolve().parents[1]

    _enable_line_buffering()

    steps: list[tuple[str, list[str], Path]] = [
        ("Python + ROS environment checks", [sys.executable, "-u", str(root / "scripts" / "test_python_env.py")], root),
        ("Open3D point cloud pipeline", [sys.executable, "-u", str(root / "scripts" / "test_open3d_pointcloud.py")], root),
    ]

    print("========================================", flush=True)
    print("AAE5303 One-command Environment Check", flush=True)
    print("Tip: read README.md for interpretation and fixes.", flush=True)
    print("========================================\n", flush=True)

    ok_all = True
    for i, (title, cmd, cwd) in enumerate(steps, start=1):
        ok_all &= _run_step(i, title, cmd, cwd)

    if args.ros2_colcon_build:
        ok_all &= _run_ros2_colcon_build(root)

    _cleanup_smoke_test_artifacts(root)
    print("\n========================================", flush=True)
    print(f"OVERALL RESULT: {'PASS' if ok_all else 'FAIL'}", flush=True)
    print("========================================", flush=True)
    return 0 if ok_all else 1


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run AAE5303 smoke tests.")
    p.add_argument(
        "--ros2-colcon-build",
        action="store_true",
        help="Also build ros2_ws with colcon (requires ROS 2 env to be sourced).",
    )
    return p.parse_args()


def _run_step(step: int, title: str, cmd: list[str], cwd: Path) -> bool:
    print(f"\n========== Step {step}: {title} ==========", flush=True)
    print(f"Running: {' '.join(cmd)}", flush=True)
    try:
        start = time.time()
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        p = subprocess.run(cmd, cwd=str(cwd), text=True, env=env)
    except FileNotFoundError as exc:
        print(f"❌ Failed to run: {cmd[0]} ({exc})")
        return False
    dur = time.time() - start

    if p.returncode == 0:
        print(f"✅ {title}: PASS ({dur:.1f}s)", flush=True)
        return True

    if p.returncode < 0:
        print(f"❌ {title}: CRASHED (signal {-p.returncode}) ({dur:.1f}s)", flush=True)
    else:
        print(f"❌ {title}: FAIL (exit code {p.returncode}) ({dur:.1f}s)", flush=True)
    return False


def _run_ros2_colcon_build(root: Path) -> bool:
    """
    Build the ROS 2 workspace if ROS 2 is available and sourced.
    """
    ros2 = shutil.which("ros2")
    colcon = shutil.which("colcon")
    ws = root / "ros2_ws"

    print("\n=== ROS 2 colcon build (optional) ===")
    if not ws.exists():
        print(f"❌ Workspace not found: {ws}")
        return False

    if not ros2 or not colcon:
        print("❌ ros2/colcon not found on PATH. Source ROS 2 and install colcon.")
        print("   ↳ Fix: source /opt/ros/<distro>/setup.bash")
        print("   ↳ Fix: sudo apt install python3-colcon-common-extensions")
        return False

    if os.environ.get("ROS_VERSION") != "2":
        print("❌ ROS_VERSION is not '2'. You likely did not source ROS 2 in this shell.")
        print("   ↳ Fix: source /opt/ros/<distro>/setup.bash")
        return False

    cmd = [colcon, "build", "--packages-select", "env_check_pkg"]
    print(f"ℹ️ Running: {' '.join(cmd)} (cwd={ws})")
    p = subprocess.run(cmd, cwd=str(ws), text=True)
    if p.returncode == 0:
        print("✅ ROS 2 workspace build: PASS")
        return True
    print(f"❌ ROS 2 workspace build: FAIL (exit code {p.returncode})")
    print("   ↳ Hint: try `rm -rf build install log` then rebuild.")
    return False


def _cleanup_smoke_test_artifacts(root: Path) -> None:
    """
    Keep the repository clean after running tests.

    Some tests intentionally write small output files to verify I/O paths.
    This cleanup ensures students do not accidentally commit generated artifacts.
    """
    data_dir = root / "data"
    if not data_dir.exists():
        return

    candidates = [
        data_dir / "sample_pointcloud_copy.pcd",
    ]
    candidates.extend(sorted(data_dir.glob("_tmp*.pcd")))

    removed = 0
    for p in candidates:
        try:
            if p.exists():
                p.unlink()
                removed += 1
        except Exception:
            # Best-effort cleanup only.
            pass

    if removed:
        print(f"\nℹ️ Cleaned up {removed} generated file(s) in data/.", flush=True)


def _enable_line_buffering() -> None:
    """
    Reduce confusing output reordering caused by stdout buffering.
    """
    try:
        # Python 3.7+: reconfigure exists for TextIOWrapper.
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass


if __name__ == "__main__":
    raise SystemExit(main())

