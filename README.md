# AAE5303 Environment Check (ROS + Python)

This repository is a **single command post** for verifying that your Ubuntu + ROS 2 + Python toolchain is ready for AAE5303. If you can:

The goal is not only to detect missing dependencies, but to run **real, functional smoke tests** so students can see what “a working environment” looks like.

If you can:

1. Run the one-command smoke tests in `scripts/`; and
2. Build + run the ROS 2 talker/listener package in `ros2_ws/`;

then your machine is ready for the coursework.

---

## Who should use this repo

- Students: run the one-command smoke tests and fix anything that fails **before** starting the labs.
- Teaching staff: use this as a standardized checklist to diagnose student setup issues.

---

## Repository layout

```
aae5303-env-check/
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   ├── sample_image.png
│   └── sample_pointcloud.pcd
├── ros2_ws/
│   └── src/
│       └── env_check_pkg/
│           ├── CMakeLists.txt
│           ├── package.xml
│           ├── launch/
│           │   └── env_check.launch.py
│           └── src/
│               ├── talker.cpp
│               └── listener.cpp
└── scripts/
    ├── run_smoke_tests.py
    ├── test_python_env.py
    └── test_open3d_pointcloud.py
```

---

## Supported environments

This repo is designed for:

- Ubuntu 22.04 (native or WSL2)
- Python 3.10+
- ROS 2 Humble (recommended) **or** ROS 1 Noetic (acceptable)

Notes:

- If you are using Docker/minimal images, ROS installation and apt repositories may differ. Read the troubleshooting section.
- If you have both ROS 1 and ROS 2 installed, do **not** source them in the same shell.

---

## Prerequisites (system-level)

### Ubuntu packages (recommended)

```bash
sudo apt update
sudo apt install -y build-essential cmake
```

### ROS installation (required: ROS 2 or ROS 1)

You must have at least one of the following installed and sourced correctly:

- ROS 2 Humble: see the official [ROS 2 Humble installation guide](https://docs.ros.org/en/humble/Installation.html)
- ROS 1 Noetic: see the official [ROS 1 Noetic installation guide](https://wiki.ros.org/noetic/Installation/Ubuntu)

This repo intentionally validates ROS **functionally**:

- ROS 2: build and run the course talker/listener package
- ROS 1: start `roscore` and query the ROS graph (`rosnode`/`rostopic`)

---

## Python dependencies (NumPy 2.x route)

This repository intentionally targets **NumPy 2.x**.

Why:

- Students often have NumPy 2.x installed already (newer Python environments).
- Open3D 0.18.0 + NumPy 2.x is a common cause of native crashes (segfaults).
- Open3D 0.19.0 adds official NumPy 2.x support.

Therefore, `requirements.txt` pins:

- `numpy>=2,<3`
- `open3d==0.19.0`

---

## Quick start (recommended workflow)

### Step 1: Create and activate a virtual environment

```bash
cd ~/aae5303-env-check
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### Step 2: Install Python requirements

```bash
python -m pip install -r requirements.txt
```

### Step 3: Run the one-command smoke test suite

```bash
python scripts/run_smoke_tests.py
```

Expected result:

- **OVERALL RESULT: PASS**
- If anything fails, the output includes an actionable remediation hint.

Important:

- The runner cleans up small generated files in `data/` automatically.
- If ROS is not installed or not sourced, the suite will fail (by design).

---

## What the tests do (detailed)

### `scripts/run_smoke_tests.py`

This is the recommended entry point for students. It:

- runs each test script in a subprocess (so native crashes are reported as readable failures)
- prints step headers, command lines, and timing
- prints a final **OVERALL RESULT: PASS/FAIL**
- cleans up generated artifacts

### `scripts/test_python_env.py`

This script runs a **teaching-oriented, step-by-step report**. It intentionally keeps running after failures so you get a full diagnostic summary.

It checks:

1. Environment snapshot (platform, Python, key ROS environment variables)
2. Python version (must be ≥ 3.10)
3. Python imports:
   - required: `numpy`, `scipy`, `matplotlib`, `opencv-python`
   - optional: `rclpy` (useful for ROS 2 Python exercises)
4. NumPy computation sanity check
5. SciPy FFT sanity check
6. Matplotlib headless backend check (writes a tiny image)
7. OpenCV PNG decode test (subprocess; validates `data/sample_image.png`)
8. Open3D native-extension test (subprocess; validates:
   - basic geometry operations
   - point cloud I/O with `data/sample_pointcloud.pcd`
9. ROS toolchain checks (functional):
   - If ROS 2 is detected:
     - require `colcon`
     - build `ros2_ws/` package `env_check_pkg`
     - run `ros2 launch env_check_pkg env_check.launch.py` briefly
     - verify talker/listener exchanged messages (looks for `Publishing:` and `I heard:`)
   - Else if ROS 1 is detected:
     - start `roscore` briefly
     - probe the ROS graph using `rosnode list` and/or `rostopic list`
10. Basic CLI checks (e.g. `python3`)

### `scripts/test_open3d_pointcloud.py`

This script validates Open3D I/O + geometry using a real PCD file:

- reads `data/sample_pointcloud.pcd`
- computes centroid and axis-aligned bounds
- filters points and writes `data/sample_pointcloud_copy.pcd`
- reloads the file and computes bounding boxes

---

## ROS 2 workspace: manual build + run (recommended for learning)

Run in a clean shell where ROS 2 is sourced:

```bash
cd ~/aae5303-env-check/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select env_check_pkg
source install/setup.bash
ros2 launch env_check_pkg env_check.launch.py
```

What you should see:

- talker prints `Publishing: 'AAE5303 hello #<n>'` at ~2 Hz
- listener prints `I heard: 'AAE5303 hello #<n>'`

---

## Passing criteria (for students)

You pass the environment check only if:

- `python scripts/run_smoke_tests.py` ends with **OVERALL RESULT: PASS**

This implies:

- Python scientific stack is installed and functional
- OpenCV can decode PNGs
- Open3D works with NumPy 2.x (no segfaults)
- At least one ROS toolchain (ROS 2 or ROS 1) is installed and usable

---

## Common pitfalls and fixes (very common student issues)

### Mixed ROS 1 and ROS 2 in the same shell

Do **not** source ROS 1 and ROS 2 in the same terminal session.

Fix:

1. Open a new terminal.
2. Source exactly one:
   - ROS 2: `source /opt/ros/humble/setup.bash`
   - ROS 1: `source /opt/ros/noetic/setup.bash`

### `colcon` not found

If ROS 2 is your toolchain, `colcon` is required.

Ubuntu/WSL2:

```bash
sudo apt update
sudo apt install python3-colcon-common-extensions
```

If apt says `Unable to locate package python3-colcon-common-extensions`, enable the Ubuntu `universe` repository:

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository universe
sudo apt update
sudo apt install python3-colcon-common-extensions
```

Docker/minimal images:

```bash
python -m pip install -U colcon-common-extensions
```

### Open3D segfaults

This is almost always an ABI mismatch (e.g., old Open3D with NumPy 2.x).

Fix:

1. Create a fresh venv.
2. Reinstall requirements:

```bash
python -m pip install -r requirements.txt
```

---

## Teaching staff checklist

Ask students to paste the full output of:

```bash
python scripts/run_smoke_tests.py
```

Do not accept partial screenshots; the full output is the fastest way to diagnose:

- missing ROS installation vs not-sourced environment
- ABI issues (native crashes) vs Python import issues
- workspace build failures vs runtime message exchange failures

