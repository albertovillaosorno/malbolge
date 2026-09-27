# Ternary machine lowering

## Status

Active

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

All declared prerequisites are complete, so implementation may now proceed. No
executable ternary lowering exists yet, and this contract does not claim target
code support before that implementation lands.

### Authoritative Inputs

The first implementation must consume existing identities without renaming or
reinterpreting them:

- canonical compiler state is `malbolge-typed-ir-v1` under ABI
  `malbolge-c32-v1`, preserving the module's exact source and target-profile
  provenance;
- guest-runtime semantics are versioned by `malbolge-guest-runtime-v1`, whose
  current reviewed target profile is `malbolge-2026`;
- compiler-generated startup must realize the one-shot
  `malbolge_guest_runtime_bind_heap` entry before allocation wrappers become
  available to user code;
- byte input and output must realize the exact declaration-only identities
  `malbolge_guest_intrinsic_input_word` and
  `malbolge_guest_intrinsic_output_byte`; and
- the guest-runtime contract's `host_fallback` value is `forbidden`, so none of
  these operations may be replaced by host callbacks in accepted lowering.

No ternary-stage serialization identity is defined yet. The implementation must
introduce one only together with its concrete deterministic representation and
round-trip or normalized golden evidence; this document does not reserve an
unimplemented wire name.

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
