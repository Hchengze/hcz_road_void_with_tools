"""波场快照接口。

Stage 2A 先建立接口，不生成假装真实的波动方程波场。Stage 2B 新增
Devito acoustic 标量波场快照保存函数，但只有真实后端 runtime 可用时才会
写出 PNG/GIF。当前运动学后端没有网格波场变量，只能说明“不可用”。
后续 OpenSWPC 或弹性波后端可以继续把位移、速度、应力或应变快照写入这里
约定的数据结构和输出目录。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from hcz_road_void.visualization.plots import _configure_fonts


@dataclass(frozen=True)
class WavefieldSnapshotResult:
    """波场快照输出状态。

    - `snapshot_type`：`not_available`、`proxy` 或 `true_wave_equation`；
    - `is_true_wave_equation_wavefield`：是否来自真实波动方程求解器；
    - `snapshot_paths`：已生成的快照图片或数据文件路径；
    - `animation_path`：波场动图路径，当前运动学后端为 `None`；
    - `metadata`：后端、物理量和限制说明。
    """

    snapshot_type: str
    is_true_wave_equation_wavefield: bool
    snapshot_paths: Sequence[str] = field(default_factory=tuple)
    animation_path: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "snapshot_type": self.snapshot_type,
            "is_true_wave_equation_wavefield": self.is_true_wave_equation_wavefield,
            "snapshot_paths": list(self.snapshot_paths),
            "animation_path": self.animation_path,
            "metadata": dict(self.metadata),
        }


def unavailable_wavefield_snapshots(backend_name: str) -> WavefieldSnapshotResult:
    """返回当前后端没有真实波场快照的明确状态。"""

    return WavefieldSnapshotResult(
        snapshot_type="not_available",
        is_true_wave_equation_wavefield=False,
        metadata={
            "backend_name": backend_name,
            "reason": "当前运动学绕射后端没有网格波场变量，不能输出真实波动方程快照。",
            "future_backend": "Devito 或 OpenSWPC 接入后再输出真实波场快照和动图。",
        },
    )


def ensure_wavefield_output_dir(output_dir: str | Path) -> Path:
    """创建波场快照输出目录。

    当前目录可以为空；它的存在用于固定后续输出约定：
    `outputs/wavefield_snapshots/snapshot_000.png` 等。
    """

    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_scalar_wavefield_snapshots(
    output_dir: str | Path,
    snapshot_cube: np.ndarray,
    x_m: Sequence[float],
    y_m: Sequence[float],
    depth_m: Sequence[float],
    snapshot_times_s: Sequence[float],
    fixed_y_m: float,
    animation_path: str | Path | None = None,
    backend_name: str = "devito_acoustic_3d",
) -> WavefieldSnapshotResult:
    """保存 Devito acoustic 标量波场快照和 GIF 动图。

    参数中的 `snapshot_cube` 约定为
    `n_snapshots x nx x ny x ndepth`。这里选择最接近 `fixed_y_m` 的
    `x-depth` 剖面来绘图，原因是道路空洞位于地下浅层，`x-depth` 剖面最直观
    地展示锤击波在沿路方向和深度方向的传播。

    重要说明：图中显示的是 acoustic 标量波场，不是弹性位移、速度、应力，
    也不是 DAS 沿光纤方向轴向应变。
    """

    _configure_fonts()
    cube = np.asarray(snapshot_cube, dtype=float)
    if cube.ndim != 4:
        raise ValueError("snapshot_cube 必须是 n_snapshots x nx x ny x ndepth。")
    if cube.shape[0] != len(snapshot_times_s):
        raise ValueError("snapshot_times_s 长度必须与快照数量一致。")
    x_axis = np.asarray(x_m, dtype=float)
    y_axis = np.asarray(y_m, dtype=float)
    depth_axis = np.asarray(depth_m, dtype=float)
    if cube.shape[1:] != (len(x_axis), len(y_axis), len(depth_axis)):
        raise ValueError("snapshot_cube 空间维度必须与 x_m、y_m、depth_m 匹配。")

    output_path = ensure_wavefield_output_dir(output_dir)
    iy = int(np.argmin(np.abs(y_axis - float(fixed_y_m))))
    vmax = float(np.percentile(np.abs(cube), 99.0))
    vmax = vmax if vmax > 0 else 1.0
    snapshot_paths: list[str] = []

    for index, time_s in enumerate(snapshot_times_s):
        values = cube[index, :, iy, :].T
        fig, ax = plt.subplots(figsize=(8, 4.8))
        image = ax.imshow(
            values,
            aspect="auto",
            origin="upper",
            cmap="seismic",
            vmin=-vmax,
            vmax=vmax,
            extent=[x_axis[0], x_axis[-1], depth_axis[-1], depth_axis[0]],
        )
        ax.set_xlabel("x 沿道路/光纤方向 (m)")
        ax.set_ylabel("depth 向下为正 (m)")
        ax.set_title(f"Devito 三维声波场 x-depth 快照，y={y_axis[iy]:.2f} m，t={time_s:.4f} s")
        plt.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="标量声波场振幅")
        fig.tight_layout()
        path = output_path / f"snapshot_{index:03d}.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        snapshot_paths.append(str(path))

    animation_output = None
    if animation_path is not None and snapshot_paths:
        animation_output_path = Path(animation_path)
        animation_output_path.parent.mkdir(parents=True, exist_ok=True)
        frames = [Image.open(path) for path in snapshot_paths]
        try:
            frames[0].save(
                animation_output_path,
                save_all=True,
                append_images=frames[1:],
                duration=220,
                loop=0,
            )
            animation_output = str(animation_output_path)
        finally:
            for frame in frames:
                frame.close()

    return WavefieldSnapshotResult(
        snapshot_type="true_wave_equation",
        is_true_wave_equation_wavefield=True,
        snapshot_paths=tuple(snapshot_paths),
        animation_path=animation_output,
        metadata={
            "backend_name": backend_name,
            "wavefield_source": backend_name,
            "wavefield_component": "scalar acoustic field",
            "slice_type": "x-depth at nearest y",
            "fixed_y_m": float(y_axis[iy]),
            "is_elastic_wavefield": False,
            "supports_das_strain": False,
            "note": "这是 Devito acoustic 标量波场，不是弹性位移场或 DAS 轴向应变。",
        },
    )
