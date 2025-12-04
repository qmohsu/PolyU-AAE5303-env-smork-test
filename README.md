# AAE5303 Environment Check

This repository is a **single command post** for verifying that your Ubuntu + ROS 2 + Python toolchain is ready for AAE5303. If you can:

1. Run the Python smoke tests inside `scripts/`; and
2. Build + launch the ROS 2 talker/listener inside `ros2_ws/`;

…then you have everything we need for the coursework.

---

## Repository layout

```
aae5303-env-check/
├── README.md
├── data/
│   ├── sample_image.png
│   └── sample_pointcloud.pcd
├── ros2_ws/
│   └── src/
│       └── env_check_pkg/
│           ├── CMakeLists.txt
│           ├── launch/
│           │   └── env_check.launch.py
│           ├── package.xml
│           └── src/
│               ├── listener.cpp
│               └── talker.cpp
└── scripts/
    ├── test_open3d_pointcloud.py
    └── test_python_env.py
```

---

## 1. Prerequisites

| Component | Version | Installation hint |
|-----------|---------|-------------------|
| Ubuntu | 22.04 LTS | Native, dual‑boot, WSL2, or VM |
| ROS 2 | Humble (desktop) | Follow the [ROS 2 Humble guide](https://docs.ros.org/en/humble/Installation.html) |
| Python | 3.10+ | Ships with Ubuntu 22.04 |
| Build tools | `colcon`, `clang`/`gcc`, `cmake` | `sudo apt install build-essential cmake python3-colcon-common-extensions` |
| Python packages | `numpy`, `scipy`, `matplotlib`, `open3d`, `opencv-python` | `pip install -r requirements.txt` *(or install manually)* |

> ⚠️ The repo **does not** install ROS 2 or Python dependencies automatically. Install them first, then return here.

---

## 2. Python smoke tests

### 2.1 Create (optional) virtual environment

```bash
cd ~/aae5303-env-check
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install numpy scipy matplotlib open3d opencv-python
```

### 2.2 Validate the interpreter + packages

```bash
python scripts/test_python_env.py
```

What the script does:

- Ensures Python ≥ 3.10.
- Checks `numpy`, `scipy`, `matplotlib`, `opencv-python`, `open3d`, and (optionally) `rclpy`.
- Runs small computations (matrix multiply, FFT, random plotting backend check) so imports are not the only signal.
- Verifies that CLI tooling such as `ros2` and `colcon` is on your `$PATH`.
- Loads `data/sample_image.png` via OpenCV to catch codec issues.

You should see **“All checks passed”**. Any failure prints a remediation hint and the script exits with a non-zero code.

### 2.3 Validate Open3D I/O with a real point cloud

```bash
python scripts/test_open3d_pointcloud.py
```

This script uses `open3d.io.read_point_cloud` to load `data/sample_pointcloud.pcd`, computes bounding boxes and centroid statistics, and writes a filtered copy to `data/sample_pointcloud_copy.pcd`. It is modeled after the official Open3D I/O examples and ensures both the Python binding and shared libraries are functional.

---

## 3. ROS 2 talker/listener workspace

1. **Setup environment**

   ```bash
   cd ~/aae5303-env-check/ros2_ws
   source /opt/ros/humble/setup.bash
   ```

2. **Build**

   ```bash
   colcon build --packages-select env_check_pkg
   ```

3. **Source workspace**

   ```bash
   source install/setup.bash
   ```

4. **Launch both nodes**

   ```bash
   ros2 launch env_check_pkg env_check.launch.py
   ```

Expected terminal output:

- `env_check_pkg_talker` logs `Publishing: "AAE5303 hello #<n>"` at 2 Hz.
- `env_check_pkg_listener` logs `I heard: "AAE5303 hello #<n>"`.

Stop with `Ctrl+C`. If you prefer separate terminals, run `ros2 run env_check_pkg talker` and `ros2 run env_check_pkg listener`.

---

## 4. Troubleshooting

- **Missing Python packages**: activate your virtual environment (if any) and rerun `pip install ...`. The smoke tests re-print helpful `pip install` commands for every missing module.
- **`ros2` or `colcon` not found**: ensure `/opt/ros/humble/bin` is on your `PATH` (add `source /opt/ros/humble/setup.bash` to your shell profile).
- **Build errors**: delete the workspace build artifacts (`rm -rf build install log`) and rebuild after sourcing ROS 2.
- **Open3D cannot load shared library**: install from pip wheels (`pip install open3d==0.18.0`) or from apt if available. Refer to the [Open3D installation guide](https://www.open3d.org/docs/release/getting_started.html).

If your results differ from the expectations above, capture the full console output and reach out on the course forum—we can help interpret the failure signal.

