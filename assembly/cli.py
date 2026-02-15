"""Assembly CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import __version__
from . import context as context_builder
from . import indexer
from . import lint as lint_builder


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="assembly", description="Deterministic pack builder")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Build a deterministic pack")
    build.add_argument("--repo", default=".", help="Repository root")
    build.add_argument("--task", required=True, help="Task file reference or task text")
    build.add_argument("--out", default="pack", help="Output directory")
    build.add_argument("--max-tokens", type=int, default=6000, help="Token budget")
    build.add_argument("--task-id", required=True, help="Task identifier")
    build.add_argument("--include", action="append", help="Glob to include")
    build.add_argument("--include-add", action="append", help="Glob to include (additive)")
    build.add_argument("--exclude", action="append", help="Glob to exclude")
    build.add_argument("--exclude-add", action="append", help="Glob to exclude (additive)")

    return parser.parse_args(argv)


def _resolve_repo(repo: str) -> Path:
    path = Path(repo)
    try:
        return path.resolve()
    except OSError:
        return path


def _task_paths(task_input: str, repo_root: Path) -> list[str]:
    if not task_input.startswith("@"):
        return []
    raw = task_input[1:]
    if not raw:
        raise SystemExit("--task @<file> requires a file path")
    task_path = Path(raw)
    if not task_path.is_absolute():
        task_path = (Path.cwd() / task_path).resolve()
    if not task_path.is_file():
        raise SystemExit(f"Task file not found: {task_path}")
    try:
        rel = task_path.relative_to(repo_root)
    except ValueError:
        return []
    return [rel.as_posix()]


def _git_commit(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    sha = result.stdout.strip()
    if len(sha) != 40:
        return "unknown"
    return sha


def _resolve_globs(
    base: Iterable[str] | None,
    additions: Iterable[str] | None,
    defaults: list[str],
) -> list[str]:
    if base is None:
        resolved = list(defaults)
    else:
        resolved = list(base)
    seen = set(resolved)
    if additions:
        for value in additions:
            if value in seen:
                continue
            resolved.append(value)
            seen.add(value)
    return resolved


def _created_at() -> str:
    timestamp = datetime.now(timezone.utc).isoformat()
    return timestamp.replace("+00:00", "Z")


def _output_posix(repo_root: Path, out_dir: Path, filename: str) -> str:
    out_path = (out_dir / filename)
    if out_path.is_absolute():
        try:
            rel = out_path.relative_to(repo_root)
        except ValueError:
            return out_path.as_posix()
        return rel.as_posix()
    return out_path.as_posix()


def build_pack(args: argparse.Namespace) -> int:
    repo_root = _resolve_repo(args.repo)
    includes = _resolve_globs(args.include, args.include_add, indexer.DEFAULT_INCLUDES)
    excludes = _resolve_globs(args.exclude, args.exclude_add, indexer.DEFAULT_EXCLUDES)
    task_paths = _task_paths(args.task, repo_root)
    git_sha = _git_commit(repo_root)

    blocks = context_builder.build_context_blocks(
        repo_root,
        args.max_tokens,
        include_globs=includes,
        exclude_globs=excludes,
        task_paths=task_paths,
        git_sha=git_sha,
    )
    selected_paths = [block.path for block in blocks]

    index_data = indexer.build_index(
        repo_root,
        include_globs=includes,
        exclude_globs=excludes,
        selected_paths=selected_paths,
        task_paths=task_paths,
    )

    lint_data = lint_builder.build_lint_issues(
        repo_root,
        include_globs=includes,
        exclude_globs=excludes,
        task_paths=task_paths,
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    index_path = out_dir / "index.json"
    context_path = out_dir / "context.md"
    policy_path = out_dir / "policy.md"
    lint_path = out_dir / "lint.json"

    outputs = {
        "manifest": _output_posix(repo_root, out_dir, "manifest.json"),
        "index": _output_posix(repo_root, out_dir, "index.json"),
        "context": _output_posix(repo_root, out_dir, "context.md"),
        "policy": _output_posix(repo_root, out_dir, "policy.md"),
        "lint": _output_posix(repo_root, out_dir, "lint.json"),
    }

    manifest = {
        "repo_commit": git_sha,
        "task_id": args.task_id,
        "max_tokens": args.max_tokens,
        "inputs": {
            "task": args.task,
            "repo": str(repo_root),
            "include": includes,
            "exclude": excludes,
        },
        "outputs": outputs,
        "created_at": _created_at(),
        "tool_version": __version__,
    }

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    indexer.write_index_json(index_data, index_path)
    context_builder.write_context_md(blocks, context_path)
    policy_path.write_bytes(b"")
    lint_builder.write_lint_json(lint_data, lint_path)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "build":
        return build_pack(args)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
