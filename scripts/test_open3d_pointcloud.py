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
        print(f"❌ Required module missing: {exc.name}. Run `pip install -r requirements.txt`.")
        return 1

    source = _get_sample_pcd_path()
    if not source.exists():
        print(f"❌ Point cloud not found at {source}.")
        return 1

    print(f"ℹ️ Loading {source} ...")
    cloud = o3d.io.read_point_cloud(str(source))
    if cloud.is_empty():
        print("❌ Loaded cloud is empty; Open3D I/O may be broken.")
        return 1

    pts = np.asarray(cloud.points)
    _print_cloud_stats(pts)

    filtered = _filter_and_colorize(o3d, pts)
    target = source.with_name("sample_pointcloud_copy.pcd")
    if not _write_and_verify(o3d, filtered, target):
        return 1

    _print_bounding_boxes(filtered)
    print("🎉 Open3D point cloud pipeline looks good.")
    return 0


def _get_sample_pcd_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "data" / "sample_pointcloud.pcd"


def _print_cloud_stats(pts) -> None:
    centroid = pts.mean(axis=0)
    mins = pts.min(axis=0)
    maxs = pts.max(axis=0)
    print(f"✅ Loaded {len(pts)} points.")
    print(f"   • Centroid: {centroid}")
    print(f"   • Axis-aligned bounds: min={mins}, max={maxs}")


def _filter_and_colorize(o3d, pts):
    """
    Create a filtered point cloud to exercise downstream Open3D operations.
    """
    # Filter out points close to origin to ensure downstream ops work
    mask = (pts**2).sum(axis=1) > 0.0005
    kept = pts[mask]

    filtered = o3d.geometry.PointCloud()
    filtered.points = o3d.utility.Vector3dVector(kept)
    filtered.paint_uniform_color([1.0, 0.0, 0.0])
    print(f"✅ Filtered point cloud kept {len(kept)} points.")
    return filtered


def _write_and_verify(o3d, cloud, target: Path) -> bool:
    ok = o3d.io.write_point_cloud(str(target), cloud, write_ascii=True)
    if not ok:
        print(f"❌ Failed to write point cloud to {target}.")
        return False
    reloaded = o3d.io.read_point_cloud(str(target))
    if reloaded.is_empty():
        print(f"❌ Wrote {target} but reloading produced an empty cloud.")
        return False
    print(f"✅ Wrote filtered copy with {len(reloaded.points)} points to {target}")
    return True


def _print_bounding_boxes(cloud) -> None:
    aabb = cloud.get_axis_aligned_bounding_box()
    obb = cloud.get_oriented_bounding_box()

    aabb_extent = aabb.get_extent()
    obb_extent = obb.get_extent() if hasattr(obb, "get_extent") else obb.extent
    max_dim = float(max(obb_extent))

    print(f"   • AABB extents: {aabb_extent}")
    print(f"   • OBB  extents: {obb_extent}, max dim {max_dim:.4f} m")


if __name__ == "__main__":
    sys.exit(main())

