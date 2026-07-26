# malbolge-tidy lowerability contract

- Status: Proposed
- Planning identity: `malbolge-tidy-lowerability-contract`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Deterministic C Surface And Clang
  Tooling](../../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)

## Purpose

Partition checks into language, ABI, runtime, determinism, and resource families
and enforce the promise that every accepted translation unit is supported by the
compiler for its declared target profile.

## Proposed Model

This record defines the contract that implementation must satisfy for
`malbolge-tidy-lowerability-contract`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Every accepted fixture compiles successfully for its declared profile, and
  every compiler rejection of a linter-clean supported program is treated as a
  regression in the compiler/linter contract.
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

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
