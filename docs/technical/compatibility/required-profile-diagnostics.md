# Required-profile diagnostics

## Status

Active implementation

## Purpose

Fail before unsafe or semantically incorrect execution when an artifact or
caller
requires a target profile that the selected runtime cannot implement.
Diagnostics
must name the exact profile, version, semantic features, word width, memory
capacity, runtime capability, and missing dimensions without silently falling
back to the classic machine.

When `malbolge-1998` itself is too small for a requested program, the diagnostic
must identify 59,049 words as a historical-profile ceiling rather than
presenting
it as a permanent Malbolge language limit.

## Scope

This document currently governs:

- `malbolge.json`
- `src/automation/repository/composition/scripts/validate/target_profile.py`
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
- `src/automation/repository/composition/scripts/validate/profile_requirements.py`
- `src/runtime/virtual-machine/domain/profile.rs`
- `src/runtime/virtual-machine/domain/profile_generated.rs`
- `src/runtime/virtual-machine/domain/execution.rs`
- `src/runtime/virtual-machine/domain/execution_ir.rs`
- `src/runtime/virtual-machine/domain/loader.rs`
- `src/runtime/virtual-machine/domain/profile_machine.rs`
- `src/interface/command-line/composition/main.rs`
- `tests/test_target_profile.py`
- `tests/cli_malbolge.rs`
- `tests/vm/profile_requirements.rs`
- `tests/tiered_execution.rs`
- `tests/compatibility/test_profile_requirements.py`
- `tests/compatibility/test_scalable_memory.py`

## Current Behavior

### Canonical Profile Projection

`malbolge.json` remains the target-profile authority. Rust does not maintain a
second handwritten copy of profile geometry.

`src/automation/repository/composition/scripts/validate/target_profile.py`
renders
`src/runtime/virtual-machine/domain/profile_generated.rs` deterministically
from the validated canonical JSON.
The checked-in projection contains immutable descriptors for `malbolge-1998`,
`malbolge-2026`, `malbolge-2026.1`, `malbolge-2026.2`, and
`malbolge-2026.3`. A Python
regression test requires the
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

`src/automation/repository/composition/scripts/validate/profile_requirements.py`
derives immutable requirements from a
fully validated `malbolge.json` document and accepts only an explicit immutable
runtime capability. It does not copy profile geometry into a second authority,
inspect host capacity, select a profile, load an artifact, or execute guest
code.

The Python boundary uses the same normative feature order and the same explicit
`safe-rust-classic` and `safe-rust-profiled` envelopes as Rust. It validates the
selected profile's own capacity before runtime capacity, preserves exact
`malbolge-1998`, `malbolge-2026`, `malbolge-2026.1`, `malbolge-2026.2`, and
`malbolge-2026.3` identities, rejects
unknown IDs without fallback, and emits byte-identical `MALBOLGE-PROFILE-001`
and `MALBOLGE-PROFILE-002` text for the shared reference cases. Direct public
error construction validates the exact error enum, immutable canonical missing
dimensions, a real rejected requirement/runtime pair, and profile-capacity
precedence before rendering diagnostic text. Public requirement objects are
re-resolved against canonical `malbolge.json` during preflight: profile kind,
version, word width, memory capacity, and normative features must still match
the declared profile identity exactly. Only the program-specific required-memory
footprint may vary within that canonical profile capacity; zero is a valid
footprint for an empty region/source preflight, while profile/runtime capacities
remain strictly positive. Reserved Python
runtime identities are revalidated too: `safe-rust-classic` and
`safe-rust-profiled` cannot be reused with forged feature, word, or memory
capabilities. Canonical authority re-resolution maps unreadable or invalid
`malbolge.json` state into `ProfileRequirementValidationError`, so direct
preflight never leaks raw filesystem or target-profile parser exceptions.
Canonical profile parsing admits the top-level mapping and public
JSON/path input types before iteration, JSON decoding, or pathlib access. Named
profile IDs are validated before dictionary lookup or hashing, and runtime
feature members are type-checked before duplicate hashing. These direct input
failures therefore remain typed profile validation errors rather than raw Python
exceptions. The profiled runtime limit is implementation capacity, so it
stays
at 14 trits and 4,782,969 words even if a future canonical current profile
selects a larger valid geometry. Explicitly named external runtime identities
may still carry their own validated envelopes.

The current `malbolge-2026` profile therefore fails preflight when explicitly
sent to `ExecutionMachine`/`safe-rust-classic`, but is admitted by
`ProfileMachine`/`safe-rust-profiled`. The retained `malbolge-2026.1` transition
profile is admitted by both normative interpreters while retaining its exact
profile identity.

### Execution Preflight

`ExecutionMachine::from_source()` remains the compatibility-preserving classic
constructor and binds the resulting machine to `malbolge-1998`.

`ExecutionMachine::from_source_for_profile()` requires an explicit canonical
profile descriptor. Before lexical or instruction admission, the loader-owned
source counter derives the exact number of non-whitespace program words using
the same six C-locale whitespace bytes as source loading. Canonical profile
preflight then checks program capacity first and runtime capability second. A
source that needs 59,050 words under `malbolge-1998` therefore emits
`MALBOLGE-PROFILE-002` even when a later source byte would also be invalid;
whitespace does not consume profile memory.

`ProfileMachine::from_source()` uses the same source-word requirement before its
profile-width loader. The raw `.malbolge` CLI constructs its historical
interpreter through `ExecutionMachine`, while recognized capsules dispatch
through `ProfileMachine` using the capsule-selected profile. Both product paths
therefore preserve `MALBOLGE-PROFILE-002` before loader admission; a historical
capsule with 59,050 payload words retains `historical-profile-ceiling` and the
exact required-memory count.

Every constructed `ExecutionMachine` retains its exact target-profile identity
through `ExecutionMachine::profile()`.

Unknown textual profile IDs return no descriptor. There is no `current-ish`,
nearest-version, or implicit historical fallback.

### Portable Artifact Preflight

`TargetProfileRequirement` is now VM-owned semantic data and is re-exported by
`src/runtime/virtual-machine/domain/execution_ir.rs` for transport in effect
IR. It
carries the published
version, stable feature IDs, word trits, and profile capacity without copying
the
canonical profile registry into the execution layer.

`preflight_runtime_requirement()` consumes an independently admitted profile ID
and requirement envelope plus one explicit `RuntimeCapability`. It shares the
same geometry comparison and `MALBOLGE-PROFILE-001` formatter as canonical
descriptor preflight. The current-profile envelope is therefore rejected by
`safe-rust-classic` with byte-identical text and accepted by
`safe-rust-profiled`. An unknown feature ID fails closed and is surfaced in the
stable `missing=` list.

`preflight_portable_profile_requirement()` additionally accepts an exact `u64`
program-memory requirement, including zero. It checks that value against profile
capacity before
runtime capability and emits the same `MALBOLGE-PROFILE-002` text as canonical
preflight, including `historical-profile-ceiling` for `malbolge-1998`.
`RegionEffectProgram::required_memory_words()` derives this value from every C/D
observation, live-in, and write without adding another IR wire field.

This boundary does not prove that an arbitrary envelope is canonical. Profile
ID/fingerprint and requirement equality remain the responsibility of capsule,
verifier, cache-key, and COFF admission before runtime preflight.

The direct-template selector now invokes the combined preflight before host
validation or backend construction. Program capacity has precedence over runtime
capability, which has precedence over host/backend selection. Neither `002` nor
`001` is converted to a deopt artifact.

Bootstrap C23 source generation now exposes the same product-facing ordering
through `lower_preflighted_clang_c23()`. The transported requirement must first
be canonical for its exact declared profile ID; combined portable preflight then
checks program capacity before runtime capability, and bootstrap target
validation/rendering happens only after those gates pass. Raw
`lower_clang_c23()` intentionally remains an untrusted lowering surface so
verifier-rejection and transport tests can still construct invalid candidates.
An admitted preflighted result is byte-identical to raw lowering for the same
program/target. The sibling `compile_preflighted_clang_c23()` process adapter is
the product-owned external compiler boundary: it performs that same profile
admission before spawning Clang, streams deterministic C23 over stdin, captures
opaque object bytes from stdout, and never exposes a raw-unpreflighted compile
entry point. Missing-compiler tests prove canonical `002` and `001` text wins
before launch failure; admitted work reaches a typed launch error instead.

### Stable Diagnostic Categories

`MALBOLGE-PROFILE-001` means that the selected runtime cannot implement the
selected profile. Its deterministic text names:

- profile ID and version;
- the complete required semantic feature set;
- required word trits and memory words;
- runtime capability ID and its maximum word/memory capacity; and
- the exact missing dimensions.

For `safe-rust-classic` and `malbolge-2026`, the missing dimensions are
`word-trits,memory-words`. `safe-rust-profiled` has no missing dimension for
that
profile.

`MALBOLGE-PROFILE-002` means that a program requirement exceeds the capacity of
the explicitly selected profile itself. For `malbolge-1998`, the diagnostic
contains `constraint=historical-profile-ceiling` and reports the profile
capacity
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
- Source program-capacity validation happens before runtime-capability
  validation, lexical admission, or execution.
- Runtime-capability validation happens before source loading or execution.
- `malbolge-1998` retains its exact ten-trit/59,049-word historical machine.
- `malbolge-2026`, `malbolge-2026.1`, `malbolge-2026.2`, and
  `malbolge-2026.3` retain their
  immutable identities even when profiles happen to share an implementation
  capability; only the registry `kind` role may advance without changing an
  existing fingerprint.
- Unsupported profiles never execute through silent classic fallback.
- The default `ExecutionMachine` constructor remains explicitly classic;
  scalable execution requires explicit `ProfileMachine` selection rather than
  implicit runtime substitution.

## Failure Behavior

Profile requirement failures are deterministic typed errors and leave no machine
state because construction has not yet reached the loader.

A profile unsupported by the selected runtime reports `MALBOLGE-PROFILE-001`.
For example, current Malbolge is unsupported by `safe-rust-classic` but
supported
by `safe-rust-profiled`. A request beyond the selected profile's own capacity
reports `MALBOLGE-PROFILE-002`. Unknown profile identities fail lookup instead
of
selecting another profile.

Python validation consumers can construct and preflight the immutable
requirement object without invoking a VM. Portable effect IR v3, native keys,
and
direct COFF `MBPF` v3 metadata carry the canonical published version, stable
features, word trits, profile capacity, and exact derived region memory
alongside
ID/fingerprint. Safe Rust
can now consume an independently admitted envelope against either explicit
runtime capability without reloading the profile document.

Effect IR now derives the exact region-specific memory requirement needed to
distinguish `MALBOLGE-PROFILE-002`, including the full `u32` address domain.
Although raw IR remains serializable for deterministic rejection,
`RegionEffectIdentity` and `NativeArtifactKey` reject a footprint beyond the
embedded profile capacity before bootstrap or direct artifact construction.
Direct `MBPF` v3 objects additionally retain that exact footprint, so structural
admission detects same-profile object/key disagreement before runtime preflight.
The preflighted tier planner then maps unsupported direct host format to the
interpreter only after combined profile preflight; `002` and `001` are never
converted to fallback. Its cache-aware form performs the same profile and
explicit
`DirectHost` checks before exact-key lookup. A populated verified-direct cache
cannot bypass either diagnostic, and profile/interpreter outcomes do not mutate
cache cardinality. Native-retry planning also keeps profile failure hard: it
retains the stable retry step/index category while snapshotting exact canonical
profile text before taking ownership of the suspension. The owned planning
failure therefore renders the same diagnostic as direct sequence preflight
instead of degrading it to a generic `profile` label. Retry routing preserves
the same owned snapshot, and retry-cycle hard routing failure retains that
routing object without touching native mappings or runner state. The cache-aware
routing-cycle owner delegates direct profile-diagnostic access and `Display` to
that retained routing failure. A legitimate retry suffix cannot newly produce
`MALBOLGE-PROFILE-002`: every `NativeRetry` suspension owns a suffix of an
already published `VerifiedDirectSequencePlan`, and sequence publication
preflights every immutable step against its selected profile capacity. A focused
regression rejects a capacity-overflow step as `002` before plan publication.
Other artifact families do not yet universally expose an equivalent program
requirement. Raw and capsule `.malbolge` product invocation use canonical source
preflight, and bootstrap source generation plus external Clang compilation have
explicit combined portable preflight. Durable-cache/AOT/JIT execution and the
remaining product/artifact paths do not yet universally invoke that boundary.
This contract therefore remains active rather than claiming repository-wide
profile diagnostic completion.

## Verification

- `tests/test_target_profile.py` proves the checked-in Rust projection is
  byte-exactly generated from canonical `malbolge.json`.
- `tests/compatibility/test_profile_requirements.py` verifies immutable Python
  requirement/capability objects, profile-before-runtime precedence, no
  fallback,
  malformed-input rejection, stable missing-dimension order, and byte-exact Rust
  diagnostic parity for current/classic and historical-capacity failures.
- `tests/vm/profile_requirements.rs` verifies current-profile rejection by the
  classic facade before loading, exact source-word capacity before loader
  errors, canonical whitespace non-consumption, profiled-source parity,
  transition-profile acceptance, classic default identity, exact
  historical-ceiling diagnostics, portable/canonical `001` and `002` parity,
  explicit profiled-runtime acceptance, unknown-feature rejection, and
  no-fallback lookup.
- `tests/cli_malbolge.rs` proves an oversized raw historical source surfaces
  `MALBOLGE-PROFILE-002` with `historical-profile-ceiling` while normal raw
  interpreter-authority output remains unchanged. `tests/cli_capsule.rs` proves
  the same capacity diagnostic after successful historical capsule parsing and
  before payload loading, so capsule dispatch cannot bypass profile preflight.
- `tests/tiered_execution.rs` proves exact derived IR footprint, including
  `u32::MAX`, native-identity rejection of inconsistent capacity, `MBPF` v3
  footprint mismatch rejection, emitter propagation, direct-template precedence
  `002` then `001` then host/backend, the same precedence before verified direct
  cache lookup without cache mutation on rejection/interpreter selection,
  native-retry preservation of exact `MALBOLGE-PROFILE-001` text across owned
  planning, routing, retry-cycle hard failure, and the outer cache-aware routing
  owner, plus byte-identical `002`/`001` precedence before external Clang
  launch. The same
  suite compiles real x86-64/AArch64 COFF through the product compiler adapter.
- `tests/vm/profile_machine.rs` verifies `safe-rust-profiled` admits and
  executes
  the current profile while preserving full 1998 equivalence on historical
  input.
- `tests/compatibility/test_scalable_memory.py` independently verifies the
  scalable geometry used by the requirement descriptors.
- Strict Clippy and the full Rust suite cover the profile-aware execution
  facade.
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
