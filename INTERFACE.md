# Assembly Pack Interface
Assembly is the context compiler powering Agency's stage-gated runtime. The pack stays frozen once emitted so `control` and `crowbar` can rely on deterministic surfaces.

## Pack Surfaces

### `pack/manifest.json` (build receipt)
**Job:** Tell downstream tools exactly how the pack was produced and where to find every artifact.
**Signals:** `repo_commit`, `task_id`, `max_tokens`, input echo, output paths, build timestamp, and CLI version.

#### Field schema
| field | type | description | constraints |
| --- | --- | --- | --- |
| `repo_commit` | string | Git HEAD commit SHA used to produce this pack. | Use the exact 40-char SHA when the repo has commits; otherwise emit the literal string `unknown`. |
| `task_id` | string | Identifier passed via `--task-id`. | Non-empty ASCII string; must match the task input. |
| `max_tokens` | integer | Token budget used while selecting snippets. | Positive integer equal to `--max-tokens` CLI flag. |
| `inputs` | object | Echo of build inputs. | Must include `task`, `repo`, `include`, `exclude` keys (see below). |
| `outputs` | object | Paths for generated pack files. | Must include `manifest`, `index`, `context`, `policy`, `lint` keys; every value is a repo-relative POSIX path under `pack/`. |
| `created_at` | string | Timestamp for when the manifest was produced. | RFC3339 format with timezone offset; precision at least to seconds. |
| `tool_version` | string | Semantic version of the `assembly` CLI. | Non-empty string; bump whenever breaking changes occur. |

#### `inputs` object
| field | type | description | constraints |
| --- | --- | --- | --- |
| `task` | string | Original task text or `@<file>` reference from CLI. | Preserve exact user-provided value. |
| `repo` | string | Absolute or repo-relative path passed via `--repo`. | Normalize to real path if resolvable. |
| `include` | array<string> | Glob patterns additionally included. | Empty array allowed; default to `["**/*"]` when user omits `--include`. |
| `exclude` | array<string> | Glob patterns removed from consideration. | Empty array allowed; default to the CLI's built-in ignore list when unspecified. |

#### `outputs` object
The manifest lists canonical pack files so other tools can fetch them without assumptions.

| key | required path |
| --- | --- |
| `manifest` | `pack/manifest.json` (self-reference for completeness) |
| `index` | `pack/index.json` |
| `context` | `pack/context.md` |
| `policy` | `pack/policy.md` |
| `lint` | `pack/lint.json` |

#### Minimal manifest example
```json
{
  "repo_commit": "unknown",
  "task_id": "ASM-001",
  "max_tokens": 6000,
  "inputs": {
    "task": "@/tmp/task.md",
    "repo": ".",
    "include": ["**/*"],
    "exclude": [
      ".git/**",
      ".ralph/**",
      "node_modules/**",
      "dist/**",
      "build/**",
      "target/**",
      "vendor/**",
      ".venv/**",
      "__pycache__/**",
      ".DS_Store"
    ]
  },
  "outputs": {
    "manifest": "pack/manifest.json",
    "index": "pack/index.json",
    "context": "pack/context.md",
    "policy": "pack/policy.md",
    "lint": "pack/lint.json"
  },
  "created_at": "2026-01-27T15:04:05Z",
  "tool_version": "0.1.0"
}
```
The example above uses `repo_commit: "unknown"` to illustrate the fallback for non-git builds, and `created_at` is formatted as RFC3339 with a UTC offset.

### `pack/index.json` (selection ledger)
**Job:** Capture every candidate file plus deterministic scores so downstream tooling can reason about coverage without opening `context.md`.
**Signals:** Ranked `files[]` entries and a `total_token_est` checksum that always matches the per-entry sum.

#### Field schema
| field | type | description | constraints |
| --- | --- | --- | --- |
| `files` | array<object> | Ordered list of candidate files ranked per the scoring rules. | Non-empty when any files are analyzed; order is stable and must match the selection pipeline. |
| `total_token_est` | integer | Aggregate token estimate for the pack. | Must equal the sum of `token_est` across every entry in `files`; recompute whenever any entry changes. |

#### `files[]` entry
| field | type | description | constraints |
| --- | --- | --- | --- |
| `path` | string | Repo-relative POSIX path to the file. | Always use forward slashes; no leading `./`. |
| `sha256` | string | Hex-encoded SHA-256 digest of the file bytes. | Lowercase hex; 64 characters. |
| `size_bytes` | integer | File size in bytes. | Non-negative integer sourced from the filesystem stat. |
| `token_est` | integer | Estimated token usage if the full file were included. | Non-negative integer; typically `ceil(bytes/4)` and must be consistent with `total_token_est`. |
| `score` | integer | Deterministic priority score assigned during selection. | Higher scores indicate earlier selection; ties break by path. |
| `selected` | boolean | Whether the file (or a snippet from it) was emitted into `context.md`. | `true` when any portion made it into the context; `false` otherwise. |

#### Minimal index example
```json
{
  "total_token_est": 900,
  "files": [
    {
      "path": "README.md",
      "sha256": "50d858e9c54d1a63f0e1d763ce7f1c0c0f6e78fba7e3ea0d3a2c3cfc3cbed221",
      "size_bytes": 2400,
      "token_est": 600,
      "score": 3,
      "selected": true
    },
    {
      "path": "docs/usage.md",
      "sha256": "8d615cb3c2a7d7f6507c2d0cb42f2a0bff173a8b7f39f7895d7c6bd5671d042e",
      "size_bytes": 1200,
      "token_est": 300,
      "score": 4,
      "selected": false
    }
  ]
}
```
In the example above, `total_token_est` equals `600 + 300 = 900`, demonstrating the required relationship between the aggregate and the per-file entries.

### `pack/context.md` (snippet log)
**Job:** Emit a machine-readable stream of every snippet inserted into the pack.
**Format:** Snippets are concatenated blocks separated by metadata fences so stream processors can parse without loading the full file.

#### Block layout
1. `---` (three hyphens) begins the metadata header.
2. Five metadata lines, each in `key: value` form:
   - `path: <repo-relative POSIX path>`
   - `lines: <start>-<end>`
   - `git: <commit-sha-or-unknown>`
   - `score: <integer>`
   - `truncated: <true|false>`
3. `---` closes the header.
4. Raw snippet text exactly as copied from the source file; no additional fences or indentation are added. The snippet ends immediately before the next `---` line or EOF.

#### Metadata semantics
| key | type | description | constraints |
| --- | --- | --- | --- |
| `path` | string | Repo-relative POSIX path to the source file. | Always matches an entry in `pack/index.json`; use forward slashes and omit leading `./`. |
| `lines` | string | Inclusive `start-end` line numbers corresponding to the snippet within `path`. | Start and end are positive integers with `start <= end`; numbers refer to the file revision at `git`. |
| `git` | string | Git commit SHA that produced the snippet. | Use the same 40-char SHA as `manifest.repo_commit`; fall back to `unknown` when the repo state lacks commits. |
| `score` | integer | Selection score used for ordering snippets. | Matches the score assigned in `pack/index.json`; higher scores appear earlier when other ordering factors tie. |
| `truncated` | boolean | Whether the snippet omits trailing content from the source because of the token budget. | `true` when only a prefix of the file fits; `false` when the entire file segment from `start` to `end` is present. |

The `lines` range must always reflect the snippet boundaries actually present in the block, even when `truncated: true`. Downstream tools can rely on `git` plus `path` and `lines` to reconstruct or diff the source, so the trio must remain consistent.

#### Minimal context example
```
---
path: README.md
lines: 1-24
git: 4f3b6ad9c2f4c1e8d7fca3b1c5d2e6141c8fb2aa
score: 3
truncated: false
---
# Project README
...
```

### `pack/policy.md` (policy placeholder)
**Job:** Keep the surface contract stable even before policy extraction ships.
**Rules:** The file MUST exist at `pack/policy.md` and contain zero bytes—no header, newline, or placeholder text. Later phases will backfill normalized policy lines, but consumers should currently treat the empty file as an intentional "not implemented yet" signal.

### `pack/lint.json` (lint stream)
**Job:** Convey normalized lint findings so `control` can halt or warn without re-parsing build logs.
**Structure:** Optional `issues` array sorted by severity (error → warn → info) and then by stable `id`.

#### Field schema
| field | type | description | constraints |
| --- | --- | --- | --- |
| `issues` | array<object> | Normalized lint findings sorted by deterministic priority (higher severity first, then stable by `id`). | Optional but, when present, every entry must follow the schema below. |

#### `issues[]` entry
| field | type | description | constraints |
| --- | --- | --- | --- |
| `id` | string | Stable identifier for the lint rule (e.g., `missing-readme`). | Non-empty ASCII; repeat the same `id` for identical rules across runs so tooling can de-dupe. |
| `severity` | string | Importance of the issue for consumers. | Must be exactly one of `info`, `warn`, or `error`; lowercase only. |
| `message` | string | Human-readable explanation of the issue. | Concise English sentence that gives concrete remediation hints. |
| `files` | array<string> | Repo-relative POSIX paths the issue applies to. | Empty array allowed for repo-wide findings; otherwise include `./`-less paths. |

#### Minimal lint example
```json
{
  "issues": [
    {
      "id": "missing-tests",
      "severity": "warn",
      "message": "No tests matched the include globs; double-check the repo path and filters.",
      "files": []
    },
    {
      "id": "large-file",
      "severity": "info",
      "message": "Skipped docs/legacy.md because it exceeds the 200 KB file limit.",
      "files": ["docs/legacy.md"]
    }
  ]
}
```

## CLI Contract

### Deterministic include/exclude globs
- `assembly build --repo <path> --task <text-or-@file> --task-id <id>` is the canonical entry point; `--out pack/` and `--max-tokens 6000` remain defaults.
- Base include globs default to `["**/*"]` and base excludes default to `.git/**`, `.ralph/**`, `node_modules/**`, `dist/**`, `build/**`, `target/**`, `vendor/**`, `.venv/**`, `__pycache__/**`, `.DS_Store`.
- `--include` or `--exclude` replace the entire respective list; additive flags (`--include-add`, `--exclude-add`) append new patterns without restating the defaults.
- The merger is deterministic: base entries are kept in order, additive entries are appended in the order provided, and duplicates are removed while preserving the first occurrence. Identical inputs therefore always yield the same arrays and downstream file ordering.
- `pack/manifest.json.inputs.include` and `.exclude` surface the exact lists used during selection so callers can verify glob provenance without recomputing the merge rules.

### Machine-readable build summary
- After a successful build the CLI prints a JSON summary to stdout unless `--no-summary` is present. The object currently contains:
  - `status`: string outcome (`"ok"` on success; no summary is emitted on failure).
  - `outputs`: object with `manifest`, `index`, `context`, `policy`, and `lint` keys. Each value is the resolved absolute path to the artifact rooted at `--out`.
- Paths are normalized by resolving `--out/<file>` on the host filesystem and serializing the result with `Path.as_posix()`, yielding absolute forward-slash strings even on Windows. If resolution fails (for example, due to permissions), the CLI falls back to the lexical path but still serializes with POSIX separators.
- The payload is serialized via `json.dumps(..., sort_keys=True, indent=2, ensure_ascii=True)` followed by a trailing newline, so identical repos, flags, and output directories always produce byte-for-byte identical summaries.

#### Canonical summary example
```
{
  "outputs": {
    "context": "/abs/repo/pack/context.md",
    "index": "/abs/repo/pack/index.json",
    "lint": "/abs/repo/pack/lint.json",
    "manifest": "/abs/repo/pack/manifest.json",
    "policy": "/abs/repo/pack/policy.md"
  },
  "status": "ok"
}
```

### Summary suppression behavior
- `--no-summary` suppresses the stdout payload while still writing every pack artifact to disk. Callers that dedicate stdout to another protocol can enable this flag and rely solely on exit codes plus known `--out` paths.
- Suppression affects only the summary emission; globs, selection, manifest/index/context contents, and linting proceed unchanged so deterministic pack behavior is preserved.
