"""Stage 2A 波动方程正演过渡接口测试。

这些测试不要求 Devito 或 OpenSWPC 已安装。目标是保证当前项目在缺少外部
大型正演工具时仍能稳定运行，并且体异常、速度网格和波场接口已经具备
后续接入真实三维正演后端的最小骨架。
"""

from pathlib import Path

import numpy as np
import pytest

from hcz_road_void.forward import DevitoBackend, KinematicDiffractionBackend, OpenSWPCBackend
from hcz_road_void.models import (
    VoidBody3D,
    build_uniform_road_velocity_grid,
    embed_void_body_into_velocity_grid,
    sample_void_body_as_scatterers,
)
from hcz_road_void.visualization import (
    ensure_wavefield_output_dir,
    plot_velocity_model_slices,
    unavailable_wavefield_snapshots,
)
from main import build_stage1_scene, run


def test_forward_backend_availability_and_metadata_are_stable() -> None:
    kinematic = KinematicDiffractionBackend()
    devito = DevitoBackend()
    openswpc = OpenSWPCBackend(executable_path="definitely_missing_swpc_3d.x")

    assert kinematic.is_available() is True
    assert isinstance(devito.is_available(), bool)
    assert openswpc.is_available() is False

    metadata = kinematic.metadata()
    for key in [
        "backend_name",
        "physics_type",
        "is_wave_equation_solver",
        "is_elastic_solver",
        "supports_wavefield_snapshots",
        "supports_das_strain",
        "approximation",
    ]:
        assert key in metadata
    assert metadata["backend_name"] == "kinematic"
    assert metadata["is_wave_equation_solver"] is False


def test_main_summary_records_stage2a_backend_fields(tmp_path) -> None:
    summary = run(output_dir=tmp_path, quiet=True)

    assert summary["backend_name"] == "kinematic"
    assert summary["physics_type"] == "kinematic_diffraction"
    assert summary["is_wave_equation_solver"] is False
    assert summary["is_elastic_solver"] is False
    assert summary["void_representation"] == "point_or_body_proxy"
    assert summary["localization_accuracy_is_primary_metric"] is False
    assert summary["wavefield_snapshot_type"] == "not_available"
    assert (tmp_path / "velocity_model_3d.npz").exists()
    assert (tmp_path / "velocity_model_slices.png").exists()
    assert (tmp_path / "wavefield_snapshots").is_dir()


def test_required_stage2a_documents_exist() -> None:
    docs = Path("docs")
    for name in [
        "TOOLS_DEEP_DIVE.md",
        "DEVITO_INTEGRATION_NOTES.md",
        "OPENSWPC_INTEGRATION_NOTES.md",
        "STAGE2_WAVE_EQUATION_FORWARD_PLAN.md",
        "VOID_BODY_MODEL.md",
        "FORWARD_OUTPUTS.md",
    ]:
        path = docs / name
        assert path.exists()
        assert path.stat().st_size > 0


def test_void_body_supports_sphere_and_ellipsoid() -> None:
    sphere = VoidBody3D(
        center_xyz=(40.0, 7.5, 2.0),
        body_type="sphere",
        size_xyz_m=(2.0, 2.0, 2.0),
        velocity_scale=0.5,
    )
    ellipsoid = VoidBody3D(
        center_xyz=(40.0, 7.5, 2.0),
        body_type="ellipsoid",
        size_xyz_m=(2.0, 2.0, 1.0),
        velocity_scale=0.5,
    )

    assert sphere.body_type.value == "sphere"
    assert ellipsoid.body_type.value == "ellipsoid"
    assert sphere.contains_xyz(np.array([[40.0, 7.5, 2.0]])).item() is True
    assert ellipsoid.contains_xyz(np.array([[40.0, 7.5, 2.0]])).item() is True


def test_void_body_rejects_invalid_size_and_velocity_scale() -> None:
    with pytest.raises(ValueError, match="尺寸"):
        VoidBody3D(center_xyz=(0.0, 0.0, 1.0), body_type="ellipsoid", size_xyz_m=(1.0, -1.0, 1.0), velocity_scale=0.5)
    with pytest.raises(ValueError, match="velocity_scale"):
        VoidBody3D(center_xyz=(0.0, 0.0, 1.0), body_type="sphere", size_xyz_m=(1.0, 1.0, 1.0), velocity_scale=0.0)


def test_void_body_embedding_and_scatterer_sampling() -> None:
    void_body = VoidBody3D(
        center_xyz=(4.0, 2.0, 1.0),
        body_type="ellipsoid",
        size_xyz_m=(2.0, 2.0, 1.0),
        velocity_scale=0.5,
    )
    grid = build_uniform_road_velocity_grid(
        road_length_m=8.0,
        road_width_m=4.0,
        max_depth_m=3.0,
        spacing_m=0.5,
        background_vp_mps=1000.0,
    )
    embedded = embed_void_body_into_velocity_grid(grid, void_body)
    scatterers = sample_void_body_as_scatterers(void_body, spacing_m=0.5)

    assert embedded.vp_mps.shape == grid.vp_mps.shape
    assert np.min(embedded.vp_mps) == pytest.approx(500.0)
    assert embedded.metadata["contains_void_body"] is True
    assert len(scatterers) > 1
    assert all(scatterer.depth >= 0.0 for scatterer in scatterers)


def test_velocity_model_slice_plot_runs(tmp_path) -> None:
    scene = build_stage1_scene()
    output_path = tmp_path / "velocity_model_slices.png"
    plot_velocity_model_slices(
        output_path,
        velocity_grid=scene["velocity_grid"],
        x_m=scene["void_model"].void_xyz.x,
        y_m=scene["void_model"].void_xyz.y,
        depth_m=scene["void_model"].void_xyz.depth,
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_wavefield_snapshot_interface_handles_unavailable_backend(tmp_path) -> None:
    output_dir = ensure_wavefield_output_dir(tmp_path / "wavefield_snapshots")
    result = unavailable_wavefield_snapshots("kinematic")

    assert output_dir.is_dir()
    assert result.snapshot_type == "not_available"
    assert result.is_true_wave_equation_wavefield is False
    assert result.as_dict()["metadata"]["backend_name"] == "kinematic"
