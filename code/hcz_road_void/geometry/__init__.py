"""三维几何基础类型。

这里统一导出 ``Coordinate3D``、三维距离函数和道路空洞场景容器。所有
模块都应通过这些对象传递 source、receiver、fiber 和 void 几何。
"""

from hcz_road_void.geometry.coordinates import Coordinate3D, distance_3d, ensure_coordinate3d
from hcz_road_void.geometry.scenario import RoadVoidScenario, SourceArray3D

__all__ = [
    "Coordinate3D",
    "RoadVoidScenario",
    "SourceArray3D",
    "distance_3d",
    "ensure_coordinate3d",
]
