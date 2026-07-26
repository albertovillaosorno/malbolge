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
- `vm/src/profile.rs`
- `vm/src/profile_generated.rs`
- `vm/src/execution.rs`
- `tests/test_target_profile.py`
- `tests/vm/profile_requirements.rs`
- `tests/compatibility/`

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

The current safe Rust execution engine advertises one explicit capability:

- runtime ID: `safe-rust-classic`
- maximum word width: 10 trits
- maximum directly addressed memory: 59,049 words
- semantic features: byte input, byte output, crazy operation, deterministic
  execution, post-instruction encryption, rotate, self-modification, and
  sequential guest execution.

The current language profile `malbolge-2026.2` requires 14 trits and 4,782,969
words. The safe Rust classic runtime therefore rejects it before source loading.
The retained `malbolge-2026.1` transition profile has the same ten-trit geometry
and semantic core as the classic runtime and is admitted while retaining its
exact profile identity.

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

For the current safe Rust runtime and `malbolge-2026.2`, the missing dimensions
are `word-trits,memory-words`.

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
- The default safe Rust constructor remains explicitly classic until a separate
  profile-aware top-level runtime owns current-profile selection.

## Failure Behavior

Profile requirement failures are deterministic typed errors and leave no machine
state because construction has not yet reached the loader.

An unsupported current profile reports `MALBOLGE-PROFILE-001`. A request beyond
the selected profile's own capacity reports `MALBOLGE-PROFILE-002`. Unknown
profile identities fail lookup instead of selecting another profile.

Compiler artifact metadata, top-level runtime profile selection, and other
non-VM consumers do not yet universally carry this requirement object. This
contract therefore remains active rather than claiming repository-wide profile
diagnostic completion.

## Verification

- `tests/test_target_profile.py` proves the checked-in Rust projection is
  byte-exactly generated from canonical `malbolge.json`.
- `tests/vm/profile_requirements.rs` verifies current-profile rejection before
  loading, transition-profile acceptance, classic default identity, exact
  historical-ceiling diagnostics, and no-fallback profile lookup.
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
