"""验证单空洞合成场景下三维定位可以恢复网格真值。"""

import pytest

from hcz_road_void.forward import ForwardConfig, simulate_kinematic_diffraction
from hcz_road_void.localization import SearchGrid3D, extract_objective_slices, travel_time_energy_stack


def test_3d_localization_recovers_single_void_on_grid() -> None:
    true_void = (4.0, 1.0, 3.0)
    sources = [(0.0, 0.0, 0.0), (8.0, 2.0, 0.0)]
    receivers = [(0.0, 4.0, 0.0), (4.0, -3.0, 0.0), (8.0, 4.0, 0.0), (10.0, -2.0, 0.0)]
    velocity = 220.0
    forward = simulate_kinematic_diffraction(
        source_xyz=sources,
        receiver_xyz=receivers,
        void_xyz=true_void,
        background_velocity_mps=velocity,
        config=ForwardConfig(dt_s=0.001, nt=160, wavelet_frequency_hz=35.0),
        scatter_amplitude=5.0,
        geometric_spreading=False,
    )
    grid = SearchGrid3D(
        search_x=[3.0, 4.0, 5.0],
        search_y=[0.0, 1.0, 2.0],
        search_depth=[2.0, 3.0, 4.0],
    )
    result = travel_time_energy_stack(
        data=forward.data,
        time_axis_s=forward.time_axis_s,
        source_xyz=forward.source_xyz,
        receiver_xyz=forward.receiver_xyz,
        background_velocity_mps=velocity,
        search_grid=grid,
        half_window_samples=1,
        true_xyz=true_void,
    )
    assert result.objective_volume.shape == (3, 3, 3)
    assert result.best_xyz.xyz == pytest.approx(true_void)
    assert result.localization_error_m == pytest.approx(0.0)
    slices = extract_objective_slices(result)
    assert slices["x_depth_at_best_y"].shape == (3, 3)
    assert slices["y_depth_at_best_x"].shape == (3, 3)
    assert slices["x_y_at_best_depth"].shape == (3, 3)
