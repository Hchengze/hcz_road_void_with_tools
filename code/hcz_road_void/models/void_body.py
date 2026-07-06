"""三维空洞体异常模型。

地球物理意义
------------
Stage 1 把空洞简化成单个点绕射体，这对于检查三维走时和定位流程很有用，
但真实道路空洞是有体积、有边界、有速度/密度扰动的三维异常体。Stage 2A
先不做复杂边界散射，而是提供两个过渡能力：

1. 把球体或椭球体异常采样成多个散射点，兼容当前运动学后端；
2. 把球体或椭球体异常嵌入三维速度网格，供后续 Devito/OpenSWPC 真实
   波动方程正演直接使用。

这里的体模型仍是几何/参数表达，不等于已经实现了真实空洞边界散射。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

import numpy as np

from hcz_road_void.geometry import Coordinate3D, ensure_coordinate3d


class VoidBodyType(str, Enum):
    """体异常形状类型。

    `sphere` 表示三方向尺寸相同的球体；`ellipsoid` 表示沿 `x`、`y`、
    `depth` 三个方向尺寸可不同的椭球体。尺寸单位均为 m，`depth` 向下为正。
    """

    SPHERE = "sphere"
    ELLIPSOID = "ellipsoid"


@dataclass(frozen=True)
class VoidBody3D:
    """三维空洞或低速异常体。

    字段说明：
    - `center_xyz`：异常体中心，坐标为 `(x, y, depth)`，单位 m；
    - `body_type`：`sphere` 或 `ellipsoid`；
    - `size_xyz_m`：沿 `x`、`y`、`depth` 的完整尺寸，不是半径，单位 m；
    - `velocity_scale`：异常体内部速度相对背景速度的比例，例如 `0.5`
      表示把体内速度降为背景速度的一半。

    `velocity_scale` 必须为正。第一阶段通常用低速体表达空洞、脱空或松散区；
    严格真空边界、强阻抗反差和弹性参数耦合要留给后续波动方程后端处理。
    """

    center_xyz: Coordinate3D | Sequence[float]
    body_type: VoidBodyType | str
    size_xyz_m: Sequence[float]
    velocity_scale: float

    def __post_init__(self) -> None:
        center = ensure_coordinate3d(self.center_xyz, "center_xyz")
        body_type = VoidBodyType(self.body_type)
        if len(self.size_xyz_m) != 3:
            raise ValueError("size_xyz_m 必须包含 x、y、depth 三个方向的完整尺寸。")
        sizes = tuple(float(value) for value in self.size_xyz_m)
        if any(value <= 0 for value in sizes):
            raise ValueError("size_xyz_m 中的尺寸必须全部为正。")
        if body_type is VoidBodyType.SPHERE and not np.allclose(sizes, sizes[0]):
            raise ValueError("sphere 类型要求 x、y、depth 三个尺寸相同。")
        if self.velocity_scale <= 0:
            raise ValueError("velocity_scale 必须为正。")
        object.__setattr__(self, "center_xyz", center)
        object.__setattr__(self, "body_type", body_type)
        object.__setattr__(self, "size_xyz_m", sizes)

    @property
    def radii_xyz_m(self) -> tuple[float, float, float]:
        """返回沿 `x`、`y`、`depth` 的半轴长度，单位 m。"""

        return tuple(0.5 * value for value in self.size_xyz_m)

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "void_body_type": self.body_type.value,
            "center_xyz": self.center_xyz.xyz,
            "size_xyz_m": self.size_xyz_m,
            "velocity_scale": self.velocity_scale,
            "representation_note": "体异常几何表达；多散射点只是运动学代理，不是严格边界散射。",
        }

    def contains_xyz(self, xyz: np.ndarray) -> np.ndarray:
        """判断一组三维点是否落在体异常内部。

        输入 `xyz` 的最后一维必须为 `(x, y, depth)`。椭球体判据为
        `((x-cx)/rx)^2 + ((y-cy)/ry)^2 + ((depth-cd)/rd)^2 <= 1`。
        球体是该判据在三个半轴相同情况下的特例。
        """

        points = np.asarray(xyz, dtype=float)
        if points.shape[-1] != 3:
            raise ValueError("xyz 的最后一维必须是 3，对应 x、y、depth。")
        center = np.asarray(self.center_xyz.xyz, dtype=float)
        radii = np.asarray(self.radii_xyz_m, dtype=float)
        normalized = (points - center) / radii
        return np.sum(normalized * normalized, axis=-1) <= 1.0


def sample_void_body_as_scatterers(void_body: VoidBody3D, spacing_m: float) -> tuple[Coordinate3D, ...]:
    """把体异常采样成多个点散射体。

    这只是为了让当前运动学点绕射后端能“看见”一个有限尺寸体的近似范围。
    每个采样点仍是独立的运动学代理点，不包含真实空洞边界散射、绕射振幅、
    模式转换或多次散射。
    """

    if spacing_m <= 0:
        raise ValueError("spacing_m 必须为正。")
    cx, cy, cd = void_body.center_xyz.xyz
    rx, ry, rd = void_body.radii_xyz_m
    xs = np.arange(cx - rx, cx + rx + 0.5 * spacing_m, spacing_m)
    ys = np.arange(cy - ry, cy + ry + 0.5 * spacing_m, spacing_m)
    depths = np.arange(cd - rd, cd + rd + 0.5 * spacing_m, spacing_m)
    mesh = np.stack(np.meshgrid(xs, ys, depths, indexing="ij"), axis=-1)
    inside = void_body.contains_xyz(mesh)
    scatterers = [
        Coordinate3D(float(point[0]), float(point[1]), float(point[2]))
        for point in mesh[inside]
        if point[2] >= 0.0
    ]
    if not scatterers:
        scatterers = [void_body.center_xyz]
    return tuple(scatterers)


def embed_void_body_into_velocity_grid(velocity_grid: object, void_body: VoidBody3D) -> object:
    """把体异常嵌入三维速度网格。

    该函数调用 `VelocityGrid3D.with_embedded_void_body`。单独保留这个函数是为了
    让调用侧表达清楚：体异常嵌入网格是 Stage 2 波动方程正演的准备工作，
    不等同于当前运动学后端已经完成真实体散射。
    """

    if not hasattr(velocity_grid, "with_embedded_void_body"):
        raise TypeError("velocity_grid 必须是支持 with_embedded_void_body 的三维速度网格对象。")
    return velocity_grid.with_embedded_void_body(void_body)
