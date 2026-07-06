# 项目交接记录

## 当前阶段

当前处于 Stage 2A：从三维运动学绕射原型，过渡到准备接入真实三维波动方程正演后端。

当前默认三维道路场景：

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
8. Stage 2A 新增统一 `ForwardBackend` 接口。
9. Stage 2A 新增 `KinematicDiffractionBackend`、`DevitoBackend`、`OpenSWPCBackend`。
10. Stage 2A 新增 `VoidBody3D` 和 `VelocityGrid3D`。
11. Stage 2A 新增速度模型 `.npz` 输出和切片图。
12. Stage 2A 新增波场快照接口；当前运动学后端明确标注没有真实波场。

## 本地 tools 二次审计结论

1. Devito：优先候选，Python API 最适合先接入三维声波方程。
2. OpenSWPC：高保真外部程序候选，适合后续三维弹性/黏弹性与 DAS 应变。
3. SW4：地表弹性波能力强，可作为外部对照。
4. SPECFEM3D：物理能力强，但网格和编译成本高。
5. SAVA、SeisCL：可研究，但 GPL 和编译链较重。
6. SOFI2D、SPECFEM1D：不是三维主后端，只能作为教学或降维参考。

详细记录见：

- `code/docs/TOOLS_DEEP_DIVE.md`
- `code/docs/DEVITO_INTEGRATION_NOTES.md`
- `code/docs/OPENSWPC_INTEGRATION_NOTES.md`

## Devito / OpenSWPC 当前可用性

`myvoid` 中 Devito 当前不可 import：

```text
ModuleNotFoundError: No module named 'devito'
```

OpenSWPC 当前未编译，未配置可执行文件。因此 `OpenSWPCBackend.is_available()` 返回 `False`。

本轮未安装大型正演工具。

## 运行环境

继续使用用户指定环境：

```powershell
D:\HczApp\Anaconda\envs\myvoid\python.exe main.py
D:\HczApp\Anaconda\envs\myvoid\python.exe -m pytest -p no:cacheprovider
```

不得使用 `mywork` 作为本项目验证环境。

## 当前限制

1. 当前默认正演仍是三维运动学点绕射近似。
2. 当前不是完整三维声波/弹性波正演。
3. 当前 DAS 仍是 polyline 点采样近似，不是真实 gauge-length averaged axial strain。
4. 当前体异常已能嵌入速度网格，但运动学后端仍默认使用中心点作为等效绕射体。
5. 当前波场快照接口存在，但没有真实波动方程波场输出。
6. 当前定位准确度不是核心验收指标，不应为了降低误差过拟合目标函数。

## 下一轮建议

1. 在 `myvoid` 中评估并安装 Devito。
2. 实现最小 Devito 3D acoustic 后端。
3. 用 `VelocityGrid3D` 构建 Devito `Model`。
4. 输出真实声波炮集、波场快照和动图。
5. 更新 Notebook，删除或标注运动学阶段旧结论。
6. 之后再考虑 OpenSWPC 外部程序接入和 DAS 轴向应变。
