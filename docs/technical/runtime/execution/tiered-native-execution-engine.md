# Tiered native execution engine

## Status

Active implementation

## Purpose

Build a tiered execution engine instead of choosing between interpretation, AOT,
and JIT. Decode Malbolge into a compact execution IR, simplify that IR through
verified state-graph mathematics, compile demonstrably stable regions to native
machine code before execution, specialize hot or mutation-sensitive regions at
runtime, and deoptimize safely to the interpreter whenever a code-version guard
or speculative assumption fails. The normative VM contract remains the semantic
baseline; native tiers are accelerators of identical observable behavior.

## Scope

This document governs the following declared TODO scope:

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Implemented Foundation

`execution/ir/main.rs` now owns portable effect IR v3 as product code. It
defines `EffectOp`, `MemoryLiveIn`, and `RegionEffectProgram`, and re-exports the
VM-owned `TargetProfileRequirement` under the existing responsibility-oriented
topology. Cargo composition uses explicit paths rather than introducing a
language-shaped crate boundary.

State-graph verification projects normative `ProfileStepTrace` records into that
IR only after exact region verification. An untrusted portable artifact must
match IR version, exact declared profile ID, canonical profile fingerprint,
published profile version, stable semantic features, word trits, profile
capacity, verifier-derived live-ins, semantic-step budget, bounded outcome, and
every state-changing effect before a verified artifact exists. Guard hits apply
only admitted effects. Guard misses
run the normative `ProfileMachine` for the same verified budget and reconstruct
the incremental lineage from real traces; typed VM rejection propagates
unchanged.

`vm/src/profile.rs` now owns the portable requirement type and
`preflight_runtime_requirement()`. Given an independently admitted profile ID and
envelope, it compares word width, profile capacity, and every declared semantic
feature with an explicit `RuntimeCapability`. Current-profile IR is rejected by
`safe-rust-classic` with byte-identical `MALBOLGE-PROFILE-001` text to canonical
descriptor preflight and accepted by `safe-rust-profiled`; unknown feature IDs
fail closed and are named in `missing=`. This consumes artifact metadata without
reloading `malbolge.json`, but does not replace profile identity/fingerprint or
verifier admission.

`execution/cache/main.rs` now owns collision-safe native artifact identity and
caller-owned process-local reuse storage. `RegionEffectProgram` has a versioned
layout-independent canonical byte encoding, frozen by an independently rendered
fixture. Raw canonical transport may preserve a profile-capacity-inconsistent
untrusted envelope for deterministic rejection, but `RegionEffectIdentity` and
`NativeArtifactKey` return typed `NativeIdentityError::ProfileCapacity` before
hashing or artifact construction. Native keys retain the exact profile
ID/fingerprint plus the canonical requirement envelope and additionally bind host
OS, x86-64/AArch64 ISA, backend identity/revision, native ABI revision, and sorted
required features. `NativeArtifactCache<Value>` uses FNV-1a only to choose a
bucket, then confirms full key equality for lookup, replacement, and removal.
Forced-collision entries remain independent. The store performs no persistence,
eviction, synchronization, or semantic admission.

`execution/native/main.rs` now owns the first host-code artifact boundary. The
bootstrap backend lowers one structurally consistent `RegionEffectProgram` into
deterministic freestanding C23 and binds the candidate to the exact
`NativeArtifactKey`. Generated code performs all entry-observation, memory,
input/EOF, pointer, and output-capacity checks before any guest-visible commit.
Repeated writes to one address collapse to its first required value and final
committed value, so a guard miss cannot leave an intermediate region state.

Pinned Clang 22.1.8 materializes the same bootstrap representation as real
Windows COFF objects for both x86-64 and AArch64 under strict warning-clean C23
compilation. Source and object containers remain explicitly `Untrusted*`:
matching IR/target identity proves provenance of the claim, not semantic
correctness of compiler-produced machine code.

`execution/native/profile_metadata.rs` is the single private owner of the
format-neutral `MBPF` v3 payload. Bootstrap source rendering, direct object
construction, and COFF admission consume that encoding without making the parser
or either emitter authoritative over the schema.

`execution/native/coff.rs` now provides a second, independent structural gate for
those Windows objects. It parses COFF bytes directly in safe Rust rather than
trusting Clang/LLVM diagnostics, requires machine identity to match the native
key, requires exactly one executable/non-writable `.text` section and the exact
`malbolge_native_region_apply` external function, rejects unexpected external
functions or undefined external symbols, and admits relocations only when their
targets are defined inside the same object. ARM64's compiler-generated `.rdata`
constant relocations therefore remain valid while host-library dependencies fail
closed. Direct backends and `clang-c23-bootstrap` revision 2 additionally
require one initialized, read-only, non-relocated `.mbprof` section. Its `MBPF` v3
payload must match the profile ID, fingerprint, published version, stable features,
word trits, profile capacity, and exact derived `u64` region memory requirement
retained by the native key. Missing or mismatched required metadata, including a
same-profile footprint mismatch, fails before semantic admission. Bootstrap
revision-2 C23 source renders the canonical bytes through a read-only custom-section
declaration; historical revision 1 remains legal without the section. The pinned
Clang test remains responsible for cross-ISA compiled-object confirmation. The
result is named `StructurallyAdmittedNativeObjectArtifact`; it still has no
semantic execution authority.

`execution/native/direct.rs` now crosses that semantic boundary for one minimal
native program only: a direct deoptimization stub. The x86-64 sequence is
`mov eax, 1; ret`; the AArch64 sequence is `mov w0, #1; ret`. Both are wrapped in
a deterministic minimal COFF object with timestamp zero, one executable `.text`,
one read-only `.mbprof`, one external entry symbol, and no relocations.
Independent hex fixtures freeze the complete 413-byte x86-64 and 415-byte
AArch64 revision-4 objects. Promotion to
`VerifiedDeoptNativeObjectArtifact` first requires structural COFF admission and
then exact equality with the canonical object bytes. A changed opcode can remain
structurally valid but is rejected semantically.

This verified stub never reads the state argument, never commits guest-visible
state, and always returns native guard-miss status `1`, forcing deterministic
deoptimization to the normative interpreter. It is therefore the first
semantically admitted native artifact but intentionally provides no acceleration.
Development evidence links both ISA objects and executes the x86-64 DLL with a
null state pointer, returning `1`; direct region-effect fast paths remain open.

The next reviewed template is `direct-initial-halt`. Admission requires an exact
one-effect IR: zero entry registers/input/output counters, no input/output
effect, no memory live-ins or writes, no prior termination, unchanged exit
observation except `HaltInstruction`, terminated one-step outcome, and budget
one. Both ISAs preflight the ABI state before committing only the termination
byte. Complete COFF fixtures freeze the generated objects and object-byte
tampering fails semantic admission after structural COFF acceptance. Development
evidence links both ISA objects; x86-64 execution proves valid state returns
`applied=0` with only termination changed, while accumulator mismatch and null
state return guard miss without mutation. This is the first accelerated
state-applying native subset; all other IR still requires deopt/bootstrap/VM.

`select_verified_direct_native()` now removes direct-backend identity selection
from callers and requires one explicit `RuntimeCapability`. It derives the exact
region memory footprint from the IR and checks profile capacity before runtime
capability, host validation, or backend construction. Out-of-profile addressing
returns typed `MALBOLGE-PROFILE-002`; otherwise current-profile IR under
`safe-rust-classic` returns the byte-identical `MALBOLGE-PROFILE-001` diagnostic.
Even when the host format is also unsupported, no native object or deopt fallback
is constructed.

After program/profile/runtime admission, it classifies IR from narrowest to
broadest:
zero-register halt uses `direct-initial-halt`, other eligible one-step halts use
`direct-halt-registers`, and otherwise the selector emits/verifies direct deopt.
Only admitted program shape controls this fallback; profile, emission, or
admission errors are propagated rather than silently retried. Non-Windows host
formats fail explicitly because direct ELF/Mach-O templates do not exist yet.

The two state-applying emitter/verifier pairs independently repeat the
profile-capacity shape check. A caller bypassing the selector cannot semantically
promote an initial-halt or register-halt object whose IR footprint exceeds its
embedded profile envelope.

`select_preflighted_execution_tier()` is the first planning boundary above direct
selection. It maps only top-level direct `TargetFormat` absence to the normative
interpreter after profile preflight. Windows returns the exact verified direct
artifact; `MALBOLGE-PROFILE-002`, `MALBOLGE-PROFILE-001`, and any backend,
emission, or admission failure remain errors. This boundary performs no cache
lookup, executable-memory policy, linking, or invocation.

`select_cached_preflighted_execution_tier()` adds exact process-local reuse without
weakening those gates. One explicit `DirectHost` plus runtime capability is
preflighted before lookup. A private `PreparedDirectTarget` binds specialization
and exact `NativeArtifactKey`. The same prepared key selects the bucket and is
consumed by miss emission, eliminating a second IR canonicalization at that
boundary. State-applying semantic verifiers continue reconstructing their expected
key independently from IR before promotion. `VerifiedDirectNativeCache` privately
wraps the generic cache and accepts values only through successful direct emission
and semantic admission. Results distinguish `Inserted` from full-key `Hit`; all
three current templates match uncached selection byte-for-byte and reuse the same
immutable `Arc` allocation rather than cloning verified object bytes. A populated
cache cannot bypass `002`, `001`, or non-Windows interpreter selection, and those
outcomes leave cache cardinality unchanged. Exact invalidation removes the
full-equality key from future lookup without revoking outstanding `Arc` plans; a
later request reinserts the same key/bytes under a distinct allocation. `Arc`
provides shared immutable ownership only. Durable storage, automatic eviction,
synchronization policy, linking, executable memory, invocation, and performance
policy remain outside.

### Remaining Implementation

Semantic admission beyond the deopt and one-step halt template family, general
direct accelerated x86-64/AArch64 region-effect instruction selection,
executable-memory policy/invocation, durable native cache
serialization/storage/eviction, cache-aware AOT/JIT policy beyond verified
direct process-local reuse, and performance policy remain open. The
interpreter remains the only normative execution authority and the guaranteed
fallback.

## Invariants

- Interpreter, AOT, JIT, native cache, and deoptimization share one observable
  VM contract; disabling every native tier produces the same guest behavior.
- Observable state, I/O, termination, and diagnostics match the declared
  semantic profile across positive, boundary, and adversarial fixtures.

## Failure Behavior

Invalid program memory requirements, unsupported profiles/runtimes, or broken
native assumptions fail deterministically without changing guest-visible state
silently. Direct selection preserves precedence `002`, then `001`, then host and
backend errors.

## Verification

- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- Required evidence: semantic fixtures, state/I/O traces where diagnostic, and
  differential results against independent specification-conformant
  implementations; the historical interpreter is compared only on its documented
  agreement domain.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`,
  `self-modification-state-graph-optimizer`.
- Current executable foundation is covered by `tests/state_graph_research.rs`
  and `tests/tiered_execution.rs`: artifact tampering fails closed, verified
  effects/deoptimization match their normative baselines, canonical IR matches a
  byte-exact independent fixture, forced bucket collisions keep process-local
  cache entries independent, cache-aware direct planning reports insert/hit
  with pointer-identical immutable artifacts while preserving profile/host
  preflight, profile-invalid IR cannot gain
  cache/bootstrap/direct identity, direct `MBPF` v3 binds exact region memory,
  bootstrap source is
  deterministic/atomic/key-bound, direct selection
  preflights profile capability before host/backend selection, and
  pinned Clang emits real x86-64 and AArch64 COFF object candidates.
- Safe-Rust COFF tests admit both real objects, including ARM64 internal
  relocations, while rejecting truncated bytes, mismatched machine identity, and
  a renamed callable entry. Structural admission remains non-semantic.
- Clang bootstrap objects remain structurally admitted but semantically
  untrusted. The direct deopt-only objects are the sole current semantically
  admitted machine-code artifacts; their complete bytes match independent
  fixtures and opcode tampering fails after structural admission.
- Development execution evidence links both direct ISA objects and runs the
  x86-64 function with a null state pointer, observing guard-miss status `1`.
## References

### Host Architecture Baseline

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`

- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
