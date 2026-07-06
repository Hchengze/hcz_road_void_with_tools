# Stage 2 波动方程正演计划

## 当前阶段摘要

Stage 2 的目标是把项目从三维运动学点绕射原型，逐步推进到真实三维波动方程正演能力。

当前状态：

1. Stage 2A：已建立统一 `ForwardBackend` 接口、`VelocityGrid3D`、`VoidBody3D`、速度模型切片、波场快照接口。
2. Stage 2B：已实现 `DevitoBackend` 代码路径，并在 Windows `myvoid` 中安装 Devito；但 Windows 原生 Operator runtime 被 JIT 编译链阻塞。
3. Stage 2C：已在 WSL Linux conda 环境 `hcz_void_devito` 中跑通 Devito 4.8.22 Operator runtime，并成功运行 `main.py --backend devito_acoustic_3d`。

Stage 2C 的核心结论是：项目已经具备最小真实三维 acoustic 声波波动方程正演后端，但还不是三维弹性波正演，也不能直接模拟真实 DAS 轴向应变。

## 当前默认三维场景

默认几何保持不变：

```text
道路长度 = 80 m
道路宽度 = 15 m
DAS 光纤 = y=0 m
锤击炮线 = y=15 m
空洞中心 = (40.0, 7.5, 2.0)
depth = 向下为正
```

光纤、锤击点和空洞不在同一条二维剖面线上；横向 `y` 和 `depth` 的可分辨性仍是后续分析重点。

## 后端职责

### kinematic

用途：

1. 默认稳定演示；
2. 三维几何和数据结构回归测试；
3. 定位搜索与不确定性接口验证。

限制：

1. 不是波动方程；
2. 不输出真实波场；
3. 体异常只作为点绕射或多散射点代理。

### devito_acoustic_3d

用途：

1. 三维 acoustic 标量声波方程正演；
2. 使用 `VelocityGrid3D` 和 `VoidBody3D`；
3. 输出真实声波炮集；
4. 输出标量波场快照和 GIF。

当前 WSL 成功输出：

```text
data_shape = [3, 41, 220]
snapshot_count = 10
runtime_environment = wsl_linux_conda
```

限制：

1. 当前没有 PML/自由表面；
2. 当前不是弹性波；
3. 当前不能直接输出 DAS 轴向应变。

### openswpc_elastic_3d

用途：

1. 后续高保真三维弹性/黏弹性正演候选；
2. 更适合真实 DAS 轴向应变路线。

当前状态：

1. 只建立占位后端和接入文档；
2. 未编译；
3. 未作为 Stage 2C 运行目标。

## Stage 2C 已完成能力

1. WSL conda 环境 `hcz_void_devito` 中安装 Devito 4.8.22。
2. Devito import 成功。
3. Devito 极小 Operator smoke test 成功。
4. `DevitoRuntimeStatus` 区分三态：无法 import、可 import 但 runtime 不可用、runtime 可用。
5. `main.py --backend devito_acoustic_3d` 在 WSL 中成功运行。
6. 使用项目统一 `VelocityGrid3D`。
7. 使用项目统一 `VoidBody3D` 嵌入低速体异常。
8. 使用项目统一 `source_xyz` 和 `receiver_xyz`。
9. 输出真实声波炮集 `devito_synthetic_gather.png`。
10. 输出真实标量声波场快照目录。
11. 输出 `devito_wavefield_animation.gif`。
12. 输出 `devito_forward_summary.json`。

## 下一步计划

### 1. 稳定 Devito acoustic 后端

1. 加入 PML 或阻尼边界，减少边界反射。
2. 检查 CFL、网格间距、主频和时间步长的自动建议。
3. 支持多次运行的输出目录命名，避免覆盖。
4. 增加更小、更快的 Devito CI/pytest optional smoke case。

### 2. 改进波场输出

1. 同时输出 `x-depth`、`y-depth` 和 `x-y` 切片。
2. 增加 `.npz` 波场快照数据保存。
3. 解决 WSL 中文字体显示问题。
4. 为后续弹性波场预留分量字段。

### 3. 从 acoustic 推进到 elastic

1. 评估 Devito elastic 示例是否适合浅层道路模型。
2. 评估 OpenSWPC 外部程序路线。
3. 输出位移/速度/应力分量。
4. 构造 DAS gauge-length axial strain proxy 或真实应变算子。

### 4. 再系统优化定位

当前定位准确度不是 Stage 2C 核心验收指标。只有当真实正演后端更稳定后，才把 Devito/OpenSWPC 输出接入定位模块，并系统评估定位误差、横向-深度混淆和不确定性。

## 当前不做

1. 不为了让当前 `best_xyz` 更接近 `true_xyz` 硬调目标函数。
2. 不把 acoustic 结果说成 elastic 结果。
3. 不把点接收器记录说成真实 DAS 轴向应变。
4. 不安装或编译 OpenSWPC、SPECFEM3D、SW4、SeisCL、SAVA。
5. 不提交 `code/outputs/` 中的运行结果。
