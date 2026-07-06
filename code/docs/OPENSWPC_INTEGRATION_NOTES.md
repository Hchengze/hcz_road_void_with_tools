# OpenSWPC 三维弹性/黏弹性正演接入笔记

## 当前状态

1. 本地路径：`tools/OpenSWPC-master`。
2. 当前是否编译：未编译。
3. 当前可执行文件：未配置。
4. 本项目 `OpenSWPCBackend.is_available()`：未配置时返回 `False`，不会让项目崩溃。
5. 推荐路线：作为外部程序调用，而不是改写为 Python 包。

## 编译和依赖

OpenSWPC 本地源码为 Fortran 90 + MPI。`src/swpc_3d/makefile` 引用 `src/shared/makefile.arch`，并包含 NetCDF、SAC、MPI 等共享模块。后续编译通常需要：

1. Fortran 编译器；
2. MPI；
3. NetCDF Fortran 库；
4. 运行环境变量和数据集路径配置。

本轮不编译、不安装依赖。

## 主要程序入口

1. 三维入口：`src/swpc_3d/main.f90`。
2. 三维 makefile：`src/swpc_3d/makefile`。
3. 速度模型模块：`m_vmodel_uni.f90`、`m_vmodel_grd.f90`、`m_vmodel_lhm.f90`、`m_vmodel_user.f90`。
4. 波形输出模块：`m_wav.f90`。
5. 快照输出模块：`m_snap.f90`。
6. 震源模块：`m_source.f90`。

## 示例参数文件

1. 主示例：`example/input.inf`。
2. 震源文件：`example/source.dat`。
3. 接收点文件：`example/stloc.xy`。
4. 分层模型：`example/lhm.dat`。
5. Green 函数示例：`example/green/*.inf`。

## 三维弹性/黏弹性正演配置

`input.inf` 中的关键字段：

1. `nx, ny, nz, dx, dy, dz, nt, dt`：三维网格和时间步长；
2. `vmodel_type`：`uni`、`grd`、`lhm` 等速度模型类型；
3. `vp0, vs0, rho0, qp0, qs0`：均匀模型参数；
4. `abc_type`、`na`：PML 或 Cerjan 吸收边界；
5. `fn_stf`、`stf_format`：震源文件；
6. `fn_stloc`、`st_format`：接收点文件；
7. `sw_wav_v/u/stress/strain`：速度、位移、应力、应变波形输出开关；
8. `xy/xz/yz/fs/ob_*%sw`：不同切片或表面快照输出开关。

## 模型文件格式

OpenSWPC 支持：

1. 均匀模型 `uni`；
2. GMT grid `grd`；
3. laterally homogeneous model `lhm`；
4. linear gradient model `lgm`；
5. user-defined model。

本项目后续可先把 `VelocityGrid3D` 转为 OpenSWPC 可读的 user/grid 模型；具体格式需要下一轮进一步从 `m_vmodel_user.f90` 和 `m_vmodel_grd.f90` 落地。

## 震源文件格式

`source.dat` 支持 moment tensor 或 body force。道路锤击更接近地表体力/冲击源，建议下一轮优先研究 body force 模式：

1. 坐标使用 xy 或 lon-lat；
2. `z` 为深度或边界修正模式；
3. 支持多行多源。

## 接收点文件格式

`stloc.xy` 示例列为：

`x y z stnm zsw`

其中 `zsw` 可控制接收点位于给定深度、自由面附近或边界附近。DAS polyline 采样后的 `receiver_xyz` 可写成多行 station。

## 输出炮集和快照

1. 炮集：SAC 或 csf，取决于 `wav_format`。
2. 波场快照：native 或 NetCDF，取决于 `snp_format`。
3. 可输出速度、位移、应力、应变；这对后续 DAS 轴向应变很关键。

## 道路浅层模型表达

建议下一轮外部程序路线：

本项目生成：

1. 速度模型文件；
2. 震源文件；
3. 接收点文件；
4. OpenSWPC 参数文件；
5. 运行目录。

然后：

`调用 OpenSWPC 外部程序 -> 读取 SAC/NetCDF -> 转为 ForwardResult3D`

## 低速空洞、脱空或松散区体模型表达

1. `VoidBody3D` 先嵌入 `VelocityGrid3D`；
2. 写出 OpenSWPC 可读的三维速度或用户模型；
3. 空洞第一版用低速体表达，不直接模拟真空边界；
4. 后续再研究密度、Vs、Q 和边界条件的更真实设置。

## DAS 轴向应变潜力

OpenSWPC 若输出应变张量或位移/速度波场，可沿 DAS 切向量计算：

`epsilon_fiber = t_i * epsilon_ij * t_j`

当前项目尚未实现该算子。Stage 2A 只记录 metadata：当前接收仍为点接收器或 polyline 点采样近似。

## 推荐接入方式

OpenSWPC 后端不应复制外部源码。推荐：

1. 本项目生成输入文件；
2. `OpenSWPCBackend` 通过子进程调用可执行文件；
3. 本项目读取输出；
4. 转为统一 `ForwardResult3D`；
5. 把快照数据转成 `WavefieldSnapshotResult`。
