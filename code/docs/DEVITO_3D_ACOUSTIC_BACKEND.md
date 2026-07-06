# Devito 3D Acoustic 后端说明

## 后端定位

`devito_acoustic_3d` 是本项目 Stage 2B 新增的三维声波波动方程后端。它的目标是把当前三维道路 DAS + 锤击地下空洞原型，从运动学点绕射过渡到真实波动方程数据结构。

必须强调：

1. 这是 acoustic 标量声波后端；
2. 不是三维弹性波后端；
3. 当前不能直接模拟 DAS gauge-length averaged axial strain；
4. 当前不以定位误差最小为验收目标。

## 安装方式和版本

安装命令：

```powershell
D:\HczApp\Anaconda\envs\myvoid\python.exe -m pip install devito --index-url https://pypi.org/simple
D:\HczApp\Anaconda\Scripts\conda.exe install -n myvoid -c conda-forge -y m2w64-toolchain
```

当前版本：

```text
devito 4.8.22
```

## 当前运行状态

当前 `myvoid` 可 import Devito，但 Windows 原生环境执行 Devito JIT Operator 仍失败。失败点在 Devito/CodePy/MinGW 编译链，而不是本项目三维几何或速度模型。

因此：

```text
Devito import_available = True
Devito runtime_available = False
```

`DevitoBackend.is_available()` 返回 `False`，表示当前机器还不能真实运行 Devito Operator。

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
  "is_wave_equation_solver": true,
  "is_elastic_solver": false,
  "supports_wavefield_snapshots": true,
  "supports_das_strain": false
}
```

## 快照和动图

当 runtime 可用时，`main.py --backend devito_acoustic_3d` 会输出：

```text
code/outputs/devito_synthetic_gather.png
code/outputs/devito_wavefield_snapshots/
code/outputs/devito_wavefield_animation.gif
code/outputs/devito_forward_summary.json
```

快照绘制的是穿过空洞横向位置附近的 `x-depth` 剖面。物理量是 acoustic scalar field，不是弹性位移或 DAS 应变。

## 当前 Windows 原生限制

当前失败诊断：

```text
Devito 可导入，但极小 Operator 运行失败。
codepy.CompileError: module compilation failed
```

主要原因：

1. Devito 默认 allocator 依赖 POSIX `posix_memalign`。
2. Windows Python 没有 `os.getuid`，需临时补丁才可进入 JIT。
3. MinGW/GCC 已安装后，CodePy 仍把 Windows 路径传成 gcc 无法识别的形式。

本项目不会伪造 Devito 波场，也不会把失败的占位结果当成真实声波正演。

## 下一步扩展

1. 在 WSL/Linux 或 Devito Docker 中验证同一 `DevitoBackend`。
2. Devito acoustic 跑通后，输出真实炮集、快照和 GIF。
3. 再把 Devito 炮集接入定位模块做对比。
4. 后续若要模拟 DAS 轴向应变，应扩展到 elastic displacement field 和 strain tensor，或接入 OpenSWPC。
