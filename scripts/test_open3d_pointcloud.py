#!/usr/bin/env python3
"""
Validate Open3D can load and manipulate the bundled sample point cloud.

Run: `python scripts/test_open3d_pointcloud.py`
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    try:
        import numpy as np
        import open3d as o3d
    except ModuleNotFoundError as exc:
        print(f"❌ Required module missing: {exc.name}. Run `pip install open3d numpy`.")
        return 1

    root = Path(__file__).resolve().parents[1]
    source = root / "data" / "sample_pointcloud.pcd"
    if not source.exists():
        print(f"❌ Point cloud not found at {source}.")
        return 1

    print(f"ℹ️ Loading {source} ...")
    cloud = o3d.io.read_point_cloud(str(source))
    if cloud.is_empty():
        print("❌ Loaded cloud is empty; Open3D I/O may be broken.")
        return 1

    pts = np.asarray(cloud.points)
    centroid = pts.mean(axis=0)
    mins = pts.min(axis=0)
    maxs = pts.max(axis=0)

    print(f"✅ Loaded {len(pts)} points.")
    print(f"   • Centroid: {centroid}")
    print(f"   • Axis-aligned bounds: min={mins}, max={maxs}")

    # Filter out points close to origin to ensure downstream ops work
    mask = (pts ** 2).sum(axis=1) > 0.0005
    kept = pts[mask]
    filtered = o3d.geometry.PointCloud()
    filtered.points = o3d.utility.Vector3dVector(kept)
    filtered.paint_uniform_color([1, 0, 0])
    target = source.with_name("sample_pointcloud_copy.pcd")
    o3d.io.write_point_cloud(str(target), filtered, write_ascii=True)
    print(f"✅ Wrote filtered copy with {len(kept)} points to {target}")

    bbox = filtered.get_oriented_bounding_box()
    diam = bbox.extent.max()
    print(f"   • Oriented bbox extents: {bbox.extent}, max dim {diam:.4f} m")
    print("🎉 Open3D point cloud pipeline looks good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

