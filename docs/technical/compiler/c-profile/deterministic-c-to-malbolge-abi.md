# Deterministic C-to-Malbolge ABI

## Status

Proposed

## Purpose

Specify fixed integer widths, signed behavior, endianness, pointers, alignment,
object representation, stack rules, recursion policy, I/O, and a fail-closed
policy for undefined or target-dependent C behavior.

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
`deterministic-c-to-malbolge-abi`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- The ABI specifies integer representation, multiword values, pointers,
  stack/frame layout, calls/returns, byte I/O, memory lifetime, alignment, and
  target-profile requirements without host ABI leakage.
- Accepted and rejected C fixtures exercise the boundary, and diagnostics
  identify the unsupported construct/profile requirement at source level.
- The admitted profile rejects C only for a documented semantic, ABI, runtime,
  determinism, or target-resource reason. Style preferences and limitations of
  unrelated host C implementations are not guest-language restrictions.
- Source constructs such as recursion, allocation, aggregate types, or function
  pointers are not forbidden merely because Malbolge is difficult; they are
  accepted whenever the selected profile/runtime gives them deterministic
  lowerable semantics.

## Failure Behavior

Unsupported or nondeterministic C is rejected at source locations rather than
lowered through host-dependent behavior.

## Verification

- Expected durable artifact surface: `tools/tidy/`, `libc/`, `runtime/`,
  `docs/technical/specification/`, `tests/tidy/`.
- Required evidence: accepted/rejected source fixtures, source-located
  diagnostics, and compiler/linter contract regression tests.
- Prerequisite completion evidence: `canonical-malbolge-target-profile`,
  `latex-mathematical-specification-framework`.
## References

- [Deterministic C Surface And Clang
  Tooling](../../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)

### Governing ADR Paths

- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
