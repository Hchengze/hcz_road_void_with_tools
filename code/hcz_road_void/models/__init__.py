"""物理模型数据结构。

当前包含常速度背景模型和最小空洞模型。二者均服务于三维道路空洞场景。
"""

from hcz_road_void.models.velocity import VelocityModel3D
from hcz_road_void.models.velocity_grid import VelocityGrid3D, build_uniform_road_velocity_grid
from hcz_road_void.models.void import VoidModel3D
from hcz_road_void.models.void_body import (
    VoidBody3D,
    VoidBodyType,
    embed_void_body_into_velocity_grid,
    sample_void_body_as_scatterers,
)

__all__ = [
    "VelocityGrid3D",
    "VelocityModel3D",
    "VoidBody3D",
    "VoidBodyType",
    "VoidModel3D",
    "build_uniform_road_velocity_grid",
    "embed_void_body_into_velocity_grid",
    "sample_void_body_as_scatterers",
]
