"""三维道路空洞场景的共享容器。

场景对象负责把震源、接收几何、速度模型和空洞模型放在同一坐标约定下。
它不做正演计算，只做“这些对象能否放进同一个三维道路问题”的一致性检查。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from hcz_road_void.geometry.coordinates import Coordinate3D, ensure_coordinate3d


@dataclass(frozen=True)
class SourceArray3D:
    """一组三维震源或锤击点。

    ``sources`` 中每个点均为 ``(x, y, depth)``，单位 m。默认道路示例中，
    锤击点沿道路另一侧排列，和 DAS 光纤不在同一条线上。
    """

    sources: Sequence[Coordinate3D | Sequence[float]]

    def __post_init__(self) -> None:
        normalized = tuple(
            ensure_coordinate3d(source, f"sources[{index}]")
            for index, source in enumerate(self.sources)
        )
        if not normalized:
            raise ValueError("SourceArray3D requires at least one source.")
        object.__setattr__(self, "sources", normalized)

    @property
    def source_xyz(self) -> tuple[tuple[float, float, float], ...]:
        return tuple(source.xyz for source in self.sources)


@dataclass(frozen=True)
class RoadVoidScenario:
    """最小三维道路空洞场景描述。

    字段含义：

    - ``sources``：三维 source_xyz 阵列；
    - ``receivers``：点接收器或 DAS 光纤采样几何；
    - ``velocity_model``：背景速度和密度元数据；
    - ``void_model``：空洞/异常体三维位置和尺度；
    - ``coordinate_units``：当前只支持 m；
    - ``depth_positive``：当前必须为 ``down``，表示 depth 向下为正。
    """

    sources: SourceArray3D
    receivers: object
    velocity_model: object
    void_model: object
    coordinate_units: str = "m"
    depth_positive: str = "down"

    def __post_init__(self) -> None:
        if self.coordinate_units != "m":
            raise ValueError("Only meter coordinates are supported in the Stage 1 skeleton.")
        if self.depth_positive != "down":
            raise ValueError("Depth convention must be positive down.")
        if not hasattr(self.receivers, "receiver_xyz") and not hasattr(self.receivers, "receiver_polyline"):
            raise ValueError("receivers must expose receiver_xyz or receiver_polyline.")
        if not hasattr(self.velocity_model, "vp_mps"):
            raise ValueError("velocity_model must expose vp_mps.")
        if not hasattr(self.void_model, "void_xyz"):
            raise ValueError("void_model must expose void_xyz.")
