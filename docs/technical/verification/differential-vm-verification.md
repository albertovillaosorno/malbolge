# Differential VM verification

## Status

Accepted implementation

## Purpose

Run interpreter-authority fixtures through the Rust VM, independent C VM, and
accelerator VM and compare output, termination, state, mutation, and instruction
traces. Use the preserved original source as primary evidence only where its C
behavior is defined and reproducible; retain prose behavior as explicit
comparison evidence.

## Scope

This document governs the following implemented surface:

- `src/runtime/virtual-machine/domain/differential.rs`
- `tests/vm/differential.rs`
- `tests/vm/cuda_run.rs`
- `tests/vm/cuda_profile_run.rs`
- `tests/differential/classic_profile.rs`
- `tests/test_historical_interpreter_sanitizer.py`

## Current Behavior

### Implemented Differential Surface

The safe Rust VM and independent C VM compute the same classic semantic
signature over arithmetic, loader state, byte I/O, mutation, pointer behavior,
and rejection boundaries. Classic/profiled Rust comparison additionally checks
all 59,049 final words for generated cases. CUDA compact-step and resident
classic/current tests compare complete observable state against normative Rust,
including all memory words for admitted workloads.

The original C interpreter remains bounded to defined and reproducible behavior.
Sanitizer evidence classifies historical undefined behavior rather than turning
it into a comparison result.

### Integrated Candidate Verification

`verify_differential_candidates()` requires at least two labeled observations,
uses the first only as an explicit comparison reference, compares complete
observations with `Eq`, and reports the first mismatching backend pair. It never
infers authority from ordering or accepts hashes/partial projections as proof.

The independent-C semantic signature and full CUDA classic/current snapshots use
this boundary. Tests reject a deliberately mutated C signature and a single
unproved candidate with deterministic backend-aware diagnostics.

## Invariants

- The Rust VM, independent C VM, and accelerator VM agree with defined,
  reproducible original-interpreter behavior on all admitted classic fixtures.
  Undefined C behavior is a typed boundary, not an oracle result.
- The verifier is tested against valid cases and deliberately mutated invalid
  cases so acceptance and rejection boundaries are evidenced independently.

## Failure Behavior

Unknown or unproved equivalence is rejection or an explicitly bounded result,
never implicit acceptance.

## Verification

- Rust and the independent C VM agree on the fixed complete semantic signature.
- A one-bit mutation of the C signature is rejected with exact backend identity.
- A lone candidate is rejected as unproved.
- CUDA classic and current-profile resident batches compare complete checkpoints
  through the same verifier; unavailable CUDA remains an optional-path pass.
- Generated classic/profile cases compare full 59,049-word memory and replay
  deterministically; sanitizer evidence bounds the original interpreter.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`,
  `independent-pure-c-malbolge-vm`, `reference-interpreter-sanitizer-harness`.
## References

- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/verification-trust-boundary.md`
