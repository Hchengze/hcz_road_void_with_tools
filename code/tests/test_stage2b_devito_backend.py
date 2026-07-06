"""Stage 2B/2C Devito acoustic 后端测试。

这些测试刻意区分 “Devito 能 import” 和 “Devito 能真正执行 Operator”。
当前 Windows 原生 `myvoid` 可能属于前者但不属于后者；项目必须给出清晰诊断，
并且默认 kinematic 流程仍然可用。Stage 2C 在 WSL Linux conda 中验证真实
Operator runtime；这些测试在没有 Devito runtime 的环境中仍应优雅跳过。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from hcz_road_void.forward import (
    DevitoBackend,
    DevitoForwardConfig,
    KinematicDiffractionBackend,
    detect_runtime_environment,
    velocity_grid_to_devito_inputs,
)
from hcz_road_void.models import VelocityGrid3D, VoidBody3D, embed_void_body_into_velocity_grid
from hcz_road_void.visualization import save_scalar_wavefield_snapshots
from main import build_stage1_scene


def test_devito_backend_runtime_status_is_explicit() -> None:
    backend = DevitoBackend()
    status = backend.runtime_status()

    assert isinstance(status.import_available, bool)
    assert isinstance(status.runtime_available, bool)
    assert status.state in {
        "import_unavailable",
        "import_available_runtime_unavailable",
        "runtime_available",
    }
    assert status.as_dict()["state"] == status.state
    assert isinstance(backend.is_available(), bool)
    if status.import_available:
        assert status.version is not None
    if not status.runtime_available:
        assert status.message


def test_devito_backend_metadata_contains_stage2b_fields() -> None:
    metadata = DevitoBackend().metadata()

    for key in [
        "backend_name",
        "physics_type",
        "is_wave_equation_solver",
        "is_elastic_solver",
        "supports_wavefield_snapshots",
        "supports_das_strain",
        "devito_import_available",
        "runtime_available",
        "devito_version",
        "runtime_state",
        "runtime_environment",
        "runtime_message",
    ]:
        assert key in metadata
    assert metadata["backend_name"] == "devito_acoustic_3d"
    assert metadata["physics_type"] == "acoustic_wave_equation"
    assert metadata["is_wave_equation_solver"] is True
    assert metadata["is_elastic_solver"] is False
    assert metadata["supports_das_strain"] is False
    assert metadata["runtime_state"] in {
        "import_unavailable",
        "import_available_runtime_unavailable",
        "runtime_available",
    }
    assert isinstance(detect_runtime_environment(), str)


def test_stage2b_devito_documents_exist() -> None:
    docs = Path("docs")
    for name in [
        "DEVITO_INTEGRATION_NOTES.md",
        "DEVITO_3D_ACOUSTIC_BACKEND.md",
        "DEVITO_LINUX_RUNTIME_GUIDE.md",
        "STAGE2_WAVE_EQUATION_FORWARD_PLAN.md",
        "FORWARD_OUTPUTS.md",
    ]:
        path = docs / name
        assert path.exists()
        assert path.stat().st_size > 0


def test_velocity_grid_to_devito_inputs_preserves_3d_axes() -> None:
    grid = VelocityGrid3D.uniform(
        x_m=[0.0, 1.0, 2.0],
        y_m=[0.0, 1.0],
        depth_m=[0.0, 1.0, 2.0, 3.0],
        vp_mps=900.0,
    )
    converted = velocity_grid_to_devito_inputs(grid)

    assert converted["shape"] == (3, 2, 4)
    assert converted["origin"] == (0.0, 0.0, 0.0)
    assert converted["extent"] == (2.0, 1.0, 3.0)
    assert converted["spacing"] == (1.0, 1.0, 1.0)
    assert converted["axis_order"] == "x, y, depth"


def test_devito_backend_rejects_2d_coordinates_before_forward() -> None:
    scene = build_stage1_scene()
    scene["receiver_xyz"] = [(0.0, 0.0)]
    scene.pop("sampled_receivers")
    backend = DevitoBackend()

    if backend.is_available():
        with pytest.raises(ValueError, match="receiver_xyz"):
            backend.run_forward(scene, DevitoForwardConfig(nt=12, source_indices=(0,)))
    else:
        with pytest.raises(RuntimeError, match="Devito"):
            backend.run_forward(scene, DevitoForwardConfig(nt=12, source_indices=(0,)))


def test_wavefield_snapshot_writer_outputs_png_and_gif(tmp_path) -> None:
    snapshot_cube = np.zeros((3, 5, 4, 6), dtype=float)
    snapshot_cube[0, 2, 1, 2] = 1.0
    snapshot_cube[1, 3, 1, 3] = -0.8
    snapshot_cube[2, 4, 1, 4] = 0.5

    result = save_scalar_wavefield_snapshots(
        output_dir=tmp_path / "snapshots",
        snapshot_cube=snapshot_cube,
        x_m=np.linspace(0.0, 4.0, 5),
        y_m=np.linspace(0.0, 3.0, 4),
        depth_m=np.linspace(0.0, 5.0, 6),
        snapshot_times_s=[0.0, 0.01, 0.02],
        fixed_y_m=1.0,
        animation_path=tmp_path / "wavefield.gif",
    )

    assert result.snapshot_type == "true_wave_equation"
    assert result.is_true_wave_equation_wavefield is True
    assert len(result.snapshot_paths) == 3
    assert (tmp_path / "wavefield.gif").exists()


def test_devito_backend_can_use_velocity_grid_and_void_body_when_runtime_available(tmp_path) -> None:
    backend = DevitoBackend()
    if not backend.is_available():
        pytest.skip("当前环境 Devito runtime 不可用，跳过真实 acoustic 正演 smoke test。")

    grid = VelocityGrid3D.uniform(
        x_m=np.linspace(0.0, 8.0, 9),
        y_m=np.linspace(0.0, 4.0, 5),
        depth_m=np.linspace(0.0, 4.0, 5),
        vp_mps=900.0,
    )
    void_body = VoidBody3D(
        center_xyz=(4.0, 2.0, 1.5),
        body_type="ellipsoid",
        size_xyz_m=(2.0, 2.0, 1.0),
        velocity_scale=0.6,
    )
    scene = {
        "velocity_grid": embed_void_body_into_velocity_grid(grid, void_body),
        "source_xyz": [(2.0, 4.0, 0.0)],
        "receiver_xyz": [(2.0, 0.0, 0.0), (6.0, 0.0, 0.0)],
    }
    result = backend.run_forward(
        scene,
        DevitoForwardConfig(dt_s=0.00025, nt=120, wavelet_frequency_hz=70.0, snapshot_interval=20),
    )

    assert result.data.shape == (1, 2, 120)
    assert np.max(np.abs(result.data)) > 0.0
    assert result.metadata["backend_name"] == "devito_acoustic_3d"
    assert result.metadata["is_wave_equation_solver"] is True
    assert result.metadata["is_elastic_solver"] is False
    snapshot_cube = result.metadata["wavefield_snapshot_array"]
    assert np.max(np.abs(snapshot_cube)) > 0.0


def test_main_devito_backend_cli_is_clear_when_runtime_unavailable(tmp_path) -> None:
    backend = DevitoBackend()
    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--backend",
            "devito_acoustic_3d",
            "--output-dir",
            str(tmp_path),
            "--quiet",
        ],
        cwd=".",
        check=False,
        capture_output=True,
        text=True,
    )

    if backend.is_available():
        assert completed.returncode == 0
        summary = json.loads((tmp_path / "devito_forward_summary.json").read_text(encoding="utf-8"))
        assert summary["backend_name"] == "devito_acoustic_3d"
        assert summary["is_wave_equation_solver"] is True
        assert summary["stage"] == "Stage 2C"
        assert summary["runtime_environment"]
        assert summary["devito_runtime_state"] == "runtime_available"
        assert summary["source_count"] == summary["data_shape"][0]
        assert summary["receiver_count"] == summary["data_shape"][1]
        assert summary["time_sample_count"] == summary["data_shape"][2]
        assert summary["snapshot_count"] >= 1
        assert len(summary["velocity_grid_shape"]) == 3
    else:
        assert completed.returncode == 2
        assert "运行失败" in completed.stderr
        assert "Devito" in completed.stderr


def test_kinematic_backend_still_available() -> None:
    assert KinematicDiffractionBackend().is_available() is True
