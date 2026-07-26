# tools/tidy lowerability contract

## Status

Proposed

## Purpose

Partition checks into language, ABI, runtime, determinism, and resource families
and enforce the promise that every accepted translation unit is supported by the
compiler for its declared target profile.

## Scope

This document governs the following declared TODO scope:

- `tools/tidy/`
- `scripts/validate/`
- `libc/`
- `runtime/`
- `docs/technical/specification/`
- `tests/tidy/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`tools-tidy-lowerability-contract`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- Every accepted fixture compiles successfully for its declared profile, and
  every compiler rejection of a linter-clean supported program is treated as a
  regression in the compiler/linter contract.
- Accepted and rejected C fixtures exercise the boundary, and diagnostics
  identify the unsupported construct/profile requirement at source level.
- Rust tests are conformance/regression evidence for creating the profile; they
  do not replace manual `tools/tidy` validation of user-selected C.
- A rejection corresponds to a documented lowerability/determinism/profile
  requirement, not to arbitrary formatting or host-C style policy.

## Failure Behavior

Unsupported or nondeterministic C is rejected at source locations rather than
lowered through host-dependent behavior.

## Verification

- Expected durable artifact surface: `tools/tidy/`, `scripts/validate/`, `libc/`,
  `runtime/`,
  `docs/technical/specification/`, `tests/tidy/`.
- Required evidence: accepted/rejected source fixtures, source-located
  diagnostics, and compiler/linter contract regression tests.
- Prerequisite completion evidence: `tools-tidy-clang-tidy-plugin`,
  `malbolge-layout-and-encoding-backend`, `supported-libc-contract`.
## References

- [Deterministic C Surface And Clang
  Tooling](../../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)

### Governing ADR Paths

- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
