"""波场快照接口。

Stage 2A 只建立接口，不生成假装真实的波动方程波场。当前运动学后端没有
网格波场变量，只能说明“不可用”。后续 Devito/OpenSWPC 接入后，可以把真实
压力、速度、位移或应变快照写入这里约定的数据结构和输出目录。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class WavefieldSnapshotResult:
    """波场快照输出状态。

    - `snapshot_type`：`not_available`、`proxy` 或 `true_wave_equation`；
    - `is_true_wave_equation_wavefield`：是否来自真实波动方程求解器；
    - `snapshot_paths`：已生成的快照图片或数据文件路径；
    - `animation_path`：波场动图路径，当前运动学后端为 `None`；
    - `metadata`：后端、物理量和限制说明。
    """

    snapshot_type: str
    is_true_wave_equation_wavefield: bool
    snapshot_paths: Sequence[str] = field(default_factory=tuple)
    animation_path: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "snapshot_type": self.snapshot_type,
            "is_true_wave_equation_wavefield": self.is_true_wave_equation_wavefield,
            "snapshot_paths": list(self.snapshot_paths),
            "animation_path": self.animation_path,
            "metadata": dict(self.metadata),
        }


def unavailable_wavefield_snapshots(backend_name: str) -> WavefieldSnapshotResult:
    """返回当前后端没有真实波场快照的明确状态。"""

    return WavefieldSnapshotResult(
        snapshot_type="not_available",
        is_true_wave_equation_wavefield=False,
        metadata={
            "backend_name": backend_name,
            "reason": "当前运动学绕射后端没有网格波场变量，不能输出真实波动方程快照。",
            "future_backend": "Devito 或 OpenSWPC 接入后再输出真实波场快照和动图。",
        },
    )


def ensure_wavefield_output_dir(output_dir: str | Path) -> Path:
    """创建波场快照输出目录。

    当前目录可以为空；它的存在用于固定后续输出约定：
    `outputs/wavefield_snapshots/snapshot_000.png` 等。
    """

    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path
