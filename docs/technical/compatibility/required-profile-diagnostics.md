# Required-profile diagnostics

## Status

Active implementation

## Purpose

Fail before unsafe or semantically incorrect execution when an artifact or caller
requires a target profile that the selected runtime cannot implement. Diagnostics
must name the exact profile, version, semantic features, word width, memory
capacity, runtime capability, and missing dimensions without silently falling
back to the classic machine.

When `malbolge-1998` itself is too small for a requested program, the diagnostic
must identify 59,049 words as a historical-profile ceiling rather than presenting
it as a permanent Malbolge language limit.

## Scope

This document currently governs:

- `malbolge.json`
- `scripts/validate/target_profile.py`
- `scripts/validate/profile_requirements.py`
- `vm/src/profile.rs`
- `vm/src/profile_generated.rs`
- `vm/src/execution.rs`
- `tests/test_target_profile.py`
- `tests/vm/profile_requirements.rs`
- `tests/compatibility/test_profile_requirements.py`
- `tests/compatibility/test_scalable_memory.py`

## Current Behavior

### Canonical Profile Projection

`malbolge.json` remains the target-profile authority. Rust does not maintain a
second handwritten copy of profile geometry.

`scripts/validate/target_profile.py` renders
`vm/src/profile_generated.rs` deterministically from the validated canonical JSON.
The checked-in projection contains immutable descriptors for `malbolge-1998`,
`malbolge-2026.1`, and `malbolge-2026.2`. A Python regression test requires the
checked-in Rust source to equal the canonical renderer byte for byte, including
the final rustfmt-compatible layout.

The projection therefore exists for runtime composition and reviewability, not
as independent semantic authority.

### Runtime Capability Envelope

Safe Rust advertises two explicit interpreter capabilities:

- `safe-rust-classic`: maximum 10 trits and 59,049 directly addressed words;
- `safe-rust-profiled`: maximum 14 trits and 4,782,969 directly addressed words.

Both advertise the same defining semantic features: byte input/output, crazy,
deterministic sequential execution, post-instruction encryption, rotate, and
self-modification. Capability identity describes implementation capacity, not a
new language semantic profile.

### Python Consumer Preflight

`scripts/validate/profile_requirements.py` derives immutable requirements from a
fully validated `malbolge.json` document and accepts only an explicit immutable
runtime capability. It does not copy profile geometry into a second authority,
inspect host capacity, select a profile, load an artifact, or execute guest code.

The Python boundary uses the same normative feature order and the same explicit
`safe-rust-classic` and `safe-rust-profiled` envelopes as Rust. It validates the
selected profile's own capacity before runtime capacity, preserves exact
`malbolge-1998`, `malbolge-2026.1`, and `malbolge-2026.2` identities, rejects
unknown IDs without fallback, and emits byte-identical `MALBOLGE-PROFILE-001`
and `MALBOLGE-PROFILE-002` text for the shared reference cases.

The current `malbolge-2026.2` profile therefore fails preflight when explicitly
sent to `ExecutionMachine`/`safe-rust-classic`, but is admitted by
`ProfileMachine`/`safe-rust-profiled`. The retained `malbolge-2026.1` transition
profile is admitted by both normative interpreters while retaining its exact
profile identity.

### Execution Preflight

`ExecutionMachine::from_source()` remains the compatibility-preserving classic
constructor and binds the resulting machine to `malbolge-1998`.

`ExecutionMachine::from_source_for_profile()` requires an explicit canonical
profile descriptor. It performs runtime preflight before invoking the classic
loader. A capability failure therefore has precedence over source-format errors;
an unsupported scalable target cannot reach a loader that only understands the
classic machine.

Every constructed `ExecutionMachine` retains its exact target-profile identity
through `ExecutionMachine::profile()`.

Unknown textual profile IDs return no descriptor. There is no `current-ish`,
nearest-version, or implicit historical fallback.

### Stable Diagnostic Categories

`MALBOLGE-PROFILE-001` means that the selected runtime cannot implement the
selected profile. Its deterministic text names:

- profile ID and version;
- the complete required semantic feature set;
- required word trits and memory words;
- runtime capability ID and its maximum word/memory capacity; and
- the exact missing dimensions.

For `safe-rust-classic` and `malbolge-2026.2`, the missing dimensions are
`word-trits,memory-words`. `safe-rust-profiled` has no missing dimension for that
profile.

`MALBOLGE-PROFILE-002` means that a program requirement exceeds the capacity of
the explicitly selected profile itself. For `malbolge-1998`, the diagnostic
contains `constraint=historical-profile-ceiling` and reports the profile capacity
as 59,049 words.

These categories are distinct: an artifact that exceeds its selected profile is
invalid for that profile even if some runtime could allocate more memory, while
a valid profile may still be unsupported by a particular runtime.

## Invariants

- `malbolge.json` is the semantic authority; generated Rust profile data must be
  a byte-exact deterministic projection.
- Runtime capability is explicit data, never inferred from host pointer width,
  allocator behavior, or accidental integer size.
- Profile-capacity validation happens before runtime-capability validation.
- Runtime-capability validation happens before source loading or execution.
- `malbolge-1998` retains its exact ten-trit/59,049-word historical machine.
- `malbolge-2026.1` and `malbolge-2026.2` retain their immutable identities even
  when two profiles happen to share an implementation capability.
- Unsupported profiles never execute through silent classic fallback.
- The default `ExecutionMachine` constructor remains explicitly classic;
  scalable execution requires explicit `ProfileMachine` selection rather than
  implicit runtime substitution.

## Failure Behavior

Profile requirement failures are deterministic typed errors and leave no machine
state because construction has not yet reached the loader.

A profile unsupported by the selected runtime reports `MALBOLGE-PROFILE-001`.
For example, current Malbolge is unsupported by `safe-rust-classic` but supported
by `safe-rust-profiled`. A request beyond the selected profile's own capacity
reports `MALBOLGE-PROFILE-002`. Unknown profile identities fail lookup instead of
selecting another profile.

Python validation consumers can now construct and preflight the immutable
requirement object without invoking a VM. Compiler artifact metadata, top-level
runtime profile selection, and product consumers do not yet universally carry it.
This contract therefore remains active rather than claiming repository-wide
profile diagnostic completion.

## Verification

- `tests/test_target_profile.py` proves the checked-in Rust projection is
  byte-exactly generated from canonical `malbolge.json`.
- `tests/compatibility/test_profile_requirements.py` verifies immutable Python
  requirement/capability objects, profile-before-runtime precedence, no fallback,
  malformed-input rejection, stable missing-dimension order, and byte-exact Rust
  diagnostic parity for current/classic and historical-capacity failures.
- `tests/vm/profile_requirements.rs` verifies current-profile rejection by the
  classic facade before loading, transition-profile acceptance, classic default
  identity, exact historical-ceiling diagnostics, and no-fallback lookup.
- `tests/vm/profile_machine.rs` verifies `safe-rust-profiled` admits and executes
  the current profile while preserving full 1998 equivalence on historical input.
- `tests/compatibility/test_scalable_memory.py` independently verifies the
  scalable geometry used by the requirement descriptors.
- Strict Clippy and the full Rust suite cover the profile-aware execution facade.
- `jig validate --root .` remains the repository-wide closure gate.

## References

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)
- [Scalable Malbolge memory model](scalable-malbolge-memory-model.md)
- [Canonical Malbolge target profile](../specification/target-profile.md)
- [Safe Rust Malbolge VM](../runtime/vm/safe-rust-malbolge-vm.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
- `docs/technical/adr/verification-trust-boundary.md`
