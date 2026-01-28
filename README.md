# Assembly

Assembly is a minimal, deterministic context compiler that will produce a stable `pack/` directory for agent runners. The spec targets a simple, reproducible selection pipeline and a predictable pack interface.

Note: This project is ~80% AI-generated using
[Codex CLI](https://github.com/openai/codex), a Swiss Army knife, duct tape, and
some chewing gum.

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

## Development

The Ralph loop and task agent have moved to https://github.com/signalreason/lever.
This repo focuses on the pack spec and compiler; see Lever for task-running tools.
