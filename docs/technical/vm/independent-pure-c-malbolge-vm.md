# Independent pure C Malbolge VM

- Status: Proposed
- Planning identity: `independent-pure-c-malbolge-vm`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Implement a small auditable pure-C VM independently from the stabilized
specification rather than mechanically translating the Rust implementation.

## Proposed Model

This record defines the contract that implementation must satisfy for
`independent-pure-c-malbolge-vm`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- The C VM is independently implemented from the stabilized specification, is
  small enough to audit, and does not mechanically mirror Rust control structure
  or share semantic implementation code.
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

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
