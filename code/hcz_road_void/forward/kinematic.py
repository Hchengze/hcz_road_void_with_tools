"""三维运动学绕射正演工具。

本模块实现第一阶段最小正演闭环：把地下空洞近似为一个点绕射体，
用三维欧氏距离计算震源到空洞、空洞到接收点的传播时间，并在该时间
位置放置一个 Ricker 子波。

重要边界：

- 这里没有求解声波方程或弹性波方程；
- 没有自由表面、PML、模式转换、真实散射振幅或 DAS 应变算子；
- 结果只能用于验证三维几何、走时关系和定位目标函数。
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from hcz_road_void.geometry import Coordinate3D, distance_3d, ensure_coordinate3d
from hcz_road_void.forward.config import ForwardConfig
from hcz_road_void.forward.result import ForwardResult3D


def predict_point_scatter_travel_time(
    source_xyz: Coordinate3D | Sequence[float],
    receiver_xyz: Coordinate3D | Sequence[float],
    scatter_xyz: Coordinate3D | Sequence[float],
    velocity_mps: float,
) -> float:
    """预测三维点绕射路径的总走时。

    物理含义是：

    ``总走时 = 震源到空洞的传播时间 + 空洞到接收点的传播时间``

    即：

    ``t_total = |source_xyz - scatter_xyz| / v + |scatter_xyz - receiver_xyz| / v``

    这里的 ``source_xyz``、``receiver_xyz`` 和 ``scatter_xyz`` 均为
    ``(x, y, depth)``，所以横向 y 偏移会真实进入路径长度计算。
    """

    if velocity_mps <= 0:
        raise ValueError("velocity_mps must be positive.")
    source = ensure_coordinate3d(source_xyz, "source_xyz")
    receiver = ensure_coordinate3d(receiver_xyz, "receiver_xyz")
    scatter = ensure_coordinate3d(scatter_xyz, "scatter_xyz")
    return (distance_3d(source, scatter) + distance_3d(scatter, receiver)) / velocity_mps


def ricker_wavelet(time_offsets_s: np.ndarray, frequency_hz: float) -> np.ndarray:
    """生成以零时刻为中心的 Ricker 子波。

    Ricker 子波是地震勘探中常用的零相位子波。这里用它给运动学走时
    加一个“像波形”的脉冲，使后续能量栈可以从时间记录中取样。
    """

    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be positive.")
    arg = np.pi * frequency_hz * time_offsets_s
    arg2 = arg * arg
    return (1.0 - 2.0 * arg2) * np.exp(-arg2)


def simulate_kinematic_diffraction(
    source_xyz: Sequence[Coordinate3D | Sequence[float]],
    receiver_xyz: Sequence[Coordinate3D | Sequence[float]],
    void_xyz: Coordinate3D | Sequence[float],
    background_velocity_mps: float,
    config: ForwardConfig,
    scatter_amplitude: float = 1.0,
    geometric_spreading: bool = True,
) -> ForwardResult3D:
    """生成三维运动学点绕射合成记录。

    输出数据顺序为 ``n_sources x n_receivers x n_times``。

    对每一对震源和接收通道：

    1. 计算震源到空洞中心的三维距离；
    2. 计算空洞中心到接收通道的三维距离；
    3. 用背景速度把两段距离换算成总走时；
    4. 在时间轴对应位置叠加 Ricker 子波；
    5. 可选地用简单几何扩散因子衰减振幅。

    这仍然是单点绕射体的运动学近似，不是完整三维弹性波正演。
    """

    if background_velocity_mps <= 0:
        raise ValueError("background_velocity_mps must be positive.")
    if scatter_amplitude == 0:
        raise ValueError("scatter_amplitude must be nonzero.")

    sources = tuple(ensure_coordinate3d(source, f"source_xyz[{index}]") for index, source in enumerate(source_xyz))
    receivers = tuple(ensure_coordinate3d(receiver, f"receiver_xyz[{index}]") for index, receiver in enumerate(receiver_xyz))
    if not sources:
        raise ValueError("source_xyz must not be empty.")
    if not receivers:
        raise ValueError("receiver_xyz must not be empty.")
    void = ensure_coordinate3d(void_xyz, "void_xyz")

    time_axis_s = np.arange(config.nt, dtype=float) * config.dt_s
    data = np.zeros((len(sources), len(receivers), config.nt), dtype=float)
    travel_times_s = np.zeros((len(sources), len(receivers)), dtype=float)

    for isource, source in enumerate(sources):
        for ireceiver, receiver in enumerate(receivers):
            # 三维路径分成两段：source -> void 和 void -> receiver。
            # 因为使用 distance_3d，x、y、depth 三个方向都会影响走时；
            # 这正是本项目不能退化为 x-depth 二维剖面的关键。
            source_to_void = distance_3d(source, void)
            void_to_receiver = distance_3d(void, receiver)
            travel_time = (source_to_void + void_to_receiver) / background_velocity_mps
            travel_times_s[isource, ireceiver] = travel_time

            # 几何扩散只是一个保守的振幅占位：传播路径越长，振幅越弱。
            # 它不能替代真实三维弹性散射振幅。
            amplitude = scatter_amplitude
            if geometric_spreading:
                amplitude /= np.sqrt(max(source_to_void * void_to_receiver, 1.0))

            # 把零相位 Ricker 子波平移到理论绕射走时处，形成合成记录。
            data[isource, ireceiver, :] += amplitude * ricker_wavelet(
                time_axis_s - travel_time,
                config.wavelet_frequency_hz,
            )

    metadata = {
        "forward_type": "3d_kinematic_diffraction",
        "data_order": "n_sources x n_receivers x n_times",
        "background_velocity_mps": background_velocity_mps,
        "is_wave_equation_solver": False,
        "is_elastic_solver": False,
        "is_kinematic_approximation": True,
        "approximation": "单点绕射体 / 运动学走时近似",
        "uses_external_tool": False,
        "wavelet": "Ricker",
        "geometric_spreading": geometric_spreading,
    }
    return ForwardResult3D(
        data=data,
        time_axis_s=time_axis_s,
        source_xyz=tuple(source.xyz for source in sources),
        receiver_xyz=tuple(receiver.xyz for receiver in receivers),
        travel_times_s=travel_times_s,
        metadata=metadata,
    )
