# Scalable Malbolge memory model

## Status

Proposed

## Purpose

Remove the practical 59,049-word ceiling from current Malbolge while retaining
`malbolge-1998` as an exact historical conformance profile. Define a deterministic
ternary scaling model for words, addressing, and memory that can support useful
workloads without inheriting accidental limits from Ben's interpreter or the
host architecture.

## Scope

This document governs the following declared TODO scope:

- `compatibility/`
- `docs/technical/specification/`
- `tests/compatibility/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`scalable-malbolge-memory-model`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- Current Malbolge permits logical addresses beyond 59048 under an explicit
  versioned profile; `malbolge-1998` remains exactly ten-trit and 59,049 words.
- The design evaluates ternary-native generalization (for example a larger trit
  width with correspondingly defined rotate/crazy behavior) and/or explicit
  multiword/paged addressing. It must not inherit host pointer width implicitly.
- Scaling preserves Malbolge's defining ternary arithmetic, crazy operation,
  rotate, self-modification, post-encryption, sequential execution, and
  determinism unless a profile deliberately versions a semantic change.
- Workload evidence, including normalized DOOM requirements, informs practical
  capacities; arbitrary decimal or host-memory multipliers are not authority.

## Failure Behavior

A profile mismatch or unsupported capacity fails with an explicit requirement
diagnostic; neither current nor `malbolge-1998` semantics are guessed.

## Verification

- Expected durable artifact surface: `compatibility/`,
  `docs/technical/specification/`, `tests/compatibility/`.
- Required evidence: `malbolge-1998` specification-conformance corpus plus
  current/profile capacity boundary fixtures and exact diagnostics.
- Prerequisite completion evidence: `canonical-malbolge-target-profile`,
  `safe-rust-malbolge-vm`.
## References

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
