# Property, fuzz, and exhaustive testing

- Status: Proposed
- Planning identity: `property-fuzz-and-exhaustive-testing`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Use property testing, fuzzing, sanitizers, regression corpora, and exhaustive
finite-domain verification for small functions and VM primitives such as rotate
and crazy operations.

## Proposed Model

This record defines the contract that implementation must satisfy for
`property-fuzz-and-exhaustive-testing`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Generators cover valid/invalid words, instruction positions, crazy/rotate
  arithmetic, self-modification, loader boundaries, and small-state exhaustive
  domains with deterministic shrinking/replay.
- The verifier is tested against valid cases and deliberately mutated invalid
  cases so acceptance and rejection boundaries are evidenced independently.

## Failure Behavior

Unknown or unproved equivalence is rejection or an explicitly bounded result,
never implicit acceptance.

## Verification

- Expected durable artifact surface: `verifier/`, `tests/differential/`,
  `tests/exhaustive/`, `tests/fuzz/`.
- Required evidence: known-valid fixtures, seeded invalid mutations,
  counterexamples for rejected candidates, and deterministic replay.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
