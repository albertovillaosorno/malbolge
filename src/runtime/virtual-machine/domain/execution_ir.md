# Portable execution IR

## Purpose

Own the architecture-neutral, versioned state-changing effect program shared by
future AOT and JIT backends after deterministic verifier admission.

## Owns

- `EffectOp`: one compact verified state transition effect.
- `MemoryLiveIn`: one verifier-derived entry-memory dependency.
- `ProfileExecutionGeometryRequirement`: a validated, portable declaration of
  exact `3^N` execution width/capacity. It deliberately carries no hidden
  verifier input-policy authority.
- `RegionEffectProgram`: profile-bound bounded-region metadata plus ordered
  effects.
- `RegionEffectProgram::from_profile_step_trace()`: exact one-step
  projection from complete normative trace evidence.
- Transport of the VM-owned `TargetProfileRequirement`: canonical version,
  semantic features, word width, and directly addressed profile capacity
  required
  by the artifact. `execution_ir.rs` reuses the semantic type rather than
  duplicating it.
- `EFFECT_IR_VERSION`: the native-supported v3 schema identity.
- `EFFECT_IR_WIDE_PROFILE_VERSION`: portable v4 identity with a `u64` profile
  capacity field.
- `EFFECT_IR_EXECUTION_GEOMETRY_VERSION`: portable v5 identity that retains the
  canonical profile requirement and adds an explicit execution-geometry field.
- `ExecutionGeometryRegionEffectProgram`: v5 trace projection and canonical byte
  transport. No native consumer accepts this type yet.

## Does Not Own

- Malbolge semantics, target-profile requirement semantics, or runtime
  capability preflight.
- Region verification or optimization acceptance.
- x86-64/AArch64 instruction encoding.
- Native cache serialization or executable-memory policy.

## Contents

`execution_ir.rs` defines the product-owned IR surface exported by `malbolge`.
Data in this IR is not trusted by construction: the state-graph verifier remains
responsible for reprojecting and admitting a candidate program before any
accelerated tier may execute it. Tiered and research consumers use the public
package boundary instead of mounting this source through explicit paths.

### Exact one-step trace projection

`RegionEffectProgram::from_profile_step_trace()` converts one successful
normative `ProfileStepTrace` into ordinary one-step IR. Fetch, data, and
encryption reads become one sorted, deduplicated live-in set. Repeated reads of
the same address must agree exactly; missing or inconsistent fetch evidence, a
rejected trace, an already terminated entry, or an outcome/termination mismatch
fails with `StepProgramProjectionError`.

This projection preserves evidence needed by one-step direct admission. It does
not make an arbitrary trace trusted, and it does not reconstruct intermediate
reads from compact regional IR. Callers must obtain complete traces from a
normative or independently admitted VM boundary.

`ProfileExecutionGeometryRequirement` is the non-authoritative portable shape
used by explicit-geometry v5. Its constructor validates exact `3^N` capacity
within the current `u32` execution envelope, while `from_execution_geometry()`
projects only visible width and capacity from the opaque trusted token. The
hidden input-domain proof remains inside `ProfileExecutionGeometry`;
constructing this declarative requirement never grants runtime execution
authority.

Legacy v3/v4 `RegionEffectProgram` projection therefore still rejects derived
traces. `ExecutionGeometryRegionEffectProgram::from_profile_step_trace()`
accepts the same complete trace and binds its exact visible geometry into v5
without changing canonical profile identity.

### Canonical identity encoding v3, v4, and v5

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

`TargetProfileRequirement` carries profile capacity as `u64` in memory so the
semantic/preflight envelope can represent widths beyond the current `u32`
execution backend. Frozen v3 stores that field as `u32` and rejects a wider
envelope with `ProfileMemoryWordsOverflow`. Portable v4 keeps the same field
order but stores profile capacity as little-endian `u64`; unknown versions fail
with `UnsupportedFormatVersion`. Neither path truncates or reinterprets v3.

The encoding never depends on Rust struct layout, enum discriminants, pointer
width, or host endianness. Canonical transport intentionally remains available
for an untrusted envelope whose addresses exceed its declared profile capacity;
that permits deterministic verification and rejection. The separate
`fits_declared_profile_capacity()` predicate classifies this structural
mismatch,
and native identity construction must reject it before cache or artifact
creation.

`tests/execution/fixtures/region-effect-v3.hex` is an independently rendered
415-byte v3 vector and is compared byte-for-byte in `tests/tiered_execution.rs`.
Version 3 adds the immutable target-profile requirement envelope while
preserving
the version-2 rule that profile aliases do not share compiler or cache identity
silently. V4 adds four bytes only to widen profile capacity from `u32` to `u64`;
N21 tests check the exact v4 header, length delta, and wide capacity.

V5 uses the v4 `u64` canonical-profile capacity encoding and then appends the
explicit execution geometry as one `u8` word-trit width plus one little-endian
`u32` memory-word count before the step budget. That pair is validated as exact
`3^N` geometry. V5 projection can therefore carry a QP/N10 trace while its
profile requirement remains current canonical N15. The v5 wrapper is a separate
portable type: native cache, lowering, direct templates, invocation, and
legacy native-continuation APIs still consume only `RegionEffectProgram`.

A separate one-step geometry interpreter handoff may consume v5 only when a
validated checkpoint supplies the opaque geometry token and normative replay
reprojects an exact v5 match. The schema itself therefore never gains execution
authority.

Native cache/artifact identity accepts canonical v3 and v4 bytes, preserving the
IR version as part of exact identity. Native profile metadata follows that
version: MBPF v3 keeps the frozen `u32` capacity field and MBPF v4 carries the
v4 `u64` capacity. The deoptimization-only direct backend can emit and verify
both versions even when v4 declares N21 because its machine code never reads or
writes guest state.

Bootstrap, state-applying direct templates, and native invocation accept either
canonical version when the declared profile capacity fits their `u32`
word/address representation. N21 v4 fails those execution boundaries on
geometry,
not schema version.

Profile capacity is the complete runtime capability required to implement the
selected profile. `RegionEffectProgram::required_memory_words()` separately
derives the minimum region footprint from every C/D observation, memory live-in,
and data/encryption write. The derived `u64` value is not another wire field, so
IR v3 bytes remain unchanged; it can still represent address `u32::MAX` exactly
as 4,294,967,296 required words for `MALBOLGE-PROFILE-002` preflight.
