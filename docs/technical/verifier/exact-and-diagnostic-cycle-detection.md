# Exact and diagnostic cycle detection

- Status: Proposed
- Planning identity: `exact-and-diagnostic-cycle-detection`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Provide optional repeated-state detection using collision-safe confirmation for
exact results and clearly label probabilistic hash-only diagnostics.

## Proposed Model

This record defines the contract that implementation must satisfy for
`exact-and-diagnostic-cycle-detection`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

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

- Expected durable artifact surface: `verifier/`, `tests/differential/`,
  `tests/exhaustive/`, `tests/fuzz/`.
- Required evidence: known-valid fixtures, seeded invalid mutations,
  counterexamples for rejected candidates, and deterministic replay.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
