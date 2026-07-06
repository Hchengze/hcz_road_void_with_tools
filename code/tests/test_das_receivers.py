"""验证 DAS 光纤折线采样、切向量和 gauge metadata。"""

import math

import pytest

from hcz_road_void.receivers import ReceiverPolyline3D


def test_polyline_sampling_produces_3d_receiver_xyz_and_tangents() -> None:
    fiber = ReceiverPolyline3D(
        points=[(0.0, -1.0, 0.2), (4.0, -1.0, 0.2), (4.0, 2.0, 0.2)],
        gauge_length_m=2.0,
        channel_spacing_m=2.0,
    )
    channels = fiber.sample_channels()
    assert all(len(xyz) == 3 for xyz in channels.receiver_xyz)
    assert len(channels.receiver_xyz) == len(channels.tangent_xyz)
    assert channels.metadata["is_true_das_axial_strain"] is False
    for tangent in channels.tangent_xyz:
        assert len(tangent) == 3
        assert math.sqrt(sum(value * value for value in tangent)) == pytest.approx(1.0)


def test_polyline_rejects_invalid_gauge_or_spacing() -> None:
    with pytest.raises(ValueError, match="gauge_length_m"):
        ReceiverPolyline3D(points=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)], gauge_length_m=0.0, channel_spacing_m=1.0)
    with pytest.raises(ValueError, match="channel_spacing_m"):
        ReceiverPolyline3D(points=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)], gauge_length_m=1.0, channel_spacing_m=-1.0)


def test_polyline_rejects_2d_coordinate() -> None:
    with pytest.raises(ValueError, match="exactly three"):
        ReceiverPolyline3D(points=[(0.0, 0.0), (1.0, 0.0, 0.0)], gauge_length_m=1.0, channel_spacing_m=1.0)
