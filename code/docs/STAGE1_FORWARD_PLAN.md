# 第一阶段三维正演计划

## 1. 推荐路线

第一阶段采用项目内部的三维运动学绕射/点散射最小原型，并为后续 Devito 或 OpenSWPC 外部正演后端保留接口。

选择原因：

- 当前最重要的是先稳定三维几何、数据结构和测试；
- 外部三维正演工具构建成本高，且 DAS 算子仍需自研；
- 运动学原型能快速验证 source、receiver、void 和 `x-y-depth` 搜索是否一致；
- 所有输出都明确标注不是完整三维弹性波正演。

## 2. 默认三维道路场景

默认示例为道路宽 `15 m`、长 `80 m`，DAS 光纤位于 `y=0 m` 一侧，锤击炮线位于 `y=15 m` 另一侧，空洞位于道路中部地下，默认 `void_xyz=(40.0, 7.5, 2.0)`。

坐标系统：

- `x`：沿道路或 DAS 光纤方向；
- `y`：横穿道路方向；
- `depth`：向下为正。

搜索范围：

- `search_x = 25..55 m`，31 个采样；
- `search_y = 0..15 m`，31 个采样，覆盖道路全宽；
- `search_depth = 0.5..5.0 m`，19 个采样，覆盖浅层空洞。

## 3. 当前正演物理

当前模型使用：

```text
tau(s, r, p) = |s - p| / v + |r - p| / v
```

其中：

- `s` 为三维震源；
- `r` 为三维接收点或 DAS 通道；
- `p` 为三维空洞中心或候选绕射点；
- `v` 为背景速度。

合成记录在理论走时处放置 Ricker 子波，并可选使用简单几何扩散振幅。该模型只用于运动学走时和定位目标函数研究，不表示完整波场传播。

## 4. 输入

必需输入：

- `source_xyz`：一个或多个三维震源位置；
- `receiver_xyz` 或 `receiver_polyline`：点接收器或 DAS 光纤三维折线；
- `void_xyz`：空洞中心或候选绕射点；
- `void_radius_m` 或 `void_size_xyz_m`：空洞尺度；
- `VelocityModel3D`：至少包含 `vp_mps`、`vs_mps`、密度；
- `ForwardConfig`：时间采样、子波主频和正演类型 metadata。

## 5. 输出

当前正演输出为：

```text
ForwardResult3D
  data
  time_axis_s
  source_xyz
  receiver_xyz
  travel_times_s
  metadata
```

数据顺序为 `n_sources x n_receivers x n_times`。metadata 必须记录：

- 坐标单位；
- depth 向下为正；
- 背景速度；
- 采样间隔；
- 正演类型；
- 是否运动学近似；
- 是否波动方程求解器；
- 是否弹性求解器；
- 是否使用外部工具。

## 6. 包结构

当前模块职责：

- `geometry`：三维坐标、场景容器和距离计算；
- `models`：速度模型和空洞模型；
- `receivers`：点接收器、DAS 光纤折线采样、切向量和 gauge metadata；
- `forward`：运动学走时、Ricker 子波和合成记录；
- `localization`：三维搜索网格、travel-time energy stack 和切片；
- `uncertainty`：目标函数体不确定性指标；
- `visualization`：三维场景、炮集和定位切片绘图；
- `io`：坐标和输出 metadata 约定。

## 7. 测试计划

测试应覆盖：

- 三维坐标拒绝二维输入；
- 速度、采样间隔、gauge length、channel spacing 必须为正；
- source、receiver、void 使用一致三维几何；
- DAS 光纤采样返回三维通道和单位切向量；
- 正演输出维度为 `n_sources x n_receivers x n_times`；
- 定位搜索网格为 `x-y-depth` 三维；
- 合成单空洞场景可恢复接近真值的 `best_xyz`；
- 默认道路几何中光纤在 `y=0`，锤击在 `y=road_width_m`，空洞在道路内部；
- `main.py` smoke test 能写出图像和 `run_summary.json`。

## 8. 当前不做内容

当前阶段不做：

- 完整三维弹性波正演；
- Devito/OpenSWPC/SPECFEM/SW4 执行；
- 自由表面、PML、衰减、各向异性或真实散射振幅；
- 真正 DAS gauge-length 轴向应变；
- FWI、生产偏移或概率反演；
- 把二维剖面算法包装成三维主结果。

## 9. 第一阶段验收标准

第一阶段可接受条件：

- 包可从 `code` 目录导入；
- `python main.py` 可以生成图像、数据和 JSON 摘要；
- `pytest` 通过；
- 文档明确声明当前只是三维运动学近似；
- `tools/` 和 `reference/` 的复用、版权和提交策略清楚；
- 后续能在不改变核心三维几何约定的情况下接入高保真正演后端。
