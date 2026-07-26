# Self-hosting equivalence proof

## Status

Proposed

## Purpose

Compare native and Malbolge-hosted compiler outputs or normalized semantic
artifacts and prove self-hosting does not silently change compilation meaning.

## Scope

This document governs the following declared TODO scope:

- `examples/self_host/`
- `compiler/`
- `tests/self_hosting/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`self-hosting-equivalence-proof`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- Native and Malbolge-hosted compiler outputs are compared by canonical artifact
  identity or a proved semantic normalization across a representative and
  adversarial compiler corpus.
- The hosted stage performs the claimed compilation work inside the guest
  execution model rather than delegating the essential operation to the host.

## Failure Behavior

Hosted compilation that delegates essential compiler work to the host is a
failed conformance result.

## Verification

- Expected durable artifact surface: `examples/self_host/`, `compiler/`,
  `tests/self_hosting/`.
- Required evidence: compiler inputs/outputs, canonical comparison against
  native compilation, resource/profile requirements, and verifier acceptance.
- Prerequisite completion evidence: `malbolge-compiler-compiles-c-to-malbolge`,
  `translation-validation`, `proof-producing-lowering`.
## References

- [Self Hosting As Conformance
  Goal](../../adr/self-hosting-as-conformance-goal.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/self-hosting-as-conformance-goal.md`
- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
- `docs/technical/adr/verification-trust-boundary.md`
