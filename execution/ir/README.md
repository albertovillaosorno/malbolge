# Portable execution IR

## Purpose

Own the architecture-neutral, versioned state-changing effect program shared by
future AOT and JIT backends after deterministic verifier admission.

## Owns

- `EffectOp`: one compact verified state transition effect.
- `MemoryLiveIn`: one verifier-derived entry-memory dependency.
- `RegionEffectProgram`: profile-bound bounded-region metadata plus ordered
  effects.
- Transport of the VM-owned `TargetProfileRequirement`: canonical version,
  semantic features, word width, and directly addressed profile capacity required
  by the artifact. `main.rs` re-exports the semantic type rather than duplicating
  it.
- `EFFECT_IR_VERSION`: the portable schema identity.

## Does Not Own

- Malbolge semantics, target-profile requirement semantics, or runtime
  capability preflight.
- Region verification or optimization acceptance.
- x86-64/AArch64 instruction encoding.
- Native cache serialization or executable-memory policy.

## Contents

`main.rs` defines the first product-owned IR surface. Data in this IR is not
trusted by construction: the state-graph verifier remains responsible for
reprojecting and admitting a candidate program before any accelerated tier may
execute it. The current research bridge composes this file by explicit Cargo
paths rather than creating a language-shaped crate boundary.

### Canonical identity encoding v3

`RegionEffectProgram::canonical_bytes()` is the byte authority for cache/native
identity. It starts with ASCII `MBIR`, then the `u16` IR version. All integers
use fixed-width little-endian encoding; host-sized counts are first converted to
`u64`; strings and vectors use `u64` length prefixes. Field order is:

1. declared profile ID and canonical profile fingerprint;
2. published profile version, ordered semantic features, word trits, and profile
   memory capacity;
3. semantic step budget and bounded `RunOutcome` tag/reason/step count;
4. verifier-ordered memory live-ins as `(address, value)` `u32` pairs;
5. ordered effects, each containing before/after observations, input/output
   tags, and data/encryption memory-write options.

The encoding never depends on Rust struct layout, enum discriminants, pointer
width, or host endianness. `tests/execution/fixtures/region-effect-v3.hex` is an
independently rendered 415-byte v3 vector and is compared byte-for-byte in
`tests/tiered_execution.rs`. Version 3 adds the immutable target-profile
requirement envelope while preserving the version-2 rule that profile aliases do
not share compiler or cache identity silently.

Profile capacity is the complete runtime capability required to implement the
selected profile. It is not the program-specific requested-memory value used by
the separate profile-capacity diagnostic.
