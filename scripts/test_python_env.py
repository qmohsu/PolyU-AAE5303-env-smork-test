#!/usr/bin/env python3
"""
AAE5303 Python + ROS environment smoke test.

Run: `python scripts/test_python_env.py`
The script keeps running even if individual checks fail so you get a full report.

Design goals:
- Provide actionable diagnostics for students.
- Guard against native-extension crashes (e.g., Open3D) by isolating risky checks in subprocesses.
"""

from __future__ import annotations

import importlib
import json
import os
import platform
import subprocess
import shutil
import signal
import sys
import tempfile
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence


@dataclass
class CheckResult:
    ok: bool
    message: str
    remediation: str | None = None


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SAMPLE_IMAGE = DATA_DIR / "sample_image.png"
SAMPLE_PCD = DATA_DIR / "sample_pointcloud.pcd"
ROS2_WS = ROOT / "ros2_ws"

REQUIRED_MODULES: dict[str, str] = {
    "numpy": "python -m pip install -r requirements.txt",
    "scipy": "python -m pip install -r requirements.txt",
    "matplotlib": "python -m pip install -r requirements.txt",
    "cv2": "python -m pip install -r requirements.txt",
    # Open3D is checked in a subprocess to guard against segfaults.
}

OPTIONAL_MODULES: dict[str, str] = {
    "rclpy": "Install ROS 2 Python bindings (typically via ROS 2 apt repos) or `python -m pip install rclpy` if applicable.",
}

REQUIRED_BINARIES: dict[str, str] = {
    "python3": "Ensure Python 3.10+ is installed and on PATH",
    # ROS tooling checks are handled separately with better diagnostics.
}


def main() -> int:
    _enable_line_buffering()
    print("========================================", flush=True)
    print("AAE5303 Environment Check (Python + ROS)", flush=True)
    print("Goal: help you verify your environment and understand what each check means.", flush=True)
    print("========================================\n", flush=True)

    results: List[CheckResult] = []
    results.extend(_run_step_one(
        step=1,
        title="Environment snapshot",
        why="We capture platform/Python/ROS variables to diagnose common setup mistakes (especially mixed ROS env).",
        fn=_environment_snapshot,
    ))
    results.extend(_run_step_one(
        step=2,
        title="Python version",
        why="The course assumes Python 3.10+; older versions often break package wheels.",
        fn=_python_version_check,
    ))
    results.extend(_run_step_many(
        step=3,
        title="Python imports (required/optional)",
        why="Imports verify packages are installed and compatible with your Python version.",
        fn=_run_module_import_checks,
    ))
    results.extend(_run_step_many(
        step=4,
        title="NumPy sanity checks",
        why="We run a small linear algebra operation so success means more than just `import numpy`.",
        fn=_run_numpy_checks,
    ))
    results.extend(_run_step_many(
        step=5,
        title="SciPy sanity checks",
        why="We run a small FFT to confirm SciPy is functional (not just installed).",
        fn=_run_scipy_checks,
    ))
    results.extend(_run_step_one(
        step=6,
        title="Matplotlib backend check",
        why="We generate a tiny plot image (headless) to confirm plotting works on your system.",
        fn=_run_matplotlib_check,
    ))
    results.extend(_run_step_many(
        step=7,
        title="OpenCV PNG decoding (subprocess)",
        why="PNG decoding uses native code; we isolate it so corruption/codec issues cannot crash the whole report.",
        fn=_run_cv_subprocess_check,
    ))
    results.extend(_run_step_many(
        step=8,
        title="Open3D basic geometry + I/O (subprocess)",
        why="Open3D is a native extension; ABI mismatches can segfault. Subprocess isolation turns crashes into readable failures.",
        fn=_run_open3d_subprocess_checks,
    ))
    results.extend(_run_step_many(
        step=9,
        title="ROS toolchain checks",
        why="The course requires ROS tooling. This check passes if ROS 2 OR ROS 1 is available (either one is acceptable).",
        fn=_run_ros_checks,
    ))
    results.extend(_run_step_many(
        step=10,
        title="Basic CLI availability",
        why="We confirm core commands exist on PATH so students can run the same commands as in the labs.",
        fn=_check_binaries,
    ))

    failures = [r for r in results if not r.ok]
    print("\n=== Summary ===", flush=True)
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


def _environment_snapshot() -> CheckResult:
    snapshot = {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "cwd": os.getcwd(),
        "ros": {
            "ROS_VERSION": os.environ.get("ROS_VERSION"),
            "ROS_DISTRO": os.environ.get("ROS_DISTRO"),
            "ROS_ROOT": os.environ.get("ROS_ROOT"),
            "ROS_PACKAGE_PATH": os.environ.get("ROS_PACKAGE_PATH"),
            "AMENT_PREFIX_PATH": os.environ.get("AMENT_PREFIX_PATH"),
            "CMAKE_PREFIX_PATH": os.environ.get("CMAKE_PREFIX_PATH"),
        },
    }
    return CheckResult(True, f"Environment: {json.dumps(snapshot, indent=2)}")


def _python_version_check() -> CheckResult:
    if sys.version_info < (3, 10):
        return CheckResult(
            False,
            f"Python {sys.version.split()[0]} detected (< 3.10).",
            "Install Python 3.10 or newer (Ubuntu 22.04 ships 3.10).",
        )
    return CheckResult(True, f"Python version OK: {sys.version.split()[0]}")


def _run_module_import_checks() -> List[CheckResult]:
    results: List[CheckResult] = []
    for name, cmd in REQUIRED_MODULES.items():
        results.append(_module_import_check(name, cmd, required=True))
    for name, cmd in OPTIONAL_MODULES.items():
        results.append(_module_import_check(name, cmd, required=False))
    return results


def _module_import_check(name: str, hint: str, required: bool) -> CheckResult:
    try:
        module = importlib.import_module(name)
    except ModuleNotFoundError:  # pragma: no cover - informative output
        prefix = "Missing required" if required else "Missing optional"
        return CheckResult(False if required else True, f"{prefix} module '{name}'.", hint)
    version = getattr(module, "__version__", "unknown")
    return CheckResult(True, f"Module '{name}' found (v{version}).")


def _run_numpy_checks() -> List[CheckResult]:
    results: List[CheckResult] = []
    try:
        import numpy as np
    except Exception as exc:  # pragma: no cover
        results.append(CheckResult(False, f"Failed to import numpy: {exc}", "pip install -r requirements.txt"))
        return results

    a = np.arange(9).reshape(3, 3)
    b = np.eye(3)
    if not np.array_equal(a @ b, a):
        results.append(CheckResult(False, "numpy matrix multiply returned unexpected result.", "Reinstall numpy."))
    else:
        results.append(CheckResult(True, "numpy matrix multiply OK."))
    results.append(CheckResult(True, f"numpy version {np.__version__} detected."))
    return results


def _run_scipy_checks() -> List[CheckResult]:
    results: List[CheckResult] = []
    try:
        import numpy as np
        from scipy import fft
        import scipy
    except Exception as exc:  # pragma: no cover
        results.append(CheckResult(False, f"Failed to import scipy/fft: {exc}", "pip install -r requirements.txt"))
        return results

    sample = np.sin(np.linspace(0, 8 * np.pi, 128))
    spectrum = np.abs(fft.fft(sample))
    if not np.isfinite(spectrum).all():
        results.append(CheckResult(False, "scipy FFT produced non-finite values.", "Reinstall scipy."))
    else:
        results.append(CheckResult(True, "scipy FFT OK."))
    results.append(CheckResult(True, f"scipy version {scipy.__version__} detected."))
    return results


def _run_matplotlib_check() -> CheckResult:
    try:
        warnings.filterwarnings("ignore", message="Unable to import Axes3D.*")
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        return CheckResult(False, f"matplotlib import failed: {exc}", "pip install -r requirements.txt")

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
    return CheckResult(True, f"matplotlib backend OK (Agg), version {matplotlib.__version__}.")


def _run_cv_subprocess_check() -> List[CheckResult]:
    """
    Decode the sample PNG in a subprocess.

    In rare cases, corrupted images or codec issues can crash native decoders.
    Running in a subprocess guarantees we can turn crashes into readable errors.
    """
    results: List[CheckResult] = []
    if not SAMPLE_IMAGE.exists():
        results.append(
            CheckResult(
                False,
                f"Sample image not found at {SAMPLE_IMAGE}",
                "Re-clone the repo or run `git checkout -- data/sample_image.png`.",
            )
        )
        return results

    if SAMPLE_IMAGE.stat().st_size < 256:
        results.append(
            CheckResult(
                False,
                f"Sample image looks too small ({SAMPLE_IMAGE.stat().st_size} bytes): {SAMPLE_IMAGE}",
                "Restore the file from git: `git checkout -- data/sample_image.png`.",
            )
        )
        return results

    code = r"""
import json
import os
import cv2

path = os.environ["AAE5303_SAMPLE_IMAGE"]
img = cv2.imread(path)
payload = {
  "cv2": cv2.__version__,
  "ok": img is not None,
  "shape": None if img is None else [int(img.shape[0]), int(img.shape[1]), int(img.shape[2])],
}
print(json.dumps(payload))
"""
    ok, stdout, stderr, rc = _run_python_subprocess(code, env={"AAE5303_SAMPLE_IMAGE": str(SAMPLE_IMAGE)})
    if ok:
        payload = _safe_json_last_line(stdout)
        if payload and payload.get("ok"):
            h, w, _c = payload.get("shape", [0, 0, 0])
            results.append(CheckResult(True, f"OpenCV OK (v{payload.get('cv2')}), decoded sample image {w}x{h}."))
        else:
            results.append(
                CheckResult(
                    False,
                    f"OpenCV failed to decode {SAMPLE_IMAGE}.",
                    "Ensure OpenCV has PNG support and the file is not corrupted (try `git checkout -- data/sample_image.png`).",
                )
            )
        return results

    results.append(CheckResult(False, f"OpenCV subprocess failed: {_format_subprocess_failure(rc, stdout, stderr)}", "Reinstall OpenCV: `pip install -r requirements.txt`"))
    return results


def _run_open3d_subprocess_checks() -> List[CheckResult]:
    """
    Run Open3D checks in a subprocess so we can report segfaults as actionable errors.

    Open3D is a native extension; ABI mismatches (e.g. Open3D 0.18.0 + NumPy 2.x) can crash Python.
    """
    results: List[CheckResult] = []
    if not SAMPLE_PCD.exists():
        results.append(CheckResult(False, f"Sample point cloud missing at {SAMPLE_PCD}.", "Restore data/sample_pointcloud.pcd."))
        return results

    code = r"""
import json
import os
import tempfile
import numpy as np
import open3d as o3d

pc = o3d.geometry.PointCloud()
# Use a non-degenerate point set to avoid QHull failures in OBB computation.
pc.points = o3d.utility.Vector3dVector([
  [0.0, 0.0, 0.0],
  [1.0, 0.0, 0.0],
  [0.0, 1.0, 0.0],
  [0.0, 0.0, 1.0],
  [1.0, 1.0, 0.0],
  [1.0, 0.0, 1.0],
  [0.0, 1.0, 1.0],
  [1.0, 1.0, 1.0],
])
pc.paint_uniform_color([1.0, 0.0, 0.0])
aabb = pc.get_axis_aligned_bounding_box()
obb = pc.get_oriented_bounding_box()

cloud = o3d.io.read_point_cloud(os.environ['AAE5303_SAMPLE_PCD'])
assert not cloud.is_empty()

tmp = tempfile.NamedTemporaryFile(suffix='.pcd', delete=False)
tmp.close()
ok = o3d.io.write_point_cloud(tmp.name, pc, write_ascii=True)
pc2 = o3d.io.read_point_cloud(tmp.name)

payload = {
  'open3d': o3d.__version__,
  'numpy': np.__version__,
  'aabb_extent': list(aabb.get_extent()),
  'obb_extent': list(obb.get_extent()) if hasattr(obb, 'get_extent') else list(getattr(obb, 'extent')),
  'sample_pcd_points': len(cloud.points),
  'write_ok': bool(ok),
  'roundtrip_points': len(pc2.points),
}
print(json.dumps(payload))
"""
    ok, stdout, stderr, rc = _run_python_subprocess(code, env={"AAE5303_SAMPLE_PCD": str(SAMPLE_PCD)})
    if ok:
        payload = _safe_json_last_line(stdout)
        if payload:
            results.append(CheckResult(True, f"Open3D OK (v{payload.get('open3d')}), NumPy {payload.get('numpy')}."))
            results.append(CheckResult(True, f"Open3D loaded sample PCD with {payload.get('sample_pcd_points')} pts and completed round-trip I/O."))
        else:
            results.append(CheckResult(True, "Open3D subprocess check passed (output parsing skipped)."))
        return results

    if rc < 0:
        results.append(
            CheckResult(
                False,
                f"Open3D crashed with signal {signal.Signals(-rc).name} (native extension crash).",
                "Ensure you use Open3D >= 0.19.0 with NumPy 2.x. Prefer a fresh virtualenv and reinstall via `pip install -r requirements.txt`.",
            )
        )
        return results

    results.append(CheckResult(False, f"Open3D subprocess failed: {_format_subprocess_failure(rc, stdout, stderr)}", "Reinstall Open3D: `pip install -r requirements.txt`"))
    return results


def _run_ros_checks() -> List[CheckResult]:
    results: List[CheckResult] = []

    ros2_path = shutil.which("ros2")
    colcon_path = shutil.which("colcon")
    roscore_path = shutil.which("roscore")
    rosversion_path = shutil.which("rosversion")
    rostopic_path = shutil.which("rostopic")
    rosnode_path = shutil.which("rosnode")

    ros2_ok = False
    ros1_ok = False

    # ROS 2: presence + a minimal command check.
    if ros2_path:
        ok, out, err, rc = _run_command([ros2_path, "--help"], timeout_s=6)
        if ok:
            ros2_ok = True
            results.append(CheckResult(True, f"ROS 2 CLI OK: {ros2_path}"))
        else:
            results.append(
                CheckResult(
                    False,
                    f"ROS 2 CLI found but failed (exit {rc}): {err.strip() or out.strip()}",
                    "Re-source ROS 2 in a clean shell: `source /opt/ros/<distro>/setup.bash`",
                )
            )
    else:
        results.append(CheckResult(True, "ROS 2 CLI not found (acceptable if ROS 1 is installed)."))

    # ROS 1: rosversion is the cleanest signal; roscore is a weaker fallback.
    if rosversion_path:
        ok, out, err, rc = _run_command([rosversion_path, "-d"], timeout_s=6)
        if ok:
            ros1_ok = True
            distro = out.strip().splitlines()[-1] if out.strip() else "unknown"
            results.append(CheckResult(True, f"ROS 1 detected: rosversion -d -> {distro}"))
        else:
            results.append(
                CheckResult(
                    False,
                    f"ROS 1 tools found but `rosversion -d` failed (exit {rc}).",
                    "Re-source ROS 1 in a clean shell: `source /opt/ros/noetic/setup.bash`",
                )
            )
    elif roscore_path:
        ros1_ok = True
        results.append(CheckResult(True, "ROS 1 detected: `roscore` found (but `rosversion` missing)."))
    else:
        results.append(CheckResult(True, "ROS 1 tools not found (acceptable if ROS 2 is installed)."))

    # Course policy: at least one ROS version must be available.
    if not _is_ros_requirement_satisfied(ros2_ok=ros2_ok, ros1_ok=ros1_ok):
        results.append(
            CheckResult(
                False,
                "ROS requirement not satisfied: neither ROS 2 nor ROS 1 appears to be installed/working.",
                _ros_install_hint(),
            )
        )
        return results

    # Functional checks (students should "feel" the system works).
    #
    # Policy:
    # - If ROS 2 is detected, we validate colcon and attempt to build + run the course ROS 2 package.
    # - Else if ROS 1 is detected, we attempt to start roscore and query the graph briefly.
    if ros2_ok:
        results.extend(_run_ros2_functional_checks(ros2_path=ros2_path, colcon_path=colcon_path))
    else:
        results.extend(
            _run_ros1_functional_checks(
                roscore_path=roscore_path,
                rostopic_path=rostopic_path,
                rosnode_path=rosnode_path,
                rosversion_path=rosversion_path,
            )
        )

    # Detect common environment conflicts (sourcing ROS 1 + ROS 2 in the same shell).
    ros_version = os.environ.get("ROS_VERSION")
    has_ros1_env = bool(os.environ.get("ROS_ROOT")) or bool(os.environ.get("ROS_PACKAGE_PATH"))
    has_ros2_env = bool(os.environ.get("AMENT_PREFIX_PATH")) or bool(os.environ.get("COLCON_PREFIX_PATH"))
    if has_ros1_env and has_ros2_env:
        results.append(
            CheckResult(
                True,
                "Warning: both ROS 1 and ROS 2 environment variables are set (mixed environment).",
                "Use a fresh terminal and source only one of ROS 1 or ROS 2 before building/running.",
            )
        )
    if ros_version == "1" and ros2_path:
        results.append(CheckResult(True, "Warning: ROS_VERSION=1 but `ros2` is on PATH.", "Source ROS 2 in a clean shell: `source /opt/ros/<distro>/setup.bash`"))
    if ros_version == "2" and roscore_path:
        results.append(CheckResult(True, "Warning: ROS_VERSION=2 but ROS 1 tools are on PATH.", "Avoid sourcing ROS 1 and ROS 2 together in the same shell."))

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


def _run_command(
    cmd: Sequence[str],
    timeout_s: float,
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> tuple[bool, str, str, int]:
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
            cwd=cwd,
            env=env,
        )
    except FileNotFoundError:
        return False, "", f"Command not found: {cmd[0]}", 127
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout_s:.1f}s: {' '.join(cmd)}", 124
    return p.returncode == 0, (p.stdout or ""), (p.stderr or ""), p.returncode


def _run_python_subprocess(code: str, env: dict[str, str] | None = None) -> tuple[bool, str, str, int]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    try:
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30, check=False, env=merged_env)
    except subprocess.TimeoutExpired:
        return False, "", "Python subprocess timed out after 30.0s", 124
    return p.returncode == 0, (p.stdout or ""), (p.stderr or ""), p.returncode


def _safe_json_last_line(stdout: str) -> dict | None:
    lines = [ln for ln in (stdout or "").splitlines() if ln.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except Exception:
        return None


def _format_subprocess_failure(return_code: int, stdout: str, stderr: str) -> str:
    if return_code < 0:
        try:
            sig = signal.Signals(-return_code).name
        except Exception:
            sig = f"SIG{-return_code}"
        return f"terminated by {sig}"
    msg = (stderr or "").strip() or (stdout or "").strip()
    return msg if msg else f"exit code {return_code}"


def _run_step_one(step: int, title: str, why: str, fn) -> List[CheckResult]:
    print(f"Step {step}: {title}", flush=True)
    print(f"  Why: {why}", flush=True)
    try:
        return [fn()]
    except Exception as exc:
        return [CheckResult(False, f"{title} raised an unexpected exception: {exc}", "Please report this output to the teaching team.")]


def _run_step_many(step: int, title: str, why: str, fn) -> List[CheckResult]:
    print(f"Step {step}: {title}", flush=True)
    print(f"  Why: {why}", flush=True)
    try:
        return list(fn())
    except Exception as exc:
        return [CheckResult(False, f"{title} raised an unexpected exception: {exc}", "Please report this output to the teaching team.")]


def _colcon_install_hint() -> str:
    """
    Provide a robust, student-friendly installation hint for colcon.

    Students may run on Ubuntu, WSL2, Docker, or minimal base images.
    The apt package name exists on Ubuntu repositories, but may not exist on Debian/minimal images.
    """
    osr = _read_os_release()
    distro_id = (osr.get("ID") or "").lower()
    distro_like = (osr.get("ID_LIKE") or "").lower()
    is_ubuntu_like = "ubuntu" in distro_id or "ubuntu" in distro_like

    if is_ubuntu_like:
        return (
            "On Ubuntu/WSL2:\n"
            "  - sudo apt update\n"
            "  - sudo apt install python3-colcon-common-extensions\n"
            "If apt says 'Unable to locate package python3-colcon-common-extensions', enable the Ubuntu 'universe' repository and retry:\n"
            "  - sudo apt install -y software-properties-common\n"
            "  - sudo add-apt-repository universe\n"
            "  - sudo apt update\n"
            "  - sudo apt install python3-colcon-common-extensions\n"
            "If you are inside a minimal container with trimmed apt sources, you can also use pip:\n"
            "  - python -m pip install -U colcon-common-extensions"
        )

    return (
        "You are not on an Ubuntu apt repository (common in Docker/minimal images). Try one of:\n"
        "  - python -m pip install -U colcon-common-extensions\n"
        "  - Or install ROS 2 properly (recommended) so colcon is available in the OS environment."
    )


def _read_os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    if not path.exists():
        return {}
    data: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"')
            data[k.strip()] = v
    except Exception:
        return {}
    return data


def _is_ros_requirement_satisfied(*, ros2_ok: bool, ros1_ok: bool) -> bool:
    """
    Course policy: ROS 2 OR ROS 1 is acceptable.
    """
    return bool(ros2_ok or ros1_ok)


def _ros_install_hint() -> str:
    """
    Provide a high-signal hint without assuming the OS package manager works.
    """
    return (
        "Install either ROS 2 (recommended) or ROS 1, then open a new terminal and source it:\n"
        "  - ROS 2 (Humble): source /opt/ros/humble/setup.bash\n"
        "  - ROS 1 (Noetic): source /opt/ros/noetic/setup.bash\n"
        "If you are in a container/VM, ensure you followed the official installation guide and that the binaries are on PATH."
    )


def _enable_line_buffering() -> None:
    """
    Reduce confusing output reordering caused by stdout buffering.
    """
    try:
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass


def _run_ros2_functional_checks(*, ros2_path: str | None, colcon_path: str | None) -> List[CheckResult]:
    """
    Validate ROS 2 is usable by actually building and running the course package.

    We do not rely on demo packages being installed. Instead we build `ros2_ws/src/env_check_pkg`
    and then run `ros2 launch` for a short period and verify output patterns.
    """
    results: List[CheckResult] = []
    _ = ros2_path  # present by construction; keep signature explicit for clarity.

    if not colcon_path:
        results.append(CheckResult(False, "colcon not found on PATH (required for ROS 2 builds).", _colcon_install_hint()))
        return results
    results.append(CheckResult(True, f"colcon found: {colcon_path}"))

    if not ROS2_WS.exists():
        results.append(CheckResult(False, f"ROS 2 workspace not found: {ROS2_WS}", "Re-clone the repo or ensure ros2_ws/ exists."))
        return results

    if os.environ.get("ROS_VERSION") != "2":
        results.append(
            CheckResult(
                False,
                "ROS 2 detected on PATH but ROS 2 environment does not appear to be sourced (ROS_VERSION != 2).",
                "Open a new terminal and run: `source /opt/ros/humble/setup.bash` then re-run this test.",
            )
        )
        return results

    print("  Action: building ROS 2 workspace package `env_check_pkg` (this may take 1-3 minutes on first run)...")
    build_cmd = [colcon_path, "build", "--packages-select", "env_check_pkg"]
    ok, out, err, rc = _run_command(build_cmd, timeout_s=300, cwd=str(ROS2_WS))
    if not ok:
        results.append(CheckResult(False, f"ROS 2 workspace build failed (exit {rc}).", "Fix build errors, then retry. Hint: `rm -rf build install log` in ros2_ws/ can help."))
        return results
    results.append(CheckResult(True, "ROS 2 workspace build OK (env_check_pkg)."))

    # Run launch for a short time and validate expected output strings.
    print("  Action: running ROS 2 talker/listener for a few seconds to verify messages flow...")
    distro = os.environ.get("ROS_DISTRO") or "humble"
    launch_cmd = ["bash", "-lc", f"source /opt/ros/{distro}/setup.bash && source install/setup.bash && ros2 launch env_check_pkg env_check.launch.py"]
    ok, lines = _run_process_collect_output(
        launch_cmd,
        cwd=str(ROS2_WS),
        timeout_s=8.0,
    )
    talker_ok = any("Publishing:" in ln for ln in lines)
    listener_ok = any("I heard:" in ln for ln in lines)
    if ok and talker_ok and listener_ok:
        results.append(CheckResult(True, "ROS 2 runtime OK: talker and listener exchanged messages."))
        return results

    # Provide a compact failure summary.
    tail = "\n".join(lines[-20:])
    results.append(
        CheckResult(
            False,
            "ROS 2 runtime check failed: could not confirm talker/listener message exchange.",
            "Re-run after sourcing ROS 2. If it still fails, run manually:\n"
            "  cd ros2_ws && source /opt/ros/humble/setup.bash && colcon build --packages-select env_check_pkg\n"
            "  source install/setup.bash && ros2 launch env_check_pkg env_check.launch.py\n\n"
            f"Last output lines:\n{tail}",
        )
    )
    return results


def _run_ros1_functional_checks(
    *,
    roscore_path: str | None,
    rostopic_path: str | None,
    rosnode_path: str | None,
    rosversion_path: str | None,
) -> List[CheckResult]:
    """
    Validate ROS 1 is usable by starting a ROS master briefly and querying the graph.
    """
    results: List[CheckResult] = []
    if not roscore_path:
        results.append(CheckResult(False, "ROS 1 detected but `roscore` not found.", "Install ROS 1 (Noetic) and source it: `source /opt/ros/noetic/setup.bash`"))
        return results

    if not rosnode_path and not rostopic_path:
        results.append(
            CheckResult(
                False,
                "ROS 1 tools incomplete: neither `rosnode` nor `rostopic` was found on PATH.",
                "Install the full ROS 1 desktop/base and source it: `source /opt/ros/noetic/setup.bash`",
            )
        )
        return results

    if os.environ.get("ROS_VERSION") == "2":
        results.append(CheckResult(True, "Warning: ROS_VERSION=2 in current shell; ROS 1 may not be sourced."))

    distro = None
    if rosversion_path:
        ok, out, _err, _rc = _run_command([rosversion_path, "-d"], timeout_s=6)
        if ok:
            distro = out.strip().splitlines()[-1] if out.strip() else None
    if distro:
        results.append(CheckResult(True, f"ROS 1 distro: {distro}"))

    print("  Action: starting roscore briefly and probing the ROS graph (rosnode/rostopic)...")
    ok, roscore_lines = _run_roscore_and_probe(
        roscore_path=roscore_path,
        rosnode_path=rosnode_path,
        rostopic_path=rostopic_path,
    )
    if ok:
        results.append(CheckResult(True, "ROS 1 runtime OK: roscore started and graph queries succeeded."))
        return results

    tail = "\n".join(roscore_lines[-30:])
    results.append(
        CheckResult(
            False,
            "ROS 1 runtime check failed: could not start roscore or query the ROS graph.",
            "Try in a fresh terminal:\n"
            "  source /opt/ros/noetic/setup.bash\n"
            "  roscore\n"
            "Then in another terminal:\n"
            "  rosnode list\n"
            "  rostopic list\n\n"
            f"Last output lines:\n{tail}",
        )
    )
    return results


def _run_process_collect_output(cmd: Sequence[str], *, cwd: str, timeout_s: float) -> tuple[bool, list[str]]:
    """
    Run a subprocess, collect stdout/stderr lines for a short duration, then terminate.
    """
    lines: list[str] = []
    try:
        p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except Exception as exc:
        return False, [f"Failed to start process: {exc}"]

    try:
        try:
            out, _ = p.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            try:
                p.terminate()
            except Exception:
                pass
            try:
                out, _ = p.communicate(timeout=3)
            except Exception:
                out = ""
        if out:
            lines.extend([ln for ln in out.splitlines() if ln.strip()])
    finally:
        if p.poll() is None:
            try:
                p.kill()
            except Exception:
                pass

    # We treat "process started" as ok, but callers decide based on output signals.
    return True, lines


def _run_roscore_and_probe(
    *,
    roscore_path: str,
    rosnode_path: str | None,
    rostopic_path: str | None,
) -> tuple[bool, list[str]]:
    """
    Start roscore for a short time and probe the ROS graph.
    """
    lines: list[str] = []
    cmd = [roscore_path]
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except Exception as exc:
        return False, [f"Failed to start roscore: {exc}"]

    try:
        # Give roscore time to start.
        time.sleep(2.0)
        if p.poll() is not None:
            out = ""
            if p.stdout is not None:
                try:
                    out = p.stdout.read() or ""
                except Exception:
                    out = ""
            lines.extend([ln for ln in out.splitlines() if ln.strip()])
            return False, lines

        # Probe using rosnode/rostopic.
        if rosnode_path:
            ok, out, err, rc = _run_command([rosnode_path, "list"], timeout_s=6)
            lines.extend((out or "").splitlines())
            lines.extend((err or "").splitlines())
            if ok and "/rosout" in out:
                return True, lines

        if rostopic_path:
            ok, out, err, rc = _run_command([rostopic_path, "list"], timeout_s=6)
            lines.extend((out or "").splitlines())
            lines.extend((err or "").splitlines())
            if ok:
                return True, lines

        # If we got here, graph probing was not successful.
        return False, lines
    finally:
        try:
            p.terminate()
        except Exception:
            pass
        try:
            p.wait(timeout=3)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())

