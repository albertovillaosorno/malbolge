# Ahead-of-execution native translation

## Status

Proposed

## Purpose

Translate reachable stable Malbolge regions into native code in memory before
guest execution begins. Use a compact portable micro-IR between Malbolge decode
and architecture-specific code generation, cache verified compiled regions by
program identity, target profile, architecture, and code-state assumptions, and
fall back to ordinary VM execution for regions that cannot yet be proven stable.

## Scope

This document governs the following declared TODO scope:

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`ahead-of-execution-native-translation`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- Only regions whose code-state assumptions are explicit may be compiled before
  execution, and cache keys include every assumption required for safe native
  reuse.
- Observable state, I/O, termination, and diagnostics match the declared
  semantic profile across positive, boundary, and adversarial fixtures.
- Performance conclusions use equivalent workloads and report raw-sample
  provenance, resource budgets, dispersion/uncertainty, and failure/success
  behavior rather than only a best-case number.

## Failure Behavior

Invalid programs, unsupported profiles, or broken native assumptions fail
deterministically without changing guest-visible state silently.

## Verification

- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- Required evidence: semantic fixtures, state/I/O traces where diagnostic, and
  differential results against independent specification-conformant
  implementations; the historical interpreter is compared only on its documented
  agreement domain.
- Prerequisite completion evidence: `tiered-native-execution-engine`,
  `native-x86-64-and-aarch64-backends`,
  `self-modification-state-graph-optimizer`.
- Performance evidence pending: raw measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.
## References

- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
