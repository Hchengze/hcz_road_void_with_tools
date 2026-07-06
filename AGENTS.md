# HCZ 道路地下空洞项目开发约定

本项目面向三维道路地下空洞、脱空和浅层异常体探测。主线始终是三维道路场景，不得把二维 `x-depth` 剖面算法包装成三维算法。

核心坐标约定：

- `x`：沿道路或沿 DAS 光纤方向；
- `y`：横穿道路方向；
- `depth`：深度方向，向下为正；
- `source_xyz`：三维震源或锤击点坐标；
- `receiver_xyz`：三维接收点坐标；
- `receiver_polyline`：DAS/光纤三维折线；
- `void_xyz`：异常体或空洞中心三维坐标。

开发要求：

- 主代码放在 `code/` 下，核心模块放在 `code/hcz_road_void/`。
- 示例入口为 `code/main.py`，运行环境为用户指定的 `myvoid`。
- 当前第一阶段只实现三维运动学绕射/点散射近似，不声称完整三维弹性波正演。
- DAS 当前只能作为光纤折线采样点近似，不能声称已经实现真实 gauge-length averaged axial strain。
- `tools/` 只作为本地外部工具参考目录，提交前必须检查许可证，不盲目复制第三方源码。
- `reference/` 只作为本地文献目录，论文 PDF 默认不提交到 GitHub。
- 每轮修改后应运行 `D:\HczApp\Anaconda\envs\myvoid\python.exe main.py` 和 `D:\HczApp\Anaconda\envs\myvoid\python.exe -m pytest -p no:cacheprovider`。

历史完整说明保留在 `agent.md`；本文件用于让 GitHub 仓库根目录具备标准 `AGENTS.md` 入口。
