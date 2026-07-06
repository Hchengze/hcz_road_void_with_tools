"""三维空洞或浅层异常体模型。

第一阶段把空洞简化为一个中心点和一个尺度参数。这个模型足够用于
运动学点绕射定位闭环，但不能表示真实空洞边界、形状、充填物或弹性
参数扰动。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from hcz_road_void.geometry import Coordinate3D, ensure_coordinate3d


@dataclass(frozen=True)
class VoidModel3D:
    """最小三维空洞表示。

    - ``void_xyz``：空洞中心或等效绕射点，坐标为 ``(x, y, depth)``，单位 m；
    - ``void_radius_m``：球状等效半径，单位 m；
    - ``void_size_xyz_m``：沿 x、y、depth 三方向的等效尺寸，单位 m。

    至少需要提供半径或三向尺寸中的一种。当前正演只使用 ``void_xyz``，
    尺度参数主要用于场景说明、可视化和后续有限尺寸散射扩展。
    """

    void_xyz: Coordinate3D | Sequence[float]
    void_radius_m: float | None = None
    void_size_xyz_m: Sequence[float] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "void_xyz", ensure_coordinate3d(self.void_xyz, "void_xyz"))
        if self.void_radius_m is None and self.void_size_xyz_m is None:
            raise ValueError("VoidModel3D requires void_radius_m or void_size_xyz_m.")
        if self.void_radius_m is not None and self.void_radius_m <= 0:
            raise ValueError("void_radius_m must be positive.")
        if self.void_size_xyz_m is not None:
            if len(self.void_size_xyz_m) != 3:
                raise ValueError("void_size_xyz_m must contain x, y, depth sizes.")
            sizes = tuple(float(value) for value in self.void_size_xyz_m)
            if any(value <= 0 for value in sizes):
                raise ValueError("void_size_xyz_m values must be positive.")
            object.__setattr__(self, "void_size_xyz_m", sizes)
