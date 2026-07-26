# Malbolge compiler compiles C to Malbolge

## Status

Proposed

## Purpose

Use `c2malbolge.malbolge` to consume C source and emit a new working `.malbolge`
program, proving practical self-hosting of the translation path.

## Scope

This document governs the following declared TODO scope:

- `examples/self_host/`
- `compiler/`
- `tests/self_hosting/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`malbolge-compiler-compiles-c-to-malbolge`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- Running `c2malbolge.malbolge` inside the VM can consume C source bytes and
  emit a valid `.malbolge` program without invoking the native compiler as a
  hidden host service.
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
- Prerequisite completion evidence: `compile-c2malbolge-c-to-malbolge`,
  `deterministic-binary-byte-stream-runtime`.
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
