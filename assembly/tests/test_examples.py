from __future__ import annotations

import json
from pathlib import Path

from assembly import indexer


def test_pack_minimal_manifest_defaults_match_indexer() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    manifest_path = repo_root / "assembly" / "examples" / "pack-minimal" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    excludes = manifest["inputs"]["exclude"]
    assert excludes == indexer.DEFAULT_EXCLUDES
