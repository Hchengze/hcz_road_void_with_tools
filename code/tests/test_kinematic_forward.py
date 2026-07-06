"""验证三维运动学绕射正演输出维度和输入检查。"""

import numpy as np
import pytest

from hcz_road_void.forward import ForwardConfig, simulate_kinematic_diffraction


def test_kinematic_forward_output_shape_and_metadata() -> None:
    result = simulate_kinematic_diffraction(
        source_xyz=[(0.0, 0.0, 0.0), (4.0, 0.0, 0.0)],
        receiver_xyz=[(0.0, 3.0, 0.0), (4.0, 3.0, 0.0), (8.0, 3.0, 0.0)],
        void_xyz=(4.0, 1.0, 3.0),
        background_velocity_mps=200.0,
        config=ForwardConfig(dt_s=0.002, nt=200, wavelet_frequency_hz=30.0),
    )
    assert result.data.shape == (2, 3, 200)
    assert result.travel_times_s.shape == (2, 3)
    assert len(result.time_axis_s) == 200
    assert result.metadata["forward_type"] == "3d_kinematic_diffraction"
    assert result.metadata["is_wave_equation_solver"] is False
    assert result.metadata["is_elastic_solver"] is False
    assert np.max(np.abs(result.data)) > 0.0


def test_kinematic_forward_rejects_negative_velocity() -> None:
    with pytest.raises(ValueError, match="background_velocity_mps"):
        simulate_kinematic_diffraction(
            source_xyz=[(0.0, 0.0, 0.0)],
            receiver_xyz=[(1.0, 0.0, 0.0)],
            void_xyz=(0.5, 0.0, 1.0),
            background_velocity_mps=-1.0,
            config=ForwardConfig(dt_s=0.002, nt=100, wavelet_frequency_hz=30.0),
        )
