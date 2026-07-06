"""验证 main.py 可以端到端运行并写出主要输出。"""

import json
import subprocess
import sys


def test_main_smoke_runs_and_writes_outputs(tmp_path) -> None:
    completed = subprocess.run(
        [sys.executable, "main.py", "--output-dir", str(tmp_path), "--quiet"],
        cwd=".",
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    summary_path = tmp_path / "run_summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["data_shape"][0] > 1
    assert summary["objective_shape"][1] > 1
    assert summary["localization_error_m"] <= 1.5
    for name in ["geometry_3d.png", "synthetic_gather.png", "localization_slices.png"]:
        assert (tmp_path / name).exists()
