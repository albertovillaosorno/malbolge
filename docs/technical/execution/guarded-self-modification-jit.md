# Guarded self-modification JIT

- Status: Proposed
- Planning identity: `guarded-self-modification-jit`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Tiered Native Execution](../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Compile hot mutable regions after observing their concrete code-state versions.
Attach explicit guards to assumptions about self-modifying cells, code/data
aliasing, addressing, and control flow. A failed guard deoptimizes to the
interpreter, updates the observed state graph, and may create a new
specialization without changing observable Malbolge behavior.

## Proposed Model

This record defines the contract that implementation must satisfy for
`guarded-self-modification-jit`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Every speculative native specialization has explicit code-state guards and a
  tested deoptimization path that reconstructs an equivalent interpreter state
  on guard failure.
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
  differential results against independent specification-conformant
  implementations; the historical interpreter is compared only on its documented
  agreement domain.
- Performance evidence pending: raw measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
