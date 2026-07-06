"""把 WSL 项目 outputs 同步到 Windows 项目 outputs。

推荐方式仍是直接运行：

```bash
python main.py --backend devito_acoustic_3d --output-dir /mnt/e/.../code/outputs
```

这个脚本作为备用同步工具：当 Devito 输出已经生成在 WSL Linux 文件系统
`/home/hcz/projects/.../code/outputs` 中时，可将结果复制到 Windows 项目目录，
方便用户在资源管理器、Notebook 或普通图片查看器中检查。

脚本不会提交任何输出文件；`code/outputs/` 仍由 `.gitignore` 排除。
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


DEFAULT_SOURCE = Path("/home/hcz/projects/hcz_road_void_with_tools/code/outputs")
DEFAULT_TARGET = Path(
    "/mnt/e/HczDocument/BaiduDisk/BaiduSyncdisk/HCZ_work/CodexProject/"
    "HCZ_road_void_with_tools/code/outputs"
)


def sync_outputs(source: Path = DEFAULT_SOURCE, target: Path = DEFAULT_TARGET) -> list[Path]:
    """同步 Devito 运行输出，并返回已复制的目标路径列表。"""

    if not source.exists():
        raise FileNotFoundError(f"源目录不存在，请先运行 Devito 后端：{source}")
    target.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)
        copied.append(destination)
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="WSL outputs 源目录。")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET, help="Windows outputs 目标目录的 WSL 路径。")
    args = parser.parse_args()

    copied = sync_outputs(args.source, args.target)
    print(f"已同步 {len(copied)} 个文件或目录到 Windows 项目 outputs：{args.target}")
    for path in copied:
        print(f"- {path}")


if __name__ == "__main__":
    main()
