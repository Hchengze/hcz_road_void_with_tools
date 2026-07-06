# Devito Linux Runtime 验证指南

## 目标

本指南记录 Stage 2C 如何在 WSL Linux Anaconda 环境中跑通 Devito 3D acoustic runtime。它不是通用安装手册，而是本项目当前可复现的运行路径。

## 为什么使用 WSL Linux

上一轮已经确认 Windows 原生 `myvoid` 中 Devito 可以 import，但 Operator runtime 被 CodePy/MinGW/JIT 编译链阻塞。Devito 的 JIT、编译器和内存分配路径更接近 Linux/gcc 环境，因此 Stage 2C 将 Devito runtime 验证放在 WSL Linux conda 环境中。

Windows `myvoid` 仍用于：

1. 默认 `kinematic` 后端运行；
2. 普通单元测试；
3. 代码开发与文档维护。

WSL `hcz_void_devito` 用于：

1. Devito import 验证；
2. Devito Operator smoke test；
3. `main.py --backend devito_acoustic_3d`；
4. 真实声波炮集、波场快照和 GIF 输出。

## 已验证环境

```text
WSL distro: ubuntu2204
WSL version: 2
WSL user: hcz
Project path: /home/hcz/projects/hcz_road_void_with_tools
Anaconda path: /home/hcz/Software/Anaconda
Conda env: hcz_void_devito
Python: 3.11
Devito: 4.8.22
Compiler: /usr/bin/gcc
```

本文件不记录任何密码或交互认证信息。

## 安装命令

```bash
source /home/hcz/Software/Anaconda/etc/profile.d/conda.sh
conda create -n hcz_void_devito python=3.11 -y
conda activate hcz_void_devito
python -m pip install --upgrade pip
python -m pip install devito pytest numpy scipy matplotlib imageio pillow --index-url https://pypi.org/simple
```

本轮检查到 WSL 中已有 `gcc`、`g++` 和 `make`，因此没有执行 `sudo apt install`。如果后续新机器缺少编译器，可再安装 `build-essential gcc g++ gfortran make`，但不要把密码写入脚本或文档。

## 推荐仓库位置

优先在 WSL Linux 文件系统中运行，而不是 `/mnt/e/...`：

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/Hchengze/hcz_road_void_with_tools.git
cd hcz_road_void_with_tools
```

若仓库已存在：

```bash
cd ~/projects/hcz_road_void_with_tools
git pull
git status
```

## Devito smoke test

```bash
cd ~/projects/hcz_road_void_with_tools/code
source /home/hcz/Software/Anaconda/etc/profile.d/conda.sh
conda activate hcz_void_devito
python -c "import devito; print(devito.__version__)"
python -c "from hcz_road_void.forward import DevitoBackend; print(DevitoBackend().runtime_status(force=True).as_dict())"
```

成功条件：

```text
state = runtime_available
import_available = True
runtime_available = True
version = 4.8.22
compiler_path = /usr/bin/gcc
```

## 项目 Devito 后端运行

```bash
cd ~/projects/hcz_road_void_with_tools/code
source /home/hcz/Software/Anaconda/etc/profile.d/conda.sh
conda activate hcz_void_devito
python main.py --backend devito_acoustic_3d
```

成功后应输出：

```text
code/outputs/devito_synthetic_gather.png
code/outputs/devito_forward_summary.json
code/outputs/devito_wavefield_snapshots/
code/outputs/devito_wavefield_animation.gif
```

`devito_forward_summary.json` 应包含：

```json
{
  "backend_name": "devito_acoustic_3d",
  "runtime_environment": "wsl_linux_conda",
  "devito_version": "4.8.22",
  "is_wave_equation_solver": true,
  "is_elastic_solver": false,
  "is_true_wave_equation_wavefield": true,
  "supports_das_strain": false,
  "velocity_grid_shape": [81, 16, 9],
  "receiver_count": 41,
  "source_count": 3,
  "time_sample_count": 220,
  "snapshot_count": 10
}
```

## 当前已知小问题

1. WSL 若没有中文字体，Matplotlib 可能提示缺少中文 glyph；这不影响波动方程求解，只影响图题和坐标轴文字显示。
2. 当前最小 Devito 模型没有 PML 或自由表面，会产生边界反射。
3. 当前 acoustic 标量波场不是弹性位移场，不能直接用于真实 DAS 轴向应变。

## 验证命令

WSL：

```bash
python main.py --backend devito_acoustic_3d
python -m pytest -p no:cacheprovider
```

Windows：

```powershell
D:\HczApp\Anaconda\envs\myvoid\python.exe main.py
D:\HczApp\Anaconda\envs\myvoid\python.exe -m pytest -p no:cacheprovider
```

Windows Devito runtime 不作为本阶段验收条件。
