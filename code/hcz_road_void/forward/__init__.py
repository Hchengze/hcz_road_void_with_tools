"""正演接口。

当前只导出三维运动学点绕射正演及其配置和结果容器。后续接入 Devito 或
OpenSWPC 时，应保持这里的三维几何接口不变。
"""

from hcz_road_void.forward.config import ForwardConfig
from hcz_road_void.forward.backends import (
    DevitoBackend,
    ForwardBackend,
    KinematicDiffractionBackend,
    OpenSWPCBackend,
)
from hcz_road_void.forward.kinematic import (
    predict_point_scatter_travel_time,
    ricker_wavelet,
    simulate_kinematic_diffraction,
)
from hcz_road_void.forward.result import ForwardResult3D

__all__ = [
    "ForwardConfig",
    "ForwardBackend",
    "ForwardResult3D",
    "DevitoBackend",
    "KinematicDiffractionBackend",
    "OpenSWPCBackend",
    "predict_point_scatter_travel_time",
    "ricker_wavelet",
    "simulate_kinematic_diffraction",
]
