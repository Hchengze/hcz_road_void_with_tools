# tools 工具审计清单

本审计阅读了 `tools/` 下各工具的说明文件和代表性源码。结论是：这些工具应作为外部求解器或算法参考使用，第一阶段不把第三方源码复制进 `code/`，也不默认提交到 GitHub。

## 1. 总表

| 工具 | 本地目录 | 许可证 | 三维支持 | 主要物理/方法 | 输入输出 | 本项目适配性 | 推荐复用方式 | 主要风险 |
|---|---|---:|---|---|---|---|---|---|
| Devito | `tools/devito-main` | MIT | 支持 | 符号化有限差分 DSL；示例含 acoustic、elastic、viscoacoustic、viscoelastic | Python model/geometry 对象、数组、接收记录 | Python 侧三维原型和后续波动方程正演的强候选 | 作为依赖或外部 API 调用，不复制内部源码 | JIT 编译、Windows 环境、DAS 算子仍需自研 |
| OpenSWPC | `tools/OpenSWPC-master` | MIT | 支持 | 三维/二维弹性、黏弹性 FDM，MPI | 参数文件、source/station 文件、波形和快照 | 成熟三维弹性外部正演候选 | 写适配器后外部调用 | Fortran/MPI 构建、网格调参、非 DAS 原生 |
| SAVA | `tools/SAVA-master` | GPLv3-only | 支持 | 三维 FD、FWI、RTM；声学/弹性/黏弹/各向异性 | 输入文件、震源接收点文件、SU/快照 | 物理相关，但不适合直接混入主代码 | 外部可执行程序或思想参考 | GPLv3、MPI/C 构建、大代码库 |
| SeisCL | `tools/SeisCL-master` | GPLv3-only | 支持 | 2D/3D acoustic、elastic、viscoelastic FDTD，CUDA/OpenCL | Python wrapper、HDF5、二进制程序 | 可作 GPU 高性能对比 | 外部 wrapper/HDF5 调用 | GPU/OpenCL/HDF5/MPI 依赖、GPL、单位标定 |
| SOFI2D | `tools/sofi2d-master` | GPLv2 | 不支持三维 | 二维黏弹各向异性 P-SV FDM | JSON、source/receiver、SU/快照 | 不能作为主正演 | 仅作二维工程参考 | 维度错误、GPL |
| SPECFEM1D | `tools/specfem1d-master` | GPLv2 | 不支持三维 | 一维谱元波传播教学代码 | Fortran/Python 示例 | 不适合主线 | 教学参考 | 维度错误、GPL |
| SPECFEM3D | `tools/specfem3d-master` | GPLv3 | 支持 | 三维谱元；acoustic、elastic、poroelastic | 网格、数据库、source/station、seismogram | 高保真验证候选 | 后续外部求解器 | 网格流程重、GPL、DAS 算子需自研 |
| SW4 | `tools/sw4-master` | GPLv2+ | 支持 | 三维四阶有限差分弹性波，曲网格、衰减、各向异性 | 文本输入、时序、图像 | 外部 benchmark 候选 | 后续外部调用 | GPL、C++/Fortran 构建、非 DAS 原生 |

## 2. Devito

审计文件包括 `README.md`、`LICENSE.md`、`examples/seismic/acoustic/acoustic_example.py`、`examples/seismic/elastic/elastic_example.py` 和 `examples/seismic/model.py`。

Devito 是 Python 中较适合本项目后续阶段的工具。它支持三维 acoustic/elastic 示例，许可证为 MIT，便于通过公共 API 接入。风险是 JIT 编译和依赖环境较复杂，且 DAS gauge-length 轴向应变算子仍需本项目自行实现。

建议：后续作为 Python 原生三维正演候选，不复制源码。

## 3. OpenSWPC

审计文件包括 `LICENSE` 和 `src/swpc_3d/` 下代表性 Fortran 模块。源码中有三维速度、应力、密度、Lamé 参数、衰减变量和 `nx, ny, nz` 网格变量，支持 station 输出速度、位移、应力和应变。

OpenSWPC 是成熟 MIT 许可的三维弹性/黏弹性外部求解器，适合后续高保真正演。风险是 Fortran/MPI 构建、参数文件适配和坐标约定映射。

建议：作为后续优先外部求解器候选，第一阶段不集成。

## 4. SAVA 与 SeisCL

SAVA 和 SeisCL 都支持三维波场模拟、FWI 或 RTM，物理能力较强。但二者均为 GPLv3-only，且依赖 MPI、GPU/OpenCL 或 HDF5 等复杂环境。

建议：仅作为外部可执行程序、benchmark 或算法参考；不复制源码进入本项目。

## 5. SOFI2D 与 SPECFEM1D

SOFI2D 是二维代码，SPECFEM1D 是一维教学代码。它们可以帮助理解有限差分或谱元工程结构，但不能作为三维道路空洞主流程。

建议：仅作背景参考，不用于主线正演。

## 6. SPECFEM3D 与 SW4

SPECFEM3D 和 SW4 都是成熟三维波动模拟工具，适合更后期高保真验证。但二者许可证和构建工作流较重，且都不是 DAS 原生工具。

建议：等本项目三维几何、DAS 观测接口和轻量定位闭环稳定后，再开发外部适配器。

## 7. 第一阶段工具决策

第一阶段不直接依赖 `tools/` 中任何外部大工具。当前路线是：

1. 先稳定三维几何、metadata、正演和定位接口；
2. 实现清楚标注的三维运动学绕射最小原型；
3. 保持接口可扩展，后续可接入 Devito 或 OpenSWPC；
4. 不盲目复制第三方源码，不忽略许可证。
