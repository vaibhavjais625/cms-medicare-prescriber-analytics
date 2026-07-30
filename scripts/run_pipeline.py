"""Run the complete reproducible pipeline in dependency order."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(script: str, *args: str) -> None:
    command = [sys.executable, str(ROOT / "scripts" / script), *args]
    print(f"\n==> {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    run("download_data.py")
    run("profile_data.py")
    run("clean_transform.py")
    run("build_database.py")
    run("build_dashboard_data.py")
    run("render_reports.py")
    run("validate_project.py")
    subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, check=True)
