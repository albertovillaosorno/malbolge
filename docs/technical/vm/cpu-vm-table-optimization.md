# CPU VM table optimization

- Status: Proposed
- Planning identity: `cpu-vm-table-optimization`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Historical Compatibility And Malbolge
  Evolution](../adr/historical-compatibility-and-malbolge-evolution.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Optimize scalar execution with precomputed rotate tables, position-dependent
decode tables, efficient crazy-operation decomposition, cheap pointer updates,
and benchmarked micro-optimizations without semantic drift.

## Proposed Model

This record defines the contract that implementation must satisfy for
`cpu-vm-table-optimization`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Lookup tables or predecoded forms measurably reduce CPU work while
  exhaustive/property checks prove equality to the scalar rotate/crazy/decode
  definitions.
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
  differential results against the applicable oracle/reference implementation.
- Performance evidence pending: raw measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
