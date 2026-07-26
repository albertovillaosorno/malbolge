# Translation validation

- Status: Proposed
- Planning identity: `translation-validation`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Verify compiled programs and blocks against source IR so optimizer and search
components may remain untrusted. Prefer a small deterministic verifier over
trusting a large heuristic backend.

## Proposed Model

This record defines the contract that implementation must satisfy for
`translation-validation`. The implementation may change internal representation
or language choices without changing the observable behavior, trust boundary, or
ownership rules stated by its governing decisions.

## Invariants

- Each compiled block/program is checked against its source IR contract after
  optimization; an untrusted optimizer cannot make an invalid candidate
  acceptable by its own verdict.
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
