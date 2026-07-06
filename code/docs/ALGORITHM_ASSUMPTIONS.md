# 算法假设

## 1. 当前算法类别

当前第一阶段流程是三维道路地下空洞的运动学绕射近似。它把空洞简化为单个点绕射体，用三维路径长度计算走时，再用 Ricker 子波生成合成记录。

它不是：

- 完整三维弹性波正演；
- 完整声波、黏弹性或孔弹性波动方程求解；
- FWI；
- 生产级偏移成像；
- 真实 DAS 轴向应变模拟。

## 2. 几何假设

- `x` 为沿道路或沿光纤方向；
- `y` 为横穿道路方向；
- `depth` 为向下为正的深度；
- `source_xyz`、`receiver_xyz`、`receiver_polyline` 和 `void_xyz` 始终是三维；
- 定位网格始终为 `search_x x search_y x search_depth`。

默认示例为道路宽 `15 m`、长 `80 m`，DAS 光纤位于 `y=0 m` 一侧，锤击炮线位于 `y=15 m` 另一侧，空洞位于道路中部地下，默认 `void_xyz=(40.0, 7.5, 2.0)`。

光纤和震源不在同一条线上，空洞也不在光纤正下方。由于观测仍然是单侧光纤和对侧锤击，横向 `y` 与深度 `depth` 的混淆仍然可能明显。

## 3. 正演假设

当前正演使用：

```text
t_total = |source_xyz - void_xyz| / v_background
        + |void_xyz - receiver_xyz| / v_background
```

合成记录是在每个理论走时处放置一个 Ricker 子波，并可选地乘以简单几何扩散衰减。

metadata 必须明确：

- `forward_type = "3d_kinematic_diffraction"`；
- `is_wave_equation_solver = False`；
- `is_elastic_solver = False`；
- `is_kinematic_approximation = True`；
- `approximation = "单点绕射体 / 运动学走时近似"`。

## 4. DAS/光纤假设

`ReceiverPolyline3D` 当前实现：

- 接收三维 `receiver_polyline`；
- 按固定 `channel_spacing_m` 采样为 `receiver_xyz`；
- 计算每个采样点局部切向量；
- 记录 `gauge_length_m` metadata。

当前限制：

- DAS 通道仍作为点接收器近似；
- 没有计算 gauge-length 平均轴向应变；
- 没有应变率转换；
- 真实 DAS 需要弹性位移场、应变张量和 `e^T epsilon(u)e` 观测算子。

## 5. 定位假设

定位目标函数是 travel-time energy stack：

1. 对每个候选点 `candidate_xyz=(x, y, depth)`，计算所有 source-candidate-receiver 理论走时；
2. 在合成记录对应时间附近提取绝对振幅；
3. 对所有炮道对平均或叠加；
4. 得到三维目标函数体，维度为 `(nx, ny, ndepth)`。

默认搜索范围为 `x=25..55 m`、`y=0..15 m`、`depth=0.5..5.0 m`，覆盖道路全宽和浅层空洞深度。

## 6. 不确定性假设

当前不确定性指标是目标函数体的轻量诊断：

- best/second ratio：峰值是否唯一；
- half-max 体素数量和比例：高能区域是否宽；
- x、y、depth 半高宽：不同方向上的定位扩散；
- y-depth confusion：单侧光纤条件下横向位置和埋深是否混淆。

这些指标不是校准后的置信区间，只用于第一阶段解释和筛查。

## 7. 后续高保真后端

当前几何和 metadata 层为后续外部正演工具预留接口：

- Devito：Python 原生三维 acoustic/elastic 原型；
- OpenSWPC：成熟 MIT 许可证三维弹性/黏弹性外部求解器；
- SPECFEM3D 或 SW4：更重的高保真验证工具。
