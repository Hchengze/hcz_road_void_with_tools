"""验证三维坐标、速度模型、空洞模型和场景一致性。"""

import pytest

from hcz_road_void.geometry import Coordinate3D, RoadVoidScenario, SourceArray3D, distance_3d
from hcz_road_void.models import VelocityModel3D, VoidModel3D
from hcz_road_void.receivers import PointReceiverGeometry3D, ReceiverPolyline3D


def test_coordinate_requires_true_3d() -> None:
    with pytest.raises(ValueError):
        SourceArray3D([(0.0, 1.0)])


def test_depth_positive_down_is_enforced() -> None:
    with pytest.raises(ValueError):
        Coordinate3D(0.0, 0.0, -1.0)


def test_distance_uses_y_dimension() -> None:
    assert distance_3d((0.0, 0.0, 0.0), (0.0, 3.0, 4.0)) == pytest.approx(5.0)


def test_velocity_model_validation() -> None:
    model = VelocityModel3D(vp_mps=800.0, vs_mps=300.0, density_kg_m3=1800.0)
    assert model.rayleigh_velocity_mps == pytest.approx(276.0)
    with pytest.raises(ValueError):
        VelocityModel3D(vp_mps=200.0, vs_mps=300.0, density_kg_m3=1800.0)


def test_void_model_validation() -> None:
    void = VoidModel3D(void_xyz=(10.0, 2.0, 5.0), void_radius_m=1.5)
    assert void.void_xyz.xyz == (10.0, 2.0, 5.0)
    with pytest.raises(ValueError):
        VoidModel3D(void_xyz=(10.0, 2.0, 5.0), void_radius_m=-1.0)


def test_source_receiver_void_scenario_consistency() -> None:
    scenario = RoadVoidScenario(
        sources=SourceArray3D([(0.0, 0.0, 0.0)]),
        receivers=PointReceiverGeometry3D([(10.0, 2.0, 0.0)]),
        velocity_model=VelocityModel3D(vp_mps=900.0, vs_mps=350.0, density_kg_m3=1900.0),
        void_model=VoidModel3D(void_xyz=(5.0, 1.0, 3.0), void_radius_m=1.0),
    )
    assert scenario.sources.source_xyz == ((0.0, 0.0, 0.0),)
    assert scenario.receivers.receiver_xyz == ((10.0, 2.0, 0.0),)


def test_receiver_polyline_metadata() -> None:
    fiber = ReceiverPolyline3D(
        points=[(0.0, 1.0, 0.2), (3.0, 1.0, 0.2), (3.0, 5.0, 0.2)],
        gauge_length_m=2.0,
        channel_spacing_m=1.0,
    )
    assert fiber.length_m == pytest.approx(7.0)
    with pytest.raises(ValueError):
        ReceiverPolyline3D(points=[(0.0, 0.0, 0.0)], gauge_length_m=2.0, channel_spacing_m=1.0)
