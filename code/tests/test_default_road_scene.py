"""验证默认三维道路 DAS + 锤击场景几何。"""

import json

import pytest

from hcz_road_void.visualization import plot_geometry_3d
from main import build_stage1_scene, run


def test_default_scene_uses_opposite_road_sides_for_fiber_and_sources() -> None:
    scene = build_stage1_scene()
    road_width_m = scene["road_width_m"]
    receiver_polyline = scene["receiver_polyline"]
    sampled_receivers = scene["sampled_receivers"]
    source_xyz = scene["source_xyz"]

    assert scene["road_length_m"] == pytest.approx(80.0)
    assert road_width_m == pytest.approx(15.0)
    assert all(point.y == pytest.approx(0.0) for point in receiver_polyline.points)
    assert all(receiver.y == pytest.approx(0.0) for receiver in sampled_receivers.receivers)
    assert all(source.y == pytest.approx(road_width_m) for source in source_xyz)
    assert all(source.depth == pytest.approx(0.0) for source in source_xyz)


def test_default_void_is_road_center_shallow_and_search_grid_covers_it() -> None:
    scene = build_stage1_scene()
    road_width_m = scene["road_width_m"]
    void_xyz = scene["void_model"].void_xyz
    search_grid = scene["search_grid"]

    assert void_xyz.xyz == pytest.approx((40.0, 7.5, 2.0))
    assert 0.0 < void_xyz.y < road_width_m
    assert void_xyz.y != pytest.approx(0.0)
    assert void_xyz.y != pytest.approx(road_width_m)
    assert search_grid.search_y[0] == pytest.approx(0.0)
    assert search_grid.search_y[-1] == pytest.approx(road_width_m)
    assert search_grid.search_depth[0] <= void_xyz.depth <= search_grid.search_depth[-1]
    assert search_grid.shape == (31, 31, 19)


def test_main_summary_records_default_road_geometry(tmp_path) -> None:
    summary = run(output_dir=tmp_path, quiet=True)
    summary_path = tmp_path / "run_summary.json"
    loaded = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["road_length_m"] == pytest.approx(80.0)
    assert loaded["road_width_m"] == pytest.approx(15.0)
    assert loaded["fiber_y_m"] == pytest.approx(0.0)
    assert loaded["source_y_m"] == pytest.approx(15.0)
    assert loaded["true_void_xyz"] == pytest.approx([40.0, 7.5, 2.0])
    assert loaded["void_radius_m"] == pytest.approx(1.0)
    assert loaded["search_x_range_m"] == pytest.approx([25.0, 55.0])
    assert loaded["search_y_range_m"] == pytest.approx([0.0, 15.0])
    assert loaded["search_depth_range_m"] == pytest.approx([0.5, 5.0])


def test_geometry_plot_handles_default_road_layout(tmp_path) -> None:
    scene = build_stage1_scene()
    output_path = tmp_path / "geometry_3d.png"
    plot_geometry_3d(
        output_path,
        source_xyz=scene["source_xyz"],
        receiver_polyline=scene["receiver_polyline"].points,
        receiver_xyz=scene["sampled_receivers"].receivers,
        true_void_xyz=scene["void_model"].void_xyz,
        void_radius_m=scene["void_model"].void_radius_m,
        road_length_m=scene["road_length_m"],
        road_width_m=scene["road_width_m"],
        fiber_y_m=scene["fiber_y_m"],
        source_y_m=scene["source_y_m"],
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0
