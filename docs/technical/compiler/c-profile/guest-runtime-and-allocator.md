# Guest runtime and allocator

## Status

Proposed

## Purpose

Implement startup, calling convention, frames, allocation, streams, integer
helpers, strings, scheduling primitives, and other runtime facilities as code
that ultimately executes under Malbolge semantics.

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
`guest-runtime-and-allocator`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- Allocation, streams, arithmetic helpers, calling convention support, and other
  runtime facilities execute inside guest Malbolge semantics rather than hidden
  host callbacks.
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
- Prerequisite completion evidence: `supported-libc-contract`,
  `safe-rust-malbolge-vm`.
## References

- [Deterministic C Surface And Clang
  Tooling](../../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)

### Governing ADR Paths

- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
