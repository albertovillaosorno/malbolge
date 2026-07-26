# Safe Rust Malbolge VM

## Status

Active implementation

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

### Model

The safe-Rust VM is the primary normative classic execution engine. Internal
representation may change without changing observable behavior, the verification
trust boundary, or the authority of the written 1998 specification.

### Implementation Status

The safe-Rust classic VM is implemented under `vm/` with exact ten-trit words,
fixed memory, deterministic loading, byte I/O, atomic single-step transitions,
bounded execution, and optional in-memory trace hooks.

The public trace surface records before/after observations, decoded instruction
bytes, committed I/O, termination, and rejected transition results without
changing guest semantics. Memory-transition correctness remains directly covered
by instruction and atomicity fixtures rather than duplicated by the trace layer.

Independent differential evidence now exists against the separately implemented
pure-C VM. Both implementations compute semantic signature
`0xa74cec75a875c85a` without sharing transition implementation code. The
signature covers word operations, the complete loaded `ctO` memory image, normal
byte I/O and halt, rejected jump atomicity, and non-graphical termination.

The typed TODO remains active until its declared repository-wide validation
command passes at retirement time.

## Invariants

- The Rust VM implements the stabilized state machine without `unsafe`,
  arbitrary historical array assumptions, or host-dependent integer behavior and
  passes the classic specification-conformance corpus.
- Observable state, I/O, termination, and diagnostics match the declared
  semantic profile across positive, boundary, and adversarial fixtures.
- Tracing is observational and cannot alter guest state or execution results.
- The independent C implementation is evidence, not an implementation dependency
  of the Rust VM.

## Failure Behavior

Invalid programs, unsupported profiles, or broken native assumptions fail
deterministically without changing guest-visible state silently. Rejected
transitions expose their diagnostic without partially committing registers,
memory, input consumption, or output.

## Verification

- `tests/vm/` exercises all seven instruction families, no-op behavior, pointer
  wrap, byte/EOF I/O, loader boundaries, bounded execution, self-encryption,
  jump-target encryption, rejected-transition atomicity, and trace hooks.
- `tests/vm/differential.rs` recomputes semantic signature
  `0xa74cec75a875c85a` from the public Rust API.
- `tests/vm/c_conformance.c` independently produces and asserts the same
  signature from the pure-C VM.
- `tests/compatibility/specification/` contains versioned specification fixtures
  for historical disagreement edges and byte-I/O semantics.
- Trace hooks are observational only: traced and untraced executions over the
  same state and input must produce identical outcomes, output, and final state.
- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- The historical interpreter is compared only on its documented agreement
  domain.
- Prerequisite completion evidence: `canonical-malbolge-target-profile`,
  `historical-malbolge-semantics-specification`.

## References

- [Specification Authority And Malbolge
  Evolution](../../adr/specification-authority-and-malbolge-evolution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
- `docs/technical/adr/verification-trust-boundary.md`
