"""三维道路地下空洞探测原型包。

包内模块围绕统一三维坐标 ``x-y-depth`` 组织：几何、速度模型、DAS 光纤
接收、运动学绕射正演、三维定位搜索和不确定性诊断。当前阶段是算法
原型，不是完整三维弹性波工业软件。
"""

from hcz_road_void.forward import ForwardConfig, predict_point_scatter_travel_time, simulate_kinematic_diffraction
from hcz_road_void.geometry import Coordinate3D, RoadVoidScenario, SourceArray3D
from hcz_road_void.localization import SearchGrid3D, travel_time_energy_stack
from hcz_road_void.models import VelocityModel3D, VoidModel3D
from hcz_road_void.receivers import DASChannelGeometry3D, PointReceiverGeometry3D, ReceiverPolyline3D

__all__ = [
    "Coordinate3D",
    "DASChannelGeometry3D",
    "ForwardConfig",
    "PointReceiverGeometry3D",
    "ReceiverPolyline3D",
    "RoadVoidScenario",
    "SearchGrid3D",
    "SourceArray3D",
    "VelocityModel3D",
    "VoidModel3D",
    "predict_point_scatter_travel_time",
    "simulate_kinematic_diffraction",
    "travel_time_energy_stack",
]
