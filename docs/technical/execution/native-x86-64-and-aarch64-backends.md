# Native x86-64 and AArch64 backends

- Status: Proposed
- Planning identity: `native-x86-64-and-aarch64-backends`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Tiered Native Execution](../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Implement native-code emitters for x86-64 and AArch64 behind one execution-IR
backend contract. Architecture-specific register allocation, instruction
selection, calling conventions, executable-memory handling, instruction-cache
synchronization, and hardening remain adapters rather than VM semantics.

## Proposed Model

This record defines the contract that implementation must satisfy for
`native-x86-64-and-aarch64-backends`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- x86-64 and AArch64 consume the same portable execution IR and independently
  pass cross-backend differential suites including executable-memory and
  instruction-cache edge cases.
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
