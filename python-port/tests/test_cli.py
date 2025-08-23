import json
import subprocess
import sys
from pathlib import Path


def test_cli_runs(tmp_path):
    project = tmp_path / "proj.json"
    project.write_text(json.dumps({"network": {}, "uks": {}, "modules": []}), encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, "cli.py", str(project), "--ticks", "0"], cwd=root, check=True)
