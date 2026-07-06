"""三维定位搜索接口。

定位主线是对 ``search_x``、``search_y`` 和 ``search_depth`` 形成的真实
三维网格做 travel-time energy stack，不输出伪三维的二维剖面结果。
"""

from hcz_road_void.localization.energy_stack import (
    LocalizationResult3D,
    extract_objective_slices,
    travel_time_energy_stack,
)
from hcz_road_void.localization.search_grid import SearchGrid3D

__all__ = [
    "LocalizationResult3D",
    "SearchGrid3D",
    "extract_objective_slices",
    "travel_time_energy_stack",
]
