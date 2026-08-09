# Ternary machine lowering

## Status

Proposed

## Purpose

Lower typed C IR into a compact ternary virtual-machine representation suited to
Malbolge instead of translating C operations directly instruction by
instruction.

## Scope

This document governs the following declared TODO scope:

- `compiler/`
- `src/`
- `tests/compiler/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`ternary-machine-lowering`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- Every IR operation lowers to explicit ternary/runtime operations with defined
  pre/postconditions and no direct host implementation of guest computation.
- Guest-runtime semantic identities supplied by `guest-runtime-and-allocator`
  lower to executable ternary/Malbolge-oriented operations without host callback
  substitution.
- The stage has deterministic input/output form, rejects malformed or
  unsupported input explicitly, and preserves source/profile provenance needed
  downstream.

## Failure Behavior

Malformed IR, unsatisfied proof obligations, impossible layout, or unsupported
profile requirements fail closed before emitting accepted target code.

## Verification

- Expected durable artifact surface: `compiler/`, `src/`, `tests/compiler/`.
- Required evidence: golden/round-trip or normalized stage fixtures,
  deterministic hashes where promised, and end-to-end lowering regression cases.
- Runtime realization evidence: consume guest-runtime semantic identities
  unchanged and prove their executable ternary/Malbolge lowering, including the
  one-time heap startup bind and declaration-only byte-I/O intrinsic symbols.
- Prerequisite completion evidence: `typed-compiler-ir`,
  `guest-runtime-and-allocator`, `malbolge-specific-optimization-mathematics`.
## References

- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Deterministic C Surface And Clang
  Tooling](../adr/deterministic-c-surface-and-clang-tooling.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/verification-trust-boundary.md`
