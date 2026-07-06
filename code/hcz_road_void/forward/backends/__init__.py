"""三维正演后端统一入口。

本目录的作用是把“正演方法”从 `main.py` 中抽出来。这样当前的三维运动学
绕射近似、后续的 Devito 三维声波方程正演、以及 OpenSWPC 三维弹性/黏弹性
外部程序，都可以返回同一种 `ForwardResult3D` 数据结构。
"""

from hcz_road_void.forward.backends.base import ForwardBackend
from hcz_road_void.forward.backends.devito_backend import DevitoBackend
from hcz_road_void.forward.backends.kinematic_backend import KinematicDiffractionBackend
from hcz_road_void.forward.backends.openswpc_backend import OpenSWPCBackend

__all__ = [
    "DevitoBackend",
    "ForwardBackend",
    "KinematicDiffractionBackend",
    "OpenSWPCBackend",
]
