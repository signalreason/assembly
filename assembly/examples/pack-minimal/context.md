---
path: INTERFACE.md
lines: 1-37
git: 4307130adebf699b5e8e98f13781380a16394f08
score: 8
truncated: false
---
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
