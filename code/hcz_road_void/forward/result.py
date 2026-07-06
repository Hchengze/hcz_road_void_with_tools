"""正演结果容器。

正演结果不仅包含合成记录，还要携带 source、receiver、time axis 和
metadata。这样后续定位、不确定性分析和可视化不会从不同地方读取互相
矛盾的几何参数。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ForwardResult3D:
    """三维正演输出。

    - ``data``：合成记录，当前约定为 ``n_sources x n_receivers x n_times``；
    - ``time_axis_s``：时间轴，单位 s；
    - ``source_xyz``：每个震源的三维坐标；
    - ``receiver_xyz``：每个接收通道的三维坐标；
    - ``travel_times_s``：理论绕射走时表；
    - ``metadata``：正演类型、速度、近似性质和数据顺序说明。
    """

    data: Any
    time_axis_s: Sequence[float]
    source_xyz: Sequence[tuple[float, float, float]]
    receiver_xyz: Sequence[tuple[float, float, float]]
    travel_times_s: Any | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.time_axis_s) == 0:
            raise ValueError("time_axis_s must not be empty.")
        if len(self.source_xyz) == 0:
            raise ValueError("source_xyz must not be empty.")
        if len(self.receiver_xyz) == 0:
            raise ValueError("receiver_xyz must not be empty.")
