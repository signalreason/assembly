from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from assembly import indexer


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
    extra_args: list[str],
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
    command.extend(extra_args)
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


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_cli_additive_globs_summary_and_ralph_exclusion(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "src/app.py", "print('ok')\n")
    _write(repo, "docs/guide.md", "Guide text.\n")
    _write(repo, "docs/private.md", "Secret notes.\n")
    _write(repo, ".ralph/runtime.log", "runtime trace\n")
    _write(repo, ".ralph/nested/trace.txt", "nested trace\n")
    _write(repo, "notes.txt", "misc\n")

    out_dir = tmp_path / "out" / "pack"
    stdout = _run_build(
        cwd=tmp_path,
        repo_arg="repo",
        out_arg="out/pack",
        task_text="CLI contract: additive globs",
        task_id="ASM-019-A",
        extra_args=[
            "--include",
            "src/**",
            "--include-add",
            "docs/**",
            "--include-add",
            ".ralph/**",
            "--exclude-add",
            "docs/private.md",
        ],
    )

    summary = json.loads(stdout)
    assert summary["status"] == "ok"
    for key in ("manifest", "index", "context", "policy", "lint"):
        output_path = Path(summary["outputs"][key])
        assert output_path.is_file()

    manifest = _load_json(out_dir / "manifest.json")
    assert manifest["inputs"]["include"] == ["src/**", "docs/**", ".ralph/**"]
    assert manifest["inputs"]["exclude"] == indexer.DEFAULT_EXCLUDES + ["docs/private.md"]

    index_data = _load_json(out_dir / "index.json")
    paths = [entry["path"] for entry in index_data["files"]]
    assert "src/app.py" in paths
    assert "docs/guide.md" in paths
    assert "docs/private.md" not in paths
    assert not any(path.startswith(".ralph/") for path in paths)

    context_text = (out_dir / "context.md").read_text(encoding="utf-8")
    assert ".ralph/" not in context_text
    assert "docs/private.md" not in context_text


def test_cli_repeated_builds_are_stable_with_additive_globs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "src/app.py", "print('ok')\n")
    _write(repo, "docs/guide.md", "Guide text.\n")
    _write(repo, ".ralph/runtime.log", "runtime trace\n")
    _write(repo, "notes.txt", "misc\n")

    out_dir = tmp_path / "out" / "pack"
    extra_args = [
        "--include",
        "src/**",
        "--include-add",
        "docs/**",
        "--exclude-add",
        "notes.txt",
    ]

    _run_build(
        cwd=tmp_path,
        repo_arg="repo",
        out_arg="out/pack",
        task_text="CLI contract: determinism",
        task_id="ASM-019-B",
        extra_args=extra_args,
        suppress_summary=True,
    )

    manifest_a = _load_json(out_dir / "manifest.json")
    index_a = _load_json(out_dir / "index.json")
    context_a = (out_dir / "context.md").read_text(encoding="utf-8")
    lint_a = _load_json(out_dir / "lint.json")

    shutil.rmtree(out_dir)

    _run_build(
        cwd=tmp_path,
        repo_arg="repo",
        out_arg="out/pack",
        task_text="CLI contract: determinism",
        task_id="ASM-019-B",
        extra_args=extra_args,
        suppress_summary=True,
    )

    manifest_b = _load_json(out_dir / "manifest.json")
    index_b = _load_json(out_dir / "index.json")
    context_b = (out_dir / "context.md").read_text(encoding="utf-8")
    lint_b = _load_json(out_dir / "lint.json")

    manifest_a_no_ts = {key: value for key, value in manifest_a.items() if key != "created_at"}
    manifest_b_no_ts = {key: value for key, value in manifest_b.items() if key != "created_at"}
    assert manifest_a_no_ts == manifest_b_no_ts
    assert index_a == index_b
    assert context_a == context_b
    assert lint_a == lint_b
