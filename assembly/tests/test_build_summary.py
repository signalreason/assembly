from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _write(repo_root: Path, relative: str, content: str) -> None:
    path = repo_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _run_build(
    *,
    cwd: Path,
    repo_arg: str,
    out_arg: str,
    task_text: str,
    task_id: str,
    suppress_summary: bool = False,
) -> str:
    project_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)
    command = [
        sys.executable,
        "-m",
        "assembly",
        "build",
        "--repo",
        repo_arg,
        "--task",
        task_text,
        "--task-id",
        task_id,
        "--out",
        out_arg,
    ]
    if suppress_summary:
        command.append("--no-summary")
    result = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_build_summary_json_order_and_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "README.md", "Summary output check.\n")

    out_dir = tmp_path / "out" / "pack"
    stdout = _run_build(
        cwd=tmp_path,
        repo_arg="repo",
        out_arg="out/pack",
        task_text="Summary output check",
        task_id="ASM-016",
    )

    expected_outputs = {
        "manifest": (out_dir / "manifest.json").resolve().as_posix(),
        "index": (out_dir / "index.json").resolve().as_posix(),
        "context": (out_dir / "context.md").resolve().as_posix(),
        "policy": (out_dir / "policy.md").resolve().as_posix(),
        "lint": (out_dir / "lint.json").resolve().as_posix(),
    }
    expected = {"status": "ok", "outputs": expected_outputs}

    summary = json.loads(stdout)
    assert summary == expected

    expected_json = json.dumps(expected, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    assert stdout == expected_json


def test_build_summary_can_be_suppressed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "README.md", "Summary suppression check.\n")

    out_dir = tmp_path / "out" / "pack"
    stdout = _run_build(
        cwd=tmp_path,
        repo_arg="repo",
        out_arg="out/pack",
        task_text="Summary suppression check",
        task_id="ASM-018",
        suppress_summary=True,
    )

    assert stdout == ""
    assert (out_dir / "manifest.json").is_file()
    assert (out_dir / "index.json").is_file()
    assert (out_dir / "context.md").is_file()
    assert (out_dir / "policy.md").is_file()
    assert (out_dir / "lint.json").is_file()
