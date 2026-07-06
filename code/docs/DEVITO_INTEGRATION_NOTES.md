# Devito 三维声波正演接入笔记

## 当前状态

1. 本地路径：`tools/devito-main`。
2. `myvoid` 环境可用性：不可用。
3. 检查命令：`D:\HczApp\Anaconda\envs\myvoid\python.exe -c "import devito; print(devito.__version__)"`。
4. 当前结果：`ModuleNotFoundError: No module named 'devito'`。
5. 本轮是否建议安装：暂不安装。Stage 2A 先完成接口、速度网格、体异常和文档；下一轮再评估安装 Devito 及编译器依赖。

## 本地示例入口

重点阅读位置：

1. `tools/devito-main/examples/seismic/acoustic/acoustic_example.py`
2. `tools/devito-main/examples/seismic/acoustic/wavesolver.py`
3. `tools/devito-main/examples/seismic/acoustic/operators.py`
4. `tools/devito-main/examples/seismic/model.py`
5. `tools/devito-main/examples/seismic/source.py`
6. `tools/devito-main/examples/seismic/tutorials/01_modelling.ipynb`
7. `tools/devito-main/examples/seismic/tutorials/08_snapshotting.ipynb`
8. `tools/devito-main/examples/seismic/elastic/elastic_example.py`

## 3D acoustic 核心流程

1. 用 `Grid` 定义三维计算域、网格点数、物理尺寸和坐标原点。
2. 用 `Model` 写入速度模型、网格间距、吸收边界层和物理参数。
3. 用 `TimeFunction` 表示随时间推进的波场，例如声压或标量波场。
4. 用 `RickerSource` 或 `SparseTimeFunction` 表示锤击源。需要把本项目 `source_xyz=(x,y,depth)` 转为 Devito 的稀疏坐标。
5. 用 `Receiver` 表示 DAS polyline 采样点。当前仍是点接收器近似，不是真实 DAS 轴向应变。
6. 用 `Operator` 生成并执行有限差分时间推进。
7. 把 `Receiver.data` 重排为本项目 `n_sources x n_receivers x n_times`。

## 关键对象说明

- `Grid`：三维网格容器，对应本项目 `VelocityGrid3D.x_m/y_m/depth_m`。
- `Model`：物性模型，下一轮应由 `VelocityGrid3D.vp_mps` 构建。
- `TimeFunction`：波场变量，后续可用于保存波场快照。
- `SparseTimeFunction`：稀疏源或接收插值对象。
- `Operator`：由符号方程生成的计算核。
- `RickerSource`：Ricker 子波震源，适合锤击近似的第一版声波源。
- `Receiver`：接收点数组，第一版映射为 DAS 通道点。

## 本项目坐标到 Devito 的映射

本项目坐标约定为 `x` 沿道路、`y` 横穿道路、`depth` 向下为正。Devito 需要一个规则三维网格。建议下一轮采用：

1. `origin=(x_min, y_min, depth_min)`，通常为 `(0,0,0)`；
2. `spacing=(dx, dy, dz)`，由 `VelocityGrid3D.spacing_m` 给出；
3. `shape=(nx, ny, ndepth)`，由 `VelocityGrid3D.shape` 给出；
4. `source.coordinates.data[:, :] = source_xyz`；
5. `receiver.coordinates.data[:, :] = receiver_xyz`。

需要特别验证 Devito 的第三坐标是否按数学 `z` 轴处理；本项目会把它解释为 `depth`，绘图时再保持向下为正。

## source、receiver 和 model 转换

1. `source_xyz`：每个锤击点建立一个 source，或多炮循环逐炮运行。
2. `receiver_xyz`：由 `ReceiverPolyline3D.sample_channels()` 生成，直接作为 receiver coordinates。
3. `VelocityModel3D`：常速度元数据，只能生成均匀 `VelocityGrid3D`。
4. `VelocityGrid3D`：下一轮的 Devito `Model` 主要输入。
5. `VoidBody3D`：应先嵌入 `VelocityGrid3D`，再交给 Devito，不应再作为单点散射体。

## 输出转换

1. `Receiver.data` 转为 `ForwardResult3D.data`。
2. 维度必须统一为 `n_sources x n_receivers x n_times`。
3. `ForwardResult3D.metadata` 必须包含：
   - `backend_name="devito_acoustic_3d"`
   - `physics_type="acoustic_wave_equation"`
   - `is_wave_equation_solver=True`
   - `is_elastic_solver=False`
   - `supports_wavefield_snapshots=True`
   - `supports_das_strain=False`

## 波场快照和动图

Devito 快照路线：

1. 用子采样 `TimeFunction` 或保存间隔记录波场；
2. 输出 `outputs/wavefield_snapshots/snapshot_000.png` 等；
3. 保存快照数据为 `.npz`；
4. 由 Matplotlib 或 imageio 生成 `outputs/wavefield_animation.gif`；
5. metadata 中明确物理量是声压/标量波场，不是弹性位移应变。

## CFL、网格和道路浅层尺度

道路模型尺度小、频率高，网格间距必须足够小以避免数值频散。下一轮需要系统确定：

1. 最小速度；
2. 最高有效频率；
3. 每波长网格点数；
4. 时间步长 CFL；
5. 吸收边界厚度；
6. 地表自由面是否先忽略或专门实现。

## 当前最小接入目标

下一轮建议只实现一个可运行的 Devito 3D acoustic 小模型：

1. 使用 `VelocityGrid3D`；
2. 单炮或少量炮；
3. DAS 点接收器；
4. 输出炮集和真实声波波场快照；
5. 不做 DAS 轴向应变；
6. 不调定位误差。

## 当前不做

1. 不安装大型依赖。
2. 不声称当前已实现 Devito 正演。
3. 不把声波压力记录说成 DAS 轴向应变。
4. 不做 Devito 弹性波或 FWI。
