# Assembly

Assembly is a minimal, deterministic context compiler that will produce a stable `pack/` directory for agent runners. The spec targets a simple, reproducible selection pipeline and a predictable pack interface.

## Completion status (as of 2026-01-27)
- Phase 1 complete
    - Spec and interface docs are complete (`ASSEMBLY_SPEC.md`, `INTERFACE.md`).
    - Example pack is checked in (`assembly/examples/pack-minimal/`).
- Phase 2 next
    - Deterministic pack production (see [ASSEMBLY_SPEC](./ASSEMBLY_SPEC.md)).

## How to use this repo
- Read the spec: `ASSEMBLY_SPEC.md`.
- Use the pack contract: `INTERFACE.md`.
- Inspect the example pack: `assembly/examples/pack-minimal/`.

## Run the Ralph loop
The Ralph loop drives tasks from a tasks JSON file (default: `prd.json`) using the task agent.

Requirements: `bash`, `jq`, and an executable task agent.

```bash
bin/ralph-loop.sh --prompt prompts/autonomous-senior-engineer.prompt.md
```

Common options:
- `--tasks <path>`: tasks JSON file (default: `prd.json`).
- `--assignee <name>`: assignee label (default: `ralph-loop`).
- `--task-agent <path>`: path to the task agent script (default: `bin/task-agent.sh`).
- `--delay <seconds>`: pause between cycles.

## Run the task agent
The task agent runs exactly one task iteration via the Codex CLI.

Requirements: `bash`, `jq`, `git`, and `codex` in `PATH`.

```bash
bin/task-agent.sh \
  --tasks prd.json \
  --task-id ASM-001 \
  --assignee ralph-loop \
  --prompt prompts/autonomous-senior-engineer.prompt.md
```

You can also select the next runnable task:

```bash
bin/task-agent.sh \
  --tasks prd.json \
  --next \
  --assignee ralph-loop \
  --prompt prompts/autonomous-senior-engineer.prompt.md
```
