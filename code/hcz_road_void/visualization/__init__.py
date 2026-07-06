"""三维道路空洞场景可视化接口。"""

from hcz_road_void.visualization.fonts import configure_chinese_matplotlib
from hcz_road_void.visualization.plots import (
    plot_geometry_3d,
    plot_localization_slices,
    plot_synthetic_gather,
)
from hcz_road_void.visualization.scene import SceneBounds3D
from hcz_road_void.visualization.velocity import plot_velocity_model_slices
from hcz_road_void.visualization.wavefield import (
    WavefieldSnapshotResult,
    ensure_wavefield_output_dir,
    save_scalar_wavefield_snapshots,
    unavailable_wavefield_snapshots,
)

__all__ = [
    "SceneBounds3D",
    "WavefieldSnapshotResult",
    "configure_chinese_matplotlib",
    "ensure_wavefield_output_dir",
    "plot_geometry_3d",
    "plot_localization_slices",
    "plot_synthetic_gather",
    "plot_velocity_model_slices",
    "save_scalar_wavefield_snapshots",
    "unavailable_wavefield_snapshots",
]
