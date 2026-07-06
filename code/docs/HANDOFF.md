# 交接说明

## 1. 本轮完成内容

- 将根目录初始化为 Git 仓库，并配置远程仓库 `https://github.com/Hchengze/hcz_road_void_with_tools.git`。
- 新增 `.gitignore`，默认排除 `code/outputs/`、缓存、运行结果、大型数据、论文 PDF 和第三方工具源码。
- 新增 `AGENTS.md`、`tools/README.md` 和 `reference/README.md`。
- 将 `code/docs/` 主要文档中文化。
- 将核心 Python 模块的模块注释、class/function docstring 和算法注释中文化。
- 将 `main.py` 终端输出、JSON 说明性 value、可视化图题/坐标轴/图例中文化。
- 将 Notebook `road_void_3d_forward_and_localization.ipynb` 中文化。
- 保持算法结构不变，不新增复杂算法，不接入 Devito/OpenSWPC。

## 2. 当前默认运行场景

默认示例为道路宽 `15 m`、长 `80 m`，DAS 光纤位于 `y=0 m` 一侧，锤击炮线位于 `y=15 m` 另一侧，空洞位于道路中部地下，默认 `void_xyz=(40.0, 7.5, 2.0)`。

当前运行结果：

- `true_xyz = (40.0, 7.5, 2.0)`；
- `best_xyz = (40.0, 7.5, 1.5)`；
- `localization_error_m = 0.5`；
- `x_error_m = 0.0`；
- `y_error_m = 0.0`；
- `depth_error_m = -0.5`；
- 数据维度：`n_sources x n_receivers x n_times = [21, 41, 600]`；
- 目标函数维度：`x-y-depth = [31, 31, 19]`；
- `y_depth_confusion = true`，符合当前单侧光纤和对侧锤击的几何限制。

## 3. 重要文件

- `code/main.py`：第一阶段可运行入口；
- `code/hcz_road_void/`：核心 Python 包；
- `code/docs/`：中文项目文档；
- `code/notebooks/road_void_3d_forward_and_localization.ipynb`：中文学习笔记；
- `tools/README.md`：外部工具本地目录说明；
- `reference/README.md`：文献本地目录说明；
- `.gitignore`：提交排除规则。

## 4. 运行环境

用户指定环境：

```text
D:\HczApp\Anaconda\envs\myvoid\python.exe
```

本轮没有安装新依赖。已有轻量依赖包括 `numpy`、`matplotlib`、`scipy`、`pytest` 和 Jupyter/notebook 相关包。

## 5. 验证命令

在 `code/` 目录下运行：

```bash
D:\HczApp\Anaconda\envs\myvoid\python.exe main.py
D:\HczApp\Anaconda\envs\myvoid\python.exe -m pytest -p no:cacheprovider
```

预期结果：

- `main.py` 成功生成 `code/outputs/` 下的图像、数据和 `run_summary.json`；
- 测试全部通过。

## 6. 当前限制

- 当前正演仍是三维运动学单点绕射近似；
- 当前不是完整三维弹性波、声波或黏弹性波动方程求解；
- DAS 光纤仍是通道点采样近似，不是真实 gauge-length averaged axial strain；
- 定位目标函数仍是简单 travel-time energy stack；
- 不确定性指标只是初步目标函数体诊断；
- 外部工具已审计但未接入。

## 7. 下一轮建议

1. 增加真实 DAS 轴向应变代理算子：沿光纤切向差分或 gauge-length 平均；
2. 加入速度模型误差扰动，分析 depth 偏差；
3. 加入有限尺寸或多散射点空洞模型；
4. 在保持当前几何 API 不变的前提下，设计 Devito 或 OpenSWPC 适配器。
