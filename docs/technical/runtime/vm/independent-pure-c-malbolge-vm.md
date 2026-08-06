# Independent pure C Malbolge VM

## Status

Accepted implementation

## Purpose

Implement a small auditable pure-C VM independently from the stabilized
specification rather than mechanically translating the Rust implementation.

## Scope

This document governs the following declared TODO scope:

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Model

The pure-C VM is a second specification-derived classic implementation and an
independent differential oracle. It is not linked into the Rust VM and does not
inherit Rust transition code, Rust value types, or Rust storage choices.

### Implementation Status

The implementation lives in
`src/runtime/virtual-machine/adapter-outbound/c/malbolge_vm.c` with public
interface
`src/runtime/virtual-machine/adapter-outbound/c/malbolge_vm.h`. It uses fixed
59049-word storage, caller-owned input and
output buffers, no heap allocation, a table-driven ternary crazy operation,
explicit byte semantics, and optional step traces.

Source loading validates the complete admitted source before initializing the
machine. Non-halting execution computes instruction effects and validates the
resulting self-encryption target before committing guest-visible state. A failed
jump to a non-graphical encryption target therefore preserves registers, memory,
input position, and output exactly.

The C design intentionally differs from the Rust representation: classic words
are explicit C integer values in caller-visible state, storage is fixed inside
the machine object, I/O capacity is supplied by the caller, and the ternary
operation is table-driven. The two VMs share only the written specification and
versioned test expectations.

`tests/vm/c_conformance.c` is an executable C harness with a normal `main` entry
point. It also computes semantic signature `0xa9dabd8fc51d13c9`. The Rust
integration suite independently recomputes that signature through the Rust
public
API and requires an exact match.

The C harness is built and executed through the repository validation stack with
the pinned Clang toolchain. Repository-wide Jig validation therefore covers the
independent oracle instead of relying on an undocumented development compiler
path.

## Invariants

- The C VM is independently implemented from the stabilized specification, is
  small enough to audit, and does not mechanically mirror Rust control structure
  or share semantic implementation code.
- Observable state, I/O, termination, and diagnostics match the declared
  semantic profile across positive, boundary, and adversarial fixtures.
- Classic execution uses only words in `0..=59048` and exactly 59049 memory
  cells after source admission.
- Halt skips post-instruction encryption and pointer advancement. A
  non-graphical current cell performs one bounded step with no register, memory,
  input, output, or termination change.
- Invalid post-jump self-encryption targets reject the transition atomically.

## Failure Behavior

Invalid source bytes, invalid source instructions, insufficient recurrence
input,
source overflow, invalid self-encryption targets, and exhausted caller output
capacity return deterministic diagnostic categories. Rejected execution
transitions do not silently commit partial guest-visible effects.

## Verification

- `tests/vm/c_conformance.c` covers word primitives, loader boundaries, the
  normative `ubO` byte-I/O roundtrip fixture, non-graphical non-progress,
  low-byte output,
  EOF, code jumps, post-jump encryption, atomic rejection, rotate, crazy, and
  pointer wrap.
- The C harness asserts semantic signature `0xa9dabd8fc51d13c9` over every
  classic word's rotate result, a deterministic 59049-pair crazy sample, the
  complete loaded `ubO` image, and representative execution boundaries.
- `tests/vm/differential.rs` independently computes the same signature through
  the safe-Rust VM. No C implementation code is called by that Rust test.
- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- The original C source is compared only where its behavior is defined and
  reproducible; undefined host behavior remains a safe failure.
- Prerequisite completion evidence: `canonical-malbolge-target-profile`,
  `historical-malbolge-semantics-specification`.

## References

- [Specification Authority And Malbolge
  Evolution](../../adr/specification-authority-and-malbolge-evolution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
- `docs/technical/adr/verification-trust-boundary.md`
