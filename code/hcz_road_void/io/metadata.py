"""共享元数据约定。

这个模块集中记录坐标轴含义，供输出 JSON、Notebook 和后续文件读写模块
复用。JSON key 可以保持英文，解释性 value 使用中文，便于用户直接阅读。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CoordinateConvention:
    """项目统一三维坐标约定。"""

    x_axis: str = "沿道路或 DAS 光纤方向"
    y_axis: str = "横穿道路方向"
    depth_axis: str = "向下为正"
    coordinate_units: str = "m"


DEFAULT_COORDINATE_CONVENTION = CoordinateConvention()
