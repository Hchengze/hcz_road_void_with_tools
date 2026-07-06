# 本地三维正演工具深度审计

本文件记录 2026-07-06 在本机 `tools/` 目录下对第三方正演工具的二次审计。审计读取了本地 README、license、examples、参数文件、tests 或核心源码目录；不是只依据 GitHub 仓库页面。第三方源码仅作为本地参考，不默认提交到本项目 Git 仓库。

本项目主场景始终是三维道路 DAS + 锤击地下空洞探测：`x` 沿道路/光纤，`y` 横穿道路，`depth` 向下为正。正演能力优先级高于当前定位误差调参。

## 总体结论

1. **优先候选：Devito**。原因是 Python 接入自然，示例中已有 3D acoustic、elastic、viscoelastic 和 snapshotting 教程；最适合先做一个小尺度三维声波方程后端。
2. **高保真外部程序候选：OpenSWPC**。原因是 MIT 许可证、3D elastic/viscoelastic FDM、SAC/NetCDF 输出、station/source 参数文件清楚；适合作为外部程序调用，不适合强行改写成 Python 包。
3. **备选/对照：SW4、SPECFEM3D、SAVA、SeisCL**。这些工具物理能力强，但编译链、许可证或输入网格成本更高，暂不作为 Stage 2A 默认接入对象。
4. **不适合作为三维主后端：SOFI2D、SPECFEM1D**。本地版本分别是二维和一维，只能作为学习材料或降维对照，不能包装成三维道路正演。

## Devito

1. 工具名称：Devito。
2. 本地路径：`tools/devito-main`。
3. 当前是否存在：存在。
4. 主要语言：Python，底层通过符号表达生成 C/C++/OpenMP/OpenACC 等计算内核。
5. 许可证：MIT，见 `tools/devito-main/LICENSE.md`。
6. 是否支持三维：支持，`examples/seismic` 下有 3D acoustic/elastic/viscoelastic 教程和示例。
7. 物理方程：acoustic、elastic、viscoacoustic、viscoelastic、TTI，各向异性示例主要见 TTI。
8. 数值方法：有限差分，基于 Python DSL 和符号代码生成。
9. 自由表面：可通过自定义边界条件实现，示例更偏吸收边界；道路浅层自由表面需要专门验证。
10. 吸收边界/PML：`examples/seismic/abc_methods` 包含 damping、PML、HABC 教程。
11. 地表震源和地表接收：`SparseTimeFunction`、`RickerSource`、`Receiver` 支持任意稀疏坐标，地表点可表达。
12. 浅层道路适配：适合小尺度原型，网格间距、CFL 和边界层需要本项目重新设定。
13. 空洞/低速异常体适配：适合用 `VelocityGrid3D` 转为模型数组，在速度网格中嵌入低速体；真实空洞边界散射仍需波动方程验证。
14. 速度模型输出：本项目可输出 `.npz`，Devito 可接收 NumPy 数组构建 `Model`。
15. 炮集输出：Devito `Receiver.data` 可转为 `ForwardResult3D.data`。
16. 波场快照输出：`examples/seismic/tutorials/08_snapshotting.ipynb` 是重点入口。
17. 波场动图所需数据：可保存 TimeFunction 子采样快照，再由本项目生成 png/gif。
18. 输出物理量：acoustic 通常为压力/标量波场；elastic 示例包含速度/应力分量。
19. DAS 轴向应变潜力：声波后端不适合真实 DAS；elastic 后端可由位移/速度场推导沿光纤方向应变，但需要额外张量计算。
20. Python 接入难度：低到中；但 Windows/编译器/依赖安装需要验证。
21. 编译难度：中；JIT 编译依赖编译器和 Python 包。
22. 输入格式：Python API；核心对象包括 `Grid`、`Model`、`TimeFunction`、`SparseTimeFunction`、`Operator`、`RickerSource`、`Receiver`。
23. 输出格式：NumPy-like 数组，适合转为 `.npz`。
24. 最小可运行示例：`examples/seismic/acoustic/acoustic_example.py`、`examples/seismic/tutorials/01_modelling.ipynb`。
25. 本轮是否尝试运行最小示例：未运行。已在 `myvoid` 中检查 `import devito`，结果为不可用。
26. 推荐接入方式：Python API。
27. 主要风险：安装依赖、JIT 编译器、自由表面设置、浅层高频网格成本、DAS 轴向应变尚需 elastic 后端。
28. 建议优先级：最高，作为 Stage 2B 的首个真实三维声波正演后端。

## OpenSWPC

1. 工具名称：OpenSWPC。
2. 本地路径：`tools/OpenSWPC-master`。
3. 当前是否存在：存在。
4. 主要语言：Fortran 90，MPI。
5. 许可证：MIT，见 `tools/OpenSWPC-master/LICENSE`。
6. 是否支持三维：支持，核心入口 `src/swpc_3d/main.f90`。
7. 物理方程：3D/2D elastic 和 viscoelastic 方程，FDM。
8. 数值方法：有限差分 + MPI。
9. 自由表面：示例参数含 free surface、ocean bottom、topography 等地表相关设置。
10. 吸收边界/PML：`input.inf` 中 `abc_type='pml'` 或 `cerjan`，源码有 `m_absorb*.f90`。
11. 地表震源和地表接收：`source.dat`、`stloc.xy` 支持 xy/z 坐标和地表/边界定位模式。
12. 浅层道路适配：物理合适，但默认示例尺度偏区域地震；需要把单位、网格、时间步长改成道路浅层尺度。
13. 空洞/低速异常体适配：可通过用户速度模型或网格模型表达低速体；真空/强边界需要谨慎。
14. 速度模型输出：支持 uniform、grid、layered homogeneous、linear gradient、user model 等。
15. 炮集输出：`sw_wav_v/u/stress/strain` 控制 station 波形输出，格式 SAC 或 csf。
16. 波场快照输出：`m_snap.f90` 和 `input.inf` 支持 xy/xz/yz/free surface/ocean bottom 的速度、位移、P/S 振幅快照。
17. 波场动图所需数据：NetCDF 快照适合后处理成 png/gif。
18. 输出物理量：速度、位移、应力、应变、P/S 振幅等。
19. DAS 轴向应变潜力：强。若能输出应变张量或位移/速度场，可沿 DAS 切向量计算轴向应变或应变率。
20. Python 接入难度：中到高；应以子进程调用为主。
21. 编译难度：中到高；需要 Fortran、MPI、可能需要 NetCDF。
22. 输入文件格式：`.inf` 参数文件、source `.dat`、station `.xy/.ll`、速度模型文本/网格文件。
23. 输出文件格式：SAC/csf 波形、NetCDF/native 快照。
24. 最小可运行示例：`example/input.inf`、`example/source.dat`、`example/stloc.xy`。
25. 本轮是否尝试运行最小示例：未运行；未编译，未配置可执行文件。
26. 推荐接入方式：子进程调用外部程序。本项目负责生成输入文件、调用 `swpc_3d.x`、读取输出并转为 `ForwardResult3D`。
27. 主要风险：Windows 编译/MPI/NetCDF 成本、道路浅层单位转换、外部输出解析、真实 DAS 算子仍需二次开发。
28. 建议优先级：高，作为 Devito 声波后端之后的弹性/黏弹性高保真后端。

## SPECFEM3D

1. 工具名称：SPECFEM3D Cartesian。
2. 本地路径：`tools/specfem3d-master`。
3. 当前是否存在：存在。
4. 主要语言：Fortran，配套脚本和网格工具。
5. 许可证：GPLv3，见 `tools/specfem3d-master/LICENSE`。
6. 是否支持三维：支持。
7. 物理方程：acoustic、elastic、acoustic/elastic coupling、poroelastic。
8. 数值方法：谱元法。
9. 自由表面：支持；`Par_file` 中说明了自由表面和吸收边界的关系。
10. 吸收边界/PML：支持 Stacey absorbing、C-PML 等。
11. 地表震源和地表接收：`FORCESOLUTION`、`CMTSOLUTION`、`STATIONS` 支持点震源和接收点。
12. 浅层道路适配：物理能力强，但需要生成 hexahedral mesh；对于 80 m × 15 m × 浅层模型，网格准备成本较高。
13. 空洞/低速异常体适配：可在材料属性或外部模型中表达，但真实空洞边界需要合适网格和材料设置。
14. 速度模型输出：可通过 mesh/material 文件和 visualization 工具输出。
15. 炮集输出：`OUTPUT_FILES` 和 seismogram 文件。
16. 波场快照输出：支持 AVS/OpenDX movie、volume/surface movie 等。
17. 波场动图所需数据：movie 输出可后处理。
18. 输出物理量：位移、速度、应力、声学压力等，取决于配置。
19. DAS 轴向应变潜力：有位移/应力场时可推导，但需要自定义采样。
20. Python 接入难度：高；更适合作外部程序。
21. 编译难度：高；需要 Fortran、MPI、网格/分区工具。
22. 输入文件格式：`Par_file`、`STATIONS`、`FORCESOLUTION/CMTSOLUTION`、mesh/material 文件。
23. 输出文件格式：seismograms、mesh/movie 文件、数据库文件。
24. 最小示例：`EXAMPLES/applications/homogeneous_acoustic/run_this_example.sh`。
25. 本轮是否尝试运行最小示例：未运行，原因是未编译且不是本轮默认后端。
26. 推荐接入方式：暂不接入；后续只在需要复杂谱元网格时作为外部程序研究。
27. 主要风险：GPLv3、网格构建复杂、开发闭环慢。
28. 建议优先级：中低。

## SeisCL

1. 工具名称：SeisCL。
2. 本地路径：`tools/SeisCL-master`。
3. 当前是否存在：存在。
4. 主要语言：C/CUDA/OpenCL，带 Python wrapper。
5. 许可证：GPLv3。
6. 是否支持三维：支持 2D/3D。
7. 物理方程：isotropic acoustic、elastic、viscoelastic。
8. 数值方法：时域有限差分，GPU/CPU OpenCL/CUDA。
9. 自由表面：本地 `src/surface3D*.cl` 表明有 3D surface kernel。
10. 吸收边界/PML：源码有 CPML 更新 kernel。
11. 地表震源和地表接收：Python wrapper 和 HDF5 输入可表达。
12. 浅层道路适配：计算性能强，但 GPU/OpenCL/CUDA 依赖重。
13. 空洞/低速异常体适配：可通过模型数组表达低速体。
14. 速度模型输出：HDF5 模型输入输出。
15. 炮集输出：HDF5 输出。
16. 波场快照输出：源码和文档有边界/快照相关能力，需进一步运行验证。
17. 波场动图所需数据：可从 HDF5 快照后处理。
18. 输出物理量：压力、速度、应力等取决于模式。
19. DAS 轴向应变潜力：elastic/viscoelastic 下可扩展，但 wrapper 需二次适配。
20. Python 接入难度：中；wrapper 存在。
21. 编译难度：高；HDF5、CUDA/OpenCL、MPI。
22. 输入文件格式：HDF5。
23. 输出文件格式：HDF5。
24. 最小示例：`docs/notebooks/1_SimpleExample.ipynb`、`SeisCL/tests/test_analytics.py`。
25. 本轮是否尝试运行最小示例：未运行，未编译。
26. 推荐接入方式：暂不接入；后续作为 GPU 高性能对照。
27. 主要风险：GPLv3、GPU/驱动/HDF5 环境、Windows 编译。
28. 建议优先级：中低。

## SAVA

1. 工具名称：SAVA。
2. 本地路径：`tools/SAVA-master`。
3. 当前是否存在：存在。
4. 主要语言：C/MPI。
5. 许可证：GPLv3。
6. 是否支持三维：支持。
7. 物理方程：3D isotropic visco-acoustic/elastic、orthorhombic/triclinic anisotropic elastic。
8. 数值方法：三维有限差分。
9. 自由表面：参数文件支持自由面、PML、吸收边界组合。
10. 吸收边界/PML：`par/SAVA_ac.inp` 和源码中有 PML 参数与更新函数。
11. 地表震源和地表接收：`par/source/*.dat`、`par/receiver/*.dat` 支持三维坐标。
12. 浅层道路适配：网格单位可设为 m，理论可用。
13. 空洞/低速异常体适配：可读二进制/SU 模型或在源码模型文件中生成低速体。
14. 速度模型输出：参数中 `MODEL` 控制输出密度/模量等。
15. 炮集输出：SU/ASCII/BINARY seismogram。
16. 波场快照输出：`SNAP` 控制速度、压力、div、加速度等快照。
17. 波场动图所需数据：快照可由 Matlab 脚本后处理。
18. 输出物理量：速度、压力、div、加速度、弹性相关分量。
19. DAS 轴向应变潜力：弹性波场可扩展，但需自己实现光纤采样。
20. Python 接入难度：高；无现成 Python API。
21. 编译难度：高；MPI/C 编译和参数文件复杂。
22. 输入文件格式：`.inp` 参数、source/receiver 文本、模型二进制/SU 或源码生成。
23. 输出文件格式：SU、ASCII、BINARY、snapshot 文件。
24. 最小示例：`quickstart.txt`、`par/SAVA_ac.inp`。
25. 本轮是否尝试运行最小示例：未运行，未编译。
26. 推荐接入方式：只参考算法和参数组织，暂不接入主流程。
27. 主要风险：GPLv3、编译和模型生成重、源码改动成本高。
28. 建议优先级：中低。

## SW4

1. 工具名称：SW4。
2. 本地路径：`tools/sw4-master`。
3. 当前是否存在：存在。
4. 主要语言：C++/Fortran。
5. 许可证：GPLv2 or newer。
6. 是否支持三维：支持。
7. 物理方程：三维弹性波，支持各向异性、衰减、曲线坐标、网格加密等。
8. 数值方法：四阶有限差分。
9. 自由表面：支持，Lamb 示例即为地表源/接收问题。
10. 吸收边界/PML：supergrid 吸收边界。
11. 地表震源和地表接收：输入文件中 `source` 和 `rec` 命令可在地表设置。
12. 浅层道路适配：地表弹性波能力很相关，适合后续做浅层弹性对照。
13. 空洞/低速异常体适配：可通过材料块、rfile/sfile 等模型表达，需要进一步验证小尺度体异常。
14. 速度模型输出：`image mode=mu/lambda/rho` 等命令可输出模型相关图像。
15. 炮集输出：`rec` 输出 USGS/SAC 等格式。
16. 波场快照输出：`image mode=ux/uy/uz` 可输出切片图像。
17. 波场动图所需数据：连续 image 输出可后处理成动图。
18. 输出物理量：位移分量、材料参数、部分派生量。
19. DAS 轴向应变潜力：有位移场时可沿光纤差分估计轴向应变，需二次采样。
20. Python 接入难度：中到高；以外部程序更合理。
21. 编译难度：中到高。
22. 输入文件格式：SW4 `.in` 文本命令。
23. 输出文件格式：USGS/SAC/图片/二进制等。
24. 最小示例：`examples/lamb/lamb-1.in`、`examples/pointsource/pointsource-sg-1.in`。
25. 本轮是否尝试运行最小示例：未运行，未编译。
26. 推荐接入方式：后续作为外部程序或地表弹性波对照；暂不默认接入。
27. 主要风险：GPL、编译、模型格式适配、DAS 自定义采样。
28. 建议优先级：中。

## SOFI2D

1. 工具名称：SOFI2D。
2. 本地路径：`tools/sofi2d-master`。
3. 当前是否存在：存在。
4. 主要语言：C/MPI。
5. 许可证：GPL，见 `COPYING` 和 `LICENSE.info`。
6. 是否支持三维：本地版本不支持三维，是 2D P-SV viscoelastic anisotropic 代码。
7. 物理方程：二维黏弹各向异性 P-SV。
8. 数值方法：有限差分。
9. 自由表面：二维代码内可能支持。
10. 吸收边界/PML：二维代码内可能支持。
11. 地表震源和接收：二维可表达。
12. 浅层道路适配：只能做二维教学或对照。
13. 空洞/低速异常体适配：二维模型可表达，但不能代表本项目三维主场景。
14. 速度模型输出：二维。
15. 炮集输出：二维。
16. 波场快照输出：二维。
17. 波场动图所需数据：二维。
18. 输出物理量：二维弹性相关量。
19. DAS 轴向应变潜力：不能作为本项目三维 DAS 主路线。
20. Python 接入难度：高。
21. 编译难度：中到高。
22. 输入文件格式：SOFI 参数文件。
23. 输出文件格式：SOFI/SU 等。
24. 最小示例：`GETTING_STARTED.txt` 和示例目录。
25. 本轮是否尝试运行最小示例：未运行。
26. 推荐接入方式：仅作为二维教学参考，不能包装成三维算法。
27. 主要风险：维度不符合项目主线。
28. 建议优先级：低。

## SPECFEM1D

1. 工具名称：SPECFEM1D。
2. 本地路径：`tools/specfem1d-master`。
3. 当前是否存在：存在。
4. 主要语言：Fortran/Python 教学版本。
5. 许可证：见本地 `LICENSE`。
6. 是否支持三维：不支持，只是一维谱元教学代码。
7. 物理方程：一维波动方程/相关教学示例。
8. 数值方法：谱元法。
9. 自由表面：一维教学语境。
10. 吸收边界/PML：不作为本项目重点。
11. 地表震源和接收：一维。
12. 浅层道路适配：不适合作为工程正演后端。
13. 空洞/低速异常体适配：只能做一维教学。
14. 速度模型输出：一维。
15. 炮集输出：一维。
16. 波场快照输出：一维。
17. 波场动图所需数据：一维。
18. 输出物理量：一维位移/速度等。
19. DAS 轴向应变潜力：不适合。
20. Python 接入难度：低，但无三维价值。
21. 编译难度：低到中。
22. 输入文件格式：示例源码/参数。
23. 输出文件格式：教学输出。
24. 最小示例：`Fortran_version/src/specfem1d.f90`。
25. 本轮是否尝试运行最小示例：未运行。
26. 推荐接入方式：只作为谱元法学习材料。
27. 主要风险：维度不符合项目主线。
28. 建议优先级：低。
