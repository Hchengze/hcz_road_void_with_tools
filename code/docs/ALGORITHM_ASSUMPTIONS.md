# 算法假设与当前边界

## 三维道路场景假设

本项目主场景始终是三维道路 DAS + 锤击地下空洞探测，不是二维 `x-depth` 剖面问题。

默认几何：

```text
道路长度 = 80 m
道路宽度 = 15 m
DAS 光纤 = y=0 m
锤击炮线 = y=15 m
空洞中心 = (40.0, 7.5, 2.0)
depth = 向下为正
```

坐标含义：

- `x`：沿道路或光纤方向；
- `y`：横穿道路方向；
- `depth`：向下为正。

光纤、锤击点和空洞共同构成真实三维观测几何。空洞不在光纤正下方，横向 `y` 和深度 `depth` 的混淆仍是重点分析对象。

## kinematic 后端假设

默认 `kinematic` 后端仍采用三维运动学点绕射近似：

```text
总走时 = 震源到空洞的走时 + 空洞到接收点的走时
t_total = |source_xyz - void_xyz| / v + |void_xyz - receiver_xyz| / v
```

它的作用是验证：

1. 三维几何是否一致；
2. `source_xyz`、`receiver_xyz`、`void_xyz` 数据结构是否贯通；
3. 三维 `x-y-depth` 定位搜索是否可运行；
4. 不确定性分析接口是否存在。

它不是：

1. 完整三维声波方程正演；
2. 完整三维弹性波正演；
3. 真实 DAS 轴向应变模拟；
4. 工程定位精度证明。

## Devito acoustic 当前假设

Stage 2C 已在 WSL Linux conda 环境中跑通 `devito_acoustic_3d` 后端。该后端使用三维 acoustic 标量声波方程：

```text
m * u.dt2 - laplace(u) = source
m = 1 / vp^2
```

当前能力：

1. 使用 `VelocityGrid3D`；
2. 使用 `VoidBody3D` 嵌入低速体异常；
3. 使用项目统一 `source_xyz` 和 `receiver_xyz`；
4. 输出真实声波炮集；
5. 输出真实标量声波场快照和 GIF；
6. 返回统一 `ForwardResult3D` 和 metadata。

当前 WSL 状态：

```text
Devito version = 4.8.22
runtime_environment = wsl_linux_conda
runtime_state = runtime_available
```

Windows 原生 `myvoid` 中 Devito 仍可能只能 import，不能稳定运行 Operator，因此 Windows 不作为本阶段 Devito runtime 主线。

## DAS 观测假设

当前 DAS 光纤通过 `receiver_polyline` 表达，并按通道间距采样为 `receiver_xyz`。这些接收点目前仍是点接收器近似。

当前不是严格 DAS 轴向应变，因为真实 DAS 需要：

1. 弹性位移场；
2. 应变张量；
3. 沿光纤方向投影；
4. gauge length 空间平均；
5. 可能还需要仪器响应和采样率建模。

Devito acoustic 输出的是标量声波场，不能直接给真实 DAS gauge-length averaged axial strain。

## 体异常假设

`VoidBody3D` 支持球体和椭球体，并可用于：

1. 嵌入 `VelocityGrid3D` 形成低速体；
2. 采样为多散射点，兼容运动学代理。

多散射点只是体模型代理，不是严格边界散射。真实体异常传播效应应优先由 Devito/OpenSWPC 等波动方程后端在速度网格中表达。

## 定位假设

当前定位目标函数仍是 travel-time energy stack。它遍历三维 `search_x`、`search_y`、`search_depth`，对每个候选点计算理论绕射走时，并在记录中提取能量形成目标函数体。

当前定位模块的作用是验证流程闭环，不是把当前示例的定位误差调到最小。只有当正演模型更接近真实场景后，才系统优化定位精度。

## 当前主要限制

1. 默认后端仍是运动学近似。
2. Devito acoustic 不是弹性波。
3. Devito 最小模型当前没有 PML 或自由表面。
4. 当前 DAS 仍是点接收器/polyline 采样近似。
5. 当前没有真实道路数据输入。
6. 当前没有工业级速度模型建模、噪声建模或仪器响应。
7. 当前不以定位误差最小作为核心验收指标。

## 下一步假设收缩方向

1. 为 Devito acoustic 加入阻尼边界或 PML。
2. 输出更多波场分量或切片类型。
3. 评估 Devito elastic 或 OpenSWPC 弹性后端。
4. 在弹性位移场基础上实现 DAS 轴向应变。
5. 再把真实波动方程炮集系统接入定位和不确定性分析。
