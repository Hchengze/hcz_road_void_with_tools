# 三维体异常模型说明

## 为什么需要体异常

上一阶段的 `VoidModel3D` 只包含 `void_xyz` 和半径，用于单点绕射近似。真实道路地下空洞、脱空或松散区不是一个数学点，而是三维体异常。Stage 2A 新增 `VoidBody3D`，目的是让项目开始从点异常过渡到体模型。

## 坐标约定

- `x`：沿道路或 DAS 光纤方向；
- `y`：横穿道路方向；
- `depth`：向下为正；
- 单位均为 m。

## 当前支持

1. `sphere`：球体，要求 `size_xyz_m` 三方向相同；
2. `ellipsoid`：椭球体，允许 `x/y/depth` 三方向尺寸不同；
3. `sample_void_body_as_scatterers()`：把体异常采样成多个散射点；
4. `embed_void_body_into_velocity_grid()`：把体异常写入三维速度网格。

## 当前默认体异常

```python
VoidBody3D(
    center_xyz=(40.0, 7.5, 2.0),
    body_type="ellipsoid",
    size_xyz_m=(2.0, 2.0, 1.0),
    velocity_scale=0.5,
)
```

含义：道路中部浅层低速椭球体，体内速度为背景速度的 50%。

## 重要限制

1. 多散射点只是当前运动学后端的体模型代理，不是严格边界散射。
2. 速度网格嵌入只改变 `vp_mps`，暂未同步 `vs`、密度、Q 或弹性张量。
3. 真实空洞可能接近空气/空腔边界，不能仅靠 `velocity_scale=0.5` 完整表达。
4. Devito/OpenSWPC 接入后，应优先使用体速度模型，而不是继续依赖单点绕射中心。
