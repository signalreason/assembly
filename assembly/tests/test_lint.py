from __future__ import annotations

from pathlib import Path

from assembly import lint


def _write(tmp_path: Path, relative: str, content: str) -> None:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_detects_duplicate_do_not_rules(tmp_path: Path) -> None:
    _write(tmp_path, "docs/guide.md", "Do not share secrets.\n")
    _write(tmp_path, "README.md", "Do not share secrets.\n")

    issues = lint.build_lint_issues(tmp_path)

    assert issues["issues"], "expected at least one lint issue"
    issue = issues["issues"][0]
    assert issue["severity"] == "warn"
    assert issue["id"].startswith("duplicate-do-not-rule-")
    assert sorted(issue["files"]) == ["README.md", "docs/guide.md"]
    assert "do not share secrets" in issue["message"].lower()


def test_detects_contradictory_must_rules(tmp_path: Path) -> None:
    _write(tmp_path, "docs/security.md", "Must encrypt all storage.\n")
    _write(tmp_path, "README.md", "Must not encrypt all storage.\n")

    issues = lint.build_lint_issues(tmp_path)

    assert issues["issues"], "expected at least one lint issue"
    issue = issues["issues"][0]
    assert issue["severity"] == "error"
    assert issue["id"].startswith("contradictory-must-rule-")
    assert sorted(issue["files"]) == ["README.md", "docs/security.md"]
    assert "encrypt all storage" in issue["message"].lower()


def test_issue_ordering_follows_severity_then_id(tmp_path: Path) -> None:
    _write(tmp_path, "docs/security.md", "Must encrypt data.\n")
    _write(tmp_path, "README.md", "Must not encrypt data.\n")
    _write(tmp_path, "docs/guide.md", "Do not leak secrets.\n")
    _write(tmp_path, "docs/guide2.md", "Do not leak secrets.\n")

    issues = lint.build_lint_issues(tmp_path)
    severities = [issue["severity"] for issue in issues["issues"]]

    assert severities == ["error", "warn"]
    assert issues["issues"][0]["id"].startswith("contradictory-must-rule-")
    assert issues["issues"][1]["id"].startswith("duplicate-do-not-rule-")
