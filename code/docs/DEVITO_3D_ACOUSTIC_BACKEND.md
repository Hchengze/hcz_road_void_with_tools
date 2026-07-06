# Devito 3D Acoustic 后端说明

## 后端定位

`devito_acoustic_3d` 是本项目 Stage 2B 建立、Stage 2C 在 WSL Linux 中验证通过的三维声波波动方程后端。它的作用是把三维道路 DAS + 锤击地下空洞原型，从运动学点绕射推进到真实三维波动方程数据结构。

必须强调：

1. 这是 acoustic 标量声波后端；
2. 不是三维弹性波后端；
3. 当前不能直接模拟 DAS gauge-length averaged axial strain；
4. 当前不以定位误差最小为验收目标。

## 运行环境

当前验证通过的运行环境为：

```text
runtime_environment = wsl_linux_conda
WSL distro = ubuntu2204
WSL user = hcz
conda_env_name = hcz_void_devito
Devito version = 4.8.22
compiler_path = /usr/bin/gcc
```

Windows 原生 `myvoid` 仍可 import Devito，但不作为本阶段 Devito Operator runtime 主线。

## 安装方式

WSL conda 环境安装命令：

```bash
source /home/hcz/Software/Anaconda/etc/profile.d/conda.sh
conda create -n hcz_void_devito python=3.11 -y
conda activate hcz_void_devito
python -m pip install --upgrade pip
python -m pip install devito pytest numpy scipy matplotlib imageio pillow --index-url https://pypi.org/simple
```

本轮未保存任何密码，也未把认证信息写入仓库。

## 输入数据结构

后端使用项目内部数据结构，不复制 Devito 示例工程结构。

### 速度模型

输入为：

```python
VelocityGrid3D(
    x_m=...,
    y_m=...,
    depth_m=...,
    vp_mps=...,
)
```

坐标轴含义：

- `x`：沿道路或光纤方向；
- `y`：横穿道路方向；
- `depth`：向下为正。

转换函数：

```python
velocity_grid_to_devito_inputs(velocity_grid)
```

输出 Devito 所需的：

```text
shape
origin
extent
spacing
vp_mps
axis_order = x, y, depth
```

### 异常体

异常体先用 `VoidBody3D` 表达，再嵌入 `VelocityGrid3D`：

```python
velocity_grid = embed_void_body_into_velocity_grid(base_grid, void_body)
```

Devito 后端读取的是已经包含低速体异常的三维速度网格。当前不在 Devito 后端里硬编码另一套空洞位置。

### 震源和接收

输入：

```text
source_xyz
receiver_xyz
```

二者均为 `(x, y, depth)` 三维坐标。`receiver_xyz` 通常来自 `ReceiverPolyline3D.sample_channels()`，代表 DAS 光纤采样点的点接收器近似。

## 输出数据结构

后端统一返回：

```python
ForwardResult3D(
    data,
    time_axis_s,
    source_xyz,
    receiver_xyz,
    metadata,
)
```

数据顺序：

```text
n_sources x n_receivers x n_times
```

metadata 至少包含：

```json
{
  "backend_name": "devito_acoustic_3d",
  "physics_type": "acoustic_wave_equation",
  "runtime_environment": "wsl_linux_conda",
  "runtime_state": "runtime_available",
  "is_wave_equation_solver": true,
  "is_elastic_solver": false,
  "supports_wavefield_snapshots": true,
  "supports_das_strain": false
}
```

## main.py 输出

在 WSL 中运行：

```bash
cd /home/hcz/projects/hcz_road_void_with_tools/code
conda activate hcz_void_devito
python main.py --backend devito_acoustic_3d
```

当前成功输出：

```text
code/outputs/devito_synthetic_gather.png
code/outputs/devito_synthetic_data.npz
code/outputs/devito_wavefield_snapshots/
code/outputs/devito_wavefield_animation.gif
code/outputs/devito_forward_summary.json
```

`devito_forward_summary.json` 记录：

```text
backend_name = devito_acoustic_3d
runtime_environment = wsl_linux_conda
is_wave_equation_solver = true
is_elastic_solver = false
is_true_wave_equation_wavefield = true
supports_das_strain = false
data_shape = [3, 41, 220]
snapshot_count = 10
```

## 快照和动图

快照绘制的是穿过空洞横向位置附近的 `x-depth` 剖面。物理量是 acoustic scalar field，不是弹性位移或 DAS 应变。

当前输出函数：

```python
save_scalar_wavefield_snapshots(...)
```

输出目录：

```text
code/outputs/devito_wavefield_snapshots/snapshot_000.png
code/outputs/devito_wavefield_snapshots/snapshot_001.png
...
code/outputs/devito_wavefield_animation.gif
```

WSL 中若没有中文字体，Matplotlib 可能出现中文 glyph 警告；这只影响图中文字显示，不影响 Devito Operator 正演结果。后续可在 WSL 安装 CJK 字体或设置项目字体路径。

## 当前限制

1. 当前 acoustic 方程为标量声波近似，不是弹性波。
2. 当前最小模型没有 PML 或自由表面，边界反射会进入记录。
3. 当前接收记录仍是点接收器采样，不是真实 DAS gauge-length averaged axial strain。
4. 当前只选择少量震源做最小 runtime 验证，不代表工程规模模拟。
5. 当前定位模块暂未使用 Devito 炮集作为主线输入，Stage 2C 不追求定位误差最小。

## 下一步扩展

1. 为 Devito acoustic 后端加入阻尼边界或 PML。
2. 让输出目录支持多次运行的参数化命名，避免覆盖。
3. 评估 Devito elastic 或 OpenSWPC，用于位移场、应力场和 DAS 轴向应变。
4. 在真实波动方程输出稳定后，再把 Devito 炮集接入定位和不确定性模块。
