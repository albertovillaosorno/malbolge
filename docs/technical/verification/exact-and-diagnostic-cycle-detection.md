# Exact and diagnostic cycle detection

## Status

Accepted implementation

## Purpose

Provide optional repeated-state detection using collision-safe confirmation for
exact results and clearly label probabilistic hash-only diagnostics.

## Scope

This document governs the following implemented surface:

- `src/runtime/virtual-machine/domain/cycle.rs`
- `tests/vm/cycle_detection.rs`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`exact-and-diagnostic-cycle-detection`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

`ExactCycleDetector` retains complete states in candidate-key buckets and
requires full `Eq` confirmation before returning `ExactRepeat`.
`DiagnosticCycleDetector` retains only keys and can return only
`PossibleRepeat`. Both use a stable checked observation sequence and fail before
mutation if its index is exhausted.

## Invariants

- Exact detection proves repeated full semantic state when feasible, while
  diagnostic approximations are clearly labeled and can never claim a proof from
  a lossy state key.
- The verifier is tested against valid cases and deliberately mutated invalid
  cases so acceptance and rejection boundaries are evidenced independently.

## Failure Behavior

Unknown or unproved equivalence is rejection or an explicitly bounded result,
never implicit acceptance.

## Verification

- `tests/vm/cycle_detection.rs` forces two distinct complete classic checkpoints
  into one candidate-key bucket and proves neither collision becomes a repeat.
- Re-observing either exact checkpoint returns its own first-seen index.
- Replaying the same sequence produces byte-for-byte equal classifications.
- The hash-only detector returns `PossibleRepeat`, never `ExactRepeat`.
- Seeded register mutation and profile checkpoints remain distinct under a
  deliberately colliding key until exact state equality is observed.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`.
## References

- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/verification-trust-boundary.md`
