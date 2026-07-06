"""三维场景可视化边界工具。

目前只提供最小包围盒计算，后续可用于自动设置三维道路、光纤、震源和
空洞图的显示范围。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from hcz_road_void.geometry import Coordinate3D, ensure_coordinate3d


@dataclass(frozen=True)
class SceneBounds3D:
    """三维场景包围盒。

    ``min_xyz`` 和 ``max_xyz`` 都按 ``(x, y, depth)`` 顺序记录，单位 m。
    """

    min_xyz: tuple[float, float, float]
    max_xyz: tuple[float, float, float]

    @classmethod
    def from_points(cls, points: Sequence[Coordinate3D | Sequence[float]]) -> "SceneBounds3D":
        """从一组三维点计算最小包围盒。"""

        normalized = [ensure_coordinate3d(point, f"points[{index}]") for index, point in enumerate(points)]
        if not normalized:
            raise ValueError("points must not be empty.")
        xs = [point.x for point in normalized]
        ys = [point.y for point in normalized]
        zs = [point.depth for point in normalized]
        return cls((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))
