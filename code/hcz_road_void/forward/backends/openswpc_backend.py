"""OpenSWPC 三维弹性/黏弹性外部正演后端占位接口。

OpenSWPC 是 Fortran/MPI 外部程序，不应被强行改写成 Python 包。推荐路线是：
本项目生成速度模型、震源文件、接收点文件和参数文件，然后调用 OpenSWPC
可执行文件，最后把 SAC/NetCDF/快照输出读回 `ForwardResult3D`。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hcz_road_void.forward.backends.base import ForwardBackend
from hcz_road_void.forward.result import ForwardResult3D


@dataclass(frozen=True)
class OpenSWPCBackend(ForwardBackend):
    """计划接入的 OpenSWPC 三维弹性/黏弹性后端。

    `executable_path` 可以显式传入，也可以通过环境变量
    `OPENSWPC_EXECUTABLE` 或 `SWPC_3D_EXECUTABLE` 配置。未配置或文件不存在时，
    `is_available()` 返回 False，项目仍可运行运动学后端。
    """

    executable_path: str | None = None
    name: str = "openswpc_elastic_3d"
    physics_type: str = "elastic_or_viscoelastic_wave_equation"

    def is_available(self) -> bool:
        path = self._resolved_executable_path()
        return path is not None and path.is_file()

    def metadata(self) -> dict[str, Any]:
        metadata = super().metadata()
        metadata.update(
            {
                "backend_name": self.name,
                "physics_type": self.physics_type,
                "is_wave_equation_solver": True,
                "is_elastic_solver": True,
                "supports_wavefield_snapshots": True,
                "supports_das_strain": True,
                "approximation": "计划通过外部 OpenSWPC 程序运行三维弹性/黏弹性正演；当前仅完成接口占位",
                "executable_path": str(self._resolved_executable_path()) if self._resolved_executable_path() else None,
            }
        )
        return metadata

    def run_forward(self, scenario: Any, config: Any) -> ForwardResult3D:
        raise NotImplementedError(
            "OpenSWPCBackend 目前只是 Stage 2A 接口占位；需要先编译并配置 OpenSWPC 可执行文件。"
        )

    def _resolved_executable_path(self) -> Path | None:
        raw_path = self.executable_path or os.environ.get("OPENSWPC_EXECUTABLE") or os.environ.get("SWPC_3D_EXECUTABLE")
        if not raw_path:
            return None
        return Path(raw_path)
