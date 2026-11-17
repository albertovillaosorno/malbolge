# Portable c2malbolge implementation in C

## Status

Proposed

## Purpose

Keep a path for the essential compiler algorithm to exist in the admitted C
profile without mandatory LLVM runtime, GPU, filesystem complexity, threads, or
other host-only capabilities. Native accelerators remain optional speedups.

## Scope

This document governs the following declared TODO scope:

- `examples/self_host/`
- `compiler/`
- `tests/self_hosting/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`portable-c2malbolge-implementation-in-c`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Bounded Acceptance (2026-11-16)

The portable compiler defines an exact freestanding C subset, versioned
  input/output stream format, finite program/resource limits and explicit
  unsupported errors. No LLVM, GPU API, guest filesystem, threads, new
  programming language or host compiler RPC may perform the essential guest
  translation work.

## Invariants

- The essential compiler algorithm fits the admitted C profile and does not
  require LLVM, GPU APIs, threads, filesystem conveniences, or other host-only
  facilities that prevent eventual self-hosting.
- The portable C implementation is built and exercised natively on a frozen
  admitted-C corpus with input/output and resource bounds. The later guest
  compiler task independently proves execution inside Malbolge; this task
  does not require a compiler that is already self-hosted.

## Failure Behavior

The native portable compiler fails explicitly on unsupported input or
exhausted limits. Later hosted compilation that delegates essential compiler
work to the host is a separate failed self-hosting conformance result.

## Verification

- Expected durable artifact surface: `examples/self_host/`, `compiler/`,
  `tests/self_hosting/`.
- Required evidence: compiler inputs/outputs, canonical comparison against
  native compilation, resource/profile requirements, and verifier acceptance.
- Prerequisite completion evidence: `malbolge-layout-and-encoding-backend`,
  `tools-tidy-lowerability-contract`, `supported-libc-contract`.
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
