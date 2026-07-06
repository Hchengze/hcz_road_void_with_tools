"""三维道路场景的速度模型元数据。

第一阶段只使用常速度背景来支撑运动学走时计算。这里保留 ``vp``、``vs``
和密度，是为了后续接入弹性波正演工具时不用重做模型接口。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VelocityModel3D:
    """第一阶段常速度三维介质参数。

    字段单位：

    - ``vp_mps``：P 波速度，m/s；
    - ``vs_mps``：S 波速度，m/s；
    - ``density_kg_m3``：密度，kg/m^3；
    - ``name``：模型名称，仅作元数据。

    当前正演没有求解弹性波方程，只用 ``rayleigh_velocity_mps`` 作为浅层
    面波/绕射运动学近似速度。
    """

    vp_mps: float
    vs_mps: float
    density_kg_m3: float
    name: str = "constant_3d"

    def __post_init__(self) -> None:
        if self.vp_mps <= 0:
            raise ValueError("vp_mps must be positive.")
        if self.vs_mps <= 0:
            raise ValueError("vs_mps must be positive.")
        if self.density_kg_m3 <= 0:
            raise ValueError("density_kg_m3 must be positive.")
        if self.vp_mps <= self.vs_mps:
            raise ValueError("vp_mps must be greater than vs_mps for the elastic Stage 1 model.")

    @property
    def rayleigh_velocity_mps(self) -> float:
        """返回一个粗略 Rayleigh 波速度占位值。

        工程上常用 ``0.9 * vs`` 量级估计 Rayleigh 速度。这里取 ``0.92``，
        只用于第一阶段走时闭环，不代表经过现场反演的真实速度。
        """

        return 0.92 * self.vs_mps
