"""验证正演配置、三维走时和搜索网格基础行为。"""

import pytest

from hcz_road_void.forward import ForwardConfig, predict_point_scatter_travel_time
from hcz_road_void.localization import SearchGrid3D


def test_forward_config_validation() -> None:
    config = ForwardConfig(dt_s=0.001, nt=1000, wavelet_frequency_hz=40.0)
    assert config.is_kinematic_approximation is True
    assert config.solves_full_wave_equation is False
    assert config.forward_type == "3d_kinematic_diffraction"
    with pytest.raises(ValueError):
        ForwardConfig(dt_s=0.0, nt=1000, wavelet_frequency_hz=40.0)


def test_kinematic_travel_time_is_3d_not_x_depth_only() -> None:
    travel_time = predict_point_scatter_travel_time(
        source_xyz=(0.0, 0.0, 0.0),
        receiver_xyz=(0.0, 0.0, 0.0),
        scatter_xyz=(0.0, 3.0, 4.0),
        velocity_mps=100.0,
    )
    assert travel_time == pytest.approx(0.1)


def test_search_grid_shape_and_size() -> None:
    grid = SearchGrid3D(search_x=[0.0, 1.0], search_y=[-2.0, 0.0, 2.0], search_depth=[1.0, 3.0])
    assert grid.shape == (2, 3, 2)
    assert grid.size == 12


def test_search_grid_rejects_empty_or_negative_depth() -> None:
    with pytest.raises(ValueError):
        SearchGrid3D(search_x=[], search_y=[0.0], search_depth=[1.0])
    with pytest.raises(ValueError):
        SearchGrid3D(search_x=[0.0], search_y=[0.0], search_depth=[-1.0])
