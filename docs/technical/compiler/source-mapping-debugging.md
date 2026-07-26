# C-level source mapping and debugging

- Status: Proposed
- Planning identity: `c-level-source-mapping-and-debugging`
- Last reviewed: 2026-07-26

## Governing Decisions

- [C Level Source Debugging](../adr/c-level-source-debugging.md)
- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)

## Purpose

Generate source maps from Malbolge addresses through lowered IR back to C source
locations. Expose debugging at the C level; keep low-level VM tracing primarily
for implementation and verification.

## Proposed Model

This record defines the contract that implementation must satisfy for
`c-level-source-mapping-and-debugging`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Source maps preserve C file/line/function/variable provenance through
  IR/lowering/layout so stepping and diagnostics can reconstruct C-level
  execution without requiring raw A/C/D inspection.
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
