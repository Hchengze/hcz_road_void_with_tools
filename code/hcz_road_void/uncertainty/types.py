"""三维定位目标函数的不确定性诊断。

第一阶段不做严格概率反演，但必须避免只报一个“最佳点”。本模块从
三维目标函数体中提取一些轻量指标，用来提示定位是否尖锐、是否存在
横向 y 与深度 depth 的混淆。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from hcz_road_void.geometry import Coordinate3D
from hcz_road_void.localization import LocalizationResult3D


@dataclass(frozen=True)
class UncertaintySummary:
    """预留的三维置信度摘要容器。"""

    best_xyz: Coordinate3D
    confidence: float
    method: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1.")


@dataclass(frozen=True)
class ObjectiveUncertainty3D:
    """第一阶段目标函数体的不确定性指标。

    - ``best_to_second_ratio``：最大值与第二大值之比，越接近 1 表示峰值越不唯一；
    - ``half_max_voxel_count``：超过半高阈值的体素数量，越多表示高能区越宽；
    - ``*_half_width_m``：半高区域在 x、y、depth 方向上的跨度；
    - ``y_depth_confusion``：横向和深度都较宽且峰值不尖锐时置为 True；
    - ``normalized_objective``：归一化目标函数体，便于绘图和后续统计。
    """

    best_to_second_ratio: float
    half_max_voxel_count: int
    half_max_fraction: float
    x_half_width_m: float
    y_half_width_m: float
    depth_half_width_m: float
    y_depth_confusion: bool
    normalized_objective: np.ndarray

    def as_dict(self) -> dict[str, float | bool | int]:
        return {
            "best_to_second_ratio": self.best_to_second_ratio,
            "half_max_voxel_count": self.half_max_voxel_count,
            "half_max_fraction": self.half_max_fraction,
            "x_half_width_m": self.x_half_width_m,
            "y_half_width_m": self.y_half_width_m,
            "depth_half_width_m": self.depth_half_width_m,
            "y_depth_confusion": self.y_depth_confusion,
        }


def summarize_objective_uncertainty(
    result: LocalizationResult3D,
    half_max_threshold: float = 0.5,
) -> ObjectiveUncertainty3D:
    """从三维目标函数体计算轻量不确定性指标。

    指标解释：

    - best/second ratio 反映目标函数峰值是否唯一；
    - half-max 区域表示“得分接近最佳点”的候选体积；
    - y-depth confusion 关注单侧 DAS 光纤或单侧震源时常见的横向-深度
      trade-off：如果 y 方向和 depth 方向的半高区域都很宽，说明定位虽然
      有最佳点，但横向位置和埋深可能并不稳定。
    """

    if not 0.0 < half_max_threshold <= 1.0:
        raise ValueError("half_max_threshold must be in (0, 1].")
    objective = np.asarray(result.objective_volume, dtype=float)
    best = float(np.max(objective))
    if best <= 0:
        normalized = np.zeros_like(objective)
        ratio = 0.0
    else:
        normalized = objective / best
        flat = np.sort(objective.ravel())
        second = float(flat[-2]) if flat.size > 1 else 0.0
        ratio = float("inf") if second <= 0 else best / second

    # 半高区域是一个很朴素但直观的“可能位置范围”：所有得分超过
    # best * threshold 的候选点都被视为与最佳点相近。
    mask = normalized >= half_max_threshold
    half_count = int(np.count_nonzero(mask))
    half_fraction = float(half_count / normalized.size)
    x_width = _axis_width(result.search_grid.search_x, mask, axis=0)
    y_width = _axis_width(result.search_grid.search_y, mask, axis=1)
    depth_width = _axis_width(result.search_grid.search_depth, mask, axis=2)
    y_depth_confusion = bool(y_width > 0 and depth_width > 0 and ratio < 1.15)

    return ObjectiveUncertainty3D(
        best_to_second_ratio=ratio,
        half_max_voxel_count=half_count,
        half_max_fraction=half_fraction,
        x_half_width_m=x_width,
        y_half_width_m=y_width,
        depth_half_width_m=depth_width,
        y_depth_confusion=y_depth_confusion,
        normalized_objective=normalized,
    )


def _axis_width(axis_values: Sequence[float], mask: np.ndarray, axis: int) -> float:
    collapsed = np.any(mask, axis=tuple(index for index in range(mask.ndim) if index != axis))
    indices = np.where(collapsed)[0]
    if indices.size <= 1:
        return 0.0
    values = tuple(float(value) for value in axis_values)
    return values[int(indices[-1])] - values[int(indices[0])]
