# Supported libc contract

## Status

Proposed

## Purpose

Define the guest C library surface: fixed-width integers, memory primitives,
byte streams, strings, allocation, formatting, `libm`, and later higher-level
routines without hidden host shortcuts.

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
`supported-libc-contract`. The implementation may change internal representation
or language choices without changing the observable behavior, trust boundary, or
ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- The supported libc and `libm` surfaces state exact C signatures and
  deterministic guest semantics and separate unsupported-today functionality
  from constructs forbidden by the language/ABI model.
- Accepted routines lower to guest code or verified compiler intrinsics and
  never
  resolve through a host libc or host math library in generated artifacts.
- Native CLI adapters are debug-only scaffolding and are not lowerability or
  conformance evidence.
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
- Prerequisite completion evidence: `deterministic-c-to-malbolge-abi`.
## References

- [Deterministic C Surface And Clang
  Tooling](../../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)

### Governing ADR Paths

- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
