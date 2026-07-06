"""matplotlib 中文字体配置工具。

本项目的图像需要同时在 Windows `myvoid` 和 WSL Linux `hcz_void_devito`
中生成。Windows 通常有 Microsoft YaHei / SimHei；WSL 默认往往只有
DejaVu Sans，不能显示中文，会导致图题、坐标轴和图例变成方框或问号。

本模块集中处理字体发现和配置，避免每个绘图文件各写一套 fallback 逻辑。
如果 WSL 没有安装 Noto CJK，本模块会尝试直接加载 Windows 挂载盘中的
中文字体，例如 `/mnt/c/Windows/Fonts/msyh.ttc`。这不会把字体复制进仓库，
也不会新增系统级依赖。
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager


_FONT_CONFIGURED = False


def configure_chinese_matplotlib() -> None:
    """配置 matplotlib 中文字体。

    字体优先级：

    1. Windows：Microsoft YaHei / SimHei / SimSun；
    2. WSL/Linux：Noto Sans CJK SC / Noto Sans CJK / WenQuanYi Micro Hei；
    3. WSL 可读 Windows 字体时：直接注册 `/mnt/c/Windows/Fonts` 下的中文字体；
    4. 最后才退回 DejaVu Sans。

    找不到中文字体时只给出 `RuntimeWarning`，不让绘图流程崩溃。这样正演、
    测试和输出仍能继续，只是图中文字可读性会下降。
    """

    global _FONT_CONFIGURED
    if _FONT_CONFIGURED:
        return

    _register_known_font_files()
    available = {font.name for font in font_manager.fontManager.ttflist}
    preferred = [
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
        "Noto Sans CJK SC",
        "Noto Sans CJK",
        "WenQuanYi Micro Hei",
        "Arial Unicode MS",
    ]
    selected = next((name for name in preferred if name in available), None)
    if selected is None:
        selected = "DejaVu Sans"
        warnings.warn(
            "未找到完整中文字体，matplotlib 将退回 DejaVu Sans；"
            "WSL 中建议安装 fonts-noto-cjk，或确保 /mnt/c/Windows/Fonts 可读。",
            RuntimeWarning,
            stacklevel=2,
        )

    plt.rcParams["font.sans-serif"] = [selected, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    _FONT_CONFIGURED = True


def _register_known_font_files() -> None:
    """把常见中文字体文件显式注册到 matplotlib font manager。"""

    candidates = [
        Path("/mnt/c/Windows/Fonts/msyh.ttc"),
        Path("/mnt/c/Windows/Fonts/msyhbd.ttc"),
        Path("/mnt/c/Windows/Fonts/simhei.ttf"),
        Path("/mnt/c/Windows/Fonts/simsun.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            font_manager.fontManager.addfont(str(path))
        except Exception:
            # 字体注册失败不应中断正演，只会影响图中文字显示。
            continue
