"""道路地下空洞项目的三维坐标工具。

本模块是整个项目的几何基石。所有震源、接收点、DAS 光纤采样点和
空洞位置都必须使用同一套三维约定：

- ``x``：沿道路或沿光纤方向；
- ``y``：横穿道路方向；
- ``depth``：深度，向下为正。

第一阶段算法很简单，但只要坐标约定不统一，正演、定位和可视化就会
互相矛盾。因此这里集中做维度检查、深度方向检查和三维距离计算。
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Sequence


@dataclass(frozen=True)
class Coordinate3D:
    """一个深度向下为正的三维点。

    字段单位均为 m：

    - ``x``：沿道路/光纤方向坐标；
    - ``y``：横穿道路方向坐标；
    - ``depth``：向下为正的深度坐标。
    """

    x: float
    y: float
    depth: float

    def __post_init__(self) -> None:
        values = (self.x, self.y, self.depth)
        if not all(isfinite(float(value)) for value in values):
            raise ValueError("Coordinate3D values must be finite numbers.")
        if self.depth < 0:
            raise ValueError("Coordinate3D.depth must be nonnegative and positive downward.")

    @property
    def xyz(self) -> tuple[float, float, float]:
        return (float(self.x), float(self.y), float(self.depth))


def ensure_coordinate3d(value: Coordinate3D | Sequence[float], name: str) -> Coordinate3D:
    """把原始三元组或 ``Coordinate3D`` 统一转换为合法三维坐标。

    这个函数刻意拒绝二维坐标，因为本项目主场景不是二维剖面；任何
    source、receiver 或 void 都必须显式给出 ``x, y, depth``。
    """

    if isinstance(value, Coordinate3D):
        return value
    if len(value) != 3:
        raise ValueError(f"{name} must contain exactly three values: x, y, depth.")
    return Coordinate3D(float(value[0]), float(value[1]), float(value[2]))


def distance_3d(a: Coordinate3D | Sequence[float], b: Coordinate3D | Sequence[float]) -> float:
    """计算两个三维点之间的欧氏距离，单位为 m。"""

    pa = ensure_coordinate3d(a, "a")
    pb = ensure_coordinate3d(b, "b")
    dx = pa.x - pb.x
    dy = pa.y - pb.y
    dz = pa.depth - pb.depth
    return sqrt(dx * dx + dy * dy + dz * dz)
