# Guarded self-modification JIT

## Status

Proposed

## Purpose

Use JIT compilation as a latency-bounded rescue tier for hot mutable code-state
versions absent from verified AOT artifacts. Exact AOT/native-cache hits always
take precedence. Attach explicit guards to assumptions about self-modifying
cells, code/data aliasing, addressing, and control flow.

A failed guard or exhausted compilation budget deoptimizes to the interpreter.
Newly observed
states may become candidates for later specialization or a future AOT build, but
observation alone never grants native execution authority.

## Scope

This document governs the following declared TODO scope:

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`guarded-self-modification-jit`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- Every speculative native specialization has explicit code-state guards and a
  tested deoptimization path that reconstructs an equivalent interpreter state
  on guard failure.
- Exact admitted AOT/native-cache hits suppress duplicate JIT compilation
  for the same semantic and code-state identity.
- Synchronous compilation has an explicit resource/time budget. Exhaustion,
  cancellation, or unsupported specialization falls back to the interpreter.
- Tail latency, compilation/admission cost, and steady-state execution are
  measured separately; no fixed speedup is assumed by this contract.
- Observable state, I/O, termination, and diagnostics match the declared
  semantic profile across positive, boundary, and adversarial fixtures.
- Performance conclusions use equivalent workloads and report raw-sample
  provenance, resource budgets, dispersion/uncertainty, and failure/success
  behavior rather than only a best-case number.

## Failure Behavior

Invalid programs, unsupported profiles, or broken native assumptions fail
deterministically without changing guest-visible state silently.

## Verification

- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- Required evidence: semantic fixtures, state/I/O traces where diagnostic, and
  differential results against independent interpreter-compatible
  implementations; the original C source is compared only where its behavior is
  defined and reproducible.
- Prerequisite completion evidence: `tiered-native-execution-engine`,
  `native-x86-64-and-aarch64-backends`,
  `ahead-of-execution-native-translation`,
  `self-modification-state-graph-optimizer`.
- Performance evidence pending: raw measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.
## References

- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
