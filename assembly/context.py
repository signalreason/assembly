"""Deterministic context snippet selection and pack/context.md generation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from . import indexer


@dataclass(frozen=True)
class ContextBlock:
    path: str
    lines: str
    git: str
    score: int
    truncated: bool
    text: str


def _token_est(byte_len: int) -> int:
    return int(math.ceil(byte_len / 4)) if byte_len else 0


def _line_count(text: str) -> int:
    if not text:
        return 0
    newlines = text.count("\n")
    if text.endswith("\n"):
        return newlines
    return newlines + 1


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _truncate_text(data: bytes, max_tokens: int) -> tuple[str, int]:
    if max_tokens <= 0:
        return "", 0
    max_bytes = max_tokens * 4
    if max_bytes <= 0:
        return "", 0
    prefix = data[:max_bytes]
    text = prefix.decode("utf-8", errors="ignore")
    token_est = _token_est(len(text.encode("utf-8")))
    return text, token_est


def build_context_blocks(
    repo_root: str | Path,
    max_tokens: int,
    include_globs: Sequence[str] | None = None,
    exclude_globs: Sequence[str] | None = None,
    task_paths: Iterable[str] | None = None,
    git_sha: str = "unknown",
) -> list[ContextBlock]:
    root = Path(repo_root).resolve()
    index_data = indexer.build_index(
        root,
        include_globs=include_globs,
        exclude_globs=exclude_globs,
        task_paths=task_paths,
    )
    remaining = max_tokens
    blocks: list[ContextBlock] = []
    for entry in index_data["files"]:
        if remaining <= 0:
            break
        if entry["token_est"] == 0:
            continue
        path = root / entry["path"]
        data = path.read_bytes()
        full_tokens = entry["token_est"]
        if full_tokens <= remaining:
            text = _read_text(path)
            line_count = _line_count(text)
            if line_count == 0:
                continue
            lines = f"1-{line_count}"
            blocks.append(
                ContextBlock(
                    path=entry["path"],
                    lines=lines,
                    git=git_sha,
                    score=entry["score"],
                    truncated=False,
                    text=text,
                )
            )
            remaining -= full_tokens
            continue
        text, used_tokens = _truncate_text(data, remaining)
        line_count = _line_count(text)
        if line_count == 0:
            break
        lines = f"1-{line_count}"
        blocks.append(
            ContextBlock(
                path=entry["path"],
                lines=lines,
                git=git_sha,
                score=entry["score"],
                truncated=True,
                text=text,
            )
        )
        remaining = 0
    return blocks


def write_context_md(blocks: Iterable[ContextBlock], out_path: str | Path) -> None:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        blocks_list = list(blocks)
        for idx, block in enumerate(blocks_list):
            handle.write("---\n")
            handle.write(f"path: {block.path}\n")
            handle.write(f"lines: {block.lines}\n")
            handle.write(f"git: {block.git}\n")
            handle.write(f"score: {block.score}\n")
            handle.write(f"truncated: {'true' if block.truncated else 'false'}\n")
            handle.write("---\n")
            handle.write(block.text)
            if idx < len(blocks_list) - 1:
                if not block.text.endswith("\n"):
                    handle.write("\n")
