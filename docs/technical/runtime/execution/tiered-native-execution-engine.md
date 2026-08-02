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

`src/runtime/tiered-execution/domain/ir/main.rs` now owns portable effect IR v3
as product code. It
defines `EffectOp`, `MemoryLiveIn`, and `RegionEffectProgram`, and re-exports
the
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

`src/runtime/virtual-machine/domain/profile.rs` now owns the portable
requirement type and
`preflight_runtime_requirement()`. Given an independently admitted profile ID
and
envelope, it compares word width, profile capacity, and every declared semantic
feature with an explicit `RuntimeCapability`. Current-profile IR is rejected by
`safe-rust-classic` with byte-identical `MALBOLGE-PROFILE-001` text to canonical
descriptor preflight and accepted by `safe-rust-profiled`; unknown feature IDs
fail closed and are named in `missing=`. This consumes artifact metadata without
reloading `malbolge.json`, but does not replace profile identity/fingerprint or
verifier admission.

`src/runtime/tiered-execution/adapter-outbound/cache/main.rs` now owns
collision-safe native artifact identity and
caller-owned process-local reuse storage. `RegionEffectProgram` has a versioned
layout-independent canonical byte encoding, frozen by an independently rendered
fixture. Raw canonical transport may preserve a profile-capacity-inconsistent
untrusted envelope for deterministic rejection, but `RegionEffectIdentity` and
`NativeArtifactKey` return typed `NativeIdentityError::ProfileCapacity` before
hashing or artifact construction. Native keys retain the exact profile
ID/fingerprint plus the canonical requirement envelope and additionally bind
host
OS, x86-64/AArch64 ISA, backend identity/revision, native ABI revision, and
sorted
required features. `RegionEffectIdentity` and `NativeArtifactKey` exclude the
derived digest from `Eq`. `NativeArtifactCache<Value>` uses FNV-1a only to
choose
the preferred bucket, then confirms full key equality and searches other buckets
when an equal key carries a different accelerator digest. Equal identities
remain
one entry across digest changes; forced-collision distinct entries remain
independent. Store equality compares the logical exact key/value mapping and
omits
bucket placement, so accelerator layout is never observable identity. The store
performs no persistence, eviction, synchronization, or semantic admission.

`src/runtime/tiered-execution/adapter-outbound/native/main.rs` now owns the
first host-code artifact boundary. The
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

`src/runtime/tiered-execution/adapter-outbound/native/profile_metadata.rs` is
the single private owner of the
format-neutral `MBPF` v3 payload. Bootstrap source rendering, direct object
construction, and COFF admission consume that encoding without making the parser
or either emitter authoritative over the schema.

`src/runtime/tiered-execution/adapter-outbound/native/coff.rs` now provides a
second, independent structural gate for
those Windows objects. It parses COFF bytes directly in safe Rust rather than
trusting Clang/LLVM diagnostics, requires machine identity to match the native
key, requires exactly one executable/non-writable `.text` section and the exact
`malbolge_native_region_apply` external function, rejects unexpected external
functions or undefined external symbols, and admits relocations only when their
targets are defined inside the same object. ARM64's compiler-generated `.rdata`
constant relocations therefore remain valid while host-library dependencies fail
closed. Direct backends and `clang-c23-bootstrap` revision 2 additionally
require one initialized, read-only, non-relocated `.mbprof` section. Its `MBPF`
v3
payload must match the profile ID, fingerprint, published version, stable
features,
word trits, profile capacity, and exact derived `u64` region memory requirement
retained by the native key. Missing or mismatched required metadata, including a
same-profile footprint mismatch, fails before semantic admission. Bootstrap
revision-2 C23 source renders the canonical bytes through a read-only
custom-section
declaration; historical revision 1 remains legal without the section. The pinned
Clang test remains responsible for cross-ISA compiled-object confirmation. The
result is named `StructurallyAdmittedNativeObjectArtifact`; it still has no
semantic execution authority.

`src/runtime/tiered-execution/adapter-outbound/native/direct/mod.rs` crosses
that semantic boundary through a reviewed
family whose deterministic fallback floor is a direct deoptimization stub. The
x86-64 sequence is
`mov eax, 1; ret`; the AArch64 sequence is `mov w0, #1; ret`. Both are wrapped
in
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
semantically admitted native artifact but intentionally provides no
acceleration.
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
state-applying native subset; wider reviewed terminal subsets are described
below and all remaining IR still requires deopt/bootstrap/VM.

`direct-halt-registers` revision 5 widens that halt-only subset to an exact
entry observation: arbitrary 32-bit `A/C/D` plus full 64-bit `input_consumed`
and
`output_len`. It still admits no memory or I/O effect and commits only the
termination byte after every guard. x86-64 uses full-width immediate loads
before
counter comparison; AArch64 materializes all four 16-bit counter pieces and
patches each conditional branch to one guard-miss return. Independent complete
objects are 495/564 bytes for x86-64/AArch64 and bind counters above `u32::MAX`.
Counter/key mutation, opcode mutation, and historical revision-4 target identity
all fail semantic admission.

`direct-halt-fetch` revision 2 binds graphical halt termination to real code
memory. Admission requires one effect ending in `HaltInstruction`, one live-in
at
`C`, unchanged observations except termination, and no memory/I/O effect. The
VM-owned `decode_profile_instruction()` result for the live-in and code pointer
must be `v`. Both ISAs guard the complete entry observation, non-null memory,
exact IR footprint, exact `memory[C]`, and prior termination before committing
only
tag `1`. Independent objects are 535/628 bytes. Development x86-64 execution
proves hit plus atomic live-in, capacity, and null-memory misses; independent
AArch64 decoding confirms the expected guards, halt tag, and common miss target.

`direct-non-graphical` revision 2 adds the first direct template guarded by
exact
memory evidence. Admission requires one effect terminating with
`NonGraphicalCell`, one live-in at the entry code pointer, unchanged
observations
except termination, and no memory/I/O effect. The VM-owned
`profile_cell_is_graphical()` predicate supplies the semantic classification.
Machine code guards the complete entry observation, non-null memory pointer,
exact IR footprint, exact `memory[C]`, and prior termination before committing
only
tag `2`. Independent x86-64/AArch64 objects are 538/631 bytes. Development
x86-64
execution proves hit plus atomic live-in, capacity, and null-memory misses;
independent AArch64 decoding confirms full observations, capacity/live-in
guards,
and one common miss target.

`direct-no-operation` revision 2 is the first non-terminal direct effect and the
first direct guest-memory write. Admission requires one VM-classified no-op
live-in at `C`, one exact self-encryption delta, unchanged accumulator/counters/
termination, modular `C/D` successors, no I/O, budget one, and
`BudgetExhausted { steps: 1 }`. The verifier derives decode classification,
`XLAT2`, and pointer wrap through VM-owned helpers. Both ISAs guard the complete
entry and fetched cell before committing only encrypted `memory[C]` plus `C/D`.
Independent objects are 557/658 bytes. Development x86-64 execution proves
`memory[5]:77->65`, `C:5->6`, `D:7->8` and atomic live-in/capacity/null misses;
independent AArch64 decoding confirms the same commit and common miss target.

`direct-jump-data` revision 1 adds the first instruction-specific semantic data
read. Admission requires two distinct entry live-ins at `C` and `D`, VM-decoded
`j`, one exact code-encryption delta, unchanged
accumulator/counters/termination,
modular `C+1` and `memory[D]+1`, no I/O, and one exhausted step. Aliasing
remains
rejected. Both ISAs guard the complete entry, exact 125-word IR footprint,
`memory[5]=35`, and `memory[7]=123` before committing only `memory[5]:35->93`,
`C:5->6`, and `D:7->124`. Independent objects are 564/699 bytes. Development
x86-64 execution proves the hit and atomic code-live-in, data-live-in,
footprint,
and null-memory misses; independent AArch64 decoding confirms both reads, exact
commit, and common miss target.

`direct-jump-code` revision 1 captures the normative post-jump encryption order.
Admission requires three distinct live-ins: entry `memory[C]`, entry
`memory[D]`,
and the graphical cell addressed by the value loaded from `D`. VM-owned decode
must classify the first as `i`; encryption and pointer successors derive the
entire no-I/O exit. Both ISAs guard the complete entry, exact 13-word footprint,
`memory[5]=93`, `memory[7]=11`, and `memory[11]=68` before committing only
`memory[11]:68->33`, `C:5->12`, and `D:7->8`. Independent objects are 622/731
bytes. x86-64 development execution proves exact hit behavior plus atomic
code/data/encryption/footprint/null misses, and all twelve `rel32` guards share
one
miss. Independent AArch64 decoding confirms three ordered reads, the exact
commit,
and twelve branches to one miss target. Aliasing among the three addresses
remains
rejected.

`direct-rotate` revision 1 adds the first reviewed direct transition with two
separate guest-memory writes. Admission requires two distinct live-ins at entry
`C` and `D`, VM-decoded `*`, one exact rotated data delta, one exact code
encryption delta, updated accumulator, modular `C/D` successors, no I/O, and one
exhausted step. The verifier uses VM-owned `profile_rotate()`, encryption, and
successor helpers. Both ISAs guard the complete entry, exact 9-word footprint,
`memory[5]=34`, and `memory[7]=10` before committing only
`memory[7]:10->1594326`, `memory[5]:34->122`, `A:0xdeadbeef->1594326`,
`C:5->6`, and `D:7->8`. Independent objects are 578/732 bytes. Development
x86-64 execution proves exact hit behavior plus atomic code-live-in,
data-live-in,
footprint, and null-memory misses; independent AArch64 decoding confirms both
reads, both writes, all register commits, and eleven branches to one miss
target.
Aliasing `C == D` remains rejected.

`direct-crazy` revision 1 adds the second reviewed two-write arithmetic
transition. Admission requires distinct entry `C/D` live-ins, VM-decoded `p`,
and data plus accumulator operands inside the declared word domain. The verifier
uses VM-owned `profile_crazy(memory[D], A, word_trits)`, encryption, and
successor helpers. Both ISAs guard the complete entry, exact 9-word footprint,
`memory[5]=57`, and `memory[7]=10` before committing
`memory[7]:10->2391494`, `memory[5]:57->91`, `A:20->2391494`, `C:5->6`, and
`D:7->8`. Independent objects are 577/731 bytes. Byte-exact fixtures and
structural-but-semantic tampering rejection bind the contract. Aliasing `C == D`
remains rejected.

`direct-output` revision 1 adds the first reviewed direct I/O transition.
Admission requires one live-in at entry `C`, VM-decoded `/`, one VM-owned low
byte, output length incremented by one, exact code encryption, modular `C/D`
successors, no input, and one exhausted step. Both ISAs guard the complete
entry, exact 9-word footprint, `memory[5]=112`, non-null output pointer, and
capacity greater than index 3 before committing byte `0xa8` and
`output_len:3->4`. Independent objects are 642/724 bytes. Development x86-64
execution proves exact hit and atomic code/capacity/output-pointer/footprint/
null
memory misses; independent AArch64 decoding confirms eleven common-miss guards.

All memory-backed direct templates compare ABI `memory_words` with the exact
`NativeArtifactKey` IR footprint before any dereference or commit. The metadata
and executable guards therefore bind the same output-reachable memory domain.

`select_verified_direct_native()` now removes direct-backend identity selection
from callers and requires one explicit `RuntimeCapability`. It derives the exact
region memory footprint from the IR and checks profile capacity before runtime
capability, host validation, or backend construction. Out-of-profile addressing
returns typed `MALBOLGE-PROFILE-002`; otherwise current-profile IR under
`safe-rust-classic` returns the byte-identical `MALBOLGE-PROFILE-001`
diagnostic.
Even when the host format is also unsupported, no native object or deopt
fallback
is constructed.

After program/profile/runtime admission, it classifies IR from narrowest to
broadest:
zero-register halt uses `direct-initial-halt`, other no-live-in one-step halts
use
`direct-halt-registers`, exact graphical halt fetch uses `direct-halt-fetch`,
exact
non-graphical termination uses `direct-non-graphical`, exact non-aliasing
jump-code uses `direct-jump-code`, jump-data uses `direct-jump-data`, rotate
uses `direct-rotate`, crazy uses `direct-crazy`, output uses `direct-output`,
and exact no-op execution uses
`direct-no-operation`, and otherwise the selector emits/verifies direct deopt.
Only admitted program shape controls this fallback; profile, emission, or
admission errors are propagated rather than silently retried. Non-Windows host
formats fail explicitly because direct ELF/Mach-O templates do not exist yet.

All state-applying emitter/verifier pairs independently repeat the
profile-capacity shape check. A caller bypassing the selector cannot
semantically
promote an initial-halt, register-halt, halt-fetch, non-graphical, no-operation,
jump-code, jump-data, rotate, crazy, or output object whose IR footprint
exceeds its embedded profile envelope.

`select_preflighted_execution_tier()` is the first planning boundary above
direct
selection. It maps only top-level direct `TargetFormat` absence to the normative
interpreter after profile preflight. Windows returns the exact verified direct
artifact; `MALBOLGE-PROFILE-002`, `MALBOLGE-PROFILE-001`, and any backend,
emission, or admission failure remain errors. This boundary performs no cache
lookup, executable-memory policy, linking, or invocation.

`select_cached_preflighted_execution_tier()` adds exact process-local reuse
without
weakening those gates. One explicit `DirectHost` plus runtime capability is
preflighted before lookup. A private `PreparedDirectTarget` binds specialization
and exact `NativeArtifactKey`. The same prepared key selects the bucket and is
consumed by miss emission, eliminating a second IR canonicalization at that
boundary. State-applying semantic verifiers continue reconstructing their
expected
key independently from IR before promotion. `VerifiedDirectNativeCache`
privately
wraps the generic cache and accepts values only through successful direct
emission
and semantic admission. Results distinguish `Inserted` from full-key `Hit`;
all eleven current templates match uncached selection byte-for-byte and reuse
the
same immutable `Arc` allocation rather than cloning verified object bytes. A
populated
cache cannot bypass `002`, `001`, or non-Windows interpreter selection, and
those
outcomes leave cache cardinality unchanged. Exact-key invalidation removes one
future lookup, while exact-program invalidation first constructs
`RegionEffectIdentity` and then removes all host/backend variants of that
region.
An out-of-profile program fails before mutation. Exact-target invalidation
removes
all regions sharing one OS/ISA/backend revision/native-ABI/features identity
while
preserving other ISAs and backend identities. No invalidation operation revokes
outstanding `Arc` plans or crosses its stated identity boundary; later requests
reinsert the same keys/bytes under distinct allocations. `Arc` provides shared
immutable ownership only. Durable storage, automatic eviction, synchronization
policy, linking, executable memory, invocation, and performance policy remain
outside.

### Remaining Implementation

Semantic admission beyond the reviewed terminal/no-op/jump/rotate/crazy/output
family, Input x86-64/AArch64 selection, executable-memory policy/invocation,
durable native cache
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
