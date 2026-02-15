from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from assembly import cli
from assembly.lint import SEVERITY_ORDER


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


def _assert_lint_order(issues: list[dict[str, object]]) -> None:
    allowed = {"error", "warn", "info"}
    severities = [issue["severity"] for issue in issues]
    assert set(severities).issubset(allowed)
    sorted_ids = [
        issue["id"]
        for issue in sorted(
            issues,
            key=lambda issue: (SEVERITY_ORDER[issue["severity"]], issue["id"]),
        )
    ]
    assert [issue["id"] for issue in issues] == sorted_ids


def test_phase2_determinism(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "README.md", "Must not expose secrets.\nDo not leak secrets.\n")
    _write(repo, "AGENTS.md", "Do not leak secrets.\n")
    _write(repo, "docs/security.md", "Must expose secrets.\n")
    _write(repo, "docs/guide.md", "Do not leak secrets.\n")
    _write(repo, "docs/guide2.md", "Do not leak secrets.\n")

    task_text = "Phase 2 determinism verification"
    task_id = "ASM-010"
    max_tokens = 6000
    canonical_out = repo / "pack"

    _run_build(repo, canonical_out, task_text=task_text, task_id=task_id, max_tokens=max_tokens)
    manifest_a = _load_json(canonical_out / "manifest.json")
    index_a = _load_json(canonical_out / "index.json")
    context_a = (canonical_out / "context.md").read_text(encoding="utf-8")
    lint_a = _load_json(canonical_out / "lint.json")
    _assert_lint_order(lint_a["issues"])

    shutil.rmtree(canonical_out)

    _run_build(repo, canonical_out, task_text=task_text, task_id=task_id, max_tokens=max_tokens)
    manifest_b = _load_json(canonical_out / "manifest.json")
    index_b = _load_json(canonical_out / "index.json")
    context_b = (canonical_out / "context.md").read_text(encoding="utf-8")
    lint_b = _load_json(canonical_out / "lint.json")
    _assert_lint_order(lint_b["issues"])

    manifest_a_no_ts = {k: v for k, v in manifest_a.items() if k != "created_at"}
    manifest_b_no_ts = {k: v for k, v in manifest_b.items() if k != "created_at"}
    assert manifest_a_no_ts == manifest_b_no_ts
    assert index_a == index_b
    assert context_a == context_b
    assert lint_a == lint_b
