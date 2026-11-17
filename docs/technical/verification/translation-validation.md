# Translation validation

## Status

Proposed

## Purpose

Verify compiled programs and blocks against source IR so optimizer and search
components may remain untrusted. Prefer a small deterministic verifier over
trusting a large heuristic backend.

## Scope

This document governs the following declared TODO scope:

- `verifier/`
- `tests/differential/`
- `tests/exhaustive/`
- `tests/fuzz/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`translation-validation`. The implementation may change internal representation
or language choices without changing the observable behavior, trust boundary, or
ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Bounded Acceptance (2026-11-16)

- Verification covers the expressly admitted target profile, supported IR
  operations, and stated local/finite semantics. A checked proof rule or
  bounded exhaustive state obligation may establish equivalence; sampling
  and fuzzing cannot by themselves certify arbitrary looping C semantics.
- An unknown or unproved candidate fails closed before artifact admission.
  Positive and mutated negative fixtures record the accepted assumptions,
  verified state relation and rejected unsound rewrites.

## Invariants

- Each admitted block/program is checked against a stated local or bounded
  source IR relation after optimization; unknown global/unbounded claims are
  rejected, not inferred from finite output samples. An untrusted optimizer
  cannot make an invalid candidate acceptable by its own verdict.
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
- Prerequisite completion evidence: `typed-compiler-ir`,
  `malbolge-layout-and-encoding-backend`, `differential-vm-verification`.
## References

- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/verification-trust-boundary.md`
