# 正演输出约定

## 总体原则

本项目的正演输出分为两类：

1. 默认 `kinematic`：三维运动学点绕射近似，用于验证三维几何、数据结构、定位流程和不确定性分析。
2. `devito_acoustic_3d`：Devito 三维 acoustic 标量声波方程后端，用于生成真实波动方程炮集、速度模型切片、波场快照和 GIF。

两类输出都必须明确 metadata，不能把运动学结果说成波动方程结果，也不能把 acoustic 标量波场说成弹性波或真实 DAS 轴向应变。

## 默认输出目录

```text
code/outputs/
```

该目录默认被 `.gitignore` 排除，不提交到 GitHub。

## kinematic 默认输出

运行：

```powershell
D:\HczApp\Anaconda\envs\myvoid\python.exe main.py
```

输出：

```text
code/outputs/geometry_3d.png
code/outputs/velocity_model_slices.png
code/outputs/synthetic_gather.png
code/outputs/localization_slices.png
code/outputs/velocity_model_3d.npz
code/outputs/synthetic_data.npz
code/outputs/localization_objective.npz
code/outputs/wavefield_snapshots/
code/outputs/run_summary.json
```

其中 `wavefield_snapshots/` 对默认后端只是目录占位，metadata 标注为：

```text
wavefield_snapshot_type = not_available
is_true_wave_equation_wavefield = false
```

原因是运动学后端没有网格波场变量。

## Devito acoustic 输出

推荐在 WSL Linux conda 中运行：

```bash
cd /home/hcz/projects/hcz_road_void_with_tools/code
source /home/hcz/Software/Anaconda/etc/profile.d/conda.sh
conda activate hcz_void_devito
python main.py --backend devito_acoustic_3d
```

成功输出：

```text
code/outputs/velocity_model_3d.npz
code/outputs/velocity_model_slices.png
code/outputs/devito_synthetic_data.npz
code/outputs/devito_synthetic_gather.png
code/outputs/devito_wavefield_snapshots/snapshot_000.png
code/outputs/devito_wavefield_snapshots/snapshot_001.png
...
code/outputs/devito_wavefield_animation.gif
code/outputs/devito_forward_summary.json
```

当前 Stage 2C WSL 运行结果：

```text
runtime_environment = wsl_linux_conda
backend_name = devito_acoustic_3d
physics_type = acoustic_wave_equation
devito_version = 4.8.22
data_shape = [3, 41, 220]
snapshot_count = 10
is_wave_equation_solver = true
is_elastic_solver = false
supports_das_strain = false
is_true_wave_equation_wavefield = true
```

## devito_forward_summary.json 关键字段

```json
{
  "stage": "Stage 2C",
  "backend_name": "devito_acoustic_3d",
  "physics_type": "acoustic_wave_equation",
  "runtime_environment": "wsl_linux_conda",
  "conda_env_name": "hcz_void_devito",
  "devito_runtime_state": "runtime_available",
  "devito_version": "4.8.22",
  "is_wave_equation_solver": true,
  "is_elastic_solver": false,
  "is_true_wave_equation_wavefield": true,
  "supports_das_strain": false,
  "velocity_grid_shape": [81, 16, 9],
  "source_count": 3,
  "receiver_count": 41,
  "time_sample_count": 220,
  "snapshot_count": 10
}
```

字段含义：

1. `runtime_environment`：用于区分 Windows、WSL Linux 或其他 Linux conda 环境。
2. `devito_runtime_state`：Devito 三态诊断标签。
3. `velocity_grid_shape`：三维速度网格的 `x-y-depth` 维度。
4. `source_count`、`receiver_count`、`time_sample_count`：炮集数据维度说明。
5. `snapshot_count`：已写出的真实声波场快照数量。

## 波场快照说明

Devito 快照为：

```text
snapshot_cube: n_snapshots x nx x ny x ndepth
```

当前绘图选择最接近空洞 `y` 位置的 `x-depth` 剖面。图中的物理量是 acoustic scalar field。

不是：

1. 弹性位移；
2. 速度矢量；
3. 应力张量；
4. DAS gauge-length averaged axial strain。

## 当前限制

1. 默认 `kinematic` 没有真实波场。
2. Devito acoustic 后端没有 PML/自由表面，边界反射会存在。
3. Devito acoustic 不是弹性波正演，无法直接输出 DAS 轴向应变。
4. Stage 2C 只验证小尺度 runtime，不代表工程规模参数。
5. WSL 输出目录不提交到 GitHub，后续若要保留样例图，应另设轻量示例资产策略。
