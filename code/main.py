"""运行第一阶段三维道路地下空洞运动学正演与定位示例。

本脚本只负责组织一次完整演示：构建道路、DAS 光纤、锤击震源和
地下空洞的三维几何，调用包内正演、定位、不确定性和绘图模块。
核心算法不放在这里，便于后续把运动学近似替换为 Devito/OpenSWPC
等高保真正演后端。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from hcz_road_void.forward import ForwardConfig, simulate_kinematic_diffraction
from hcz_road_void.geometry import Coordinate3D
from hcz_road_void.localization import SearchGrid3D, travel_time_energy_stack
from hcz_road_void.models import VelocityModel3D, VoidModel3D
from hcz_road_void.receivers import ReceiverPolyline3D
from hcz_road_void.uncertainty import summarize_objective_uncertainty
from hcz_road_void.visualization import plot_geometry_3d, plot_localization_slices, plot_synthetic_gather


def build_stage1_scene() -> dict[str, object]:
    """构建默认三维道路 DAS + 锤击空洞探测场景。

    坐标约定始终为：

    - ``x``：沿道路和光纤方向；
    - ``y``：横穿道路方向；
    - ``depth``：向下为正，单位为 m。

    默认几何把 DAS 光纤放在道路一侧 ``y=0``，把锤击点放在另一侧
    ``y=15``，空洞位于道路中部浅层 ``(40, 7.5, 2)``。这不是二维
    剖面示例，而是 source、receiver、void 三者共同形成的真实三维
    acquisition geometry。
    """

    road_length_m = 80.0
    road_width_m = 15.0
    fiber_y_m = 0.0
    source_y_m = road_width_m
    depth_positive_down = True

    # 第一阶段只需要一个常速度背景，用 Rayleigh 速度占位来模拟浅层面波绕射走时。
    # 这不是弹性波方程求解，只是为了让三维几何和定位闭环先跑通。
    velocity_model = VelocityModel3D(vp_mps=900.0, vs_mps=280.0, density_kg_m3=1850.0)
    background_velocity_mps = velocity_model.rayleigh_velocity_mps

    # 锤击点沿道路另一侧布设：x 覆盖整条示例道路，y 固定为道路宽度。
    source_xs = np.linspace(0.0, road_length_m, 21)
    source_xyz = tuple(
        Coordinate3D(float(x), source_y_m, 0.0)
        for x in source_xs
    )

    # DAS 光纤用三维 polyline 表达，再由 ReceiverPolyline3D 统一采样为通道点。
    # 不在 main.py 中手工构造 receiver_xyz，避免光纤几何和通道几何不一致。
    receiver_polyline = ReceiverPolyline3D(
        points=[
            (0.0, fiber_y_m, 0.0),
            (road_length_m, fiber_y_m, 0.0),
        ],
        gauge_length_m=4.0,
        channel_spacing_m=2.0,
    )
    sampled_receivers = receiver_polyline.sample_channels()

    # 空洞放在道路横向中部的浅层地下，不在光纤正下方。
    void_model = VoidModel3D(void_xyz=(40.0, 7.5, 2.0), void_radius_m=1.0)
    config = ForwardConfig(dt_s=0.001, nt=600, wavelet_frequency_hz=35.0)

    # 定位网格必须覆盖 x-y-depth 三个方向，尤其 search_y 覆盖道路全宽。
    search_grid = SearchGrid3D(
        search_x=[float(value) for value in np.linspace(25.0, 55.0, 31)],
        search_y=[float(value) for value in np.linspace(0.0, road_width_m, 31)],
        search_depth=[float(value) for value in np.linspace(0.5, 5.0, 19)],
    )
    return {
        "road_length_m": road_length_m,
        "road_width_m": road_width_m,
        "fiber_y_m": fiber_y_m,
        "source_y_m": source_y_m,
        "depth_positive_down": depth_positive_down,
        "velocity_model": velocity_model,
        "background_velocity_mps": background_velocity_mps,
        "source_xyz": source_xyz,
        "receiver_polyline": receiver_polyline,
        "sampled_receivers": sampled_receivers,
        "void_model": void_model,
        "config": config,
        "search_grid": search_grid,
    }


def run(output_dir: str | Path = "outputs", quiet: bool = False) -> dict[str, object]:
    """运行默认三维示例并把图像、数据和 JSON 摘要写入输出目录。"""

    scene = build_stage1_scene()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    source_xyz = scene["source_xyz"]
    receiver_polyline = scene["receiver_polyline"]
    sampled_receivers = scene["sampled_receivers"]
    void_model = scene["void_model"]
    velocity_model = scene["velocity_model"]
    config = scene["config"]
    search_grid = scene["search_grid"]
    background_velocity_mps = float(scene["background_velocity_mps"])
    road_length_m = float(scene["road_length_m"])
    road_width_m = float(scene["road_width_m"])
    fiber_y_m = float(scene["fiber_y_m"])
    source_y_m = float(scene["source_y_m"])

    forward = simulate_kinematic_diffraction(
        source_xyz=source_xyz,
        receiver_xyz=sampled_receivers.receiver_xyz,
        void_xyz=void_model.void_xyz,
        background_velocity_mps=background_velocity_mps,
        config=config,
        scatter_amplitude=8.0,
    )

    # 定位阶段对每个候选 (x, y, depth) 计算 source-candidate-receiver 走时，
    # 再在合成记录相应时间处叠加能量。高目标函数值表示该候选点更能解释
    # 多炮多道记录中的绕射事件。
    localization = travel_time_energy_stack(
        data=forward.data,
        time_axis_s=forward.time_axis_s,
        source_xyz=forward.source_xyz,
        receiver_xyz=forward.receiver_xyz,
        background_velocity_mps=background_velocity_mps,
        search_grid=search_grid,
        half_window_samples=0,
        true_xyz=void_model.void_xyz,
    )
    uncertainty = summarize_objective_uncertainty(localization)

    np.savez_compressed(
        output_path / "synthetic_data.npz",
        data=forward.data,
        time_axis_s=forward.time_axis_s,
        source_xyz=np.asarray(forward.source_xyz),
        receiver_xyz=np.asarray(forward.receiver_xyz),
        travel_times_s=forward.travel_times_s,
    )
    np.savez_compressed(
        output_path / "localization_objective.npz",
        objective_volume=localization.objective_volume,
        search_x=np.asarray(search_grid.search_x),
        search_y=np.asarray(search_grid.search_y),
        search_depth=np.asarray(search_grid.search_depth),
        normalized_objective=uncertainty.normalized_objective,
    )

    plot_geometry_3d(
        output_path / "geometry_3d.png",
        source_xyz=source_xyz,
        receiver_polyline=receiver_polyline.points,
        receiver_xyz=sampled_receivers.receivers,
        true_void_xyz=void_model.void_xyz,
        void_radius_m=void_model.void_radius_m,
        best_xyz=localization.best_xyz,
        road_length_m=road_length_m,
        road_width_m=road_width_m,
        fiber_y_m=fiber_y_m,
        source_y_m=source_y_m,
    )
    plot_synthetic_gather(
        output_path / "synthetic_gather.png",
        data=forward.data,
        time_axis_s=forward.time_axis_s,
        receiver_xyz=sampled_receivers.receivers,
        source_index=0,
    )
    plot_localization_slices(output_path / "localization_slices.png", localization)

    x_error_m = localization.best_xyz.x - void_model.void_xyz.x
    y_error_m = localization.best_xyz.y - void_model.void_xyz.y
    depth_error_m = localization.best_xyz.depth - void_model.void_xyz.depth
    summary = {
        "road_length_m": road_length_m,
        "road_width_m": road_width_m,
        "fiber_y_m": fiber_y_m,
        "source_y_m": source_y_m,
        "depth_positive_down": bool(scene["depth_positive_down"]),
        "true_void_xyz": void_model.void_xyz.xyz,
        "void_radius_m": void_model.void_radius_m,
        "search_x_range_m": [float(search_grid.search_x[0]), float(search_grid.search_x[-1])],
        "search_y_range_m": [float(search_grid.search_y[0]), float(search_grid.search_y[-1])],
        "search_depth_range_m": [float(search_grid.search_depth[0]), float(search_grid.search_depth[-1])],
        "coordinate_system": {
            "x": "沿道路或 DAS 光纤方向",
            "y": "横穿道路方向",
            "depth": "向下为正",
            "units": "m",
        },
        "true_xyz": void_model.void_xyz.xyz,
        "best_xyz": localization.best_xyz.xyz,
        "localization_error_m": localization.localization_error_m,
        "x_error_m": x_error_m,
        "y_error_m": y_error_m,
        "depth_error_m": depth_error_m,
        "best_score": localization.best_score,
        "uncertainty": uncertainty.as_dict(),
        "n_sources": len(source_xyz),
        "n_receiver_channels": len(sampled_receivers.receivers),
        "data_shape": list(forward.data.shape),
        "objective_shape": list(localization.objective_volume.shape),
        "background_velocity_mps": background_velocity_mps,
        "receiver_metadata": sampled_receivers.metadata,
        "forward_metadata": dict(forward.metadata),
        "localization_metadata": dict(localization.metadata),
        "assumptions": [
            "当前仅为三维运动学绕射近似",
            "空洞被简化为单个点绕射体或空洞中心",
            "当前不是完整三维弹性波方程求解器",
            "DAS 光纤目前只采样为点接收通道，尚未实现 gauge-length 平均轴向应变",
            "定位目标函数为 x-y-depth 三维 travel-time energy stack",
        ],
        "outputs": {
            "geometry_3d": str(output_path / "geometry_3d.png"),
            "synthetic_gather": str(output_path / "synthetic_gather.png"),
            "localization_slices": str(output_path / "localization_slices.png"),
            "synthetic_data": str(output_path / "synthetic_data.npz"),
            "localization_objective": str(output_path / "localization_objective.npz"),
            "run_summary": str(output_path / "run_summary.json"),
        },
    }
    with (output_path / "run_summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    if not quiet:
        print("第一阶段三维道路地下空洞运动学绕射示例")
        print("坐标系统：x 沿道路/光纤，y 横穿道路，depth 向下为正")
        print(f"道路几何：长度={road_length_m:.1f} m，宽度={road_width_m:.1f} m")
        print(f"DAS 光纤位于 y={fiber_y_m:.1f} m；锤击炮线位于 y={source_y_m:.1f} m")
        print(f"true_xyz: {summary['true_xyz']}")
        print(f"best_xyz: {summary['best_xyz']}")
        print(f"localization_error_m: {summary['localization_error_m']:.3f}")
        print(f"x_error_m: {summary['x_error_m']:.3f}")
        print(f"y_error_m: {summary['y_error_m']:.3f}")
        print(f"depth_error_m: {summary['depth_error_m']:.3f}")
        print(f"数据维度 n_sources x n_receivers x n_times: {summary['data_shape']}")
        print(f"目标函数维度 x-y-depth: {summary['objective_shape']}")
        print(f"不确定性指标: {summary['uncertainty']}")
        print("当前简化假设:")
        for assumption in summary["assumptions"]:
            print(f"- {assumption}")
        print(f"输出已保存到: {output_path.resolve()}")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="outputs", help="输出目录。")
    parser.add_argument("--quiet", action="store_true", help="不打印终端摘要。")
    args = parser.parse_args()
    run(output_dir=args.output_dir, quiet=args.quiet)


if __name__ == "__main__":
    main()
