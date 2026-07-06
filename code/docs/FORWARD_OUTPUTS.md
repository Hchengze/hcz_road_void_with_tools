# 正演输出约定

Stage 2A 开始把正演输出从单一合成炮集扩展为后续波动方程后端所需的完整目录约定。

## 当前输出目录

默认输出到：

```text
code/outputs/
```

当前 `code/outputs/` 已在 `.gitignore` 中排除，不提交到 GitHub。

## 当前文件

1. `geometry_3d.png`：三维道路 DAS + 锤击几何图。
2. `velocity_model_3d.npz`：三维速度模型，包含 `x_m`、`y_m`、`depth_m`、`vp_mps` 和 metadata。
3. `velocity_model_slices.png`：速度模型 `x-y`、`x-depth`、`y-depth` 切片。
4. `synthetic_data.npz`：合成记录和走时表。
5. `synthetic_gather.png`：单炮 receiver-time 记录图。
6. `localization_objective.npz`：三维定位目标函数体。
7. `localization_slices.png`：定位目标函数切片。
8. `wavefield_snapshots/`：后续真实波场快照目录，当前运动学后端为空或仅作占位。
9. `run_summary.json`：本次运行摘要。

## 当前波场快照状态

当前默认后端是 `kinematic`，没有真实网格波场变量，因此：

```json
{
  "wavefield_snapshot_type": "not_available",
  "is_true_wave_equation_wavefield": false
}
```

后续 Devito/OpenSWPC 接入后，才应输出真实波场快照和动图。

## 后续目标

1. `wavefield_snapshots/snapshot_000.png` 等真实快照；
2. `wavefield_animation.gif`；
3. 声波后端输出压力或标量波场；
4. 弹性后端输出位移、速度、应力或应变；
5. DAS 后处理输出沿光纤方向轴向应变或应变率。
