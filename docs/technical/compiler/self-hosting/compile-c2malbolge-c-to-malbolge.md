# Compile c2malbolge.c to Malbolge

- Status: Proposed
- Planning identity: `compile-c2malbolge-c-to-malbolge`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Self Hosting As Conformance
  Goal](../../adr/self-hosting-as-conformance-goal.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

## Purpose

Compile the portable C compiler implementation with `c2malbolge` itself and run
the resulting `c2malbolge.malbolge` under the modern VM.

## Proposed Model

This record defines the contract that implementation must satisfy for
`compile-c2malbolge-c-to-malbolge`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- The native compiler successfully compiles its admitted C implementation into a
  verifier-accepted `c2malbolge.malbolge` with recorded profile/resource
  requirements.
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

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
