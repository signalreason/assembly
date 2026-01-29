"""Deterministic file inventory, scoring, and pack index generation."""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Iterable, Iterator, Sequence


DEFAULT_INCLUDES = ["**/*"]
DEFAULT_EXCLUDES = [
    ".git/**",
    "node_modules/**",
    "dist/**",
    "build/**",
    "target/**",
    "vendor/**",
    ".venv/**",
    "__pycache__/**",
    ".DS_Store",
]


@dataclass(frozen=True)
class IndexEntry:
    path: str
    sha256: str
    size_bytes: int
    token_est: int
    score: int
    selected: bool


def _normalize_globs(
    include_globs: Sequence[str] | None,
    exclude_globs: Sequence[str] | None,
) -> tuple[list[str], list[str]]:
    includes = list(include_globs) if include_globs is not None else list(DEFAULT_INCLUDES)
    excludes = list(exclude_globs) if exclude_globs is not None else list(DEFAULT_EXCLUDES)
    return includes, excludes


def _posix_relpath(repo_root: Path, path: Path) -> str:
    rel = path.relative_to(repo_root)
    return rel.as_posix()


def _matches_any(path: str, globs: Iterable[str]) -> bool:
    for pattern in globs:
        if fnmatchcase(path, pattern):
            return True
    return False


def _is_text_bytes(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _iter_repo_files(repo_root: Path) -> Iterator[Path]:
    for root, dirnames, filenames in os.walk(repo_root):
        dirnames.sort()
        filenames.sort()
        for filename in filenames:
            yield Path(root) / filename


def _score_path(path: str, task_paths: set[str]) -> int:
    if path in task_paths:
        return 6
    if path == "AGENTS.md":
        return 5
    if path == "README.md":
        return 4
    if fnmatchcase(path, "docs/**/*.md"):
        return 3
    if path.endswith(".md"):
        return 2
    return 1


def inventory_paths(
    repo_root: str | Path,
    include_globs: Sequence[str] | None = None,
    exclude_globs: Sequence[str] | None = None,
) -> list[str]:
    root = Path(repo_root).resolve()
    includes, excludes = _normalize_globs(include_globs, exclude_globs)
    paths: list[str] = []
    for file_path in _iter_repo_files(root):
        rel_path = _posix_relpath(root, file_path)
        if not _matches_any(rel_path, includes):
            continue
        if _matches_any(rel_path, excludes):
            continue
        data = file_path.read_bytes()
        if not _is_text_bytes(data):
            continue
        paths.append(rel_path)
    paths.sort()
    return paths


def build_index(
    repo_root: str | Path,
    include_globs: Sequence[str] | None = None,
    exclude_globs: Sequence[str] | None = None,
    selected_paths: Iterable[str] | None = None,
    task_paths: Iterable[str] | None = None,
) -> dict:
    root = Path(repo_root).resolve()
    includes, excludes = _normalize_globs(include_globs, exclude_globs)
    selected_set = set(selected_paths or [])
    task_set = set(task_paths or [])
    entries: list[IndexEntry] = []
    for file_path in _iter_repo_files(root):
        rel_path = _posix_relpath(root, file_path)
        if not _matches_any(rel_path, includes):
            continue
        if _matches_any(rel_path, excludes):
            continue
        data = file_path.read_bytes()
        if not _is_text_bytes(data):
            continue
        size_bytes = len(data)
        token_est = int(math.ceil(size_bytes / 4)) if size_bytes else 0
        sha256 = hashlib.sha256(data).hexdigest()
        score = _score_path(rel_path, task_set)
        entries.append(
            IndexEntry(
                path=rel_path,
                sha256=sha256,
                size_bytes=size_bytes,
                token_est=token_est,
                score=score,
                selected=rel_path in selected_set,
            )
        )
    entries.sort(key=lambda entry: (-entry.score, entry.path))
    total_token_est = sum(entry.token_est for entry in entries)
    files = [
        {
            "path": entry.path,
            "sha256": entry.sha256,
            "size_bytes": entry.size_bytes,
            "token_est": entry.token_est,
            "score": entry.score,
            "selected": entry.selected,
        }
        for entry in entries
    ]
    return {"total_token_est": total_token_est, "files": files}


def write_index_json(index_data: dict, out_path: str | Path) -> None:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(index_data, indent=2, ensure_ascii=True) + "\n"
    path.write_text(payload, encoding="utf-8")
