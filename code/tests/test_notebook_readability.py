"""Notebook 可读性和图片资产回归测试。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib.pyplot as plt

from hcz_road_void.visualization import configure_chinese_matplotlib


def test_main_notebook_has_readable_chinese_and_assets() -> None:
    notebook_path = Path("notebooks/road_void_3d_forward_and_localization.ipynb")
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    text = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])

    assert "三维道路 DAS + 锤击地下空洞探测算法原型" in text
    assert "Stage 2C.1" in text
    assert "???" not in text
    assert "\ufffd" not in text
    assert "void_xyz=(52.0, 1.0, 6.0)" not in text

    image_links = re.findall(r"!\[[^\]]*\]\((assets/[^)]+)\)", text)
    assert len(image_links) >= 6
    missing = [link for link in image_links if not (notebook_path.parent / link).exists()]
    assert missing == []


def test_chinese_matplotlib_font_configuration_does_not_crash() -> None:
    configure_chinese_matplotlib()
    fonts = plt.rcParams["font.sans-serif"]

    assert fonts
    assert fonts[0] in {
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
        "Noto Sans CJK SC",
        "Noto Sans CJK",
        "WenQuanYi Micro Hei",
        "Arial Unicode MS",
        "DejaVu Sans",
    }
