"""正演计算配置。

本模块只描述第一阶段运动学正演的时间采样和元数据标记。它故意包含
``is_wave_equation_solver``、``is_elastic_solver`` 等布尔字段，是为了在
输出中清楚声明：当前结果不是完整三维弹性波正演。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ForwardConfig:
    """第一阶段三维运动学绕射正演配置。

    - ``dt_s``：时间采样间隔，单位 s；
    - ``nt``：时间采样点数；
    - ``wavelet_frequency_hz``：Ricker 子波主频，单位 Hz；
    - ``forward_type``：正演类型元数据，默认三维运动学绕射；
    - 其余布尔字段用于防止误把运动学近似标成波动方程求解器。
    """

    dt_s: float
    nt: int
    wavelet_frequency_hz: float
    forward_type: str = "3d_kinematic_diffraction"
    is_kinematic_approximation: bool = True
    solves_full_wave_equation: bool = False
    uses_external_tool: bool = False
    is_wave_equation_solver: bool = False
    is_elastic_solver: bool = False

    def __post_init__(self) -> None:
        if self.dt_s <= 0:
            raise ValueError("dt_s must be positive.")
        if self.nt <= 0:
            raise ValueError("nt must be positive.")
        if self.wavelet_frequency_hz <= 0:
            raise ValueError("wavelet_frequency_hz must be positive.")
        if self.solves_full_wave_equation and self.is_kinematic_approximation:
            raise ValueError("A forward config cannot be both full-wave and kinematic-only.")
        if self.is_wave_equation_solver or self.is_elastic_solver:
            raise ValueError("Stage 1 ForwardConfig must not claim a wave-equation or elastic solver.")
