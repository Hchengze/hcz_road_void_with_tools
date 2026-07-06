"""三维走时能量栈定位。

定位思想：如果某个候选点 ``candidate_xyz=(x, y, depth)`` 真的是空洞或
强散射体，那么多炮多道记录中应该在

``source -> candidate -> receiver``

的理论绕射走时附近出现较强能量。于是我们遍历三维搜索网格，对每个
候选点计算所有 source/receiver 对的理论走时，并从记录相应时间附近
提取绝对振幅能量后叠加。目标函数高值表示该候选点更能解释观测记录。

这仍是运动学 travel-time energy stack，不是偏移成像、FWI 或概率反演。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from hcz_road_void.geometry import Coordinate3D, ensure_coordinate3d
from hcz_road_void.localization.search_grid import SearchGrid3D


@dataclass(frozen=True)
class LocalizationResult3D:
    """三维定位搜索结果。

    - ``best_xyz``：目标函数最大处的候选空洞位置；
    - ``objective_volume``：三维目标函数体，维度为 ``x-y-depth``；
    - ``search_grid``：生成目标函数体的搜索轴；
    - ``best_score``：最大目标函数值；
    - ``best_index``：最大值在三维数组中的索引；
    - ``true_xyz`` 和 ``localization_error_m``：合成测试中可选的真值和误差。
    """

    best_xyz: Coordinate3D
    objective_volume: np.ndarray
    search_grid: SearchGrid3D
    best_score: float
    best_index: tuple[int, int, int]
    true_xyz: Coordinate3D | None = None
    localization_error_m: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


def travel_time_energy_stack(
    data: np.ndarray,
    time_axis_s: Sequence[float],
    source_xyz: Sequence[Coordinate3D | Sequence[float]],
    receiver_xyz: Sequence[Coordinate3D | Sequence[float]],
    background_velocity_mps: float,
    search_grid: SearchGrid3D,
    half_window_samples: int = 2,
    true_xyz: Coordinate3D | Sequence[float] | None = None,
) -> LocalizationResult3D:
    """对三维候选点执行 travel-time energy stack。

    输入 ``data`` 的维度必须是 ``n_sources x n_receivers x n_times``。
    搜索空间必须包含 ``search_x``、``search_y`` 和 ``search_depth``。

    对每个候选点：

    1. 计算震源到候选点的三维距离；
    2. 计算候选点到接收通道的三维距离；
    3. 用背景速度得到理论绕射走时；
    4. 在合成记录中取该时间附近的绝对振幅最大值；
    5. 对所有炮和通道平均，形成候选点得分。

    因为候选点同时改变 x、y、depth，高分区域能够揭示沿道路方向聚焦、
    横向位置不确定性和深度不确定性，而不是只给出二维剖面答案。
    """

    if background_velocity_mps <= 0:
        raise ValueError("background_velocity_mps must be positive.")
    if half_window_samples < 0:
        raise ValueError("half_window_samples must be nonnegative.")

    data_array = np.asarray(data, dtype=float)
    time_axis = np.asarray(time_axis_s, dtype=float)
    if data_array.ndim != 3:
        raise ValueError("data must have shape n_sources x n_receivers x n_times.")
    if time_axis.ndim != 1 or time_axis.size == 0:
        raise ValueError("time_axis_s must be a nonempty 1D sequence.")
    if data_array.shape[2] != time_axis.size:
        raise ValueError("data time dimension must match time_axis_s length.")
    if time_axis.size > 1 and np.any(np.diff(time_axis) <= 0):
        raise ValueError("time_axis_s must be strictly increasing.")

    sources = tuple(ensure_coordinate3d(source, f"source_xyz[{index}]") for index, source in enumerate(source_xyz))
    receivers = tuple(ensure_coordinate3d(receiver, f"receiver_xyz[{index}]") for index, receiver in enumerate(receiver_xyz))
    if data_array.shape[:2] != (len(sources), len(receivers)):
        raise ValueError("data source/receiver dimensions must match source_xyz and receiver_xyz.")

    # objective 保存每个候选 (x, y, depth) 的能量栈得分。
    objective = np.zeros(search_grid.shape, dtype=float)
    count_volume = np.zeros(search_grid.shape, dtype=int)

    # meshgrid 生成三维候选坐标体。后续每个 source/receiver 对都在整个
    # 体上一次性计算走时，比三重 Python 循环更快，但物理目标函数不变。
    grid_x, grid_y, grid_depth = np.meshgrid(
        np.asarray(search_grid.search_x, dtype=float),
        np.asarray(search_grid.search_y, dtype=float),
        np.asarray(search_grid.search_depth, dtype=float),
        indexing="ij",
    )
    abs_data = np.abs(data_array)

    for isource, source in enumerate(sources):
        # 震源到所有候选点的三维距离。这里 y 和 depth 同等进入距离公式，
        # 因而不会退化成 x-depth 二维扫描。
        source_distance = np.sqrt(
            (grid_x - source.x) ** 2
            + (grid_y - source.y) ** 2
            + (grid_depth - source.depth) ** 2
        )
        for ireceiver, receiver in enumerate(receivers):
            # 候选点到当前接收通道的三维距离。DAS 通道在第一阶段是点接收器近似。
            receiver_distance = np.sqrt(
                (grid_x - receiver.x) ** 2
                + (grid_y - receiver.y) ** 2
                + (grid_depth - receiver.depth) ** 2
            )
            tau = (source_distance + receiver_distance) / background_velocity_mps
            center_samples = np.searchsorted(time_axis, tau)
            trace = abs_data[isource, ireceiver, :]

            pair_scores = np.zeros(search_grid.shape, dtype=float)
            valid_pair = np.zeros(search_grid.shape, dtype=bool)
            for offset in range(-half_window_samples, half_window_samples + 1):
                # half_window_samples 允许在理论走时附近取一个小窗口，以容纳
                # 子波宽度、采样误差和轻微速度误差。窗口内取最大绝对振幅，
                # 作为这一炮一道对当前候选点的能量贡献。
                sample_indices = center_samples + offset
                valid = (sample_indices >= 0) & (sample_indices < time_axis.size)
                if not np.any(valid):
                    continue
                pair_scores[valid] = np.maximum(pair_scores[valid], trace[sample_indices[valid]])
                valid_pair |= valid

            objective += pair_scores
            count_volume += valid_pair.astype(int)

    # 用有效炮道对数量归一化，避免时间窗落在记录外的候选点被系统性偏置。
    objective = objective / np.maximum(count_volume, 1)

    best_flat = int(np.argmax(objective))
    best_index = tuple(int(value) for value in np.unravel_index(best_flat, objective.shape))
    best_xyz = Coordinate3D(
        search_grid.search_x[best_index[0]],
        search_grid.search_y[best_index[1]],
        search_grid.search_depth[best_index[2]],
    )
    true_point = ensure_coordinate3d(true_xyz, "true_xyz") if true_xyz is not None else None
    error = None
    if true_point is not None:
        dx = best_xyz.x - true_point.x
        dy = best_xyz.y - true_point.y
        dz = best_xyz.depth - true_point.depth
        error = float(np.sqrt(dx * dx + dy * dy + dz * dz))

    return LocalizationResult3D(
        best_xyz=best_xyz,
        objective_volume=objective,
        search_grid=search_grid,
        best_score=float(objective[best_index]),
        best_index=best_index,
        true_xyz=true_point,
        localization_error_m=error,
        metadata={
            "localization_type": "3d_travel_time_energy_stack",
            "objective_order": "x-y-depth",
            "half_window_samples": half_window_samples,
            "is_3d_search": True,
            "uses_only_x_depth": False,
        },
    )


def extract_objective_slices(result: LocalizationResult3D) -> dict[str, np.ndarray]:
    """提取穿过最佳候选点的三张诊断切片。

    - ``x_depth_at_best_y``：固定最佳 y，观察沿线位置和深度聚焦；
    - ``y_depth_at_best_x``：固定最佳 x，观察横向位置和深度混淆；
    - ``x_y_at_best_depth``：固定最佳 depth，观察道路平面内的定位范围。
    """

    ix, iy, iz = result.best_index
    return {
        "x_depth_at_best_y": result.objective_volume[:, iy, :],
        "y_depth_at_best_x": result.objective_volume[ix, :, :],
        "x_y_at_best_depth": result.objective_volume[:, :, iz],
    }
