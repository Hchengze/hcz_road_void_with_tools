"""三维正演后端的抽象基类。

地球物理意义
------------
本项目最终需要比较不同层级的三维正演：

1. `kinematic`：只使用三维几何走时的点绕射近似；
2. `devito_acoustic_3d`：计划接入的三维声波波动方程有限差分正演；
3. `openswpc_elastic_3d`：计划接入的三维弹性/黏弹性外部正演程序。

这些后端的物理方程、输入文件和运行方式不同，但项目内部定位、可视化和
不确定性分析不应该关心这些差异。统一接口的最低要求是：每个后端都说明自己
是否可用，并把结果整理成 `ForwardResult3D`。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from hcz_road_void.forward.result import ForwardResult3D


class ForwardBackend(ABC):
    """三维正演后端统一接口。

    子类必须明确坐标约定：`x` 为沿道路或光纤方向，`y` 为横穿道路方向，
    `depth` 向下为正。后端可以是近似运动学算法，也可以是真实波动方程
    求解器，但 metadata 必须如实说明物理层级，不能把近似算法说成完整
    三维弹性波正演。
    """

    name: str = "base"
    physics_type: str = "unknown"

    @abstractmethod
    def is_available(self) -> bool:
        """检查当前环境是否可以使用该后端。

        这个函数必须“温和失败”：外部包未安装、可执行文件未配置、编译产物
        不存在时，应返回 `False`，而不是让整个项目导入失败。
        """

    @abstractmethod
    def run_forward(self, scenario: Any, config: Any) -> ForwardResult3D:
        """运行三维正演，并返回统一的 `ForwardResult3D`。"""

    def metadata(self) -> dict[str, Any]:
        """返回后端能力和物理层级说明。

        后续 `run_summary.json`、Notebook 和测试都会依赖这些字段判断当前
        正演是不是波动方程、是不是弹性波、是否支持真实波场快照和 DAS 轴向
        应变。因此这里宁可保守，也不能夸大能力。
        """

        return {
            "backend_name": self.name,
            "physics_type": self.physics_type,
            "is_wave_equation_solver": False,
            "is_elastic_solver": False,
            "supports_wavefield_snapshots": False,
            "supports_das_strain": False,
            "approximation": "未指定正演近似",
        }
