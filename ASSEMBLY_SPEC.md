# Assembly MVP Spec

Goal: a minimal, deterministic context compiler that produces a stable `pack/` for agent runners, fast.

## Scope
Phased delivery:
1) Schema freeze
2) Deterministic pack production
3) Policy normalization

## CLI
`assembly build --repo <path> --task <task-file-or-text> --out <dir> --max-tokens <N> --task-id <id> [--include <glob>...] [--exclude <glob>...]`

Defaults:
- `--repo` = `.`
- `--out` = `pack/`
- `--max-tokens` = `6000`
- `--task-id` = required
- include: `**/*`
- exclude (default): `.git/**`, `node_modules/**`, `dist/**`, `build/**`, `target/**`, `vendor/**`, `.venv/**`, `__pycache__/**`, `.DS_Store`

Token estimator: `ceil(chars/4)` (ASCII, UTF-8 bytes treated as chars).

## Phase 1 — Schema (Day 1)
Define pack file shapes and example output.

### Outputs
`pack/manifest.json`
- `repo_commit` (git HEAD sha or `"unknown"` if not a git repo)
- `task_id` (from flag)
- `max_tokens`
- `inputs` (`task`, `repo`, `include`, `exclude`)
- `outputs` (paths for other files)
- `created_at` (RFC3339)
- `tool_version` (string)

`pack/index.json`
- `files`: array of `{ path, sha256, size_bytes, token_est, score, selected }`
- `total_token_est`

`pack/context.md` (machine-readable markdown)
- Repeated blocks:
  - `---`
  - `path: <repo-relative>`
  - `lines: <start>-<end>`
  - `git: <commit>`
  - `score: <number>`
  - `truncated: <true|false>`
  - `---`
  - raw snippet text

`pack/policy.md` (empty file in Phase 1)

`pack/lint.json`
- `issues`: array of `{ id, severity, message, files }`
- `severity` in `info|warn|error`

### Acceptance tests
- `INTERFACE.md` exists in repo with this schema.
- `assembly/examples/pack-minimal/` checked in and matches schema.

## Phase 2 — Deterministic pack production (Day 2)
Builds a pack from repo + task under token budget with provenance.

### Selection + scoring (deterministic)
File class priority (higher score wins):
1. `task` input
2. `AGENTS.md`
3. `README.md`
4. `docs/**/*.md`
5. other `*.md`
6. all other text files

Within same class: sort by repo-relative path (ASCII lexicographic).
Score = `class_rank` (integer). No content-based heuristics.

### Snippet policy
- Each selected file contributes one snippet (full file) until budget exhausted.
- If a file would exceed remaining budget, include leading portion that fits and set `truncated: true` with correct line range.

### Provenance
Every snippet block includes `path`, `lines`, `git` as in `context.md`.

### Lint (minimal but real)
- Detect duplicate “do not” rules across docs.
- Detect direct contradictions: `must X` vs `must not X` within high-priority docs (classes 1–4).
Heuristic: case-insensitive match on lines containing `must`, `must not`, `do not`, `don't`.

### Acceptance tests
- Running `assembly build` twice yields identical pack contents except `created_at` in `manifest.json`.
- `context.md` ordering and `index.json` are stable across runs on same repo state.
- `lint.json` uses only `info|warn|error` severities and stable `id` keys.

## Phase 3 — Policy normalization (Day 5 for assembly scope)
Produce `policy.md` by extracting rules from selected snippets.

### Policy extraction
- Rules are lines with case-insensitive prefixes: `must`, `must not`, `do`, `do not`, `should`, `should not`.
- Ignore empty/whitespace lines.

### Priority normalization
- Priority follows file class order (Phase 2). Output order is: higher priority first, then path-lexicographic.

### `policy.md` format
- One rule per line: `P<rank> [<path>] <rule>`

### Acceptance tests
- `policy.md` is deterministic and changes only when source rules change.
- Every rule line has a priority and source path.

## Non-goals / descopes
- No semantic relevance ranking beyond file class.
- No embeddings, model calls, or repo indexing services.
- No patch/test/commit automation.

