# malbolge-tidy clang-tidy plugin

## Status

Proposed

## Purpose

Build `tools/tidy/` as an out-of-tree clang-tidy plugin compiled against the
pinned LLVM version. Add Malbolge checks without forking Clang or weakening the
existing clang-tidy baseline.

## Scope

This document governs the following declared TODO scope:

- `tools/tidy/`
- `libc/`
- `runtime/`
- `docs/technical/specification/`
- `tests/tidy/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`malbolge-tidy-clang-tidy-plugin`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- The out-of-tree plugin loads against the pinned LLVM version, registers only
  documented `malbolge-*` checks, and emits deterministic source-located
  diagnostics without weakening ordinary clang-tidy checks.
- Accepted and rejected C fixtures exercise the boundary, and diagnostics
  identify the unsupported construct/profile requirement at source level.

## Failure Behavior

Unsupported or nondeterministic C is rejected at source locations rather than
lowered through host-dependent behavior.

## Verification

- Expected durable artifact surface: `tools/tidy/`, `libc/`, `runtime/`,
  `docs/technical/specification/`, `tests/tidy/`.
- Required evidence: accepted/rejected source fixtures, source-located
  diagnostics, and compiler/linter contract regression tests.
- Prerequisite completion evidence: `deterministic-c-to-malbolge-abi`,
  `jig-repository-governance`.
## References

- [Deterministic C Surface And Clang
  Tooling](../../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)

### Governing ADR Paths

- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
