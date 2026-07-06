# Stage 2A 到 Stage 2B 三维波动方程正演计划

## 阶段目标

本轮 Stage 2A 的目标不是新增复杂定位算法，也不是把当前定位误差调到最小，而是让项目从三维运动学绕射原型过渡到可接入真实三维波动方程正演后端的状态。

当前定位模块的作用是验证三维几何、观测系统、正演数据结构和定位流程是否贯通。当前不以定位误差最小为核心验收指标。只有当正演模型从运动学近似推进到更真实的三维声波/弹性波正演后，才系统优化定位反演准确度。

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

1. **Devito 3D acoustic**：下一轮首选，实现小尺度三维声波方程正演、炮集和真实声压/标量波场快照。
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

1. 不接入 Devito/OpenSWPC 大型安装。
2. 不声称完成完整三维弹性波正演。
3. 不把点接收器记录说成 DAS 真实轴向应变。
4. 不为了当前合成数据过拟合定位目标函数。
5. 不把二维剖面算法包装成三维算法。

## Stage 2B 建议路线

1. 在 `myvoid` 中安装或配置 Devito，记录依赖和编译器状态。
2. 用 `VelocityGrid3D` 构建一个小尺度 3D acoustic Devito 模型。
3. 多炮循环输出统一 `ForwardResult3D`。
4. 保存真实声波场快照。
5. 生成 `wavefield_animation.gif`。
6. 更新 Notebook，清理旧的运动学-only 结论。
7. 只在波动方程数据稳定后再讨论定位目标函数改进。
