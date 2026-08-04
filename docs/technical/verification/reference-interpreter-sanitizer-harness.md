# Reference interpreter sanitizer harness

## Status

Proposed

## Purpose

Build the historical interpreter under AddressSanitizer and
UndefinedBehaviorSanitizer where supported, preserve failing fixtures, and use
the evidence to distinguish defined interpreter semantics from host-dependent
or undefined C behavior without editing Ben's source.

## Scope

This document governs the following declared TODO scope:

- `tools/malbolge/`
- `tests/compatibility/`
- `benchmarks/interpreter/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`reference-interpreter-sanitizer-harness`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- The untouched historical interpreter can be built and exercised under
  supported sanitizers, and sanitizer findings are captured as fixtures without
  treating undefined behavior as normative semantics.
- Defined interpreter behavior is authoritative and deterministic; sanitizer
  findings identify non-portable or undefined host behavior.

## Failure Behavior

Missing authority or contradictory configuration fails closed rather than
selecting an implicit repository policy.

## Verification

- Expected durable artifact surface: `tools/malbolge/`, `tests/compatibility/`,
  `benchmarks/interpreter/`.
- Required evidence: reviewed authority text plus deterministic
  parser/schema/governance tests for the declared boundary.
- Prerequisite completion evidence: `historical-interpreter-legal-boundary`,
  `historical-undefined-behavior-catalogue`.
## References

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
- `docs/technical/adr/verification-trust-boundary.md`
