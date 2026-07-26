# Historical undefined-behavior catalogue

- Status: Proposed
- Planning identity: `historical-undefined-behavior-catalogue`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Historical Compatibility And Malbolge
  Evolution](../adr/historical-compatibility-and-malbolge-evolution.md)

## Purpose

Catalogue one-instruction loading, invalid executable cells, platform-dependent
newline behavior, source validation quirks, and other accidental or undefined C
behavior separately from intended Malbolge semantics.

## Proposed Model

This record defines the contract that implementation must satisfy for
`historical-undefined-behavior-catalogue`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Every known implementation defect or undefined/pathological behavior is
  classified as intended semantics, compatibility quirk, implementation defect,
  or unspecified historical behavior with a regression fixture where
  reproducible.
- The authoritative rule/specification is deterministic, versionable, and does
  not depend on undocumented host behavior.

## Failure Behavior

Missing authority or contradictory configuration fails closed rather than
selecting an implicit repository policy.

## Verification

- Expected durable artifact surface: `tools/malbolge/`,
  `docs/technical/specification/`, `tests/compatibility/`.
- Required evidence: reviewed authority text plus deterministic
  parser/schema/governance tests for the declared boundary.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
