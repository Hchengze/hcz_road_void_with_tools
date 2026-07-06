# Stage 2A 到 Stage 2B 三维波动方程正演计划

## 阶段目标

Stage 2A 的目标是让项目从三维运动学绕射原型过渡到可接入真实三维波动方程正演后端的状态。

Stage 2B 的目标是优先接入 Devito 3D acoustic：安装 Devito、建立 `DevitoBackend`、接通 `VelocityGrid3D` / `VoidBody3D` / `source_xyz` / `receiver_xyz`，并在 runtime 可用时输出真实声波炮集、波场快照和波场动图。

当前定位模块的作用是验证三维几何、观测系统、正演数据结构和定位流程是否贯通。当前不以定位误差最小为核心验收指标。只有当正演模型从运动学近似推进到更真实的三维声波/弹性波正演后，才系统优化定位反演准确度。

## Stage 2B 当前结果

1. `myvoid` 中已安装 `devito 4.8.22`。
2. 已安装 `m2w64-toolchain`，可找到 `gcc.EXE`。
3. 已新增 `DevitoForwardConfig`、`DevitoRuntimeStatus` 和 `velocity_grid_to_devito_inputs()`。
4. 已实现 `DevitoBackend.run_forward()` 的三维 acoustic 方程路径。
5. 已新增 `main.py --backend devito_acoustic_3d`。
6. 已新增 `save_scalar_wavefield_snapshots()`，可在真实波场可用时输出 PNG 和 GIF。
7. 当前 Windows 原生 `myvoid` 仍未通过 Devito 极小 Operator smoke test，失败点为 CodePy/MinGW JIT 编译路径。
8. 因 runtime 未通过，本机当前不会生成伪 Devito 炮集或伪波场快照。

## 已完成的 Stage 2A 接口

1. 新增统一正演后端接口 `ForwardBackend`。
2. 当前运动学后端包装为 `KinematicDiffractionBackend`。
3. 新增 Devito 占位后端 `DevitoBackend`，未安装时优雅返回不可用。
4. 新增 OpenSWPC 占位后端 `OpenSWPCBackend`，未配置可执行文件时优雅返回不可用。
5. 新增 `VoidBody3D`，支持 sphere 和 ellipsoid。
6. 新增 `VelocityGrid3D`，支持三维均匀网格和低速体嵌入。
7. 新增速度模型 `.npz` 输出和速度模型切片图。
8. 新增 `WavefieldSnapshotResult` 接口，当前运动学后端标注没有真实波场快照。

## 正演后端优先级

1. **Devito 3D acoustic**：当前首选。接口和 acoustic 运行路径已在项目内实现；本机 Windows 原生 JIT 仍需解决。
2. **OpenSWPC 3D elastic/viscoelastic**：作为外部高保真正演程序，适合后续弹性波、应变和 DAS 轴向应变路线。
3. **SW4/SPECFEM3D/SAVA/SeisCL**：作为备选或对照，不在 Stage 2B 第一优先级。

## 数据结构要求

### 输入

1. `source_xyz`：锤击点三维坐标；
2. `receiver_polyline`：DAS 光纤三维折线；
3. `receiver_xyz`：DAS polyline 采样后的三维通道点；
4. `VelocityGrid3D`：三维速度模型；
5. `VoidBody3D`：三维低速体异常；
6. 后续弹性波还需要 `vs`、`rho`、`Q` 或弹性张量。

### 输出

1. `ForwardResult3D.data`：`n_sources x n_receivers x n_times`；
2. `ForwardResult3D.metadata`：后端名称、物理方程、是否波动方程、是否弹性波、是否支持快照和 DAS 应变；
3. `velocity_model_3d.npz`；
4. `velocity_model_slices.png`；
5. `synthetic_gather.png`；
6. `wavefield_snapshots/`；
7. `wavefield_animation.gif`；
8. `run_summary.json`。

## 当前不做

1. 不声称当前 Windows 原生环境已经成功输出 Devito 真实波场。
2. 不声称 acoustic 标量波场是三维弹性波。
3. 不把点接收器记录说成 DAS 真实轴向应变。
4. 不为了当前合成数据过拟合定位目标函数。
5. 不把二维剖面算法包装成三维算法。
6. 不强行编译 OpenSWPC、SPECFEM3D、SW4、SeisCL 或 SAVA。

## Stage 2B 建议路线

1. 在 WSL/Linux 或 Devito 官方 Docker 环境中验证当前 `DevitoBackend`。
2. 若必须使用 Windows 原生，继续定位 CodePy/MinGW 路径转义和 allocator 问题。
3. Devito acoustic runtime 通过后，多炮输出统一 `ForwardResult3D`。
4. 保存真实声波场快照并生成 `devito_wavefield_animation.gif`。
5. 更新 Notebook，清理旧的运动学-only 结论。
6. 只在波动方程数据稳定后再讨论定位目标函数改进。
