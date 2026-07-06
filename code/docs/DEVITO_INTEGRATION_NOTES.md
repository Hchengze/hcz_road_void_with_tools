# Devito 三维声波正演接入笔记

## 当前 Stage 2B 状态

1. 本地源码审计路径：`tools/devito-main`。
2. 目标运行环境：`D:\HczApp\Anaconda\envs\myvoid\python.exe`。
3. Devito 安装状态：已安装，可 import。
4. 当前版本：`devito 4.8.22`。
5. 当前 runtime 状态：**尚不能在 Windows 原生 `myvoid` 中成功执行 Devito Operator**。
6. 当前项目处理方式：已实现 `DevitoBackend`、版本检测、runtime smoke test、Devito acoustic 运行路径和清晰中文错误；默认流程仍使用 `kinematic`。

## 本轮安装命令

首次尝试：

```powershell
D:\HczApp\Anaconda\envs\myvoid\python.exe -m pip install devito
```

该命令因镜像 SSL EOF 失败。

成功安装命令：

```powershell
D:\HczApp\Anaconda\envs\myvoid\python.exe -m pip install devito --index-url https://pypi.org/simple
```

为 Devito JIT 补充 MinGW/GCC 工具链：

```powershell
D:\HczApp\Anaconda\Scripts\conda.exe install -n myvoid -c conda-forge -y m2w64-toolchain
```

安装后可找到：

```text
D:\HczApp\Anaconda\envs\myvoid\Library\mingw-w64\bin\gcc.EXE
```

## 新增或变动依赖

Devito 安装引入或调整了以下关键包：

1. `devito 4.8.22`
2. `numpy 2.4.3`
3. `sympy 1.14.0`
4. `cgen 2025.1`
5. `codepy 2023.1`
6. `py-cpuinfo 9.0.0`
7. `multidict 6.2.0`
8. `anytree 2.13.0`
9. `pytools 2026.1.1`
10. `siphash24 1.8`
11. `mpmath 1.3.0`
12. `m2w64-toolchain 5.3.0` 及其 MinGW/GCC 依赖包

安装时出现提示：

```text
mkl-fft 2.2.0 requires mkl, which is not installed.
```

当前项目测试仍可通过；该提示记录为环境风险，后续若出现 NumPy/MKL 相关错误再单独处理。

## Devito runtime smoke test 结论

检查命令：

```powershell
D:\HczApp\Anaconda\envs\myvoid\python.exe -c "import devito; print(devito.__version__)"
```

结果：

```text
4.8.22
```

极小 Operator smoke test 当前失败，诊断摘要：

```text
Devito 可导入，但极小 Operator 运行失败。
codepy.CompileError: module compilation failed
```

已确认的 Windows 原生阻塞点：

1. Windows 标准 Python 没有 `os.getuid`，Devito/pytools JIT 路径会访问该函数。
2. Devito 默认内存分配器依赖 POSIX `posix_memalign`，Windows 原生 libc 不提供同样接口。
3. 补齐 MinGW/GCC 后，CodePy/MinGW 对 Windows 反斜杠路径处理仍有问题，gcc 收到类似 `C:Users...devito-jitcache...c` 的路径并找不到源文件。
4. Devito 上游 Docker 和 CI 示例主要围绕 Linux + gcc/clang/icx 环境；本机 Windows 原生不是最稳路线。

## 本项目 DevitoBackend 当前能力

已实现文件：

```text
code/hcz_road_void/forward/backends/devito_backend.py
```

已实现能力：

1. `DevitoBackend.get_version()`：返回 Devito 版本。
2. `DevitoBackend.runtime_status()`：区分 import 可用性和 Operator 运行可用性。
3. `DevitoBackend.is_available()`：只在极小 Operator smoke test 成功时返回 `True`。
4. `velocity_grid_to_devito_inputs()`：把 `VelocityGrid3D` 转成 Devito `Grid` 所需的 `shape/origin/extent/spacing`。
5. `DevitoForwardConfig`：保存 Devito acoustic 时间步长、步数、主频、差分阶数和快照间隔。
6. `DevitoBackend.run_forward()`：在 runtime 可用的机器上运行最小三维 acoustic 方程路径。
7. `main.py --backend devito_acoustic_3d`：显式尝试 Devito 后端；当前 Windows 原生环境下给出中文错误，不伪造结果。

## Devito 3D acoustic 核心流程

当前代码采用最小标量 acoustic 方程：

```text
m * u.dt2 - laplace(u) = source
m = 1 / vp^2
```

本项目映射关系：

1. `VelocityGrid3D.x_m/y_m/depth_m` → Devito `Grid(shape, origin, extent)`。
2. `VelocityGrid3D.vp_mps` → Devito `Function m=1/vp^2`。
3. `source_xyz=(x,y,depth)` → Devito `SparseTimeFunction` source 坐标。
4. `receiver_xyz=(x,y,depth)` → Devito `SparseTimeFunction` receiver 坐标。
5. `Ricker` 子波 → source time series。
6. `rec.data` → `ForwardResult3D.data`，顺序为 `n_sources x n_receivers x n_times`。
7. `u.data` 抽样 → 波场快照数组，后续保存为 PNG/GIF。

## 坐标约定

项目坐标始终为：

- `x`：沿道路或光纤方向；
- `y`：横穿道路方向；
- `depth`：向下为正。

Devito acoustic 后端把 `depth` 作为规则网格第三维，不在后端内翻转坐标轴。只要 source、receiver、速度网格和可视化全部遵守同一约定，声波方程数学上不需要关心“向上/向下”的地理语义。

## 波场快照和动图路线

已新增：

```text
code/hcz_road_void/visualization/wavefield.py
```

核心函数：

```text
save_scalar_wavefield_snapshots(...)
```

当 Devito runtime 可用时，输出：

```text
code/outputs/devito_wavefield_snapshots/snapshot_000.png
code/outputs/devito_wavefield_snapshots/snapshot_001.png
...
code/outputs/devito_wavefield_animation.gif
```

当前 Windows 原生 runtime 不可用，因此不会生成伪快照。

## 当前不做

1. 不把 acoustic 标量波场说成弹性波位移场。
2. 不把 receiver 点压力记录说成真实 DAS 轴向应变。
3. 不为降低当前定位误差修改定位目标函数。
4. 不复制 Devito 核心源码进本项目。
5. 不强行编译 OpenSWPC、SPECFEM3D、SW4、SeisCL 或 SAVA。

## 下一步建议

1. 优先在 WSL/Linux 或 Devito 官方 Docker 环境验证同一后端代码。
2. 如果必须坚持 Windows 原生，需进一步研究 CodePy/MinGW 路径转义和 Devito allocator 替换，不建议把这作为主线。
3. Devito acoustic 跑通后，再把输出接入定位模块做对比，但仍不以当前误差最小为 Stage 2B 验收指标。
4. 真正 DAS 轴向应变应转向 Devito elastic 或 OpenSWPC 弹性/黏弹性后端。
