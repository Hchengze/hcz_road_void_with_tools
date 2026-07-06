"""点接收器与 DAS 光纤几何。

DAS 光纤不是普通三分量检波器。真实 DAS 观测通常对应沿光纤切向的
轴向应变或应变率，并且需要在 gauge length 上做平均。第一阶段还没有
弹性位移场和应变张量，因此这里只实现“光纤折线采样为点通道”的代理：

- ``receiver_polyline`` 描述三维光纤路径；
- ``sample_channels`` 按固定间距生成 ``receiver_xyz``；
- 每个通道保存局部切向量和 gauge length 元数据；
- 正演仍把这些通道当作点接收器使用。
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Sequence

from hcz_road_void.geometry import Coordinate3D, distance_3d, ensure_coordinate3d


@dataclass(frozen=True)
class PointReceiverGeometry3D:
    """三维点接收器集合。

    每个接收点都是 ``(x, y, depth)``，单位 m。它可以代表普通检波器，
    也可以代表 DAS 光纤在第一阶段被采样后的近似点通道。
    """

    receivers: Sequence[Coordinate3D | Sequence[float]]

    def __post_init__(self) -> None:
        normalized = tuple(
            ensure_coordinate3d(receiver, f"receivers[{index}]")
            for index, receiver in enumerate(self.receivers)
        )
        if not normalized:
            raise ValueError("PointReceiverGeometry3D requires at least one receiver.")
        object.__setattr__(self, "receivers", normalized)

    @property
    def receiver_xyz(self) -> tuple[tuple[float, float, float], ...]:
        return tuple(receiver.xyz for receiver in self.receivers)


@dataclass(frozen=True)
class ReceiverPolyline3D:
    """DAS/光纤三维折线。

    - ``points``：光纤折线节点，每个节点为 ``(x, y, depth)``；
    - ``gauge_length_m``：DAS gauge length 元数据，单位 m；
    - ``channel_spacing_m``：相邻采样通道间距，单位 m。

    当前不会用 gauge length 计算真实轴向应变，只把它记录下来，为后续
    ``e^T epsilon(u) e`` 和有限长度平均算子预留接口。
    """

    points: Sequence[Coordinate3D | Sequence[float]]
    gauge_length_m: float
    channel_spacing_m: float

    def __post_init__(self) -> None:
        normalized = tuple(
            ensure_coordinate3d(point, f"points[{index}]")
            for index, point in enumerate(self.points)
        )
        if len(normalized) < 2:
            raise ValueError("ReceiverPolyline3D requires at least two points.")
        if self.gauge_length_m <= 0:
            raise ValueError("gauge_length_m must be positive.")
        if self.channel_spacing_m <= 0:
            raise ValueError("channel_spacing_m must be positive.")
        object.__setattr__(self, "points", normalized)

    @property
    def receiver_polyline(self) -> tuple[tuple[float, float, float], ...]:
        return tuple(point.xyz for point in self.points)

    @property
    def length_m(self) -> float:
        return sum(distance_3d(a, b) for a, b in zip(self.points[:-1], self.points[1:]))

    def sample_channels(self, include_endpoint: bool = True) -> "DASChannelGeometry3D":
        """按固定通道间距采样三维光纤折线。

        返回的 ``DASChannelGeometry3D`` 包含：

        - 采样点三维坐标 ``receiver_xyz``；
        - 每个采样点所在折线段的单位切向量；
        - gauge length 和 channel spacing 元数据。

        第一阶段仍把这些通道作为点接收器使用，不做真实 gauge-length
        平均轴向应变。
        """

        # cumulative distances 是沿光纤折线的弧长坐标，用来把一维通道距离
        # 映射回三维空间中的 (x, y, depth)。
        distances = [0.0]
        for start, end in zip(self.points[:-1], self.points[1:]):
            distances.append(distances[-1] + distance_3d(start, end))

        total_length = distances[-1]
        sample_distances = []
        current = 0.0
        while current <= total_length:
            sample_distances.append(current)
            current += self.channel_spacing_m
        if include_endpoint and sample_distances[-1] < total_length:
            sample_distances.append(total_length)

        samples: list[Coordinate3D] = []
        tangents: list[tuple[float, float, float]] = []
        for sample_distance in sample_distances:
            point, tangent = _interpolate_polyline(self.points, distances, sample_distance)
            samples.append(point)
            tangents.append(tangent)

        return DASChannelGeometry3D(
            receivers=tuple(samples),
            tangent_xyz=tuple(tangents),
            gauge_length_m=self.gauge_length_m,
            channel_spacing_m=self.channel_spacing_m,
            source_polyline=self,
        )


@dataclass(frozen=True)
class DASChannelGeometry3D(PointReceiverGeometry3D):
    """由光纤折线采样得到的 DAS 通道点。

    当前 ``observation_type`` 明确标为点接收器近似。真实 DAS 算子需要：

    1. 弹性位移场 ``u``；
    2. 应变张量 ``epsilon(u)``；
    3. 光纤切向量 ``e``；
    4. 轴向应变 ``e^T epsilon(u) e``；
    5. gauge length 上的有限长度平均或差分。

    这些都不是第一阶段的实现内容。
    """

    tangent_xyz: Sequence[Sequence[float]]
    gauge_length_m: float
    channel_spacing_m: float
    source_polyline: ReceiverPolyline3D | None = None
    observation_type: str = "point_receiver_approximation"

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.gauge_length_m <= 0:
            raise ValueError("gauge_length_m must be positive.")
        if self.channel_spacing_m <= 0:
            raise ValueError("channel_spacing_m must be positive.")
        tangents = tuple(_normalize_vector(tangent, f"tangent_xyz[{index}]") for index, tangent in enumerate(self.tangent_xyz))
        if len(tangents) != len(self.receivers):
            raise ValueError("tangent_xyz must have one tangent per receiver sample.")
        object.__setattr__(self, "tangent_xyz", tangents)

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "receiver_type": "das_polyline_sampled_channels",
            "observation_type": self.observation_type,
            "gauge_length_m": self.gauge_length_m,
            "channel_spacing_m": self.channel_spacing_m,
            "is_true_das_axial_strain": False,
            "approximation": "仅为光纤折线采样点近似；尚未计算 gauge-length 平均轴向应变",
        }


def _interpolate_polyline(
    points: Sequence[Coordinate3D],
    cumulative_distances: Sequence[float],
    sample_distance: float,
) -> tuple[Coordinate3D, tuple[float, float, float]]:
    if sample_distance <= 0:
        return points[0], _segment_tangent(points[0], points[1])

    total_length = cumulative_distances[-1]
    if sample_distance >= total_length:
        return points[-1], _segment_tangent(points[-2], points[-1])

    for index in range(len(points) - 1):
        start_s = cumulative_distances[index]
        end_s = cumulative_distances[index + 1]
        if start_s <= sample_distance <= end_s:
            start = points[index]
            end = points[index + 1]
            segment_length = end_s - start_s
            if segment_length <= 0:
                continue
            fraction = (sample_distance - start_s) / segment_length
            point = Coordinate3D(
                start.x + fraction * (end.x - start.x),
                start.y + fraction * (end.y - start.y),
                start.depth + fraction * (end.depth - start.depth),
            )
            return point, _segment_tangent(start, end)

    return points[-1], _segment_tangent(points[-2], points[-1])


def _segment_tangent(start: Coordinate3D, end: Coordinate3D) -> tuple[float, float, float]:
    return _normalize_vector((end.x - start.x, end.y - start.y, end.depth - start.depth), "polyline segment")


def _normalize_vector(vector: Sequence[float], name: str) -> tuple[float, float, float]:
    if len(vector) != 3:
        raise ValueError(f"{name} must contain exactly three values.")
    values = (float(vector[0]), float(vector[1]), float(vector[2]))
    norm = sqrt(sum(value * value for value in values))
    if norm <= 0:
        raise ValueError(f"{name} must have nonzero length.")
    return tuple(value / norm for value in values)
