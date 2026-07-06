"""重建项目主 Notebook。

这个脚本只维护 `road_void_3d_forward_and_localization.ipynb` 的结构和文字，
不运行正演算法。使用脚本生成 Notebook 的原因是：上一版在 PowerShell
here-string 中写入中文时被错误编码成问号，导致 Notebook 不可读。把中文
内容保存在 UTF-8 Python 源文件中，再由 Python 写出 `.ipynb`，可以稳定
避免这个问题。
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4


NOTEBOOK_PATH = Path("notebooks/road_void_3d_forward_and_localization.ipynb")


def markdown(source: str) -> dict[str, object]:
    return {
        "cell_type": "markdown",
        "id": uuid4().hex[:8],
        "metadata": {},
        "source": source.strip().splitlines(keepends=True),
    }


def code(source: str) -> dict[str, object]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": uuid4().hex[:8],
        "metadata": {},
        "outputs": [],
        "source": source.strip().splitlines(keepends=True),
    }


def build_notebook() -> dict[str, object]:
    cells = [
        markdown(
            """
# 三维道路 DAS + 锤击地下空洞探测算法原型

## 1. 当前项目状态摘要

| 项目 | 当前状态 |
| --- | --- |
| 当前阶段 | Stage 2C.1：修正 WSL 输出同步和 Notebook 可读性 |
| 默认几何 | 道路 80 m × 15 m，DAS 光纤 y=0 m，锤击炮线 y=15 m，空洞 (40.0, 7.5, 2.0) |
| 当前可运行后端 | `kinematic`；`devito_acoustic_3d` 在 WSL `hcz_void_devito` 中可运行 |
| 当前正演能力 | 三维运动学绕射 + Devito 三维 acoustic 标量声波方程 |
| 当前还没有 | 三维弹性波、真实 DAS gauge-length averaged axial strain |
| 当前重点 | 稳定正演输出和进度把控，不追求定位误差最小 |

本 Notebook 的第一作用是项目进度把控，第二作用才是教学说明。它只保留当前有效的默认参数、关键图像、后端状态和下一步计划。
            """
        ),
        markdown(
            """
## 2. 当前默认三维场景

坐标约定始终为：

- `x`：沿道路或 DAS 光纤方向；
- `y`：横穿道路方向；
- `depth`：向下为正。

默认场景中，DAS 光纤沿道路一侧布设在 `y=0 m`，锤击点沿道路另一侧布设在 `y=15 m`，空洞位于道路横向中部浅层地下。因此这是一个真实三维道路观测几何，不是二维 `x-depth` 剖面。

![三维道路 DAS + 锤击几何](assets/geometry_3d.png)

如果上图没有显示，请先在项目 `code/` 目录运行 `python main.py`，或重新生成 `code/notebooks/assets/geometry_3d.png`。
            """
        ),
        markdown(
            """
## 3. 当前可运行后端

### kinematic

默认后端是三维运动学点绕射近似。它使用：

```text
总走时 = 震源到空洞的走时 + 空洞到接收点的走时
t_total = |source_xyz - void_xyz| / v_background
        + |void_xyz - receiver_xyz| / v_background
```

它用于验证三维几何、炮集数据结构、定位搜索和不确定性接口。它不是波动方程正演。

### devito_acoustic_3d

Devito 后端已在 WSL Linux conda 环境中跑通。当前方程是 acoustic 标量声波方程：

```text
m * u.dt2 - laplace(u) = source
m = 1 / vp^2
```

它可以生成真实波动方程炮集和标量波场快照，但仍不是弹性波，也不能直接模拟真实 DAS 轴向应变。
            """
        ),
        markdown(
            """
## 4. Stage 1：运动学绕射原型结果

运动学原型输出的主要作用是检查三维几何和定位流程是否贯通。

### 速度模型切片

![速度模型切片](assets/velocity_model_slices.png)

### 运动学合成炮集

![运动学合成炮集](assets/synthetic_gather.png)

### 三维定位目标函数切片

![定位目标函数切片](assets/localization_slices.png)

当前定位模块使用 travel-time energy stack。它遍历 `search_x`、`search_y` 和 `search_depth`，对每个候选异常体位置计算理论绕射走时，并在记录中提取能量。现阶段定位模块用于验证流程闭环，不用于证明工程定位精度。
            """
        ),
        markdown(
            """
## 5. Stage 2：Devito 三维声波正演结果

WSL 中推荐运行命令：

```bash
cd /home/hcz/projects/hcz_road_void_with_tools/code
source /home/hcz/Software/Anaconda/etc/profile.d/conda.sh
conda activate hcz_void_devito
python main.py --backend devito_acoustic_3d --output-dir /mnt/e/HczDocument/BaiduDisk/BaiduSyncdisk/HCZ_work/CodexProject/HCZ_road_void_with_tools/code/outputs
```

这样 Devito 结果会直接写入 Windows 项目目录 `code/outputs/`，用户可以在资源管理器和本地 Notebook 中查看。

当前 Devito 关键结果：

```text
backend_name = devito_acoustic_3d
runtime_environment = wsl_linux_conda
devito_version = 4.8.22
is_wave_equation_solver = true
is_elastic_solver = false
supports_das_strain = false
data_shape = [3, 41, 220]
snapshot_count = 10
```

### Devito 声波炮集

![Devito 声波炮集](assets/devito_synthetic_gather.png)

### Devito 波场快照示例

![Devito 波场快照示例](assets/devito_wavefield_snapshot_example.png)

### Devito 波场动图

![Devito 波场动图](assets/devito_wavefield_animation.gif)
            """
        ),
        markdown(
            """
## 6. 当前正演输出

本地完整输出目录为：

```text
code/outputs/
```

关键文件包括：

```text
geometry_3d.png
velocity_model_slices.png
synthetic_gather.png
localization_slices.png
devito_synthetic_gather.png
devito_forward_summary.json
devito_wavefield_snapshots/
devito_wavefield_animation.gif
```

`code/outputs/` 不提交到 GitHub，只作为本地查看和验收目录。GitHub 上可见的小图存放在 `code/notebooks/assets/`。
            """
        ),
        code(
            """
import json
from pathlib import Path

outputs = Path("../outputs")
summary_path = outputs / "devito_forward_summary.json"
if summary_path.exists():
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    for key in [
        "stage",
        "backend_name",
        "runtime_environment",
        "devito_version",
        "data_shape",
        "velocity_grid_shape",
        "source_count",
        "receiver_count",
        "time_sample_count",
        "snapshot_count",
    ]:
        print(f"{key}: {summary.get(key)}")
else:
    print("尚未找到 devito_forward_summary.json。")
    print("请先在 WSL 中运行 Devito 后端，并把输出写入 Windows code/outputs。")
            """
        ),
        markdown(
            """
## 7. 为什么 acoustic 只是过渡，elastic 才是主线

Devito acoustic 已经让项目具备真实三维波动方程正演能力，但它只有标量声波场。道路 DAS 真实观测更接近沿光纤方向的轴向应变或应变率，这需要弹性位移场、应变张量和 gauge length 空间平均。

因此当前 acoustic 后端的定位是：

1. 验证三维速度网格、震源、接收点和波场输出结构；
2. 输出真实声波炮集和波场快照；
3. 为后续 Devito elastic 或 OpenSWPC 弹性/黏弹性后端铺路。
            """
        ),
        markdown(
            """
## 8. 当前 DAS 观测状态

当前 DAS 光纤通过 `receiver_polyline` 表示，并按通道间距采样为 `receiver_xyz`。每个通道有局部切向量和 gauge length metadata。

当前记录仍是点接收器近似，不是真实 gauge-length averaged axial strain。后续真实 DAS 路线需要：

1. 弹性位移场；
2. 应变张量；
3. 沿光纤方向投影；
4. gauge length 空间平均；
5. 仪器响应和采样率建模。
            """
        ),
        markdown(
            """
## 9. 当前限制

1. 默认 `kinematic` 不是波动方程。
2. Devito acoustic 是标量声波，不是弹性波。
3. 当前 Devito 最小模型没有 PML 或自由表面，边界反射会存在。
4. 当前 DAS 仍是点接收器/polyline 采样近似。
5. 当前没有真实道路数据输入。
6. 当前定位准确度不是核心验收指标。
7. GitHub Notebook 只提交小图资产，完整输出仍需本地重新生成。
            """
        ),
        markdown(
            """
## 10. 下一步计划

1. 稳定 WSL Devito 输出到 Windows `code/outputs/` 的使用流程。
2. 为 Devito acoustic 后端加入阻尼边界或 PML。
3. 增加波场快照 `.npz` 数据保存和更多切片类型。
4. 将 Devito 炮集作为定位模块的可选输入，先做一致性验证，不调参追求误差最小。
5. 评估 Devito elastic 或 OpenSWPC，用于位移场、应力场和真实 DAS 轴向应变。
            """
        ),
    ]
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK_PATH.write_text(json.dumps(build_notebook(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已重建 Notebook：{NOTEBOOK_PATH}")


if __name__ == "__main__":
    main()
