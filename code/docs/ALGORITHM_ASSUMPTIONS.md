# 算法假设与阶段边界

## 主场景

本项目主场景始终是三维道路 DAS + 锤击地下空洞探测，不是二维 `x-depth` 剖面问题。

坐标约定：

- `x`：沿道路或 DAS 光纤方向；
- `y`：横穿道路方向；
- `depth`：向下为正；
- `source_xyz`：锤击震源三维坐标；
- `receiver_polyline`：DAS 光纤三维折线；
- `receiver_xyz`：由光纤折线采样得到的三维通道点；
- `void_xyz`：异常体中心三维坐标。

默认场景为道路宽 15 m，DAS 光纤位于 `y=0 m` 一侧，锤击炮线位于 `y=15 m` 另一侧，空洞位于道路中部地下，默认 `void_xyz=(40.0, 7.5, 2.0)`。

## 当前正演假设

当前默认正演后端是 `kinematic`，物理关系为：

`总走时 = 震源到空洞的传播时间 + 空洞到接收点的传播时间`

即：

`t_total = |source_xyz - void_xyz| / v + |void_xyz - receiver_xyz| / v`

当前不是完整三维声波或弹性波波动方程正演，没有自由表面、PML、模式转换、真实体散射、多次波、衰减或各向异性。

## DAS 当前近似

当前 DAS 光纤已能用 `receiver_polyline` 表达并采样为 `receiver_xyz`，同时记录 gauge length metadata。但是当前记录仍是点接收器近似，不是真实 gauge-length averaged axial strain。

真实 DAS 轴向应变需要弹性位移场或应变张量，并沿光纤切向量计算：

`epsilon_fiber = t_i * epsilon_ij * t_j`

这个步骤留给后续 Devito elastic 或 OpenSWPC 后端。

## 体异常当前近似

`VoidBody3D` 支持 sphere 和 ellipsoid，并可嵌入三维速度网格。当前多散射点只是体模型代理，不是严格边界散射。后续真实波动方程后端应直接读取体速度模型。

## 定位目标函数当前假设

当前定位使用三维 `x-y-depth` travel-time energy stack。每个候选点都会计算 source-candidate-receiver 理论走时，并从合成记录中提取对应时间附近的能量。目标函数高值表示候选点更能解释多炮多道记录中的绕射事件。

当前定位模块用于验证三维几何、观测系统、正演数据结构和定位流程是否贯通。当前不以定位误差最小为核心验收指标。正演模型更真实之后，再系统优化定位精度。

## 不确定性当前假设

不确定性指标是初步指标，包括 best/second ratio、归一化目标函数、高能区域体积、半高宽和 y-depth 混淆判断。单侧光纤与单侧锤击几何容易造成横向 `y` 和深度 `depth` 混淆，后续应结合真实波形、更多观测孔径或先验约束分析。

## 后续方向

1. Devito：先接入三维声波方程正演，输出炮集和真实声波场快照。
2. OpenSWPC：作为外部三维弹性/黏弹性正演程序，推进真实 DAS 轴向应变。
3. Notebook：每轮算法推进后同步更新，清理旧参数和旧结论，作为项目进度把控入口。
