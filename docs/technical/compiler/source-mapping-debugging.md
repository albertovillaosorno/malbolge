# C-level source mapping and debugging

## Status

Proposed

## Purpose

Generate source maps from Malbolge addresses through lowered IR back to C source
locations. Expose debugging at the C level; keep low-level VM tracing primarily
for implementation and verification.

## Scope

This document governs the following declared TODO scope:

- `compiler/`
- `src/`
- `tests/compiler/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`c-level-source-mapping-and-debugging`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Bounded Acceptance (2026-11-16)

- P3 requires deterministic file/function/line/IR-region to target-address
  mapping and usable source diagnostics on a verified compiled C fixture.
  High-level stepping, reconstructed optimized-away variable values, a GUI,
  and an interactive breakpoint protocol are optional future debugger work.

## Invariants

- Source maps preserve admitted C file/function/line/region provenance
  through IR/lowering/layout; diagnostic reconstruction need not expose raw
  A/C/D state. Variable values and stepping are only reported where valid
  verified debug locations survive optimization.
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
- Prerequisite completion evidence: `typed-compiler-ir`,
  `malbolge-layout-and-encoding-backend`.
## References

- [C Level Source Debugging](../adr/c-level-source-debugging.md)
- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)

### Governing ADR Paths

- `docs/technical/adr/c-level-source-debugging.md`
- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
