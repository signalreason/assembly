from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from assembly import cli, context, indexer


def _write(repo_root: Path, relative: str, content: str) -> None:
    path = repo_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _run_build(repo_root: Path, out_dir: Path, *, task_text: str, task_id: str, max_tokens: int) -> None:
    args = argparse.Namespace(
        command="build",
        repo=str(repo_root),
        task=task_text,
        out=str(out_dir),
        max_tokens=max_tokens,
        task_id=task_id,
        include=None,
        include_add=None,
        exclude=None,
        exclude_add=None,
    )
    assert cli.build_pack(args) == 0


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_inventory_excludes_ralph_by_default(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "README.md", "Hello.\n")
    _write(repo, ".ralph/runtime.log", "runtime trace\n")
    _write(repo, ".ralph/nested/trace.txt", "nested trace\n")

    paths = indexer.inventory_paths(repo)

    assert "README.md" in paths
    assert not any(path.startswith(".ralph/") for path in paths)


def test_index_context_exclude_ralph_and_are_deterministic(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "README.md", "Readme content.\n")
    _write(repo, "src/app.py", "print('ok')\n")
    _write(repo, ".ralph/runtime.log", "runtime trace\n")
    _write(repo, ".ralph/nested/trace.txt", "nested trace\n")

    blocks = context.build_context_blocks(repo, max_tokens=6000)
    assert not any(block.path.startswith(".ralph/") for block in blocks)

    task_text = "Exclude .ralph artifacts"
    task_id = "ASM-011"
    out_dir = repo / "pack"
    _run_build(repo, out_dir, task_text=task_text, task_id=task_id, max_tokens=6000)

    index_a = _load_json(out_dir / "index.json")
    context_a = (out_dir / "context.md").read_text(encoding="utf-8")

    assert not any(entry["path"].startswith(".ralph/") for entry in index_a["files"])
    assert ".ralph/" not in context_a

    shutil.rmtree(out_dir)

    _run_build(repo, out_dir, task_text=task_text, task_id=task_id, max_tokens=6000)
    index_b = _load_json(out_dir / "index.json")
    context_b = (out_dir / "context.md").read_text(encoding="utf-8")

    assert index_a == index_b
    assert context_a == context_b
