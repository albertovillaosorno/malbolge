# Machine-checked mathematical correspondence

- Status: Proposed
- Planning identity: `machine-checked-mathematical-correspondence`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)
- [Research Evidence And Algorithm
  Mirror](../../../research/adr/research-evidence-and-algorithm-mirror.md)

## Purpose

Connect mathematical specifications to executable tests or proof tooling so the
`.tex` files are reviewable mathematics rather than decorative documentation.

## Proposed Model

This record defines the contract that implementation must satisfy for
`machine-checked-mathematical-correspondence`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Executable arithmetic/state transitions are checked against the formal
  definitions over exhaustive bounded domains or another explicit
  machine-checked correspondence mechanism.
- Definitions state domains and assumptions precisely; executable code cannot
  claim a mathematical reduction outside those stated preconditions.
- Every correctness-relevant equation or equivalence used by implementation has
  explicit domain assumptions and a traceable executable correspondence check.

## Failure Behavior

A rule outside its stated domain is inapplicable; the implementation may not
extrapolate a proof by convention.

## Verification

- Expected durable artifact surface:
  `docs/technical/specification/mathematics/`, `docs/research/algorithms/`,
  `algorithms/`, `tests/mathematics/`.
- Required evidence: `.tex` definitions/derivations plus exhaustive,
  property-based, or machine-checked correspondence for the admitted domain.
- Mathematical evidence pending: normative/research LaTeX source plus executable
  or machine-checked correspondence for the claimed domain.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
