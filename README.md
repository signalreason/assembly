# Assembly

Assembly is a minimal, deterministic context compiler that will produce a stable `pack/` directory for agent runners. The spec targets a simple, reproducible selection pipeline and a predictable pack interface.

Note: This project is ~80% AI-generated using
[Codex CLI](https://github.com/openai/codex), a Swiss Army knife, duct tape, and
some chewing gum.

## Completion status (as of 2026-01-29)
- Phase 1 complete
  - Spec and interface docs are complete (`ASSEMBLY_SPEC.md`, `INTERFACE.md`).
  - Example pack is checked in (`assembly/examples/pack-minimal/`).
- Phase 2 complete
  - Deterministic pack production tasks are tracked in `prd.json`.

## Usage
Build a pack from a repo and task input:
```
python -m assembly build --repo . --task "@task.txt" --task-id ASM-011
```

Common options:
- `--task` accepts inline text or `@<file>` references.
- `--out` defaults to `pack/` and contains `manifest.json`, `index.json`, `context.md`, `policy.md`, `lint.json`.
- `--max-tokens` defaults to `6000`.
- `--include` replaces the entire include glob list (defaults to `["**/*"]`).
- `--include-add` appends globs without restating the defaults and keeps ordering deterministic.
- `--exclude` replaces the entire ignore list.
- `--exclude-add` appends to the default ignores (`.git/**`, `.ralph/**`, `node_modules/**`, `dist/**`, `build/**`, `target/**`, `vendor/**`, `.venv/**`, `__pycache__/**`, `.DS_Store`).
- `--no-summary` suppresses the JSON summary on stdout when you need a quiet runner.

If you prefer the wrapper script:
```
./bin/assembly build --repo . --task "Summarize repo structure." --task-id ASM-012
```

### Additive include/exclude globs
The CLI keeps deterministic ordering when merging globs: base values (`--include`/`--exclude`) are taken first, then additive values are appended while de-duping. Use additive flags to extend defaults without spelling them out:
```
python -m assembly build \
  --repo repo \
  --task "Focus on docs and src." \
  --task-id ASM-020-A \
  --include-add "docs/**/*.md" \
  --include-add "src/**" \
  --exclude-add "docs/drafts/**"
```
The build above scans all regular files (`**/*` default) plus the extra doc and source trees, while still skipping the default ignore list and any drafts you add. Deterministic ordering means rerunning with the same repo state and arguments yields the same include/exclude arrays inside `pack/manifest.json` and the same file ordering inside `pack/index.json`.

### Deterministic summary output
After a successful build the CLI prints a machine-readable summary to stdout:
```
{
  "outputs": {
    "context": "/abs/path/pack/context.md",
    "index": "/abs/path/pack/index.json",
    "lint": "/abs/path/pack/lint.json",
    "manifest": "/abs/path/pack/manifest.json",
    "policy": "/abs/path/pack/policy.md"
  },
  "status": "ok"
}
```
Keys are serialized with `sort_keys=True`, indentation is fixed, and every path is normalized to an absolute POSIX string so downstream agents can rely on identical JSON (byte-for-byte, newline-terminated) whenever the repo/out arguments resolve to the same locations. The pack artifacts are still written even if you suppress stdout with `--no-summary`.

Example: capture the summary and hand the manifest path to another tool without restating any pack paths.
```
summary=$(python -m assembly build --repo . --task "@task.txt" --task-id ASM-020-B)
manifest_path=$(printf '%s' "$summary" | jq -r '.outputs.manifest')
control --manifest "$manifest_path"
```
When automation needs a silent build log (for example, when stdout is reserved for another protocol), pass `--no-summary` and the CLI exits success with an empty stdout stream while still producing the pack directory.

## How to use this repo
- Read the spec: `ASSEMBLY_SPEC.md`.
- Use the pack contract: `INTERFACE.md`.
- Inspect the example pack: `assembly/examples/pack-minimal/`.

## Development

The Ralph loop and task agent have moved to https://github.com/signalreason/lever.
This repo focuses on the pack spec and compiler; see Lever for task-running tools.
