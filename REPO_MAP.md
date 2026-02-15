# Repository Map

## Purpose
`assembly` is a deterministic context compiler. It builds a stable `pack/` with:
`manifest.json`, `index.json`, `context.md`, `policy.md`, and `lint.json`.
Core behavior is defined in `ASSEMBLY_SPEC.md` and `INTERFACE.md`.

## Top-Level Layout
| Path | Kind | Role |
| --- | --- | --- |
| `AGENTS.md` | doc | Local agent instructions for this repo. |
| `ASSEMBLY_SPEC.md` | doc | Product spec and phased acceptance criteria. |
| `INTERFACE.md` | doc | Pack contract and schema details. |
| `README.md` | doc | Project overview, status, and usage examples. |
| `assembly/` | package | Main Python implementation, tests, and example pack. |
| `bin/assembly` | script | Executable wrapper to run the CLI entrypoint. |
| `prd.json` | data | Task tracker for completed Phase 1/2 work items. |
| `prompts/` | docs | Prompt templates used for product/spec workflows. |

## Python Package: `assembly/`
| Path | Role |
| --- | --- |
| `assembly/__init__.py` | Package metadata (`__version__ = "0.1.0"`). |
| `assembly/__main__.py` | `python -m assembly` entrypoint; delegates to `assembly.cli.main`. |
| `assembly/cli.py` | CLI parsing and `build` command orchestration; writes pack outputs. |
| `assembly/context.py` | Deterministic snippet selection/truncation and `context.md` writer. |
| `assembly/indexer.py` | File inventory, include/exclude matching, scoring, hashing, `index.json` writer. |
| `assembly/lint.py` | Directive extraction and lint issue detection/writing (`duplicate do not`, contradictory `must` vs `must not`). |
| `assembly/examples/pack-minimal/` | Checked-in minimal pack example matching interface schema. |
| `assembly/tests/test_lint.py` | Unit tests for lint rule detection and issue ordering. |
| `assembly/tests/test_phase2_determinism.py` | Acceptance test for deterministic rebuilds and stable outputs. |

## Build Flow (`assembly build`)
1. Parse args and resolve repo/task inputs in `assembly/cli.py`.
2. Build context blocks via `assembly/context.py` using deterministic ordering from `assembly/indexer.py`.
3. Build full file index in `assembly/indexer.py`.
4. Build lint issues in `assembly/lint.py`.
5. Write `manifest.json`, `index.json`, `context.md`, empty `policy.md`, and `lint.json`.

## Examples and Prompts
| Path | Role |
| --- | --- |
| `assembly/examples/pack-minimal/manifest.json` | Example build receipt. |
| `assembly/examples/pack-minimal/index.json` | Example selection ledger. |
| `assembly/examples/pack-minimal/context.md` | Example snippet stream. |
| `assembly/examples/pack-minimal/policy.md` | Empty placeholder file (Phase 1/2 behavior). |
| `assembly/examples/pack-minimal/lint.json` | Example lint output. |
| `prompts/spec-writer.md` | Product spec drafting prompt. |
| `prompts/autonomous-senior-engineer.prompt.md` | Engineering execution prompt template. |

## Non-Source/Local Artifacts Present
These exist in the working tree but are runtime/environment artifacts, not core source:
`.git/`, `.env`, `.venv/`, `.pytest_cache/`, `.ralph/`, `assembly/__pycache__/`, `assembly/tests/__pycache__/`, `assembly/.pytest_cache/`.
