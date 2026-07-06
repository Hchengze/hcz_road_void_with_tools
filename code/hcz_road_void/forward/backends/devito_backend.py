"""Devito 三维声波正演后端。

地球物理意义
------------
Stage 1/2A 的运动学后端只把空洞看成一个点绕射体，并没有求解波动方程。
本模块开始把项目推向真实三维波动方程正演：如果当前环境中的 Devito 运行
时可用，`DevitoBackend.run_forward()` 会用 `VelocityGrid3D` 中的三维速度
网格、项目统一的 `source_xyz` 和 `receiver_xyz` 运行一个最小三维 acoustic
有限差分正演。

边界必须说清楚：

1. Devito acoustic 是标量声波/压力场近似，不是三维弹性波；
2. 它可以输出真实波动方程炮集和标量波场快照；
3. 它不能直接给 DAS gauge-length averaged axial strain；
4. 当前 Windows 原生 `myvoid` 环境可能可以 import Devito，但 JIT 运行会被
   POSIX 内存分配、`os.getuid` 或 MinGW/CodePy 路径问题阻塞。因此本后端
   把“可导入”和“可运行 Operator”分开诊断，避免夸大能力。
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from hcz_road_void.forward.backends.base import ForwardBackend
from hcz_road_void.forward.kinematic import ricker_wavelet
from hcz_road_void.forward.result import ForwardResult3D
from hcz_road_void.geometry import Coordinate3D, ensure_coordinate3d
from hcz_road_void.models.velocity_grid import VelocityGrid3D


@dataclass(frozen=True)
class DevitoRuntimeStatus:
    """Devito 运行时诊断结果。

    字段说明：

    - `import_available`：`myvoid` 是否能 import Devito；
    - `runtime_available`：是否已经通过极小 `Operator.apply()` smoke test；
    - `version`：Devito 版本；
    - `compiler_path`：当前 Python 进程能找到的 C 编译器；
    - `message`：面向用户的中文结论；
    - `details`：用于文档和排错的简短细节。
    """

    import_available: bool
    runtime_available: bool
    version: str | None = None
    compiler_path: str | None = None
    message: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)

    @property
    def state(self) -> str:
        """返回便于程序和文档读取的三态诊断标签。

        Stage 2C 需要把 Devito 状态说得比简单 True/False 更清楚：

        1. `import_unavailable`：连 `import devito` 都不成立；
        2. `import_available_runtime_unavailable`：能 import，但 JIT/Operator 不能跑；
        3. `runtime_available`：import、JIT 编译和极小 Operator 都通过。

        这样 Windows 原生 `myvoid` 与 WSL Linux conda 环境可以在同一套代码里
        优雅分流，不会把“已安装”误写成“可正演”。
        """

        if not self.import_available:
            return "import_unavailable"
        if not self.runtime_available:
            return "import_available_runtime_unavailable"
        return "runtime_available"

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "import_available": self.import_available,
            "runtime_available": self.runtime_available,
            "version": self.version,
            "compiler_path": self.compiler_path,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class DevitoForwardConfig:
    """Devito acoustic 最小正演配置。

    - `dt_s`：时间步长，单位 s。必须满足声波方程 CFL 稳定性约束；
    - `nt`：时间步数；
    - `wavelet_frequency_hz`：Ricker 震源主频；
    - `space_order`：空间有限差分阶数；
    - `time_order`：时间差分阶数；
    - `snapshot_interval`：每隔多少个时间步保存一张波场快照；
    - `source_indices`：可选的震源索引子集，用于小模型 smoke run。

    这里的配置只服务三维声波方程后端，不复用 Stage 1 的 `ForwardConfig`，
    因为 Stage 1 配置明确禁止把自己标成波动方程求解器。
    """

    dt_s: float = 0.00035
    nt: int = 240
    wavelet_frequency_hz: float = 70.0
    space_order: int = 2
    time_order: int = 2
    snapshot_interval: int = 30
    source_indices: Sequence[int] | None = None

    def __post_init__(self) -> None:
        if self.dt_s <= 0:
            raise ValueError("dt_s 必须为正。")
        if self.nt <= 2:
            raise ValueError("nt 必须大于 2。")
        if self.wavelet_frequency_hz <= 0:
            raise ValueError("wavelet_frequency_hz 必须为正。")
        if self.space_order <= 0 or self.time_order <= 0:
            raise ValueError("space_order 和 time_order 必须为正。")
        if self.snapshot_interval <= 0:
            raise ValueError("snapshot_interval 必须为正。")


_RUNTIME_STATUS_CACHE: DevitoRuntimeStatus | None = None


@dataclass(frozen=True)
class DevitoBackend(ForwardBackend):
    """Devito 三维 acoustic 标量波动方程正演后端。

    `is_available()` 在本模块中表示“能否真正运行 Devito Operator”，而不仅是
    `import devito` 成功。这样 `main.py` 不会把当前 Windows 原生环境里
    “可导入但 JIT 失败”的状态误报为正演可用。
    """

    name: str = "devito_acoustic_3d"
    physics_type: str = "acoustic_wave_equation"

    def is_available(self) -> bool:
        """返回 Devito acoustic 后端是否能真正执行极小 Operator。"""

        return self.runtime_status().runtime_available

    def get_version(self) -> str | None:
        """返回 Devito 版本；未安装时返回 `None`。"""

        if find_spec("devito") is None:
            return None
        try:
            import devito  # type: ignore

            return str(devito.__version__)
        except Exception:
            return None

    def runtime_status(self, force: bool = False) -> DevitoRuntimeStatus:
        """运行或读取 Devito runtime smoke test 结果。

        smoke test 会创建极小三维 `Grid`、`TimeFunction` 和 `Operator`，并执行
        一个时间步。它验证的是 Devito JIT 编译链、内存分配和动态库加载是否
        在当前 Python 进程中可用。
        """

        global _RUNTIME_STATUS_CACHE
        if _RUNTIME_STATUS_CACHE is not None and not force:
            return _RUNTIME_STATUS_CACHE
        _RUNTIME_STATUS_CACHE = _run_devito_smoke_test()
        return _RUNTIME_STATUS_CACHE

    def metadata(self) -> dict[str, Any]:
        status = self.runtime_status()
        metadata = super().metadata()
        metadata.update(
            {
                "backend_name": self.name,
                "physics_type": self.physics_type,
                "is_wave_equation_solver": True,
                "is_elastic_solver": False,
                "supports_wavefield_snapshots": True,
                "supports_das_strain": False,
                "approximation": "Devito 三维 acoustic 标量声波方程；不是弹性波，不能直接模拟真实 DAS 轴向应变",
                "devito_import_available": status.import_available,
                "runtime_available": status.runtime_available,
                "devito_version": status.version,
                "compiler_path": status.compiler_path,
                "runtime_state": status.state,
                "runtime_environment": detect_runtime_environment(),
                "conda_env_name": os.environ.get("CONDA_DEFAULT_ENV"),
                "runtime_message": status.message,
                "wavefield_snapshot_type": "true_wave_equation" if status.runtime_available else "not_available",
                "is_true_wave_equation_wavefield": status.runtime_available,
            }
        )
        return metadata

    def run_forward(self, scenario: Any, config: DevitoForwardConfig | Mapping[str, Any] | None = None) -> ForwardResult3D:
        """运行最小 Devito 三维 acoustic 正演。

        输入场景必须至少包含：

        - `velocity_grid`：`VelocityGrid3D`，形状为 `(nx, ny, ndepth)`；
        - `source_xyz`：锤击点三维坐标；
        - `receiver_xyz` 或 `sampled_receivers.receiver_xyz`：DAS 采样点坐标。

        输出记录维度统一为 `n_sources x n_receivers x n_times`。如果当前
        Devito runtime 不可用，本函数会抛出中文 `RuntimeError`，并给出
        具体诊断，而不是让用户看到底层 traceback。
        """

        status = self.runtime_status()
        if not status.runtime_available:
            raise RuntimeError(
                "Devito 已安装但当前运行时不可执行三维 Operator："
                f"{status.message}。详情：{status.details}"
            )

        devito_config = _coerce_devito_config(config)
        velocity_grid = _get_value(scenario, "velocity_grid")
        if not isinstance(velocity_grid, VelocityGrid3D):
            raise TypeError("scenario.velocity_grid 必须是 VelocityGrid3D。")
        sources_all = _coordinate_array(_get_value(scenario, "source_xyz"), "source_xyz")
        receivers = _coordinate_array(_receiver_xyz_from_scenario(scenario), "receiver_xyz")
        selected_indices = _select_source_indices(len(sources_all), devito_config.source_indices)
        sources = sources_all[selected_indices]

        _validate_coordinates_inside_velocity_grid(sources, velocity_grid, "source_xyz")
        _validate_coordinates_inside_velocity_grid(receivers, velocity_grid, "receiver_xyz")
        _validate_cfl(velocity_grid, devito_config.dt_s)

        # Devito 对象只在真正运行时导入，避免未安装 Devito 的机器导入本项目失败。
        _prepare_devito_process_environment()
        from devito import Eq, Function, Grid, Operator, SparseTimeFunction, TimeFunction, solve  # type: ignore

        model_inputs = velocity_grid_to_devito_inputs(velocity_grid)
        grid = Grid(
            shape=model_inputs["shape"],
            extent=model_inputs["extent"],
            origin=model_inputs["origin"],
        )

        # `m=1/vp^2` 是速度模型参数。虽然它在物理上不随时间变化，但源注入项
        # `src * dt^2 / m` 会在稀疏震源位置对 `m` 做插值；若这里使用
        # `space_order=0`，Devito 的稀疏插值会报 “space order too small”。
        # 因此让 `m` 与波场使用同一空间阶数，既满足插值要求，也保持模型
        # 与当前最小 acoustic 方程一致。
        m = Function(name="m", grid=grid, space_order=devito_config.space_order)
        m.data[:] = 1.0 / np.asarray(velocity_grid.vp_mps, dtype=np.float32) ** 2

        time_axis_s = np.arange(devito_config.nt, dtype=float) * devito_config.dt_s
        data = np.zeros((len(sources), len(receivers), devito_config.nt), dtype=np.float32)
        snapshot_indices = tuple(range(0, devito_config.nt, devito_config.snapshot_interval))
        if snapshot_indices[-1] != devito_config.nt - 1:
            snapshot_indices = snapshot_indices + (devito_config.nt - 1,)
        snapshot_cube = None

        # 为了让 Stage 2B 的最小模型易于理解，这里使用最朴素的二阶声波方程：
        #   m * u.dt2 - Laplacian(u) = source
        # 其中 m=1/vp^2。没有自由表面和 PML，因此边界反射会存在；这些限制会写入
        # metadata，不能把结果解释成工程级高保真正演。
        u = TimeFunction(
            name="u",
            grid=grid,
            time_order=devito_config.time_order,
            space_order=devito_config.space_order,
            save=devito_config.nt,
        )
        src = SparseTimeFunction(name="src", grid=grid, npoint=1, nt=devito_config.nt)
        rec = SparseTimeFunction(name="rec", grid=grid, npoint=len(receivers), nt=devito_config.nt)
        rec.coordinates.data[:, :] = receivers
        stencil = Eq(u.forward, solve(m * u.dt2 - u.laplace, u.forward))
        src_term = src.inject(field=u.forward, expr=src * devito_config.dt_s**2 / m)
        rec_term = rec.interpolate(expr=u)
        operator = Operator([stencil] + src_term + rec_term, opt="noop")

        wavelet = ricker_wavelet(
            time_axis_s - 1.5 / devito_config.wavelet_frequency_hz,
            devito_config.wavelet_frequency_hz,
        ).astype(np.float32)
        for isource, source in enumerate(sources):
            u.data[:] = 0.0
            rec.data[:] = 0.0
            src.data[:] = 0.0
            src.coordinates.data[0, :] = source
            src.data[:, 0] = wavelet
            operator.apply(time_m=devito_config.nt - 2, dt=devito_config.dt_s)
            data[isource, :, :] = np.asarray(rec.data.T, dtype=np.float32)
            if isource == 0:
                snapshot_cube = np.asarray(u.data[snapshot_indices, :, :, :], dtype=np.float32).copy()

        metadata = self.metadata()
        metadata.update(
            {
                "data_order": "n_sources x n_receivers x n_times",
                "coordinate_system": "x 沿道路/光纤，y 横穿道路，depth 向下为正",
                "velocity_unit": "m/s",
                "time_unit": "s",
                "dt_s": devito_config.dt_s,
                "nt": devito_config.nt,
                "wavelet": "Ricker",
                "wavelet_frequency_hz": devito_config.wavelet_frequency_hz,
                "space_order": devito_config.space_order,
                "time_order": devito_config.time_order,
                "source_indices": [int(index) for index in selected_indices],
                "source_count_used": int(len(sources)),
                "receiver_count": int(len(receivers)),
                "uses_velocity_grid": True,
                "uses_void_body_velocity_perturbation": bool(velocity_grid.metadata.get("contains_void_body", False)),
                "boundary_condition": "未加入 PML/自由表面；最小模型会有边界反射",
                "wavefield_component": "scalar acoustic field",
                "wavefield_snapshots": {
                    "snapshot_indices": [int(index) for index in snapshot_indices],
                    "snapshot_times_s": [float(time_axis_s[index]) for index in snapshot_indices],
                    "snapshot_axis_order": "snapshot_time, x, y, depth",
                },
            }
        )
        if snapshot_cube is not None:
            metadata["wavefield_snapshot_array"] = snapshot_cube
            metadata["wavefield_snapshot_times_s"] = [float(time_axis_s[index]) for index in snapshot_indices]

        return ForwardResult3D(
            data=data,
            time_axis_s=time_axis_s,
            source_xyz=tuple(tuple(float(v) for v in row) for row in sources),
            receiver_xyz=tuple(tuple(float(v) for v in row) for row in receivers),
            travel_times_s=None,
            metadata=metadata,
        )


def velocity_grid_to_devito_inputs(velocity_grid: VelocityGrid3D) -> dict[str, Any]:
    """把 `VelocityGrid3D` 转换为 Devito `Grid` 所需的最小参数。

    本项目第三坐标叫 `depth`，向下为正；Devito 内部只是把它作为规则网格的
    第三维坐标处理。只要 source、receiver、速度网格和可视化使用同一约定，
    就不需要在 acoustic 后端里翻转坐标轴。
    """

    x = np.asarray(velocity_grid.x_m, dtype=float)
    y = np.asarray(velocity_grid.y_m, dtype=float)
    depth = np.asarray(velocity_grid.depth_m, dtype=float)
    return {
        "shape": tuple(int(v) for v in velocity_grid.shape),
        "origin": (float(x[0]), float(y[0]), float(depth[0])),
        "extent": (float(x[-1] - x[0]), float(y[-1] - y[0]), float(depth[-1] - depth[0])),
        "spacing": (
            _axis_spacing(x, "x_m"),
            _axis_spacing(y, "y_m"),
            _axis_spacing(depth, "depth_m"),
        ),
        "vp_mps": np.asarray(velocity_grid.vp_mps, dtype=np.float32),
        "axis_order": "x, y, depth",
    }


def detect_runtime_environment() -> str:
    """识别当前 Devito 后端所在的运行环境。

    返回值只用于 metadata 和运行摘要，不参与物理计算。Stage 2C 的关键结论是：
    Windows 原生 `myvoid` 可继续开发与测试，但 Devito Operator runtime 应优先在
    WSL/Linux conda 中运行。这里用操作系统、WSL 标志和 conda 环境变量给出
    稳定、无敏感信息的环境标签。
    """

    if _is_wsl_linux():
        return "wsl_linux_conda" if os.environ.get("CONDA_DEFAULT_ENV") else "wsl_linux"
    system = platform.system().lower()
    if system == "windows":
        return "windows_conda" if os.environ.get("CONDA_DEFAULT_ENV") else "windows"
    if system == "linux":
        return "linux_conda" if os.environ.get("CONDA_DEFAULT_ENV") else "linux"
    return system or "unknown"


def _is_wsl_linux() -> bool:
    if platform.system().lower() != "linux":
        return False
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False


def _run_devito_smoke_test() -> DevitoRuntimeStatus:
    if find_spec("devito") is None:
        return DevitoRuntimeStatus(
            import_available=False,
            runtime_available=False,
            message="Devito 未安装，无法导入 devito 包。",
        )

    _prepare_devito_process_environment()
    compiler_path = _find_c_compiler()
    version = None
    try:
        import devito  # type: ignore

        version = str(devito.__version__)
    except Exception as exc:
        return DevitoRuntimeStatus(
            import_available=False,
            runtime_available=False,
            compiler_path=compiler_path,
            message="Devito import 失败。",
            details={"error": repr(exc)},
        )

    if compiler_path is None:
        return DevitoRuntimeStatus(
            import_available=True,
            runtime_available=False,
            version=version,
            compiler_path=None,
            message="Devito 可导入，但当前 PATH 中没有可用的 gcc/cc/clang/cl 编译器。",
        )

    try:
        smoke = _execute_tiny_devito_operator_subprocess()
    except Exception as exc:
        return DevitoRuntimeStatus(
            import_available=True,
            runtime_available=False,
            version=version,
            compiler_path=compiler_path,
            message="Devito 可导入，但极小 Operator smoke test 无法启动。",
            details={
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )

    if smoke.returncode != 0:
        return DevitoRuntimeStatus(
            import_available=True,
            runtime_available=False,
            version=version,
            compiler_path=compiler_path,
            message="Devito 可导入，但极小 Operator 运行失败。",
            details={
                "returncode": smoke.returncode,
                "captured_stdout_tail": smoke.stdout[-1200:],
                "captured_stderr_tail": smoke.stderr[-1200:],
                "likely_windows_blockers": [
                    "Devito 默认分配器依赖 POSIX posix_memalign。",
                    "Devito/CodePy JIT 在 Windows + MinGW 下可能错误处理反斜杠路径。",
                    "Devito 上游示例和 Docker 镜像主要以 Linux/gcc 环境为主。",
                ],
            },
        )

    return DevitoRuntimeStatus(
        import_available=True,
        runtime_available=True,
        version=version,
        compiler_path=compiler_path,
        message="Devito import、JIT 编译和极小 Operator 运行均成功。",
    )


def _execute_tiny_devito_operator_subprocess() -> subprocess.CompletedProcess[str]:
    """在子进程中执行 smoke test，并捕获 gcc/CodePy 的终端输出。"""

    child_code = (
        "from hcz_road_void.forward.backends.devito_backend import "
        "_prepare_devito_process_environment, _execute_tiny_devito_operator; "
        "_prepare_devito_process_environment(); "
        "_execute_tiny_devito_operator(); "
        "print('devito tiny operator ok')"
    )
    return subprocess.run(
        [sys.executable, "-c", child_code],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(Path.cwd()),
        env=os.environ.copy(),
    )


def _execute_tiny_devito_operator() -> None:
    """执行一个不依赖项目几何的小型 Devito Operator smoke test。"""

    from devito import Eq, Grid, Operator, TimeFunction, configuration  # type: ignore
    from devito.data.allocators import DataReference  # type: ignore

    old_language = configuration["language"]
    old_opt = configuration["opt"]
    try:
        configuration["language"] = "C"
        configuration["opt"] = "noop"
        shape = (8, 8, 8)
        grid = Grid(shape=shape, extent=(7.0, 7.0, 7.0))

        # Windows 上默认 PosixAllocator 会先卡在 posix_memalign，因此 smoke test
        # 用 DataReference 预分配数组，尽量把诊断推进到 JIT 编译和动态库加载层。
        data = np.zeros((3, 12, 12, 12), dtype=np.float32)
        u = TimeFunction(
            name="u",
            grid=grid,
            time_order=2,
            space_order=2,
            save=3,
            allocator=DataReference(data),
        )
        u.data[0, 4, 4, 4] = 1.0
        operator = Operator(Eq(u.forward, 0.5 * u + 0.25 * u.backward), opt="noop")
        operator.apply(time_m=1, dt=0.001)
        if not np.isfinite(np.asarray(u.data)).all():
            raise RuntimeError("Devito smoke test 结果出现非有限数。")
    finally:
        configuration["language"] = old_language
        configuration["opt"] = old_opt


def _prepare_devito_process_environment() -> None:
    """为直接调用 `myvoid/python.exe` 的场景补齐运行时环境变量。

    用户常用命令是直接运行
    `D:\\HczApp\\Anaconda\\envs\\myvoid\\python.exe main.py`，这不会像
    `conda activate myvoid` 那样自动把 `Library/mingw-w64/bin` 加入 PATH。
    因此这里仅在当前 Python 前缀下查找编译器路径，并放到当前进程 PATH 前端。
    """

    prefix = Path(sys.prefix)
    for relative in [
        Path("Library") / "mingw-w64" / "bin",
        Path("Library") / "usr" / "bin",
        Path("Library") / "bin",
        Path("Scripts"),
    ]:
        candidate = prefix / relative
        if candidate.exists():
            path_text = str(candidate)
            path_parts = os.environ.get("PATH", "").split(os.pathsep)
            if path_text not in path_parts:
                os.environ["PATH"] = path_text + os.pathsep + os.environ.get("PATH", "")

    # pytools.prefork 在 Windows 上会访问 os.getuid；标准 Windows Python 没有该
    # 函数。这个补丁只影响当前进程，用于让 Devito/CodePy 继续走到 JIT 层。
    if os.name == "nt" and not hasattr(os, "getuid"):
        os.getuid = lambda: 0  # type: ignore[attr-defined]

    # 给 JIT 一个稳定的临时目录。即便当前 Windows 路径仍可能被 MinGW 误解析，
    # 固定目录也便于用户复查失败产物。
    jit_tmp = Path(tempfile.gettempdir()) / "hcz_devito_jit"
    jit_tmp.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TMP", str(jit_tmp))
    os.environ.setdefault("TEMP", str(jit_tmp))
    os.environ.setdefault("TMPDIR", str(jit_tmp))


def _find_c_compiler() -> str | None:
    for name in ("gcc", "cc", "clang", "cl"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _coerce_devito_config(config: DevitoForwardConfig | Mapping[str, Any] | None) -> DevitoForwardConfig:
    if config is None:
        return DevitoForwardConfig()
    if isinstance(config, DevitoForwardConfig):
        return config
    return DevitoForwardConfig(**dict(config))


def _coordinate_array(values: Sequence[Coordinate3D | Sequence[float]], name: str) -> np.ndarray:
    coords = [ensure_coordinate3d(value, f"{name}[{index}]").xyz for index, value in enumerate(values)]
    if not coords:
        raise ValueError(f"{name} 不能为空。")
    return np.asarray(coords, dtype=np.float32)


def _validate_coordinates_inside_velocity_grid(points: np.ndarray, grid: VelocityGrid3D, name: str) -> None:
    mins = np.array([grid.x_m[0], grid.y_m[0], grid.depth_m[0]], dtype=float)
    maxs = np.array([grid.x_m[-1], grid.y_m[-1], grid.depth_m[-1]], dtype=float)
    if np.any(points < mins) or np.any(points > maxs):
        raise ValueError(f"{name} 必须落在 VelocityGrid3D 覆盖范围内。")


def _validate_cfl(velocity_grid: VelocityGrid3D, dt_s: float) -> None:
    spacing = velocity_grid_to_devito_inputs(velocity_grid)["spacing"]
    min_spacing = min(float(value) for value in spacing)
    max_velocity = float(np.max(velocity_grid.vp_mps))
    # 三维二阶显式声波方程的保守 CFL 近似。这个检查不追求最优，只防止示例
    # 用明显过大的时间步爆炸。
    stable_dt = 0.45 * min_spacing / (max_velocity * np.sqrt(3.0))
    if dt_s > stable_dt:
        raise ValueError(
            f"dt_s={dt_s:.6g} s 可能违反 CFL 稳定性；当前速度网格建议 dt <= {stable_dt:.6g} s。"
        )


def _select_source_indices(n_sources: int, source_indices: Sequence[int] | None) -> np.ndarray:
    if source_indices is None:
        return np.arange(n_sources, dtype=int)
    indices = np.asarray(source_indices, dtype=int)
    if indices.ndim != 1 or len(indices) == 0:
        raise ValueError("source_indices 必须是一维非空索引。")
    if np.any(indices < 0) or np.any(indices >= n_sources):
        raise ValueError("source_indices 超出 source_xyz 范围。")
    return indices


def _axis_spacing(axis: np.ndarray, name: str) -> float:
    if len(axis) < 2:
        raise ValueError(f"{name} 至少需要两个网格点。")
    diffs = np.diff(axis)
    if not np.allclose(diffs, diffs[0]):
        raise ValueError(f"{name} 必须是规则等间距坐标轴，才能直接转换为 Devito Grid。")
    return float(diffs[0])


_MISSING = object()


def _get_value(scenario: Any, key: str, default: Any = _MISSING) -> Any:
    if isinstance(scenario, dict):
        if key in scenario:
            return scenario[key]
        if default is not _MISSING:
            return default
        raise KeyError(f"scenario 缺少字段: {key}")
    if hasattr(scenario, key):
        return getattr(scenario, key)
    if default is not _MISSING:
        return default
    raise AttributeError(f"scenario 缺少属性: {key}")


def _receiver_xyz_from_scenario(scenario: Any) -> Sequence[Coordinate3D | Sequence[float]]:
    sampled_receivers = _get_value(scenario, "sampled_receivers", default=None)
    if sampled_receivers is not None and hasattr(sampled_receivers, "receiver_xyz"):
        return sampled_receivers.receiver_xyz
    receiver_xyz = _get_value(scenario, "receiver_xyz", default=None)
    if receiver_xyz is not None:
        return receiver_xyz
    receivers = _get_value(scenario, "receivers", default=None)
    if receivers is not None and hasattr(receivers, "receiver_xyz"):
        return receivers.receiver_xyz
    raise AttributeError("scenario 必须提供 receiver_xyz 或 sampled_receivers.receiver_xyz")
