"""三维运动学点绕射后端。

该后端把当前已经跑通的 `simulate_kinematic_diffraction` 包装成统一
`ForwardBackend`。它只计算

`总走时 = 震源到异常体的走时 + 异常体到接收点的走时`

并在理论到时处叠加 Ricker 子波。它用于检查三维道路 DAS + 锤击观测几何、
数据维度和定位流程是否贯通，不是波动方程求解器。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from hcz_road_void.forward.backends.base import ForwardBackend
from hcz_road_void.forward.config import ForwardConfig
from hcz_road_void.forward.kinematic import simulate_kinematic_diffraction
from hcz_road_void.forward.result import ForwardResult3D


@dataclass(frozen=True)
class KinematicDiffractionBackend(ForwardBackend):
    """三维运动学绕射正演后端。

    `scatter_amplitude` 和 `geometric_spreading` 只控制当前近似合成记录的
    波形幅度。它们不是严格的三维空洞边界散射系数，也不包含模式转换、
    自由表面、多次波或 DAS 轴向应变观测。
    """

    scatter_amplitude: float = 8.0
    geometric_spreading: bool = True

    name: str = "kinematic"
    physics_type: str = "kinematic_diffraction"

    def is_available(self) -> bool:
        """运动学后端只依赖 NumPy 和本项目代码，因此始终可用。"""

        return True

    def metadata(self) -> dict[str, Any]:
        metadata = super().metadata()
        metadata.update(
            {
                "backend_name": self.name,
                "physics_type": self.physics_type,
                "is_wave_equation_solver": False,
                "is_elastic_solver": False,
                "supports_wavefield_snapshots": False,
                "supports_das_strain": False,
                "approximation": "单点绕射体 / 三维运动学走时近似",
                "wavefield_snapshot_type": "not_available",
                "is_true_wave_equation_wavefield": False,
            }
        )
        return metadata

    def run_forward(self, scenario: Any, config: ForwardConfig | None = None) -> ForwardResult3D:
        """从场景对象或场景字典中提取三维几何并运行运动学正演。

        这里故意只读取 `source_xyz`、`receiver_xyz`、`void_xyz` 和背景速度。
        如果后续场景里同时存在 `VoidBody3D`，当前后端仍默认取中心点作为
        等效点绕射体；多散射点代理会在单独函数中显式使用，避免暗中改变
        现有示例的行为。
        """

        config = config or _get_value(scenario, "config")
        source_xyz = _get_value(scenario, "source_xyz")
        receiver_xyz = _receiver_xyz_from_scenario(scenario)
        void_model = _get_value(scenario, "void_model", default=None)
        void_xyz = getattr(void_model, "void_xyz", None) or _get_value(scenario, "void_xyz")
        background_velocity_mps = float(_get_value(scenario, "background_velocity_mps"))

        result = simulate_kinematic_diffraction(
            source_xyz=source_xyz,
            receiver_xyz=receiver_xyz,
            void_xyz=void_xyz,
            background_velocity_mps=background_velocity_mps,
            config=config,
            scatter_amplitude=self.scatter_amplitude,
            geometric_spreading=self.geometric_spreading,
        )
        merged_metadata = dict(result.metadata)
        merged_metadata.update(self.metadata())
        return ForwardResult3D(
            data=result.data,
            time_axis_s=result.time_axis_s,
            source_xyz=result.source_xyz,
            receiver_xyz=result.receiver_xyz,
            travel_times_s=result.travel_times_s,
            metadata=merged_metadata,
        )


_MISSING = object()


def _get_value(scenario: Any, key: str, default: Any = _MISSING) -> Any:
    if isinstance(scenario, dict):
        if key in scenario:
            return scenario[key]
        if default is not _MISSING:
            return default
        raise KeyError(f"scenario 缺少字段: {key}")
    if hasattr(scenario, key):
        return getattr(scenario, key)
    if default is not _MISSING:
        return default
    raise AttributeError(f"scenario 缺少属性: {key}")


def _receiver_xyz_from_scenario(scenario: Any) -> Sequence[tuple[float, float, float]]:
    sampled_receivers = _get_value(scenario, "sampled_receivers", default=None)
    if sampled_receivers is not None and hasattr(sampled_receivers, "receiver_xyz"):
        return sampled_receivers.receiver_xyz
    receiver_xyz = _get_value(scenario, "receiver_xyz", default=None)
    if receiver_xyz is not None:
        return receiver_xyz
    receivers = _get_value(scenario, "receivers", default=None)
    if receivers is not None and hasattr(receivers, "receiver_xyz"):
        return receivers.receiver_xyz
    raise AttributeError("scenario 必须提供 receiver_xyz 或 sampled_receivers.receiver_xyz")
