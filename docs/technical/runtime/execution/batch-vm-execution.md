# Batch VM execution

## Status

Active implementation

## Purpose

Execute many independent programs or inputs efficiently on CPU and accelerator
backends for fuzzing, exhaustive verification, synthesis, and search workloads.

## Scope

This document governs the following declared TODO scope:

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`batch-vm-execution`. The implementation may change internal representation or
language choices without changing the observable behavior, trust boundary, or
ownership rules stated by its governing decisions.

### Implementation Status

The first CPU batch execution slice is implemented. Requests own either source
construction inputs or an already constructed `ExecutionMachine`, plus an exact
step budget. The sequential executor is the reference ordering. The parallel
executor uses only host threads over disjoint owned requests, requires an
explicit positive worker count, and reassembles results in original input order.

A per-instance load or machine failure is represented in that instance's
`BatchResult`; it does not terminate the whole batch. Runtime failures retain the
constructed machine so atomic-state evidence remains inspectable. Host worker
panic is a scheduler-level typed error and is never translated into guest
semantics.

Integration tests compare sequential results with worker counts 1, 2, and 8,
including full-memory fingerprints, registers, I/O, termination, run outcome,
and typed diagnostics. Performance/scaling evidence is still pending and no
host-parallel speedup is claimed yet.

## Invariants

- Batch execution preserves per-instance exact semantics and deterministic
  result identity while scaling across independent programs/candidates without
  cross-instance state leakage.
- Observable state, I/O, termination, and diagnostics match the declared
  semantic profile across positive, boundary, and adversarial fixtures.

## Failure Behavior

Invalid programs, unsupported profiles, or broken native assumptions fail
deterministically without changing guest-visible state silently.

## Verification

- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- Required evidence: semantic fixtures, state/I/O traces where diagnostic, and
  differential results against independent specification-conformant
  implementations; the historical interpreter is compared only on its documented
  agreement domain.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`.
## References

- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
