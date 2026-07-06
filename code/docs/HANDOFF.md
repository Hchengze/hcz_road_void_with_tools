# 项目交接记录

## 当前阶段

当前处于 Stage 2C.1：先修正 Stage 2C 的使用体验问题，包括 WSL Devito 输出同步到 Windows `code/outputs/`，以及 Notebook 中文和图片可读性。

默认三维道路场景：

- 道路长度：80 m；
- 道路宽度：15 m；
- DAS 光纤：`y=0 m` 一侧；
- 锤击炮线：`y=15 m` 另一侧；
- 空洞中心：`void_xyz=(40.0, 7.5, 2.0)`；
- `depth` 向下为正；
- 光纤、震源和空洞共同构成真实三维几何。

## 已完成

1. Git 仓库已初始化并推送到 `https://github.com/Hchengze/hcz_road_void_with_tools`。
2. 文档、Notebook、代码注释和终端输出已中文化。
3. `code/main.py` 可运行。
4. 默认三维道路 DAS + 锤击几何已修正。
5. 三维运动学点绕射正演已实现。
6. 三维 `x-y-depth` travel-time energy stack 定位已实现。
7. DAS polyline 采样和 gauge metadata 已实现，但仍是点接收器近似。
8. 已建立统一 `ForwardBackend` 接口。
9. 已实现 `KinematicDiffractionBackend`、`DevitoBackend`、`OpenSWPCBackend`。
10. 已实现 `VoidBody3D` 和 `VelocityGrid3D`。
11. 已实现速度模型 `.npz` 输出和切片图。
12. 已实现波场快照接口；运动学后端明确标注没有真实波场。
13. Windows 原生 `myvoid` 中 Devito 4.8.22 可 import，但 Operator runtime 不作为主线。
14. WSL Linux conda 环境 `hcz_void_devito` 中 Devito 4.8.22 已通过 Operator smoke test。
15. WSL 中 `main.py --backend devito_acoustic_3d` 已成功生成真实 acoustic 炮集、波场快照和 GIF。
16. Stage 2C.1 已支持通过 `--output-dir` 把 WSL Devito 输出直接写入 Windows 项目 `code/outputs/`。
17. Stage 2C.1 已新增 `code/notebooks/assets/`，让 GitHub Notebook 能显示关键小图。
18. Stage 2C.1 已修复 Devito 时间循环参数，避免 Operator 只跑初始步导致炮集和快照全零。

## 运行环境

Windows 开发与默认验证环境：

```text
D:\HczApp\Anaconda\envs\myvoid\python.exe
```

WSL Devito runtime 环境：

```text
WSL distro = ubuntu2204
WSL user = hcz
Project path = /home/hcz/projects/hcz_road_void_with_tools
Anaconda path = /home/hcz/Software/Anaconda
Conda env = hcz_void_devito
Devito version = 4.8.22
Compiler = /usr/bin/gcc
```

本文件不记录任何密码或交互认证信息。

## 本轮 WSL 安装命令

```bash
source /home/hcz/Software/Anaconda/etc/profile.d/conda.sh
conda create -n hcz_void_devito python=3.11 -y
conda activate hcz_void_devito
python -m pip install --upgrade pip
python -m pip install devito pytest numpy scipy matplotlib imageio pillow --index-url https://pypi.org/simple
```

本轮未安装 OpenSWPC、SPECFEM3D、SW4、SeisCL 或 SAVA。WSL 中已有 `gcc`、`g++`、`make`，未执行 `sudo apt install`。

## 新增依赖

WSL `hcz_void_devito` 中新增或确认：

1. `devito 4.8.22`
2. `pytest 9.1.1`
3. `numpy 2.4.3`
4. `scipy 1.17.1`
5. `matplotlib 3.11.0`
6. `imageio 2.37.3`
7. `pillow 12.3.0`
8. Devito 依赖：`cgen`、`codepy`、`sympy`、`pytools` 等

Windows `myvoid` 上一轮已安装 `devito 4.8.22` 和 `m2w64-toolchain`，但 Windows Devito Operator runtime 仍不作为本阶段验收主线。

## Devito 当前可用性

WSL 中：

```text
import_available = True
runtime_available = True
runtime_state = runtime_available
devito_version = 4.8.22
compiler_path = /usr/bin/gcc
```

Windows 原生 `myvoid` 中：

```text
import_available = True
runtime_available = False
```

主要 Windows 阻塞点仍是 Devito/CodePy/MinGW/JIT 编译链。项目不会伪造 Windows Devito 波场。

OpenSWPC 当前未编译，未配置可执行文件。因此 `OpenSWPCBackend.is_available()` 返回 `False`。

## Stage 2C 输出

WSL 中成功运行：

```bash
cd /home/hcz/projects/hcz_road_void_with_tools/code
source /home/hcz/Software/Anaconda/etc/profile.d/conda.sh
conda activate hcz_void_devito
python main.py --backend devito_acoustic_3d --output-dir /mnt/e/HczDocument/BaiduDisk/BaiduSyncdisk/HCZ_work/CodexProject/HCZ_road_void_with_tools/code/outputs
```

输出：

```text
code/outputs/devito_synthetic_gather.png
code/outputs/devito_forward_summary.json
code/outputs/devito_wavefield_snapshots/
code/outputs/devito_wavefield_animation.gif
```

关键结果：

```text
backend_name = devito_acoustic_3d
runtime_environment = wsl_linux_conda
is_wave_equation_solver = true
is_elastic_solver = false
supports_das_strain = false
is_true_wave_equation_wavefield = true
data_shape = [3, 41, 220]
snapshot_count = 10
devito_synthetic_data_nonzero = true
```

Stage 2C.1 已修正 WSL 输出查看问题：Devito 后端可以通过 `--output-dir` 直接把结果写入 Windows 项目目录 `code/outputs/`。备用同步脚本为：

```bash
cd /home/hcz/projects/hcz_road_void_with_tools/code
python scripts/sync_outputs.py
```

`code/outputs/` 仍由 `.gitignore` 排除，不提交到 GitHub。

## Notebook 和字体状态

Stage 2C.1 已重建主 Notebook：

```text
code/notebooks/road_void_3d_forward_and_localization.ipynb
```

修正内容：

1. 清除上一版中文被写成问号的问题；
2. Notebook 改为进度把控为主、必要教学为辅；
3. 新增可提交的小图目录 `code/notebooks/assets/`；
4. Notebook 引用 `assets/` 中的小图，GitHub 上也能看到关键结果；
5. 完整运行输出仍保存在本地 `code/outputs/`。

WSL 当前没有免密 sudo，未执行系统级字体安装。项目改为在 `configure_chinese_matplotlib()` 中优先使用 Noto CJK，如果没有 Noto CJK，则在 WSL 中直接注册 `/mnt/c/Windows/Fonts/msyh.ttc`、`simhei.ttf`、`simsun.ttc` 等 Windows 中文字体。这样不需要把字体复制进仓库，也不会写入任何密码。

## 运行验证命令

Windows：

```powershell
cd /d E:\HczDocument\BaiduDisk\BaiduSyncdisk\HCZ_work\CodexProject\HCZ_road_void_with_tools\code
D:\HczApp\Anaconda\envs\myvoid\python.exe main.py
D:\HczApp\Anaconda\envs\myvoid\python.exe -m pytest -p no:cacheprovider
```

Stage 2C.1 结果：`41 passed, 1 skipped`。

WSL：

```bash
cd /home/hcz/projects/hcz_road_void_with_tools/code
source /home/hcz/Software/Anaconda/etc/profile.d/conda.sh
conda activate hcz_void_devito
python main.py --backend devito_acoustic_3d --output-dir /mnt/e/HczDocument/BaiduDisk/BaiduSyncdisk/HCZ_work/CodexProject/HCZ_road_void_with_tools/code/outputs
python -m pytest -p no:cacheprovider
```

Stage 2C.1 结果：`42 passed`。

## 当前限制

1. 默认后端仍是三维运动学点绕射近似。
2. Devito acoustic 后端已经在 WSL 跑通，但它是 acoustic 标量声波，不是弹性波。
3. 当前 Devito 最小模型没有 PML 或自由表面，边界反射会存在。
4. 当前 Devito 内部会把落在边界的震源/接收点偏移一个网格间距，以避免最小后端稀疏插值记录全零；这不是最终自由表面方案。
5. 当前 DAS 仍是 polyline 点采样近似，不是真实 gauge-length averaged axial strain。
6. 当前体异常已能嵌入速度网格，但尚未做严格边界散射解释。
7. 当前定位准确度不是核心验收指标，不应为了降低误差过拟合目标函数。

## 下一轮建议

1. 为 Devito acoustic 后端加入阻尼边界或 PML。
2. 将 Devito 输出的炮集作为定位模块可选输入，先做一致性对比，不追求误差最小。
3. 增加波场快照 `.npz` 数据保存和更多切片类型。
4. 评估 Devito elastic 或 OpenSWPC 弹性/黏弹性后端，用于真实 DAS 轴向应变。
5. 解决 WSL 中文字体显示问题，改善图像可读性。
