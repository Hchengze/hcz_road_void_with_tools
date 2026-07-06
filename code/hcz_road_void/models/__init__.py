"""物理模型数据结构。

当前包含常速度背景模型和最小空洞模型。二者均服务于三维道路空洞场景。
"""

from hcz_road_void.models.velocity import VelocityModel3D
from hcz_road_void.models.void import VoidModel3D

__all__ = ["VelocityModel3D", "VoidModel3D"]
