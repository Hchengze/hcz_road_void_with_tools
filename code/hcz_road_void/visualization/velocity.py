"""三维速度模型切片可视化。

这些图用于检查后续波动方程正演的模型输入：低速体是否在道路中部地下、
速度单位是否合理、`x-y-depth` 三个方向是否都被真实建模。切片图只是模型
审查工具，不是定位结果。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from hcz_road_void.models.velocity_grid import VelocityGrid3D
from hcz_road_void.visualization.fonts import configure_chinese_matplotlib


def plot_velocity_model_slices(
    output_path: str | Path,
    velocity_grid: VelocityGrid3D,
    x_m: float | None = None,
    y_m: float | None = None,
    depth_m: float | None = None,
) -> None:
    """绘制 `x-y`、`x-depth`、`y-depth` 三个速度模型切片。

    默认切片取网格中部；如果传入体异常中心坐标，则可直接穿过低速空洞体。
    """

    configure_chinese_matplotlib()
    ix = _nearest_index(velocity_grid.x_m, x_m)
    iy = _nearest_index(velocity_grid.y_m, y_m)
    iz = _nearest_index(velocity_grid.depth_m, depth_m)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    _imshow(
        axes[0],
        velocity_grid.vp_mps[:, :, iz].T,
        [velocity_grid.x_m[0], velocity_grid.x_m[-1], velocity_grid.y_m[0], velocity_grid.y_m[-1]],
        "x 沿道路/光纤方向 (m)",
        "y 横穿道路方向 (m)",
        f"x-y 平面速度切片，depth={velocity_grid.depth_m[iz]:.2f} m",
    )
    _imshow(
        axes[1],
        velocity_grid.vp_mps[:, iy, :].T,
        [velocity_grid.x_m[0], velocity_grid.x_m[-1], velocity_grid.depth_m[-1], velocity_grid.depth_m[0]],
        "x 沿道路/光纤方向 (m)",
        "depth 向下为正 (m)",
        f"x-depth 剖面，y={velocity_grid.y_m[iy]:.2f} m",
    )
    _imshow(
        axes[2],
        velocity_grid.vp_mps[ix, :, :].T,
        [velocity_grid.y_m[0], velocity_grid.y_m[-1], velocity_grid.depth_m[-1], velocity_grid.depth_m[0]],
        "y 横穿道路方向 (m)",
        "depth 向下为正 (m)",
        f"y-depth 剖面，x={velocity_grid.x_m[ix]:.2f} m",
    )
    fig.suptitle("三维道路速度模型切片")
    fig.tight_layout()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _nearest_index(axis: np.ndarray, value: float | None) -> int:
    if value is None:
        return len(axis) // 2
    return int(np.argmin(np.abs(np.asarray(axis, dtype=float) - float(value))))


def _imshow(ax: plt.Axes, values: np.ndarray, extent: list[float], xlabel: str, ylabel: str, title: str) -> None:
    image = ax.imshow(values, aspect="auto", origin="upper", cmap="viridis", extent=extent)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    plt.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="速度 (m/s)")
