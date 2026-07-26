# Safe Rust Malbolge VM

## Status

Proposed

## Purpose

Implement the primary modern VM in safe Rust with explicit errors, deterministic
state transitions, tracing hooks, and instruction-level conformance with the
normative 1998 specification.

## Scope

This document governs the following declared TODO scope:

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`safe-rust-malbolge-vm`. The implementation may change internal representation
or language choices without changing the observable behavior, trust boundary, or
ownership rules stated by its governing decisions.

### Implementation Status

The first safe-Rust classic VM baseline is implemented under `vm/` with exact
ten-trit words, fixed memory, deterministic loading, byte I/O, atomic
single-step transitions, bounded execution, and optional in-memory trace hooks.
The public trace surface records before/after observations, decoded instruction
bytes, committed I/O, termination, and rejected transition results without
changing guest semantics. Memory-transition correctness remains directly covered
by instruction and atomicity fixtures rather than duplicated by the trace layer.

The TODO remains open while broader independent differential evidence and the
rest of its declared durable evidence surface are completed. In particular, the
future independent pure-C VM must provide an additional specification-derived
oracle rather than inheriting Rust implementation decisions.

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

- `tests/vm/` exercises all seven instruction families, no-op behavior, pointer
  wrap, byte/EOF I/O, loader boundaries, bounded execution, self-encryption,
  jump-target encryption, rejected-transition atomicity, and trace hooks.
- `tests/compatibility/specification/` contains versioned specification fixtures
  for historical disagreement edges and byte-I/O semantics.
- Trace hooks are observational only: traced and untraced executions over the
  same state and input must produce identical outcomes, output, and final state.
- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- Remaining evidence includes differential results against an independently
  implemented specification-conformant VM; the historical interpreter is
  compared only on its documented agreement domain.
- Prerequisite completion evidence: `canonical-malbolge-target-profile`,
  `historical-malbolge-semantics-specification`.
## References

- [Specification Authority And Malbolge
  Evolution](../../adr/specification-authority-and-malbolge-evolution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
- `docs/technical/adr/verification-trust-boundary.md`
