# Safe Rust Malbolge VM

- Status: Proposed
- Planning identity: `safe-rust-malbolge-vm`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Implement the primary modern VM in safe Rust with explicit errors, deterministic
state transitions, tracing hooks, and instruction-level conformance with the
normative 1998 specification.

## Proposed Model

This record defines the contract that implementation must satisfy for
`safe-rust-malbolge-vm`. The implementation may change internal representation
or language choices without changing the observable behavior, trust boundary, or
ownership rules stated by its governing decisions.

## Invariants

- The Rust VM implements the stabilized state machine without `unsafe`,
  arbitrary historical array assumptions, or host-dependent integer behavior and
  passes the classic specification-conformance corpus.
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
