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
