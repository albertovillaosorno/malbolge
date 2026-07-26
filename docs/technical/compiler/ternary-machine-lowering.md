# Ternary machine lowering

- Status: Proposed
- Planning identity: `ternary-machine-lowering`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Deterministic C Surface And Clang
  Tooling](../adr/deterministic-c-surface-and-clang-tooling.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Lower typed C IR into a compact ternary virtual-machine representation suited to
Malbolge instead of translating C operations directly instruction by
instruction.

## Proposed Model

This record defines the contract that implementation must satisfy for
`ternary-machine-lowering`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Every IR operation lowers to explicit ternary/runtime operations with defined
  pre/postconditions and no direct host implementation of guest computation.
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

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
