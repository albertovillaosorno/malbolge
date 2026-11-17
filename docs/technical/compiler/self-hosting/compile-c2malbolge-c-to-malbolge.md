# Compile c2malbolge.c to Malbolge

## Status

Proposed

## Purpose

Compile the portable C compiler implementation with `c2malbolge` itself and run
the resulting `c2malbolge.malbolge` under the modern VM.

## Scope

This document governs the following declared TODO scope:

- `examples/self_host/`
- `compiler/`
- `tests/self_hosting/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`compile-c2malbolge-c-to-malbolge`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- The native compiler successfully compiles its admitted C implementation into a
  verifier-accepted `c2malbolge.malbolge` with recorded profile/resource
  requirements.
- The verified compiler artifact starts under the normative VM and performs
  one bounded byte-stream startup/exit smoke without delegating compiler work
  to a host service. Translating a fresh C program *inside* the guest is the
  next TODO and is not a prerequisite for this artifact's creation.

## Failure Behavior

A guest artifact that cannot be loaded or started under the declared finite
VM limits is a failed translation/runtime test. A host compiler callback cannot
stand in for guest execution; full hosted translation belongs downstream.

## Verification

- Expected durable artifact surface: `examples/self_host/`, `compiler/`,
  `tests/self_hosting/`.
- Required evidence: compiler inputs/outputs, canonical comparison against
  native compilation, resource/profile requirements, and verifier acceptance.
- Prerequisite completion evidence: `portable-c2malbolge-implementation-in-c`,
  `translation-validation`.
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
