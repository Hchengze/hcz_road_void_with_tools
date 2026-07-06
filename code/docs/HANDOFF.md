# 项目交接记录

## 当前阶段

当前处于 Stage 2B：从三维运动学绕射原型，继续推进 Devito 3D acoustic 三维声波波动方程后端。

当前默认三维道路场景：

- 道路长度：80 m；
- 道路宽度：15 m；
- DAS 光纤：`y=0 m` 一侧；
- 锤击炮线：`y=15 m` 另一侧；
- 空洞中心：`void_xyz=(40.0, 7.5, 2.0)`；
- `depth` 向下为正；
- 光纤、震源和空洞共同构成真实三维几何。

## 已完成

1. Git 仓库已初始化并推送到 `https://github.com/Hchengze/hcz_road_void_with_tools`。
2. 文档、Notebook、代码注释和终端输出已中文化。
3. `code/main.py` 可运行。
4. 默认三维道路 DAS + 锤击几何已修正。
5. 三维运动学点绕射正演已实现。
6. 三维 `x-y-depth` travel-time energy stack 定位已实现。
7. DAS polyline 采样和 gauge metadata 已实现，但仍是点接收器近似。
8. Stage 2A 新增统一 `ForwardBackend` 接口。
9. Stage 2A 新增 `KinematicDiffractionBackend`、`DevitoBackend`、`OpenSWPCBackend`。
10. Stage 2A 新增 `VoidBody3D` 和 `VelocityGrid3D`。
11. Stage 2A 新增速度模型 `.npz` 输出和切片图。
12. Stage 2A 新增波场快照接口；当前运动学后端明确标注没有真实波场。
13. Stage 2B 已在 `myvoid` 中安装 `devito 4.8.22`。
14. Stage 2B 已安装 `m2w64-toolchain`，当前可找到 `gcc.EXE`。
15. Stage 2B 已实现 `DevitoForwardConfig`、`DevitoRuntimeStatus` 和 `velocity_grid_to_devito_inputs()`。
16. Stage 2B 已实现 `DevitoBackend.run_forward()` 的最小三维 acoustic 方程路径。
17. Stage 2B 已新增 `main.py --backend devito_acoustic_3d`。
18. Stage 2B 已新增 Devito 标量波场快照 PNG/GIF 输出接口。
19. 当前 Windows 原生 `myvoid` 未通过 Devito 极小 Operator smoke test，因此不生成伪 Devito 炮集或伪波场。

## 本地 tools 二次审计结论

1. Devito：优先候选，Python API 最适合先接入三维声波方程。
2. OpenSWPC：高保真外部程序候选，适合后续三维弹性/黏弹性与 DAS 应变。
3. SW4：地表弹性波能力强，可作为外部对照。
4. SPECFEM3D：物理能力强，但网格和编译成本高。
5. SAVA、SeisCL：可研究，但 GPL 和编译链较重。
6. SOFI2D、SPECFEM1D：不是三维主后端，只能作为教学或降维参考。

详细记录见：

- `code/docs/TOOLS_DEEP_DIVE.md`
- `code/docs/DEVITO_INTEGRATION_NOTES.md`
- `code/docs/OPENSWPC_INTEGRATION_NOTES.md`

## Devito / OpenSWPC 当前可用性

`myvoid` 中 Devito 当前可 import：

```text
devito 4.8.22
```

但 Devito 极小 Operator smoke test 当前失败：

```text
Devito 可导入，但极小 Operator 运行失败。
codepy.CompileError: module compilation failed
```

已确认环境状态：

```text
Devito import_available = True
Devito runtime_available = False
GCC = D:\HczApp\Anaconda\envs\myvoid\Library\mingw-w64\bin\gcc.EXE
```

主要阻塞点：

1. Windows 原生 Python 无 `os.getuid`；
2. Devito 默认 allocator 依赖 POSIX `posix_memalign`；
3. MinGW/GCC 已安装后，CodePy 仍会把 Windows 路径传成 gcc 无法识别的形式。

OpenSWPC 当前未编译，未配置可执行文件。因此 `OpenSWPCBackend.is_available()` 返回 `False`。

本轮没有强行编译 OpenSWPC、SPECFEM3D、SW4、SeisCL 或 SAVA。

## 本轮新增依赖

Devito 安装命令：

```powershell
D:\HczApp\Anaconda\envs\myvoid\python.exe -m pip install devito --index-url https://pypi.org/simple
```

GCC/MinGW 工具链安装命令：

```powershell
D:\HczApp\Anaconda\Scripts\conda.exe install -n myvoid -c conda-forge -y m2w64-toolchain
```

新增或变动的关键依赖：

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
12. `m2w64-toolchain 5.3.0` 及其 MinGW/GCC 依赖

## 运行环境

继续使用用户指定环境：

```powershell
D:\HczApp\Anaconda\envs\myvoid\python.exe main.py
D:\HczApp\Anaconda\envs\myvoid\python.exe -m pytest -p no:cacheprovider
```

不得使用 `mywork` 作为本项目验证环境。

## 本轮运行验证

已运行：

```powershell
D:\HczApp\Anaconda\envs\myvoid\python.exe main.py
D:\HczApp\Anaconda\envs\myvoid\python.exe -m pytest -p no:cacheprovider
D:\HczApp\Anaconda\envs\myvoid\python.exe main.py --backend devito_acoustic_3d
```

结果：

1. 默认 `main.py` 成功运行，当前后端为 `kinematic`。
2. 默认输出包含 `geometry_3d.png`、`velocity_model_slices.png`、`synthetic_gather.png`、`localization_slices.png` 和 `run_summary.json`。
3. `pytest` 结果为 `39 passed, 1 skipped`；跳过项为当前环境 Devito runtime 不可用时的真实 acoustic smoke test。
4. `main.py --backend devito_acoustic_3d` 给出中文失败诊断：Devito 可导入，版本 `4.8.22`，但极小 Operator 运行失败。

## 当前限制

1. 当前默认正演仍是三维运动学点绕射近似。
2. Devito acoustic 后端代码已接入，但当前 Windows 原生 `myvoid` runtime 仍不可用。
3. 当前不是完整三维弹性波正演。
4. 当前 DAS 仍是 polyline 点采样近似，不是真实 gauge-length averaged axial strain。
5. 当前体异常已能嵌入速度网格，但运动学后端仍默认使用中心点作为等效绕射体。
6. 当前默认 kinematic 后端没有真实波动方程波场输出。
7. Devito acoustic 即便跑通，也只是标量声波场，不是弹性位移或应变。
8. 当前定位准确度不是核心验收指标，不应为了降低误差过拟合目标函数。

## 下一轮建议

1. 优先在 WSL/Linux 或 Devito 官方 Docker 环境中验证当前 `DevitoBackend`。
2. 若必须继续 Windows 原生路线，定位 CodePy/MinGW 路径转义和 allocator 问题。
3. Devito acoustic runtime 通过后，输出真实声波炮集、波场快照和动图。
4. 再把 Devito 输出接入定位模块做对比，但不要为单个合成例子过拟合。
5. 后续再考虑 OpenSWPC 外部弹性/黏弹性正演和 DAS 轴向应变。
