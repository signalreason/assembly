# Product Requirements Document: Assembly Prerequisites for Task Agent Integration

## Overview
Finalize implementation allowing integrating deterministic context compilation into task agent workflows.

## Goals
- Provide a context compiler interface for task agents.
- Prevent runtime artifact contamination in compiled packs.
- Expose stable CLI behavior task agents can rely on.
- Keep outputs deterministic and contract-compatible.

## Non-Goals
- Implementing task agent runtime integration.
- Changing pack surface names or core artifact types.
- Reworking scoring heuristics beyond integration safety needs.
- Backwards compatibility

## Assembly Plan
2. Add additive glob flags so callers can extend defaults safely.
   - Add CLI support for additive includes/excludes (for example, `--include-add` and `--exclude-add`) so callers do not need to re-specify default globs.
3. Add optional machine-readable build summary output.
   - Add a flag to print build status and resolved output paths as JSON on stdout for robust caller integration and tests.
4. Update tests and docs.
   - Add tests for glob (e.g. `.ralph/**`) exclusion and additive flag behavior.
   - Update `README.md` and `INTERFACE.md` with the new CLI contract and examples.

## Acceptance Criteria
- Context builds cannot accidentally include excluded globs (e.g. `--exclude-add .ralph/**`).
- Additive glob flags work deterministically and preserve existing defaults.
- JSON summary output is stable and parseable for external callers, and can be suppressed with a flag.
- Existing deterministic build tests continue to pass.
- Docs clearly describe the new flags and integration contract.

## Risks and Mitigations
- Risk: non-deterministic summary output.
  - Mitigation: define fixed field ordering and deterministic path normalization rules.
