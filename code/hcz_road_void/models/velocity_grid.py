"""三维速度网格模型。

地球物理意义
------------
常速度 `VelocityModel3D` 只能支撑走时近似。真实三维波动方程正演需要在
`x-y-depth` 网格上定义速度、密度和异常体。`VelocityGrid3D` 是 Stage 2A 的
最小网格容器：它可以生成均匀背景速度网格、嵌入低速体异常、保存为 `.npz`，
并为 Devito/OpenSWPC 接入提供统一数据入口。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class VelocityGrid3D:
    """三维 `x-y-depth` 速度网格。

    - `x_m`：沿道路或光纤方向坐标轴，单位 m；
    - `y_m`：横穿道路方向坐标轴，单位 m；
    - `depth_m`：向下为正的深度坐标轴，单位 m；
    - `vp_mps`：P 波速度或声波等效速度数组，形状为 `(nx, ny, ndepth)`；
    - `metadata`：网格间距、单位、是否包含异常体等说明。

    当前只把 `vp_mps` 作为最小必需字段；后续弹性波后端应同步扩展 `vs`、
    `rho`、衰减和各向异性参数。
    """

    x_m: Sequence[float]
    y_m: Sequence[float]
    depth_m: Sequence[float]
    vp_mps: np.ndarray
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        x = np.asarray(self.x_m, dtype=float)
        y = np.asarray(self.y_m, dtype=float)
        depth = np.asarray(self.depth_m, dtype=float)
        vp = np.asarray(self.vp_mps, dtype=float)
        if x.ndim != 1 or y.ndim != 1 or depth.ndim != 1:
            raise ValueError("x_m、y_m、depth_m 必须是一维坐标轴。")
        if len(x) == 0 or len(y) == 0 or len(depth) == 0:
            raise ValueError("速度网格三个坐标轴都不能为空。")
        if np.any(depth < 0):
            raise ValueError("depth_m 必须非负，且向下为正。")
        if vp.shape != (len(x), len(y), len(depth)):
            raise ValueError("vp_mps 形状必须为 (nx, ny, ndepth)。")
        if np.any(vp <= 0):
            raise ValueError("vp_mps 中的速度必须全部为正。")
        object.__setattr__(self, "x_m", x)
        object.__setattr__(self, "y_m", y)
        object.__setattr__(self, "depth_m", depth)
        object.__setattr__(self, "vp_mps", vp)
        object.__setattr__(self, "metadata", dict(self.metadata))

    @classmethod
    def uniform(
        cls,
        x_m: Sequence[float],
        y_m: Sequence[float],
        depth_m: Sequence[float],
        vp_mps: float,
        metadata: Mapping[str, Any] | None = None,
    ) -> "VelocityGrid3D":
        """创建均匀三维速度网格。"""

        if vp_mps <= 0:
            raise ValueError("vp_mps 必须为正。")
        x = np.asarray(x_m, dtype=float)
        y = np.asarray(y_m, dtype=float)
        depth = np.asarray(depth_m, dtype=float)
        vp = np.full((len(x), len(y), len(depth)), float(vp_mps), dtype=float)
        grid_metadata = {
            "velocity_unit": "m/s",
            "coordinate_unit": "m",
            "depth_positive_down": True,
            "contains_void_body": False,
        }
        if metadata:
            grid_metadata.update(metadata)
        return cls(x, y, depth, vp, grid_metadata)

    @property
    def shape(self) -> tuple[int, int, int]:
        return self.vp_mps.shape

    @property
    def spacing_m(self) -> dict[str, float | None]:
        """返回各方向平均网格间距。单点轴没有间距，返回 None。"""

        return {
            "dx_m": _mean_spacing(self.x_m),
            "dy_m": _mean_spacing(self.y_m),
            "ddepth_m": _mean_spacing(self.depth_m),
        }

    def with_embedded_void_body(self, void_body: object) -> "VelocityGrid3D":
        """返回嵌入低速体异常后的新速度网格。

        体内点通过 `VoidBody3D.contains_xyz` 判定，并把 `vp` 乘以
        `velocity_scale`。这只是速度模型层面的低速体表达，不包含空洞自由边界
        或弹性参数强反差的完整物理效应。
        """

        xs, ys, depths = np.meshgrid(self.x_m, self.y_m, self.depth_m, indexing="ij")
        points = np.stack([xs, ys, depths], axis=-1)
        mask = void_body.contains_xyz(points)
        if not np.any(mask):
            raise ValueError("体异常没有覆盖速度网格中的任何点，请检查网格范围和体尺寸。")
        vp = self.vp_mps.copy()
        vp[mask] *= float(void_body.velocity_scale)
        metadata = dict(self.metadata)
        metadata.update(
            {
                "contains_void_body": True,
                "void_body": void_body.metadata,
                "body_embedding_note": "低速体已写入 vp_mps；这不是严格空洞边界散射。",
            }
        )
        return VelocityGrid3D(self.x_m, self.y_m, self.depth_m, vp, metadata)

    def save_npz(self, output_path: str | Path) -> None:
        """保存速度网格为 `.npz`，供后续正演后端或可视化读取。"""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            x_m=self.x_m,
            y_m=self.y_m,
            depth_m=self.depth_m,
            vp_mps=self.vp_mps,
            metadata=np.array([dict(self.metadata)], dtype=object),
        )


def build_uniform_road_velocity_grid(
    road_length_m: float,
    road_width_m: float,
    max_depth_m: float,
    spacing_m: float,
    background_vp_mps: float,
) -> VelocityGrid3D:
    """按道路尺寸生成均匀三维速度网格。

    网格覆盖 `x=0~road_length_m`、`y=0~road_width_m` 和
    `depth=0~max_depth_m`。这是后续真实三维正演的最小速度模型输出。
    """

    if road_length_m <= 0 or road_width_m <= 0 or max_depth_m <= 0:
        raise ValueError("道路长度、宽度和最大深度必须为正。")
    if spacing_m <= 0:
        raise ValueError("spacing_m 必须为正。")
    x_m = np.arange(0.0, road_length_m + 0.5 * spacing_m, spacing_m)
    y_m = np.arange(0.0, road_width_m + 0.5 * spacing_m, spacing_m)
    depth_m = np.arange(0.0, max_depth_m + 0.5 * spacing_m, spacing_m)
    return VelocityGrid3D.uniform(
        x_m=x_m,
        y_m=y_m,
        depth_m=depth_m,
        vp_mps=background_vp_mps,
        metadata={
            "grid_spacing_m": spacing_m,
            "road_length_m": road_length_m,
            "road_width_m": road_width_m,
            "max_depth_m": max_depth_m,
        },
    )


def _mean_spacing(axis: Sequence[float]) -> float | None:
    values = np.asarray(axis, dtype=float)
    if len(values) < 2:
        return None
    return float(np.mean(np.diff(values)))
