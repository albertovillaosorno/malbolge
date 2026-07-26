# Reference interpreter sanitizer harness

- Status: Proposed
- Planning identity: `reference-interpreter-sanitizer-harness`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Build the historical interpreter under AddressSanitizer and
UndefinedBehaviorSanitizer where supported, preserve failing fixtures, and use
the evidence to distinguish reference semantics from C implementation defects
without editing Ben's source.

## Proposed Model

This record defines the contract that implementation must satisfy for
`reference-interpreter-sanitizer-harness`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- The untouched historical interpreter can be built and exercised under
  supported sanitizers, and sanitizer findings are captured as fixtures without
  treating undefined behavior as normative semantics.
- The authoritative rule/specification is deterministic, versionable, and does
  not depend on undocumented host behavior.

## Failure Behavior

Missing authority or contradictory configuration fails closed rather than
selecting an implicit repository policy.

## Verification

- Expected durable artifact surface: `tools/malbolge/`, `tests/compatibility/`,
  `benchmarks/interpreter/`.
- Required evidence: reviewed authority text plus deterministic
  parser/schema/governance tests for the declared boundary.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
