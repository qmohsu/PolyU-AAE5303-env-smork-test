#!/usr/bin/env python3
"""
AAE5303 Python + ROS 2 environment smoke test.

Run: `python scripts/test_python_env.py`
The script keeps running even if individual checks fail so you get a full report.
"""

from __future__ import annotations

import importlib
import json
import os
import platform
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Tuple


@dataclass
class CheckResult:
    ok: bool
    message: str
    remediation: str | None = None


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SAMPLE_IMAGE = DATA_DIR / "sample_image.png"
SAMPLE_PCD = DATA_DIR / "sample_pointcloud.pcd"

REQUIRED_MODULES: dict[str, str] = {
    "numpy": "pip install numpy",
    "scipy": "pip install scipy",
    "matplotlib": "pip install matplotlib",
    "cv2": "pip install opencv-python",
    "open3d": "pip install open3d",
}

OPTIONAL_MODULES: dict[str, str] = {
    "rclpy": "sudo apt install ros-humble-rclpy || pip install rclpy",
}

REQUIRED_BINARIES: dict[str, str] = {
    "python3": "Ensure Python 3.10+ is installed and on PATH",
    "ros2": "source /opt/ros/humble/setup.bash or add ROS 2 bin to PATH",
    "colcon": "sudo apt install python3-colcon-common-extensions",
}


def _python_version_check() -> CheckResult:
    if sys.version_info < (3, 10):
        return CheckResult(
            False,
            f"Python {sys.version.split()[0]} detected (< 3.10).",
            "Install Python 3.10 or newer (Ubuntu 22.04 ships 3.10).",
        )
    return CheckResult(True, f"Python version OK: {sys.version.split()[0]}")


def _module_import_check(name: str, hint: str, required: bool) -> CheckResult:
    try:
        module = importlib.import_module(name)
    except ModuleNotFoundError as exc:  # pragma: no cover - informative output
        prefix = "Missing required" if required else "Missing optional"
        return CheckResult(False if required else True, f"{prefix} module '{name}'.", hint if required else hint)
    return CheckResult(True, f"Module '{name}' found (v{getattr(module, '__version__', 'unknown')}).")


def _run_numpy_checks() -> List[CheckResult]:
    results: List[CheckResult] = []
    try:
        import numpy as np
    except Exception as exc:  # pragma: no cover
        results.append(CheckResult(False, f"Failed to import numpy: {exc}", REQUIRED_MODULES["numpy"]))
        return results

    a = np.arange(9).reshape(3, 3)
    b = np.eye(3)
    if not np.array_equal(a @ b, a):
        results.append(CheckResult(False, "numpy matrix multiply returned unexpected result.", "Reinstall numpy."))
    else:
        results.append(CheckResult(True, "numpy matrix multiply OK."))
    return results


def _run_scipy_checks() -> List[CheckResult]:
    results: List[CheckResult] = []
    try:
        import numpy as np
        from scipy import fft
    except Exception as exc:  # pragma: no cover
        results.append(CheckResult(False, f"Failed to import scipy/fft: {exc}", REQUIRED_MODULES["scipy"]))
        return results
    sample = np.sin(np.linspace(0, 8 * np.pi, 128))
    spectrum = np.abs(fft.fft(sample))
    if not np.isfinite(spectrum).all():
        results.append(CheckResult(False, "scipy FFT produced non-finite values.", "Reinstall scipy."))
    else:
        results.append(CheckResult(True, "scipy FFT OK."))
    return results


def _run_matplotlib_check() -> CheckResult:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        return CheckResult(False, f"matplotlib import failed: {exc}", REQUIRED_MODULES["matplotlib"])
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    tmp = Path(tempfile.gettempdir()) / "aae5303_matplotlib.png"
    try:
        fig.savefig(tmp)
        ok = tmp.exists() and tmp.stat().st_size > 0
    finally:
        plt.close(fig)
        if tmp.exists():
            tmp.unlink()
    if not ok:
        return CheckResult(False, "matplotlib could not write an image.", "Check that libpng and matplotlib backend are installed.")
    return CheckResult(True, "matplotlib backend OK (Agg).")


def _run_cv_check() -> List[CheckResult]:
    results: List[CheckResult] = []
    try:
        import cv2
    except Exception as exc:  # pragma: no cover
        results.append(CheckResult(False, f"OpenCV import failed: {exc}", REQUIRED_MODULES["cv2"]))
        return results
    results.append(CheckResult(True, f"OpenCV version {cv2.__version__} detected."))
    if not SAMPLE_IMAGE.exists():
        results.append(
            CheckResult(
                False,
                f"Sample image not found at {SAMPLE_IMAGE}",
                "Re-clone the repo or run `git checkout -- data/sample_image.png`.",
            )
        )
        return results
    img = cv2.imread(str(SAMPLE_IMAGE))
    if img is None:
        results.append(
            CheckResult(False, f"OpenCV failed to load {SAMPLE_IMAGE}.", "Ensure OpenCV PNG support is installed.")
        )
    else:
        results.append(CheckResult(True, f"OpenCV loaded sample image {img.shape[1]}x{img.shape[0]}."))
    return results


def _run_open3d_check() -> List[CheckResult]:
    results: List[CheckResult] = []
    try:
        import numpy as np
        import open3d as o3d
    except Exception as exc:  # pragma: no cover
        results.append(CheckResult(False, f"Open3D import failed: {exc}", REQUIRED_MODULES["open3d"]))
        return results

    results.append(CheckResult(True, f"Open3D version {o3d.__version__} detected."))
    cube = o3d.geometry.PointCloud()
    cube.points = o3d.utility.Vector3dVector([[0, 0, 0], [1, 1, 1]])
    bbox = cube.get_axis_aligned_bounding_box()
    if bbox.is_empty():
        results.append(CheckResult(False, "Open3D failed to compute bounding box.", "Reinstall open3d."))
    else:
        results.append(CheckResult(True, "Open3D geometry ops OK."))

    if SAMPLE_PCD.exists():
        cloud = o3d.io.read_point_cloud(str(SAMPLE_PCD))
        if cloud.is_empty():
            results.append(CheckResult(False, f"Sample PCD {SAMPLE_PCD} read but contained 0 points.", "Check Open3D installation."))
        else:
            results.append(CheckResult(True, f"Sample PCD loaded with {len(cloud.points)} pts."))
    else:
        results.append(CheckResult(False, f"Sample point cloud missing at {SAMPLE_PCD}.", "Restore data/sample_pointcloud.pcd."))
    return results


def _check_binaries() -> List[CheckResult]:
    results: List[CheckResult] = []
    for binary, fix in REQUIRED_BINARIES.items():
        path = shutil.which(binary)
        if path:
            results.append(CheckResult(True, f"Binary '{binary}' found at {path}"))
        else:
            results.append(CheckResult(False, f"Binary '{binary}' not found on PATH.", fix))
    return results


def _environment_snapshot() -> CheckResult:
    snapshot = {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "cwd": os.getcwd(),
    }
    return CheckResult(True, f"Environment: {json.dumps(snapshot, indent=2)}")


def main() -> int:
    results: List[CheckResult] = []
    results.append(_environment_snapshot())
    results.append(_python_version_check())
    for name, cmd in REQUIRED_MODULES.items():
        results.append(_module_import_check(name, cmd, True))
    for name, cmd in OPTIONAL_MODULES.items():
        results.append(_module_import_check(name, cmd, False))

    results.extend(_run_numpy_checks())
    results.extend(_run_scipy_checks())
    results.append(_run_matplotlib_check())
    results.extend(_run_cv_check())
    results.extend(_run_open3d_check())
    results.extend(_check_binaries())

    failures = [r for r in results if not r.ok]
    for res in results:
        status = "✅" if res.ok else "❌"
        print(f"{status} {res.message}")
        if not res.ok and res.remediation:
            print(f"   ↳ Fix: {res.remediation}")

    if failures:
        print(f"\nEnvironment check failed ({len(failures)} issue(s)).")
        return 1
    print("\nAll checks passed. You are ready for AAE5303 🚀")
    return 0


if __name__ == "__main__":
    sys.exit(main())

