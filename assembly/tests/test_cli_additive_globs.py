from __future__ import annotations

from assembly import cli, indexer


def test_resolve_includes_adds_to_defaults_with_dedup() -> None:
    result = cli._resolve_globs(
        base=None,
        additions=["docs/**/*.md", "src/**", "docs/**/*.md", "**/*"],
        defaults=indexer.DEFAULT_INCLUDES,
    )

    assert result == indexer.DEFAULT_INCLUDES + ["docs/**/*.md", "src/**"]


def test_resolve_excludes_adds_to_defaults_with_overlap() -> None:
    result = cli._resolve_globs(
        base=None,
        additions=[".git/**", "build/**", "custom/**", "build/**"],
        defaults=indexer.DEFAULT_EXCLUDES,
    )

    assert result == indexer.DEFAULT_EXCLUDES + ["custom/**"]


def test_resolve_globs_prefers_explicit_base_then_adds() -> None:
    result = cli._resolve_globs(
        base=["src/**", "docs/**"],
        additions=["docs/**", "tests/**"],
        defaults=indexer.DEFAULT_INCLUDES,
    )

    assert result == ["src/**", "docs/**", "tests/**"]
