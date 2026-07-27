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

The CPU batch execution layer now has two explicit request/result families.
`BatchRequest`/`BatchResult` retain the classic `ExecutionMachine` surface, while
`ProfileBatchRequest`/`ProfileBatchResult` own canonical-profile source inputs or
an already constructed `ProfileMachine`. Both carry an exact step budget.

Classic and profile-driven APIs share one generic host scheduler. Sequential
execution is the reference ordering. Parallel execution uses only host threads
over disjoint owned requests, requires an explicit positive worker count, and
reassembles results in original input order. Profile identity never comes from a
worker or completion order; it remains attached to each owned request/machine.

A per-instance load or machine failure is represented in that instance's typed
classic/profile result; it does not terminate the whole batch. Runtime failures
retain the constructed machine so atomic-state evidence remains inspectable.
Host worker panic is a shared scheduler-level typed error and is never translated
into guest semantics.

Classic integration tests compare sequential results with worker counts 1, 2,
and 8, including full-memory fingerprints, registers, I/O, termination, run
outcome, and typed diagnostics. Profile-driven tests execute two independent
`malbolge-2026.2` machines plus rejected neighbors through both sequential and
2-worker paths and compare profile identity, sampled memory including addresses
above 59,048, registers, I/O, outcomes, and exact errors.

Post-commit release measurements on `5a01c9c` use 96 independent roundtrip jobs,
a 16-step budget, and 15 raw samples per implementation. On the recorded
12-core/24-thread Xeon E5-2690 v3 host, sequential median time was 55,575,400 ns.
One explicit worker measured 55,930,200 ns (0.99x), exposing thread overhead;
2 workers measured 29,656,900 ns (1.87x), 4 measured 16,569,700 ns (3.35x), and
8 measured 9,839,800 ns (5.65x). Every implementation produced the same
checksum. These data demonstrate this classic workload on this host only and are not a
portable speedup guarantee. They do not establish a current-profile speedup;
profile-driven batching has correctness evidence only until separately measured.

The optional accelerator boundary now has a compact one-step proving layer plus
resident classic and current-profile bounded execution. Each resident CUDA work
item owns one complete profile-sized memory image plus independent registers and
I/O and performs its explicit step budget on device; there is no guest-visible
parallelism or shared guest state. `tests/vm/cuda_run.rs` compares all 59,049
classic words, while `tests/vm/cuda_profile_run.rs` compares all 4,782,969 current
words and complete observable state to normative Rust.

`execute_batch_with_backend` and `execute_profile_batch_with_backend` now expose
hardware-neutral best-effort product routes. Source/profile admission stays on
safe Rust; backends receive immutable prepared-state views, return complete
checkpoints only for successful items, and may defer individual items or the
whole batch. Unavailability, malformed result counts, deferred items, or
inconsistent completion metadata execute from the untouched CPU state instead.
Live integration tests route both classic and current-profile batches through the
real CUDA workers and compare complete results with the sequential CPU baseline.
No current-profile speedup is claimed.

## Invariants

- Batch execution preserves per-instance exact semantics, canonical profile when
  applicable, and deterministic result identity while scaling across independent
  programs/candidates without cross-instance state leakage.
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
- `tests/vm/profile_batch.rs` verifies current 14-trit sequential/parallel batch
  equality, per-item profile identity, errors, I/O, registers, and sampled memory.
- `tests/vm/cuda_step.rs` verifies optional CUDA compact-step equality against
  normative classic `StepTrace` results across every instruction family,
  termination/rejection edges, pointer wrap, and data/encryption aliasing.
- `tests/vm/cuda_run.rs` verifies resident classic bounded execution against
  normative Rust, including all 59,049 final memory words, registers, I/O,
  termination, step counts, resumption, and atomic rejection.
- `tests/vm/cuda_profile_run.rs` verifies resident `malbolge-2026.2` execution
  against normative `ProfileMachine` across eight edge/real-program cases and every
  one of the 4,782,969 final memory words.
- CPU performance evidence for the classic batch path only:
  `benchmarks/interpreter/evidence/2026-07-26-batch-windows-x86_64/` contains
  raw samples and exact commit/workload/toolchain/host provenance.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`.
## References

- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
