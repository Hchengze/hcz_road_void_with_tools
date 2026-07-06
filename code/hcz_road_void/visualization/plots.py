"""第一阶段三维道路空洞流程的绘图工具。

这些图不是算法验证本身，而是帮助检查几何和目标函数是否符合三维道路
DAS + 锤击场景。特别要看清楚：DAS 光纤在道路一侧，锤击点在另一侧，
空洞位于道路中部地下，depth 轴向下为正。
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

from hcz_road_void.geometry import Coordinate3D, ensure_coordinate3d
from hcz_road_void.localization import LocalizationResult3D, extract_objective_slices


def _configure_fonts() -> None:
    """配置中文字体 fallback，避免图题和图例显示为方框。"""

    candidates = ("Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC", "Arial Unicode MS")
    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in candidates:
        if candidate in available:
            plt.rcParams["font.sans-serif"] = [candidate, "DejaVu Sans"]
            break
    plt.rcParams["axes.unicode_minus"] = False


_configure_fonts()


def plot_geometry_3d(
    output_path: str | Path,
    source_xyz: Sequence[Coordinate3D | Sequence[float]],
    receiver_polyline: Sequence[Coordinate3D | Sequence[float]],
    receiver_xyz: Sequence[Coordinate3D | Sequence[float]],
    true_void_xyz: Coordinate3D | Sequence[float],
    void_radius_m: float | None = None,
    best_xyz: Coordinate3D | Sequence[float] | None = None,
    road_length_m: float | None = None,
    road_width_m: float | None = None,
    fiber_y_m: float | None = None,
    source_y_m: float | None = None,
) -> None:
    """绘制道路边界、DAS 光纤、锤击点、空洞和定位结果。

    所有输入都使用 ``(x, y, depth)``。图中 z/depth 轴反向显示，使
    depth 越大越靠下，符合道路地下空间直觉。
    """

    sources = np.array([ensure_coordinate3d(source, f"source_xyz[{index}]").xyz for index, source in enumerate(source_xyz)])
    polyline = np.array([ensure_coordinate3d(point, f"receiver_polyline[{index}]").xyz for index, point in enumerate(receiver_polyline)])
    receivers = np.array([ensure_coordinate3d(receiver, f"receiver_xyz[{index}]").xyz for index, receiver in enumerate(receiver_xyz)])
    true_void = ensure_coordinate3d(true_void_xyz, "true_void_xyz")
    best = ensure_coordinate3d(best_xyz, "best_xyz") if best_xyz is not None else None
    if void_radius_m is not None and void_radius_m <= 0:
        raise ValueError("void_radius_m must be positive when provided.")

    road_length = float(road_length_m) if road_length_m is not None else float(max(polyline[:, 0].max(), sources[:, 0].max()))
    road_width = float(road_width_m) if road_width_m is not None else float(max(polyline[:, 1].max(), sources[:, 1].max()) - min(polyline[:, 1].min(), sources[:, 1].min()))
    fiber_y = float(fiber_y_m) if fiber_y_m is not None else float(polyline[0, 1])
    source_y = float(source_y_m) if source_y_m is not None else float(np.median(sources[:, 1]))
    road_y_min = min(0.0, fiber_y, source_y)
    road_y_max = road_y_min + road_width

    fig = plt.figure(figsize=(10, 7.5))
    ax = fig.add_subplot(111, projection="3d")
    _plot_road_boundary(ax, road_length, road_y_min, road_y_max)
    ax.plot(polyline[:, 0], polyline[:, 1], polyline[:, 2], color="tab:blue", linewidth=2.8, label="DAS 光纤")
    ax.scatter(receivers[:, 0], receivers[:, 1], receivers[:, 2], s=12, color="tab:blue", alpha=0.5, label="DAS 通道")
    ax.plot(sources[:, 0], sources[:, 1], sources[:, 2], color="tab:red", linestyle="--", linewidth=1.8, label="锤击炮线")
    ax.scatter(sources[:, 0], sources[:, 1], sources[:, 2], marker="o", s=45, color="tab:red", label="锤击点")
    _plot_void(ax, true_void, void_radius_m)
    ax.plot(
        [true_void.x, true_void.x],
        [true_void.y, true_void.y],
        [0.0, true_void.depth],
        color="orange",
        linestyle=":",
        linewidth=1.8,
        label="空洞垂向投影",
    )
    if best is not None:
        ax.scatter([best.x], [best.y], [best.depth], marker="x", s=100, color="black", label="best_xyz")
    ax.set_xlabel("x 沿道路/光纤方向 (m)")
    ax.set_ylabel("y 横穿道路方向 (m)")
    ax.set_zlabel("depth 向下为正 (m)")
    ax.invert_zaxis()
    ax.set_xlim(0.0, road_length)
    ax.set_ylim(road_y_min, road_y_max)
    max_depth = max(true_void.depth + float(void_radius_m or 0.0) + 1.0, 5.0)
    ax.set_zlim(max_depth, 0.0)
    ax.view_init(elev=24, azim=-58)
    ax.legend(loc="upper left")
    ax.set_title("三维道路 DAS + 锤击几何示意")
    fig.tight_layout()
    _save(fig, output_path)


def plot_synthetic_gather(
    output_path: str | Path,
    data: np.ndarray,
    time_axis_s: Sequence[float],
    receiver_xyz: Sequence[Coordinate3D | Sequence[float]],
    source_index: int = 0,
) -> None:
    """绘制单炮合成记录。

    横轴是沿 DAS 光纤采样得到的通道编号，纵轴是时间。第一阶段记录是
    点接收器近似下的运动学绕射波形，用来检查绕射走时曲线是否合理。
    """

    data_array = np.asarray(data)
    if data_array.ndim != 3:
        raise ValueError("data must have shape n_sources x n_receivers x n_times.")
    if not 0 <= source_index < data_array.shape[0]:
        raise ValueError("source_index is out of range.")
    gather = data_array[source_index]
    receivers = np.array([ensure_coordinate3d(receiver, f"receiver_xyz[{index}]").xyz for index, receiver in enumerate(receiver_xyz)])
    channel_axis = np.arange(receivers.shape[0])
    time_axis = np.asarray(time_axis_s)

    fig, ax = plt.subplots(figsize=(10, 5))
    vmax = np.percentile(np.abs(gather), 99.0)
    vmax = vmax if vmax > 0 else 1.0
    ax.imshow(
        gather.T,
        aspect="auto",
        cmap="seismic",
        vmin=-vmax,
        vmax=vmax,
        extent=[channel_axis[0], channel_axis[-1], time_axis[-1], time_axis[0]],
    )
    ax.set_xlabel("DAS 采样通道编号")
    ax.set_ylabel("时间 (s)")
    ax.set_title(f"三维运动学绕射合成炮集，震源 {source_index}")
    fig.tight_layout()
    _save(fig, output_path)


def plot_localization_slices(output_path: str | Path, result: LocalizationResult3D) -> None:
    """绘制穿过最佳候选点的三维定位目标函数切片。"""

    slices = extract_objective_slices(result)
    grid = result.search_grid
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

    _imshow_slice(
        axes[0],
        slices["x_depth_at_best_y"].T,
        extent=[grid.search_x[0], grid.search_x[-1], grid.search_depth[-1], grid.search_depth[0]],
        xlabel="x 沿道路 (m)",
        ylabel="depth 深度 (m)",
        title="固定最佳 y 的 x-depth 切片",
    )
    _imshow_slice(
        axes[1],
        slices["y_depth_at_best_x"].T,
        extent=[grid.search_y[0], grid.search_y[-1], grid.search_depth[-1], grid.search_depth[0]],
        xlabel="y 横穿道路 (m)",
        ylabel="depth 深度 (m)",
        title="固定最佳 x 的 y-depth 切片",
    )
    _imshow_slice(
        axes[2],
        slices["x_y_at_best_depth"].T,
        extent=[grid.search_x[0], grid.search_x[-1], grid.search_y[0], grid.search_y[-1]],
        xlabel="x 沿道路 (m)",
        ylabel="y 横穿道路 (m)",
        title="固定最佳 depth 的 x-y 切片",
    )
    fig.suptitle("三维定位目标函数切片")
    fig.tight_layout()
    _save(fig, output_path)


def _imshow_slice(ax: plt.Axes, values: np.ndarray, extent: list[float], xlabel: str, ylabel: str, title: str) -> None:
    """绘制一张目标函数二维切片并添加色标。"""

    image = ax.imshow(values, aspect="auto", origin="upper", cmap="viridis", extent=extent)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    plt.colorbar(image, ax=ax, fraction=0.046, pad=0.04)


def _plot_road_boundary(ax: plt.Axes, road_length_m: float, road_y_min: float, road_y_max: float) -> None:
    """绘制道路平面矩形边界。"""

    corners = np.array(
        [
            [0.0, road_y_min, 0.0],
            [road_length_m, road_y_min, 0.0],
            [road_length_m, road_y_max, 0.0],
            [0.0, road_y_max, 0.0],
            [0.0, road_y_min, 0.0],
        ]
    )
    ax.plot(corners[:, 0], corners[:, 1], corners[:, 2], color="0.25", linewidth=2.0, label="道路边界")
    ax.plot_trisurf(
        corners[:4, 0],
        corners[:4, 1],
        corners[:4, 2],
        triangles=[[0, 1, 2], [0, 2, 3]],
        color="0.85",
        alpha=0.16,
        linewidth=0.0,
        shade=False,
    )


def _plot_void(ax: plt.Axes, true_void: Coordinate3D, void_radius_m: float | None) -> None:
    """绘制空洞中心或等效球体。"""

    if void_radius_m is None:
        ax.scatter([true_void.x], [true_void.y], [true_void.depth], marker="o", s=95, color="orange", label="疑似空洞")
        return
    u = np.linspace(0.0, 2.0 * np.pi, 24)
    v = np.linspace(0.0, np.pi, 12)
    xs = true_void.x + void_radius_m * np.outer(np.cos(u), np.sin(v))
    ys = true_void.y + void_radius_m * np.outer(np.sin(u), np.sin(v))
    zs = true_void.depth + void_radius_m * np.outer(np.ones_like(u), np.cos(v))
    ax.plot_surface(xs, ys, zs, color="orange", alpha=0.55, linewidth=0.0)
    ax.scatter([true_void.x], [true_void.y], [true_void.depth], marker="o", s=45, color="darkorange", label="疑似空洞")


def _save(fig: plt.Figure, output_path: str | Path) -> None:
    """保存图像并关闭 figure，避免批量运行时占用过多资源。"""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)
