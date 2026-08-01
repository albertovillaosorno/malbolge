# Portable execution IR

## Purpose

Own the architecture-neutral, versioned state-changing effect program shared by
future AOT and JIT backends after deterministic verifier admission.

## Owns

- `EffectOp`: one compact verified state transition effect.
- `MemoryLiveIn`: one verifier-derived entry-memory dependency.
- `RegionEffectProgram`: profile-bound bounded-region metadata plus ordered
  effects.
- `EFFECT_IR_VERSION`: the portable schema identity.

## Does Not Own

- Malbolge semantics or VM transition rules.
- Region verification or optimization acceptance.
- x86-64/AArch64 instruction encoding.
- Native cache serialization or executable-memory policy.

## Contents

`main.rs` defines the first product-owned IR surface. Data in this IR is not
trusted by construction: the state-graph verifier remains responsible for
reprojecting and admitting a candidate program before any accelerated tier may
execute it. The current research bridge composes this file by explicit Cargo
paths rather than creating a language-shaped crate boundary.

### Canonical identity encoding v2

`RegionEffectProgram::canonical_bytes()` is the byte authority for cache/native
identity. It starts with ASCII `MBIR`, then the `u16` IR version. All integers
use fixed-width little-endian encoding; host-sized counts are first converted to
`u64`; strings and vectors use `u64` length prefixes. Field order is:

1. declared profile ID, canonical profile fingerprint, and semantic step
   budget;
2. bounded `RunOutcome` tag/reason/step count;
3. verifier-ordered memory live-ins as `(address, value)` `u32` pairs;
4. ordered effects, each containing before/after observations, input/output
   tags, and data/encryption memory-write options.

The encoding never depends on Rust struct layout, enum discriminants, pointer
width, or host endianness. `tests/execution/fixtures/region-effect-v2.hex` is an
independently rendered 209-byte v2 vector and is compared byte-for-byte in
`tests/tiered_execution.rs`. Version 2 prevents a profile alias with an unchanged
fingerprint from sharing compiler or cache identity silently.
