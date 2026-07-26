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
and typed diagnostics.

Post-commit release measurements on `5a01c9c` use 96 independent roundtrip jobs,
a 16-step budget, and 15 raw samples per implementation. On the recorded
12-core/24-thread Xeon E5-2690 v3 host, sequential median time was 55,575,400 ns.
One explicit worker measured 55,930,200 ns (0.99x), exposing thread overhead;
2 workers measured 29,656,900 ns (1.87x), 4 measured 16,569,700 ns (3.35x), and
8 measured 9,839,800 ns (5.65x). Every implementation produced the same
checksum. These data demonstrate this workload on this host only and are not a
portable speedup guarantee.

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
- CPU performance evidence:
  `benchmarks/interpreter/evidence/2026-07-26-batch-windows-x86_64/` contains
  raw samples and exact commit/workload/toolchain/host provenance.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`.
## References

- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
