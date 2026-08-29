# CPU VM table optimization

## Status

Accepted implementation

## Purpose

Optimize scalar execution with precomputed rotate tables, position-dependent
decode tables, efficient crazy-operation decomposition, cheap pointer updates,
and benchmarked micro-optimizations without semantic drift.

## Scope

This document governs the following declared TODO scope:

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`cpu-vm-table-optimization`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

The scalar-table optimization is executable. Build-time generation produces
exact classic rotate and five-trit crazy-chunk tables. The width-generic
`ChunkedProfileWord` reuses the same crazy table chunk by chunk rather than
creating a second wide table.

Position-dependent decode and post-step encryption
use the normative 94-entry translation constants in
`domain/instruction.rs`, avoiding generated composition-owned instruction
semantics. Runtime paths require no dynamic table initialization, and exhaustive
independent tests cover every finite table and translation domain. A custom
release benchmark emits raw scalar/table timing samples with matching

deterministic checksums.

Post-commit measurements on `888b492` retain 15 raw samples per
implementation. On the recorded benchmark host, crazy improved from a
77,456,700 ns scalar median to 7,423,600 ns with tables (10.43x), and rotate
improved from 15,260,300 ns to 10,141,700 ns (1.50x). Checksums match between
scalar and table paths. These are evidence for this implementation on the
identified host, not portable hardware performance claims.

## Invariants

- Lookup tables or predecoded forms measurably reduce CPU work while
  exhaustive/property checks prove equality to the scalar rotate/crazy/decode
  definitions.
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
  differential results against independent interpreter-compatible
  implementations; the original C source is compared only where its behavior is
  defined and reproducible.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`.
- Performance evidence:
  `benchmarks/interpreter/evidence/2026-07-26-windows-x86_64/`
  contains raw samples and exact commit/workload/toolchain/host provenance.
## References

- [Specification Authority And Malbolge
  Evolution](../../adr/specification-authority-and-malbolge-evolution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
- `docs/technical/adr/verification-trust-boundary.md`
