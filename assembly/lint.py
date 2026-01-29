"""Minimal linting helpers for directive-based checks."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .indexer import inventory_paths, _score_path


SEVERITY_ORDER = {"error": 0, "warn": 1, "info": 2}
_MUST_NOT_PATTERN = re.compile(r"\bmust\s+not\b")
_MUST_PATTERN = re.compile(r"\bmust\b")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
_SLUG_MAX = 45


@dataclass(frozen=True)
class DirectiveLine:
    path: str
    raw_text: str
    normalized_text: str
    directive_type: str
    base_text: str | None
    score: int


def _normalize_text(line: str) -> str:
    stripped = line.strip().lower()
    if not stripped:
        return ""
    collapsed = _WHITESPACE_PATTERN.sub(" ", stripped)
    return collapsed


def _slugify(text: str) -> str:
    slug = _SLUG_PATTERN.sub("-", text.lower()).strip("-")
    if not slug:
        return "rule"
    if len(slug) <= _SLUG_MAX:
        return slug
    return slug[:_SLUG_MAX].rstrip("-") or slug[:_SLUG_MAX]


def _classify_line(normalized: str) -> tuple[str | None, str | None]:
    if not normalized:
        return None, None
    if _MUST_NOT_PATTERN.search(normalized):
        base = _MUST_NOT_PATTERN.sub("", normalized, count=1)
        return "must_not", _normalize_text(base)
    if _MUST_PATTERN.search(normalized):
        base = _MUST_PATTERN.sub("", normalized, count=1)
        return "must", _normalize_text(base)
    if "do not" in normalized or "don'" in normalized:
        return "do_not", normalized
    return None, None


def collect_directive_lines(
    repo_root: str | Path,
    include_globs: Sequence[str] | None = None,
    exclude_globs: Sequence[str] | None = None,
    task_paths: Iterable[str] | None = None,
) -> list[DirectiveLine]:
    root = Path(repo_root).resolve()
    task_set = set(task_paths or [])
    directives: list[DirectiveLine] = []
    for rel_path in inventory_paths(root, include_globs, exclude_globs):
        score = _score_path(rel_path, task_set)
        content = (root / rel_path).read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            normalized = _normalize_text(line)
            directive_type, base_text = _classify_line(normalized)
            if not directive_type or not normalized:
                continue
            directives.append(
                DirectiveLine(
                    path=rel_path,
                    raw_text=line.strip(),
                    normalized_text=normalized,
                    directive_type=directive_type,
                    base_text=base_text,
                    score=score,
                )
            )
    return directives


def detect_duplicate_do_not_rules(directives: Iterable[DirectiveLine]) -> list[dict[str, object]]:
    buckets: dict[str, dict[str, object]] = {}
    for directive in directives:
        if directive.directive_type != "do_not":
            continue
        key = directive.normalized_text
        if not key:
            continue
        bucket = buckets.setdefault(key, {"paths": set(), "sample": directive.raw_text.strip()})
        bucket["paths"].add(directive.path)
        if not bucket.get("sample"):
            bucket["sample"] = directive.raw_text.strip()
    issues: list[dict[str, object]] = []
    for key, bucket in sorted(buckets.items()):
        files = sorted(bucket["paths"])
        if len(files) < 2:
            continue
        slug = _slugify(key)
        sample = bucket["sample"] or key
        issues.append(
            {
                "id": f"duplicate-do-not-rule-{slug}",
                "severity": "warn",
                "message": f'The "do not" rule "{sample}" appears in multiple docs.',
                "files": files,
            }
        )
    return issues


def detect_contradictory_must_rules(directives: Iterable[DirectiveLine]) -> list[dict[str, object]]:
    groups: dict[str, dict[str, object]] = {}
    for directive in directives:
        if directive.directive_type not in {"must", "must_not"}:
            continue
        if directive.score < 3:
            continue
        base = directive.base_text
        if not base:
            continue
        group = groups.setdefault(
            base,
            {
                "must": set(),
                "must_not": set(),
                "must_sample": "",
                "must_not_sample": "",
            },
        )
        group[directive.directive_type].add(directive.path)
        sample_key = f"{directive.directive_type}_sample"
        if not group[sample_key]:
            group[sample_key] = directive.raw_text.strip()
    issues: list[dict[str, object]] = []
    for base, group in sorted(groups.items()):
        must_paths = group["must"]
        must_not_paths = group["must_not"]
        if not must_paths or not must_not_paths:
            continue
        files = sorted(must_paths | must_not_paths)
        slug = _slugify(base)
        primary = group.get("must_sample") or base
        opposite = group.get("must_not_sample") or base
        issues.append(
            {
                "id": f"contradictory-must-rule-{slug}",
                "severity": "error",
                "message": (
                    f'Conflicting directives for "{base}"; some docs say "{primary}" '
                    f'while others say "{opposite}".'
                ),
                "files": files,
            }
        )
    return issues


def build_lint_issues(
    repo_root: str | Path,
    include_globs: Sequence[str] | None = None,
    exclude_globs: Sequence[str] | None = None,
    task_paths: Iterable[str] | None = None,
) -> dict[str, list[dict[str, object]]]:
    directives = collect_directive_lines(repo_root, include_globs, exclude_globs, task_paths)
    issues = []
    issues.extend(detect_contradictory_must_rules(directives))
    issues.extend(detect_duplicate_do_not_rules(directives))
    issues.sort(key=lambda issue: (SEVERITY_ORDER[issue["severity"]], issue["id"]))
    return {"issues": issues}


def write_lint_json(lint_data: dict[str, list[dict[str, object]]], out_path: str | Path) -> None:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(lint_data, indent=2, ensure_ascii=True) + "\n"
    path.write_text(payload, encoding="utf-8")


__all__ = [
    "DirectiveLine",
    "build_lint_issues",
    "collect_directive_lines",
    "detect_contradictory_must_rules",
    "detect_duplicate_do_not_rules",
    "write_lint_json",
]
