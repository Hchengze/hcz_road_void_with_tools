"""三维定位搜索网格。

定位不能只在 ``x-depth`` 剖面里扫描。道路 DAS + 锤击场景中，空洞可能
位于道路横向任意位置，因此搜索轴必须同时包含 ``search_x``、
``search_y`` 和 ``search_depth``。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class SearchGrid3D:
    """候选空洞位置的三维搜索轴。

    - ``search_x``：沿道路方向候选坐标，单位 m；
    - ``search_y``：横穿道路方向候选坐标，单位 m；
    - ``search_depth``：向下为正的深度候选坐标，单位 m。

    目标函数体的维度顺序固定为 ``(nx, ny, ndepth)``。
    """

    search_x: Sequence[float]
    search_y: Sequence[float]
    search_depth: Sequence[float]

    def __post_init__(self) -> None:
        axes = {
            "search_x": tuple(float(value) for value in self.search_x),
            "search_y": tuple(float(value) for value in self.search_y),
            "search_depth": tuple(float(value) for value in self.search_depth),
        }
        for name, values in axes.items():
            if not values:
                raise ValueError(f"{name} must not be empty.")
        if any(value < 0 for value in axes["search_depth"]):
            raise ValueError("search_depth values must be nonnegative.")
        object.__setattr__(self, "search_x", axes["search_x"])
        object.__setattr__(self, "search_y", axes["search_y"])
        object.__setattr__(self, "search_depth", axes["search_depth"])

    @property
    def shape(self) -> tuple[int, int, int]:
        return (len(self.search_x), len(self.search_y), len(self.search_depth))

    @property
    def size(self) -> int:
        nx, ny, nz = self.shape
        return nx * ny * nz
