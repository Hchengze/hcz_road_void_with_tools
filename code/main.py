"""运行三维道路 DAS + 锤击地下空洞探测算法原型。

本脚本是项目的端到端示例入口。它负责组织一次完整流程：

1. 构建三维道路、DAS 光纤、锤击炮线和地下空洞几何；
2. 生成三维速度网格，并把空洞表达为低速体异常；
3. 使用统一正演后端接口运行默认的三维运动学点绕射正演；
4. 运行三维 `x-y-depth` travel-time energy stack 定位；
5. 输出炮集、速度模型切片、定位切片和运行摘要。

重要边界：当前默认后端仍是 `kinematic`。它不是完整三维声波/弹性波方程
求解器，也不输出真实波场快照或真实 DAS gauge-length 轴向应变。Stage 2B
新增 `--backend devito_acoustic_3d` 入口；该入口只有在 Devito import、JIT
编译和极小 Operator smoke test 全部通过时才会运行真实三维声波正演。
Stage 2C 已把 Devito runtime 验证主线迁移到 WSL Linux conda 环境。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from hcz_road_void.forward import (
    DevitoBackend,
    DevitoForwardConfig,
    DevitoRuntimeStatus,
    ForwardConfig,
    KinematicDiffractionBackend,
    OpenSWPCBackend,
)
from hcz_road_void.geometry import Coordinate3D
from hcz_road_void.localization import SearchGrid3D, travel_time_energy_stack
from hcz_road_void.models import (
    VelocityModel3D,
    VoidBody3D,
    VoidModel3D,
    build_uniform_road_velocity_grid,
    embed_void_body_into_velocity_grid,
    sample_void_body_as_scatterers,
)
from hcz_road_void.receivers import ReceiverPolyline3D
from hcz_road_void.uncertainty import summarize_objective_uncertainty
from hcz_road_void.visualization import (
    ensure_wavefield_output_dir,
    plot_geometry_3d,
    plot_localization_slices,
    plot_synthetic_gather,
    plot_velocity_model_slices,
    save_scalar_wavefield_snapshots,
    unavailable_wavefield_snapshots,
)


def build_stage1_scene() -> dict[str, object]:
    """构建默认三维道路 DAS + 锤击地下空洞场景。

    函数名保留 `stage1` 是为了兼容上一轮测试和 Notebook，但返回内容已经包含
    Stage 2A/2B 所需的体异常、速度网格和 Devito 后端输入。坐标约定始终为：

    - `x`：沿道路或光纤方向，单位 m；
    - `y`：横穿道路方向，单位 m；
    - `depth`：深度，向下为正，单位 m。

    默认几何为：道路长 80 m、宽 15 m；DAS 光纤位于 `y=0 m` 一侧；
    锤击炮线位于 `y=15 m` 另一侧；空洞中心位于道路中部浅层
    `void_xyz=(40.0, 7.5, 2.0)`。
    """

    road_length_m = 80.0
    road_width_m = 15.0
    fiber_y_m = 0.0
    source_y_m = road_width_m
    depth_positive_down = True

    # 常速度模型仍服务于运动学走时；后续 Devito/OpenSWPC 会使用三维速度网格。
    velocity_model = VelocityModel3D(vp_mps=900.0, vs_mps=280.0, density_kg_m3=1850.0)
    background_velocity_mps = velocity_model.rayleigh_velocity_mps

    # 锤击震源沿道路另一侧排列。source_xyz 是真实三维坐标，不是二维剖面投影。
    source_xs = np.linspace(0.0, road_length_m, 21)
    source_xyz = tuple(Coordinate3D(float(x), source_y_m, 0.0) for x in source_xs)

    # DAS 光纤用三维折线表达，再统一采样为 receiver_xyz，避免手写通道坐标。
    receiver_polyline = ReceiverPolyline3D(
        points=[
            (0.0, fiber_y_m, 0.0),
            (road_length_m, fiber_y_m, 0.0),
        ],
        gauge_length_m=4.0,
        channel_spacing_m=2.0,
    )
    sampled_receivers = receiver_polyline.sample_channels()

    # Stage 1 点异常模型继续用于当前定位闭环；Stage 2A/2B 同步给出体异常表达。
    void_model = VoidModel3D(void_xyz=(40.0, 7.5, 2.0), void_radius_m=1.0)
    void_body = VoidBody3D(
        center_xyz=void_model.void_xyz,
        body_type="ellipsoid",
        size_xyz_m=(2.0, 2.0, 1.0),
        velocity_scale=0.5,
    )
    scatterer_proxy_xyz = sample_void_body_as_scatterers(void_body, spacing_m=0.5)

    # 三维速度网格用于真实波动方程后端输入。本轮仍不使用它调定位误差。
    base_velocity_grid = build_uniform_road_velocity_grid(
        road_length_m=road_length_m,
        road_width_m=road_width_m,
        max_depth_m=8.0,
        spacing_m=1.0,
        background_vp_mps=velocity_model.vp_mps,
    )
    velocity_grid = embed_void_body_into_velocity_grid(base_velocity_grid, void_body)

    config = ForwardConfig(dt_s=0.001, nt=600, wavelet_frequency_hz=35.0)
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
        "velocity_grid": velocity_grid,
        "background_velocity_mps": background_velocity_mps,
        "source_xyz": source_xyz,
        "receiver_polyline": receiver_polyline,
        "sampled_receivers": sampled_receivers,
        "void_model": void_model,
        "void_body": void_body,
        "scatterer_proxy_xyz": scatterer_proxy_xyz,
        "config": config,
        "search_grid": search_grid,
    }


def run(
    output_dir: str | Path = "outputs",
    quiet: bool = False,
    backend_name: str = "kinematic",
) -> dict[str, object]:
    """运行三维示例，并把图像、数据和 JSON 摘要写入输出目录。

    `backend_name="kinematic"` 是稳定默认值，继续服务三维几何、定位闭环和
    不确定性检查。`backend_name="devito_acoustic_3d"` 会尝试运行真实 Devito
    acoustic 三维波动方程后端；如果当前环境只能 import Devito 但不能执行
    Operator，会抛出清楚的中文错误。
    """

    scene = build_stage1_scene()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    source_xyz = scene["source_xyz"]
    receiver_polyline = scene["receiver_polyline"]
    sampled_receivers = scene["sampled_receivers"]
    void_model = scene["void_model"]
    void_body = scene["void_body"]
    velocity_grid = scene["velocity_grid"]
    config = scene["config"]
    search_grid = scene["search_grid"]
    background_velocity_mps = float(scene["background_velocity_mps"])
    road_length_m = float(scene["road_length_m"])
    road_width_m = float(scene["road_width_m"])
    fiber_y_m = float(scene["fiber_y_m"])
    source_y_m = float(scene["source_y_m"])

    kinematic_backend = KinematicDiffractionBackend()
    devito_backend = DevitoBackend()
    openswpc_backend = OpenSWPCBackend()
    devito_status = devito_backend.runtime_status()

    if backend_name == "devito_acoustic_3d":
        return _run_devito_scene(
            scene=scene,
            output_path=output_path,
            quiet=quiet,
            devito_backend=devito_backend,
            openswpc_backend=openswpc_backend,
            devito_status=devito_status,
        )
    if backend_name != "kinematic":
        raise ValueError("backend_name 只能是 'kinematic' 或 'devito_acoustic_3d'。")

    backend = kinematic_backend

    # 当前默认后端仍使用单点绕射中心。体异常和速度网格服务 Stage 2C Devito 后端准备。
    forward = backend.run_forward(scene, config)

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
    wavefield_status = unavailable_wavefield_snapshots(backend.name)
    ensure_wavefield_output_dir(output_path / "wavefield_snapshots")

    velocity_grid.save_npz(output_path / "velocity_model_3d.npz")
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
    plot_velocity_model_slices(
        output_path / "velocity_model_slices.png",
        velocity_grid=velocity_grid,
        x_m=void_model.void_xyz.x,
        y_m=void_model.void_xyz.y,
        depth_m=void_model.void_xyz.depth,
    )
    plot_synthetic_gather(
        output_path / "synthetic_gather.png",
        data=forward.data,
        time_axis_s=forward.time_axis_s,
        receiver_xyz=sampled_receivers.receivers,
        source_index=0,
        title="三维运动学绕射合成炮集，震源 0",
    )
    plot_localization_slices(output_path / "localization_slices.png", localization)

    x_error_m = localization.best_xyz.x - void_model.void_xyz.x
    y_error_m = localization.best_xyz.y - void_model.void_xyz.y
    depth_error_m = localization.best_xyz.depth - void_model.void_xyz.depth
    backend_metadata = dict(forward.metadata)
    summary = {
        "road_length_m": road_length_m,
        "road_width_m": road_width_m,
        "fiber_y_m": fiber_y_m,
        "source_y_m": source_y_m,
        "depth_positive_down": bool(scene["depth_positive_down"]),
        "true_void_xyz": void_model.void_xyz.xyz,
        "void_radius_m": void_model.void_radius_m,
        "void_body": void_body.metadata,
        "void_representation": "point_or_body_proxy",
        "body_scatterer_proxy_count": len(scene["scatterer_proxy_xyz"]),
        "search_x_range_m": [float(search_grid.search_x[0]), float(search_grid.search_x[-1])],
        "search_y_range_m": [float(search_grid.search_y[0]), float(search_grid.search_y[-1])],
        "search_depth_range_m": [float(search_grid.search_depth[0]), float(search_grid.search_depth[-1])],
        "coordinate_system": {
            "x": "沿道路或 DAS 光纤方向",
            "y": "横穿道路方向",
            "depth": "向下为正",
            "units": "m",
        },
        "backend_name": backend_metadata["backend_name"],
        "physics_type": backend_metadata["physics_type"],
        "is_wave_equation_solver": backend_metadata["is_wave_equation_solver"],
        "is_elastic_solver": backend_metadata["is_elastic_solver"],
        "supports_wavefield_snapshots": backend_metadata["supports_wavefield_snapshots"],
        "supports_das_strain": backend_metadata["supports_das_strain"],
        "approximation": backend_metadata["approximation"],
        "devito_available": devito_status.runtime_available,
        "devito_import_available": devito_status.import_available,
        "devito_runtime_available": devito_status.runtime_available,
        "devito_version": devito_status.version,
        "devito_compiler_path": devito_status.compiler_path,
        "devito_runtime_message": devito_status.message,
        "openswpc_available": openswpc_backend.is_available(),
        "wavefield_snapshot_type": wavefield_status.snapshot_type,
        "is_true_wave_equation_wavefield": wavefield_status.is_true_wave_equation_wavefield,
        "localization_accuracy_is_primary_metric": False,
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
        "velocity_grid": {
            "shape": list(velocity_grid.shape),
            "spacing_m": velocity_grid.spacing_m,
            "metadata": dict(velocity_grid.metadata),
        },
        "receiver_metadata": sampled_receivers.metadata,
        "forward_metadata": backend_metadata,
        "localization_metadata": dict(localization.metadata),
        "wavefield_status": wavefield_status.as_dict(),
        "assumptions": [
            "当前默认正演后端是三维运动学点绕射近似。",
            "Devito 已安装时仍需通过 JIT/Operator smoke test 才能视为运行可用。",
            "当前默认运行不是完整三维声波或弹性波波动方程正演。",
            "体异常已能写入速度网格，但运动学后端仍默认使用中心点作为等效绕射体。",
            "DAS 光纤当前仍是 polyline 采样点接收器近似，不是真实 gauge-length averaged axial strain。",
            "定位模块用于验证三维几何、数据结构和流程贯通，当前不以定位误差最小为核心验收指标。",
        ],
        "outputs": {
            "geometry_3d": str(output_path / "geometry_3d.png"),
            "velocity_model_slices": str(output_path / "velocity_model_slices.png"),
            "synthetic_gather": str(output_path / "synthetic_gather.png"),
            "localization_slices": str(output_path / "localization_slices.png"),
            "velocity_model_3d": str(output_path / "velocity_model_3d.npz"),
            "synthetic_data": str(output_path / "synthetic_data.npz"),
            "localization_objective": str(output_path / "localization_objective.npz"),
            "wavefield_snapshots_dir": str(output_path / "wavefield_snapshots"),
            "run_summary": str(output_path / "run_summary.json"),
        },
    }
    with (output_path / "run_summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)

    if not quiet:
        print("Stage 2C 三维道路 DAS + 锤击地下空洞正演过渡原型")
        print("坐标系统：x 沿道路/光纤，y 横穿道路，depth 向下为正")
        print(f"当前正演后端：{summary['backend_name']}")
        print(f"Devito 可导入：{summary['devito_import_available']}")
        print(f"Devito 版本：{summary['devito_version']}")
        print(f"Devito 运行可用：{summary['devito_runtime_available']}")
        print(f"Devito 运行诊断：{summary['devito_runtime_message']}")
        print(f"OpenSWPC 可用：{summary['openswpc_available']}")
        print(f"当前异常体表示：{summary['void_representation']}")
        print(f"当前是否完整波动方程正演：{summary['is_wave_equation_solver']}")
        print(f"当前是否真实弹性波正演：{summary['is_elastic_solver']}")
        print(f"当前是否支持真实波场快照：{summary['supports_wavefield_snapshots']}")
        print(f"当前是否支持真实 DAS 轴向应变：{summary['supports_das_strain']}")
        print(f"当前定位准确度是否核心指标：{summary['localization_accuracy_is_primary_metric']}")
        print(f"道路几何：长度 {road_length_m:.1f} m，宽度 {road_width_m:.1f} m")
        print(f"DAS 光纤位于 y={fiber_y_m:.1f} m；锤击炮线位于 y={source_y_m:.1f} m")
        print(f"true_xyz: {summary['true_xyz']}")
        print(f"best_xyz: {summary['best_xyz']}")
        print(f"localization_error_m: {summary['localization_error_m']:.3f}")
        print(f"x_error_m: {summary['x_error_m']:.3f}")
        print(f"y_error_m: {summary['y_error_m']:.3f}")
        print(f"depth_error_m: {summary['depth_error_m']:.3f}")
        print(f"数据维度 n_sources x n_receivers x n_times: {summary['data_shape']}")
        print(f"目标函数维度 x-y-depth: {summary['objective_shape']}")
        print(f"速度网格维度 x-y-depth: {summary['velocity_grid']['shape']}")
        print(f"不确定性指标: {summary['uncertainty']}")
        print("当前简化假设:")
        for assumption in summary["assumptions"]:
            print(f"- {assumption}")
        print(f"输出已保存到: {output_path.resolve()}")

    return summary


def _run_devito_scene(
    scene: dict[str, object],
    output_path: Path,
    quiet: bool,
    devito_backend: DevitoBackend,
    openswpc_backend: OpenSWPCBackend,
    devito_status: DevitoRuntimeStatus,
) -> dict[str, object]:
    """运行 Devito acoustic 后端，并保存真实声波炮集和快照。

    该函数只在用户显式选择 `--backend devito_acoustic_3d` 时调用。它不运行
    当前 travel-time energy stack 定位，因为 Stage 2C 的验收重点是 WSL 中的
    Devito Operator runtime、真实声波正演输出、速度模型、炮集和波场输出，
    不是定位误差。
    """

    if not devito_backend.is_available():
        raise RuntimeError(
            "无法运行 Devito 三维 acoustic 后端。"
            f"Devito import 状态：{devito_status.import_available}；"
            f"版本：{devito_status.version}；"
            f"运行诊断：{devito_status.message}；"
            f"细节：{devito_status.details}"
        )

    velocity_grid = scene["velocity_grid"]
    void_model = scene["void_model"]
    void_body = scene["void_body"]
    sampled_receivers = scene["sampled_receivers"]
    source_xyz = scene["source_xyz"]

    # Stage 2C 只跑一个很小的 Devito acoustic 示例。默认选择首炮、中间炮和末炮，
    # 既覆盖道路两端和中部，又避免最小后端第一次运行时间过长。
    source_count = len(source_xyz)
    devito_config = DevitoForwardConfig(
        dt_s=0.00025,
        nt=220,
        wavelet_frequency_hz=70.0,
        snapshot_interval=25,
        source_indices=(0, source_count // 2, source_count - 1),
    )
    forward = devito_backend.run_forward(scene, devito_config)
    forward_metadata = dict(forward.metadata)
    snapshot_cube = forward_metadata.pop("wavefield_snapshot_array", None)
    snapshot_times_s = forward_metadata.pop("wavefield_snapshot_times_s", None)

    velocity_grid.save_npz(output_path / "velocity_model_3d.npz")
    plot_velocity_model_slices(
        output_path / "velocity_model_slices.png",
        velocity_grid=velocity_grid,
        x_m=void_model.void_xyz.x,
        y_m=void_model.void_xyz.y,
        depth_m=void_model.void_xyz.depth,
    )
    np.savez_compressed(
        output_path / "devito_synthetic_data.npz",
        data=forward.data,
        time_axis_s=forward.time_axis_s,
        source_xyz=np.asarray(forward.source_xyz),
        receiver_xyz=np.asarray(forward.receiver_xyz),
    )
    plot_synthetic_gather(
        output_path / "devito_synthetic_gather.png",
        data=forward.data,
        time_axis_s=forward.time_axis_s,
        receiver_xyz=sampled_receivers.receivers,
        source_index=0,
        title="Devito 三维声波方程合成炮集，震源 0",
    )

    if snapshot_cube is None or snapshot_times_s is None:
        wavefield_status = unavailable_wavefield_snapshots(devito_backend.name)
    else:
        wavefield_status = save_scalar_wavefield_snapshots(
            output_dir=output_path / "devito_wavefield_snapshots",
            snapshot_cube=snapshot_cube,
            x_m=velocity_grid.x_m,
            y_m=velocity_grid.y_m,
            depth_m=velocity_grid.depth_m,
            snapshot_times_s=snapshot_times_s,
            fixed_y_m=void_model.void_xyz.y,
            animation_path=output_path / "devito_wavefield_animation.gif",
            backend_name=devito_backend.name,
        )

    summary = {
        "stage": "Stage 2C",
        "backend_name": forward_metadata["backend_name"],
        "physics_type": forward_metadata["physics_type"],
        "runtime_environment": forward_metadata.get("runtime_environment"),
        "conda_env_name": forward_metadata.get("conda_env_name"),
        "devito_runtime_state": forward_metadata.get("runtime_state"),
        "is_wave_equation_solver": forward_metadata["is_wave_equation_solver"],
        "is_elastic_solver": forward_metadata["is_elastic_solver"],
        "supports_wavefield_snapshots": forward_metadata["supports_wavefield_snapshots"],
        "supports_das_strain": forward_metadata["supports_das_strain"],
        "is_true_wave_equation_wavefield": wavefield_status.is_true_wave_equation_wavefield,
        "wavefield_snapshot_type": wavefield_status.snapshot_type,
        "wavefield_component": "scalar acoustic field",
        "devito_import_available": devito_status.import_available,
        "devito_runtime_available": devito_status.runtime_available,
        "devito_version": devito_status.version,
        "devito_compiler_path": devito_status.compiler_path,
        "devito_runtime_message": devito_status.message,
        "openswpc_available": openswpc_backend.is_available(),
        "road_length_m": float(scene["road_length_m"]),
        "road_width_m": float(scene["road_width_m"]),
        "fiber_y_m": float(scene["fiber_y_m"]),
        "source_y_m": float(scene["source_y_m"]),
        "true_void_xyz": void_model.void_xyz.xyz,
        "void_body": void_body.metadata,
        "uses_velocity_grid": True,
        "uses_void_body": True,
        "velocity_grid_shape": list(velocity_grid.shape),
        "data_shape": list(forward.data.shape),
        "source_xyz_used": [list(coord) for coord in forward.source_xyz],
        "source_count": int(forward.data.shape[0]),
        "receiver_count": len(forward.receiver_xyz),
        "time_sample_count": int(forward.data.shape[2]),
        "snapshot_count": len(wavefield_status.snapshot_paths),
        "dt_s": devito_config.dt_s,
        "nt": devito_config.nt,
        "localization_accuracy_is_primary_metric": False,
        "localization_run": False,
        "assumptions": [
            "Devito 后端是三维 acoustic 标量声波方程正演，不是三维弹性波正演。",
            "当前波场快照是标量声波场，不是真实 DAS 轴向应变。",
            "Stage 2C 暂不以定位误差为核心验收指标。",
            "当前最小 Devito 模型未加入 PML、自由表面和真实 DAS gauge-length 算子。",
        ],
        "forward_metadata": forward_metadata,
        "wavefield_status": wavefield_status.as_dict(),
        "outputs": {
            "velocity_model_3d": str(output_path / "velocity_model_3d.npz"),
            "velocity_model_slices": str(output_path / "velocity_model_slices.png"),
            "devito_synthetic_data": str(output_path / "devito_synthetic_data.npz"),
            "devito_synthetic_gather": str(output_path / "devito_synthetic_gather.png"),
            "devito_wavefield_snapshots": str(output_path / "devito_wavefield_snapshots"),
            "devito_wavefield_animation": str(output_path / "devito_wavefield_animation.gif"),
            "devito_forward_summary": str(output_path / "devito_forward_summary.json"),
        },
    }
    with (output_path / "devito_forward_summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)

    if not quiet:
        print("Stage 2C Devito 三维 acoustic 正演")
        print("坐标系统：x 沿道路/光纤，y 横穿道路，depth 向下为正")
        print(f"当前正演后端：{summary['backend_name']}")
        print(f"运行环境：{summary['runtime_environment']}")
        print(f"Conda 环境：{summary['conda_env_name']}")
        print(f"Devito runtime 状态：{summary['devito_runtime_state']}")
        print(f"Devito 版本：{summary['devito_version']}")
        print(f"当前是否完整波动方程正演：{summary['is_wave_equation_solver']}")
        print(f"当前是否弹性波正演：{summary['is_elastic_solver']}")
        print(f"当前是否支持真实波场快照：{summary['supports_wavefield_snapshots']}")
        print(f"当前是否支持真实 DAS 轴向应变：{summary['supports_das_strain']}")
        print(f"数据维度 n_sources x n_receivers x n_times: {summary['data_shape']}")
        print(f"速度网格维度 x-y-depth: {summary['velocity_grid_shape']}")
        print(f"波场快照数量：{summary['snapshot_count']}")
        print(f"波场快照类型：{summary['wavefield_snapshot_type']}")
        print(f"输出已保存到: {output_path.resolve()}")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="outputs", help="输出目录。")
    parser.add_argument("--quiet", action="store_true", help="不打印终端摘要。")
    parser.add_argument(
        "--backend",
        default="kinematic",
        choices=["kinematic", "devito_acoustic_3d"],
        help="正演后端：默认 kinematic；显式选择 devito_acoustic_3d 时尝试运行 Devito 三维声波方程。",
    )
    args = parser.parse_args()
    try:
        run(output_dir=args.output_dir, quiet=args.quiet, backend_name=args.backend)
    except RuntimeError as exc:
        print(f"运行失败：{exc}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
