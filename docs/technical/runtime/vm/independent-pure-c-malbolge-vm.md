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
59049-word storage, caller-owned input and output buffers, no library-owned heap
allocation, a table-driven ternary crazy operation, explicit byte semantics,
and optional step traces.

`MalbolgeMachine.memory` alone occupies 118098 bytes because the public word
type is `uint16_t`; the complete machine is larger once registers, pointers, and
length fields are included. Callers must not assume that an automatic local
`MalbolgeMachine` fits a thread or embedded stack. Stack-constrained hosts
should use static-duration storage, a caller-owned arena, or caller-managed heap
storage. The C VM keeps allocation policy with the caller and does not allocate
or free the machine object itself.

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

Public pointer/length pairs fail closed. Non-zero source/input lengths require a
non-null pointer, non-zero output capacity requires non-null output storage, and
source/input/output ranges may not overlap the destination machine object.
Non-empty input and output storage must also be disjoint so guest output cannot
overwrite unread immutable input. These rules prevent initialization from
overwriting bytes that it still needs to consume or from installing
self-referential I/O storage. Checked entry points reject a null machine or
required result pointer with `MALBOLGE_DIAGNOSTIC_INVALID_ARGUMENT`. The void
`malbolge_machine_init_state` helper performs no mutation when its machine,
stream pairing, output pairing, machine-aliasing storage, or fill word is
invalid.

Stepping validates caller-visible state before execution. Registers and fetched
words must remain in the classic `0..=59048` domain; the termination tag must be
one of the declared enum values; input cursor/length and output length/capacity
must be ordered; non-empty stream storage must have a non-null pointer; and the
caller-visible stream ranges must preserve the same machine-disjoint and
input/output-disjoint alias rules enforced at construction. A violation returns
`MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE` before guest state or host I/O is
mutated. Optional trace storage and bounded-run metadata outputs are writable
auxiliary ranges, so they must not alias the machine or its declared streams;
the two bounded-run metadata outputs must also be disjoint. Alias rejection
leaves those auxiliary outputs untouched. Bounded runs count only committed or
terminating semantic steps; a rejected transition returns its diagnostic without
increasing `steps_executed`.

`tests/vm/c_conformance.c` is an executable C harness with a normal `main` entry
point. It also computes semantic signature `0xa9dabd8fc51d13c9`. The Rust
integration suite independently recomputes that signature through the Rust
public API and requires an exact match.

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

Invalid public arguments, invalid source bytes, invalid source instructions,
insufficient recurrence input, source overflow, invalid caller-visible machine
state, invalid self-encryption targets, and exhausted caller output capacity
return deterministic diagnostic categories. Rejected execution transitions do
not silently commit partial guest-visible effects.

## Verification

- `tests/vm/c_conformance.c` covers public null/pointer-pair rejection, machine
  and input/output range alias rejection (plus adjacent-range acceptance),
  trace/run-metadata alias rejection without auxiliary-output mutation, invalid
  caller-visible stream/termination/word state, rejected-run step
  accounting, word primitives, atomic invalid-source admission, loader
  boundaries, the normative `ubO` byte-I/O
  roundtrip fixture, non-graphical non-progress, low-byte output, EOF, code
  jumps, post-jump encryption, atomic rejection, rotate, crazy, and pointer
  wrap.
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
