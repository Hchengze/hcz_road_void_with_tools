"""Devito 三维声波正演后端占位接口。

本文件不直接实现 Devito 求解器。Stage 2A 的目标是让项目能够识别 Devito
是否可用，并为后续把 `VelocityGrid3D`、`source_xyz`、`receiver_xyz` 转换成
Devito `Grid`、`Model`、`RickerSource`、`Receiver` 和 `Operator` 做好接口。
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from typing import Any

from hcz_road_void.forward.backends.base import ForwardBackend
from hcz_road_void.forward.result import ForwardResult3D


@dataclass(frozen=True)
class DevitoBackend(ForwardBackend):
    """计划接入的 Devito 三维声波方程后端。

    当前 `myvoid` 环境未必安装 Devito，所以 `is_available()` 只做 import
    探测。真实正演实现需要下一轮明确安装依赖、选择网格间距、CFL 时间步长、
    吸收边界和快照输出策略后再落地。
    """

    name: str = "devito_acoustic_3d"
    physics_type: str = "acoustic_wave_equation"

    def is_available(self) -> bool:
        """Devito 未安装时返回 False，不影响项目其它测试。"""

        return find_spec("devito") is not None

    def metadata(self) -> dict[str, Any]:
        metadata = super().metadata()
        metadata.update(
            {
                "backend_name": self.name,
                "physics_type": self.physics_type,
                "is_wave_equation_solver": True,
                "is_elastic_solver": False,
                "supports_wavefield_snapshots": True,
                "supports_das_strain": False,
                "approximation": "计划接入 Devito 三维声波方程；当前仅完成可用性检查和接口占位",
            }
        )
        return metadata

    def run_forward(self, scenario: Any, config: Any) -> ForwardResult3D:
        """真实 Devito 正演尚未实现，调用时给出明确错误。"""

        raise NotImplementedError(
            "DevitoBackend 目前只是 Stage 2A 接口占位；下一轮安装并验证 Devito 后再实现三维声波正演。"
        )
