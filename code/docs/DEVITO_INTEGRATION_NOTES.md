# Devito 三维声波正演接入笔记

## 当前 Stage 2C 状态

Stage 2C 的目标是把 Stage 2B 已实现的 `DevitoBackend` 从“代码路径存在”推进到“真实 Linux runtime 可运行”。当前结论如下：

1. Windows 原生 `myvoid`：Devito 已安装，可 import，版本为 `4.8.22`，但 Devito Operator runtime 仍受 CodePy/MinGW/JIT 编译链阻塞。
2. WSL Linux：发行版为 `ubuntu2204`，用户为 `hcz`，WSL conda 环境为 `hcz_void_devito`。
3. WSL conda 中 Devito 版本为 `4.8.22`。
4. WSL 中极小 Devito Operator smoke test 已通过，编译器为 `/usr/bin/gcc`。
5. WSL 中 `python main.py --backend devito_acoustic_3d` 已成功运行，生成真实三维 acoustic 炮集、标量波场快照和 GIF 动图。

这说明当前项目第一次具备了可运行的真实三维声波波动方程正演后端。但它仍是 acoustic 标量声波，不是弹性波，也不能直接模拟真实 DAS 轴向应变。

## 环境职责分工

Windows 原生 `myvoid` 继续作为项目普通开发与默认验证环境：

```powershell
D:\HczApp\Anaconda\envs\myvoid\python.exe main.py
D:\HczApp\Anaconda\envs\myvoid\python.exe -m pytest -p no:cacheprovider
```

WSL Linux conda 环境承担 Devito runtime 验证：

```bash
source /home/hcz/Software/Anaconda/etc/profile.d/conda.sh
conda activate hcz_void_devito
cd /home/hcz/projects/hcz_road_void_with_tools/code
python main.py --backend devito_acoustic_3d
python -m pytest -p no:cacheprovider
```

项目不再把 Windows 原生 Devito JIT 作为本阶段主线。

## WSL 安装命令

创建专用环境：

```bash
source /home/hcz/Software/Anaconda/etc/profile.d/conda.sh
conda create -n hcz_void_devito python=3.11 -y
conda activate hcz_void_devito
python -m pip install --upgrade pip
```

安装 Devito 和轻量依赖：

```bash
python -m pip install devito pytest numpy scipy matplotlib imageio pillow --index-url https://pypi.org/simple
```

本轮未安装 OpenSWPC、SPECFEM3D、SW4、SeisCL 或 SAVA。WSL 中 gcc/g++/make 已存在，本轮未写入任何密码到文件。

## Windows 安装记录

上一轮在 Windows `myvoid` 中安装过：

```powershell
D:\HczApp\Anaconda\envs\myvoid\python.exe -m pip install devito --index-url https://pypi.org/simple
D:\HczApp\Anaconda\Scripts\conda.exe install -n myvoid -c conda-forge -y m2w64-toolchain
```

Windows 当前状态仍记录为：Devito 可导入，但 Operator runtime 不作为主线验收。

## Devito runtime smoke test 结论

WSL 中检查：

```bash
python -c "import devito; print(devito.__version__)"
python -c "from hcz_road_void.forward import DevitoBackend; print(DevitoBackend().runtime_status(force=True).as_dict())"
```

关键结果：

```text
devito_version = 4.8.22
runtime_state = runtime_available
compiler_path = /usr/bin/gcc
```

`DevitoRuntimeStatus` 当前区分三种状态：

1. `import_unavailable`：无法导入 Devito；
2. `import_available_runtime_unavailable`：能导入但不能运行 Operator；
3. `runtime_available`：import、JIT 编译和极小 Operator 均成功。

## 本项目 DevitoBackend 能力

已实现文件：

```text
code/hcz_road_void/forward/backends/devito_backend.py
```

当前能力：

1. `DevitoBackend.get_version()`：返回 Devito 版本。
2. `DevitoBackend.runtime_status()`：区分 import 可用性和 Operator runtime 可用性。
3. `DevitoBackend.is_available()`：只有极小 Operator smoke test 成功才返回 `True`。
4. `velocity_grid_to_devito_inputs()`：把 `VelocityGrid3D` 转成 Devito `Grid` 所需的 `shape/origin/extent/spacing`。
5. `DevitoForwardConfig`：记录时间步长、步数、主频、差分阶数、快照间隔和震源子集。
6. `DevitoBackend.run_forward()`：在 runtime 可用环境中运行最小三维 acoustic 方程。
7. `main.py --backend devito_acoustic_3d`：显式运行 Devito 后端并保存真实炮集、快照和动图。

## Devito 3D acoustic 核心流程

当前后端采用最小标量 acoustic 方程：

```text
m * u.dt2 - laplace(u) = source
m = 1 / vp^2
```

本项目映射关系：

1. `VelocityGrid3D.x_m/y_m/depth_m` → Devito `Grid(shape, origin, extent)`；
2. `VelocityGrid3D.vp_mps` → Devito `Function m=1/vp^2`；
3. `source_xyz=(x,y,depth)` → Devito `SparseTimeFunction` source 坐标；
4. `receiver_xyz=(x,y,depth)` → Devito `SparseTimeFunction` receiver 坐标；
5. `Ricker` 子波 → source time series；
6. `rec.data` → `ForwardResult3D.data`，顺序为 `n_sources x n_receivers x n_times`；
7. `u.data` 抽样 → 标量声波场快照数组，再保存为 PNG/GIF。

## 坐标约定

项目坐标始终为：

- `x`：沿道路或光纤方向；
- `y`：横穿道路方向；
- `depth`：向下为正。

Devito acoustic 后端把 `depth` 作为规则网格第三维，不在后端内翻转坐标轴。只要 source、receiver、速度网格和可视化全部遵守同一约定，声波方程数学上不需要关心“向上/向下”的地理语义。

## 当前输出

WSL Devito runtime 跑通后生成：

```text
code/outputs/devito_synthetic_gather.png
code/outputs/devito_forward_summary.json
code/outputs/devito_wavefield_snapshots/
code/outputs/devito_wavefield_animation.gif
```

当前 WSL 输出记录：

```text
data_shape = [3, 41, 220]
snapshot_count = 10
runtime_environment = wsl_linux_conda
```

输出目录仍被 `.gitignore` 排除，不提交到 GitHub。

## 当前不做

1. 不把 acoustic 标量波场说成弹性波位移场。
2. 不把 receiver 点压力记录说成真实 DAS 轴向应变。
3. 不为降低当前定位误差修改定位目标函数。
4. 不复制 Devito 核心源码进本项目。
5. 不强行编译 OpenSWPC、SPECFEM3D、SW4、SeisCL 或 SAVA。

## 下一步建议

1. 稳定 Devito acoustic 最小后端的边界条件、网格尺寸和输出管理。
2. 增加 PML 或阻尼边界，减少当前最小模型的边界反射。
3. 评估 Devito elastic 或 OpenSWPC 外部弹性正演，用于真实 DAS 轴向应变路线。
4. 在真实波动方程输出稳定后，再系统优化定位精度和不确定性分析。
