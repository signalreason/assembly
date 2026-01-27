# Assembly Pack Interface

## `pack/manifest.json`

Machine consumers rely on the manifest to discover how a pack was built and where to find its artifacts. Every manifest **must** contain the fields below.

| field | type | description | constraints |
| --- | --- | --- | --- |
| `repo_commit` | string | Git HEAD commit SHA used to produce this pack. | Use the exact 40-char SHA when the repo has commits; otherwise emit the literal string `unknown`. |
| `task_id` | string | Identifier passed via `--task-id`. | Non-empty ASCII string; must match the task input. |
| `max_tokens` | integer | Token budget used while selecting snippets. | Positive integer equal to `--max-tokens` CLI flag. |
| `inputs` | object | Echo of build inputs. | Must include `task`, `repo`, `include`, `exclude` keys (see below). |
| `outputs` | object | Paths for generated pack files. | Must include `manifest`, `index`, `context`, `policy`, `lint` keys; every value is a repo-relative POSIX path under `pack/`. |
| `created_at` | string | Timestamp for when the manifest was produced. | RFC3339 format with timezone offset; precision at least to seconds. |
| `tool_version` | string | Semantic version of the `assembly` CLI. | Non-empty string; bump whenever breaking changes occur. |

### `inputs` object

| field | type | description | constraints |
| --- | --- | --- | --- |
| `task` | string | Original task text or `@<file>` reference from CLI. | Preserve exact user-provided value. |
| `repo` | string | Absolute or repo-relative path passed via `--repo`. | Normalize to real path if resolvable. |
| `include` | array\<string> | Glob patterns additionally included. | Empty array allowed; default to `["**/*"]` when user omits `--include`. |
| `exclude` | array\<string> | Glob patterns removed from consideration. | Empty array allowed; default to the CLI’s built-in ignore list when unspecified. |

### `outputs` object

The manifest lists canonical pack files so other tools can fetch them without assumptions.

| key | required path |
| --- | --- |
| `manifest` | `pack/manifest.json` (self-reference for completeness) |
| `index` | `pack/index.json` |
| `context` | `pack/context.md` |
| `policy` | `pack/policy.md` |
| `lint` | `pack/lint.json` |

### Minimal manifest example

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

## `pack/index.json`

The index lists every file considered for the pack along with deterministic scoring metadata so downstream tools can reason about coverage without opening `context.md`.

| field | type | description | constraints |
| --- | --- | --- | --- |
| `files` | array<object> | Ordered list of candidate files ranked per the scoring rules. | Non-empty when any files are analyzed; order is stable and must match the selection pipeline. |
| `total_token_est` | integer | Aggregate token estimate for the pack. | Must equal the sum of `token_est` across every entry in `files`; recompute whenever any entry changes. |

### `files[]` entry

| field | type | description | constraints |
| --- | --- | --- | --- |
| `path` | string | Repo-relative POSIX path to the file. | Always use forward slashes; no leading `./`. |
| `sha256` | string | Hex-encoded SHA-256 digest of the file bytes. | Lowercase hex; 64 characters. |
| `size_bytes` | integer | File size in bytes. | Non-negative integer sourced from the filesystem stat. |
| `token_est` | integer | Estimated token usage if the full file were included. | Non-negative integer; typically `ceil(bytes/4)` and must be consistent with `total_token_est`. |
| `score` | integer | Deterministic priority score assigned during selection. | Higher scores indicate earlier selection; ties break by path. |
| `selected` | boolean | Whether the file (or a snippet from it) was emitted into `context.md`. | `true` when any portion made it into the context; `false` otherwise. |

### Minimal index example

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
