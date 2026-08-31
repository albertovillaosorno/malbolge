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

`src/runtime/virtual-machine/domain/execution_ir.rs` now owns portable effect
IR v3
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
ID/fingerprint plus the transported requirement envelope and additionally bind
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
Bootstrap validation uses checked input/output counter increments, so an
observation at `usize::MAX` fails closed instead of saturating into an
apparently valid transition. Repeated writes to one address collapse to their
first required value and final committed value, so a guard miss cannot leave an

intermediate region state.

`native/compiler.rs` now owns the explicit external bootstrap compiler process.
Its only public compile path first calls canonical profile/runtime-preflighted
lowering, then streams deterministic source to Clang stdin and captures object
bytes from stdout without temporary files. Profile-capacity `002` and runtime
`001` diagnostics therefore precede even a missing-compiler launch failure.
Pinned Clang 22.1.8 materializes real Windows COFF objects for both x86-64 and
AArch64 under strict warning-clean C23 compilation through that product path.
Source and object containers remain explicitly `Untrusted*`: matching IR/target
identity proves provenance of the claim, not semantic correctness of

compiler-produced machine code.

`src/runtime/tiered-execution/adapter-outbound/native/profile_metadata.rs` is
the single private owner of the versioned MBPF payload. MBPF v3 mirrors effect
IR v3 with a `u32` profile-capacity field; MBPF v4 mirrors effect IR v4 with a
`u64` capacity field. Bootstrap/direct emitters and COFF admission consume the
encoding without becoming authoritative over the schema.

`src/runtime/tiered-execution/adapter-outbound/native/coff.rs` now provides a
second, independent structural gate for
those Windows objects. It parses COFF bytes directly in safe Rust rather than
trusting Clang/LLVM diagnostics, requires machine identity to match the native
key, requires exactly one executable/non-writable `.text` section and the exact
`malbolge_native_region_apply` external function, rejects unexpected external
functions or undefined external symbols, and admits relocations only when their
targets are defined inside the same object. ARM64's compiler-generated `.rdata`
constant relocations therefore remain valid while host-library dependencies fail
closed.

Direct backends and `clang-c23-bootstrap` revision 2 additionally
require one initialized, read-only, non-relocated `.mbprof` section. Its MBPF
version follows the IR identity: v3 stores profile capacity as `u32`, v4 as
`u64`, and both bind profile ID, fingerprint, published version, stable
features,
word trits, and exact derived `u64` region memory retained by the native key.
Missing or mismatched required metadata, including a
same-profile footprint mismatch, fails before semantic admission.

Schema version is not the state-applying execution ceiling. Bootstrap, direct
shape admission, and native invocation accept canonical IR/MBPF v3 or v4 when
the declared profile capacity converts exactly to their `u32` word/address
representation. V4 N21 fails that geometry gate; direct-deopt alone may carry
N21 v4 because the reviewed stub never touches guest state.

Bootstrap revision-2 C23 source renders the canonical bytes through a read-only
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
Development evidence links both ISA deoptimization objects and executes the
x86-64 DLL with a null state pointer, returning `1`. That historical floor now
coexists with eleven reviewed direct region-effect templates; together with the
deoptimization stub, all twelve deterministic templates have exact cross-ISA
object, verification, load-image, invocation, and sequence evidence.

Native ABI revision 1 now has one Rust owner in `native/abi.rs`. The
`repr(C)` call frame is exactly 80 bytes on the supported 64-bit hosts, with
tested offsets matching the x86-64 and AArch64 templates from byte 0 through
the termination tag at byte 76. Typed applied, guard-miss, invalid-argument,
and termination values fail closed on unknown foreign integers. A borrowed
`NativeRegionCallFrame` validates buffer capacities and cursor bounds before
exposing a raw state pointer. `native/invocation.rs` now surrounds that pointer

with an exact one-effect contract. Preparation validates the IR shape, memory
footprint, live-ins, input/EOF claim, output movement, and memory-write
before-values while snapshotting complete state, memory, and output surfaces.
Completion admits only the exact IR-derived `Applied` result or a fully atomic
`GuardMiss`; unknown status, unexpected `InvalidArgument`, topology drift, and
partial commits fail closed. Every rejected completion restores the complete
entry snapshot. `PreparedVerifiedDirectInvocation` additionally reconstructs
full artifact identity from the exact program and the verified artifact target,

rejects canonical drift, and denies deopt-stub application authority.
`NativeRegionBuffers` groups caller loans so verified bytes, target assumptions,
and the ABI pointer remain one binding. `VerifiedDirectLoadImage` now reparses
that bound COFF, rejects relocations, extracts immutable `.text` plus the exact
entry offset, retains full key/target identity, and validates ISA alignment.
The fixed load policy permits only RW staging followed by RX execution and
requires instruction synchronization. All twelve direct templates produce exact

images on both ISAs. A safe lifecycle protocol now admits exact platform
reports in RW-copy, same-mapping RX-seal, and full-code instruction-sync order.
It rejects byte, permission, capacity, alignment, address, identity, range, and
sync drift before producing `ReadyNativeExecutable`, which retains the exact
release request. `PreparedNativeExecutableInvocation` binds that ready image to
the prepared call before exposing entry address and ABI state together. All 24

direct images pass the lifecycle; cross-ISA binding fails closed. Reports remain
adapter evidence only: no linking, allocation, permission syscall, cache flush,
cleanup owner, or foreign invocation is implemented. A caller-owned
`NativeExecutableMemoryAdapter` port now orchestrates exact allocate, copy,
protect, synchronize, and release operations. Allocation reports are admitted
before copy; copy bytes and identity are verified afterward. Every subsequent
adapter or lifecycle failure attempts exact release and retains primary plus

cleanup diagnostics. Explicit release preserves the ready executable for retry
when cleanup fails. Deterministic adapter evidence covers all 24 images, four
operation failures, ten report drifts, cleanup failure, and retry. The
`NativeExecutableRunner` port now accepts only a fully bound executable
invocation. `execute_verified_native()` composes load, exact binding, runner

call, result admission, and release. Load and runner failures explicitly abort
entry snapshot; completion rejection restores through the invocation contract.
Cleanup failure retains the ready executable for retry, while final-release
failure also retains the already committed outcome. Six runner cases cover
`Applied`, `GuardMiss`, load short-circuit, runner mutation rollback, completion
drift, and committed release failure. No concrete OS adapter or foreign-call

implementation exists.

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

`direct-execution-geometry-crazy` revision 1 adds an artifact-only v5 crazy
boundary from the first `p` reached after jump and rotate in the independently
verified `(&<;:9K` projection theorem. The canonical profile still selects the
crazy opcode and cell encryption, while explicit geometry supplies the word
width, memory domain, and modular C/D successors used by `profile_crazy()`.

The selector independently requires distinct C/D live-ins, exact data and
self-encryption writes, and operands inside the explicit geometry domain before
reusing the reviewed x86-64/AArch64 crazy machine-code template. N10 and N11
retain distinct v5 keys and COFF bytes; cross-geometry verification and tampered
profile metadata reject. Legacy `direct-crazy` byte-exact fixtures remain
unchanged. This boundary grants artifact identity and verification only;
checkpoint replay, load-image, invocation, reusable ownership, and residency
remain separate work.

`direct-output` revision 1 adds the first reviewed direct I/O transition.
Admission requires one live-in at entry `C`, VM-decoded `<`, one VM-owned low
byte, output length incremented by one, exact code encryption, modular `C/D`
successors, no input, and one exhausted step. Both ISAs guard the complete
entry, exact 9-word footprint, `memory[5]=94`, non-null output pointer, and
capacity greater than index 3 before committing encrypted code 57, byte
`0xa8`, and `output_len:3->4`. Independent objects are 642/724 bytes.
Development x86-64 execution proves exact hit and atomic
code/capacity/output-pointer/footprint/
null

memory misses; independent AArch64 decoding confirms eleven common-miss guards.

`direct-input` revision 1 completes reviewed direct coverage of all eight
instruction families. Admission requires one profile-declared input code-cell
live-in (`/` for current `malbolge-2026`) and exactly
one byte or EOF input observation. Byte input derives `A` from the exact byte
and
increments `input_consumed`; EOF uses VM-owned `profile_eof_word()` and keeps
the
cursor unchanged. Both forms encrypt code and advance `C/D`. Byte objects are

659/744 bytes and EOF objects are 634/715 bytes for x86-64/AArch64. Development
x86-64 execution proves EOF accepts a null input pointer, while byte input
requires a pointer, strict length, and exact byte; every tested miss is atomic.

All memory-backed direct templates compare ABI `memory_words` with the exact
`NativeArtifactKey` IR footprint before any dereference or commit. The metadata
and executable guards therefore bind the same output-reachable memory domain.

`select_verified_direct_native()` now removes direct-backend identity selection
from callers and requires one explicit `RuntimeCapability`. Before using any IR
geometry for capacity or template selection, it requires the transported
`TargetProfileRequirement` to exactly match the canonical version, ordered
features, word width, and memory capacity of the declared profile ID. A forged
or unknown envelope returns `DirectSelectionError::ProfileRequirement`. Exact
region memory is then checked against profile capacity before runtime
capability,
host validation, or backend construction. Out-of-profile addressing returns
typed `MALBOLGE-PROFILE-002`; otherwise current-profile IR under
`safe-rust-classic` returns the byte-identical `MALBOLGE-PROFILE-001`

diagnostic. Even when the host format is also unsupported, no native object,
deopt fallback, or interpreter fallback is constructed.

After program/profile/runtime admission, it classifies IR from narrowest to
broadest:
zero-register halt uses `direct-initial-halt`, other no-live-in one-step halts
use
`direct-halt-registers`, exact graphical halt fetch uses `direct-halt-fetch`,
exact
non-graphical termination uses `direct-non-graphical`, exact non-aliasing
jump-code uses `direct-jump-code`, jump-data uses `direct-jump-data`, rotate
uses `direct-rotate`, crazy uses `direct-crazy`, input uses
`direct-input`, output uses `direct-output`, and exact no-op execution uses
`direct-no-operation`, and otherwise the selector emits/verifies direct deopt.
Only admitted program shape controls this fallback; profile, emission, or
admission errors are propagated rather than silently retried. Non-Windows host
formats fail explicitly because direct ELF/Mach-O templates do not exist yet.

All state-applying emitter/verifier pairs independently repeat the
profile-capacity shape check. A caller bypassing the selector cannot
semantically
promote an initial-halt, register-halt, halt-fetch, non-graphical, no-operation,
jump-code, jump-data, rotate, crazy, input, or output object whose IR footprint
exceeds its embedded profile envelope.

`RegionEffectProgram::from_profile_step_trace()` and
`select_verified_direct_sequence()` now provide the first verified multistep
planning slice. Complete normative trace reads are projected independently into
one-step IR; compact regional IR is not split because it omits intermediate
semantic reads. Sequence admission requires one-effect/budget-one programs, one
canonical profile identity, exact adjacent observations, no non-final
termination, and a real direct fast path for every step. Any hidden deopt or
step failure rejects the whole plan before publication.

A retained rotate/output normative trace selects byte-verified
`direct-rotate` and `direct-output` artifacts for both x86-64 and AArch64. It
derives the exact regional entry, exit, and `BudgetExhausted { steps: 2 }`
outcome. `select_cached_verified_direct_sequence()` adds atomic process-local
reuse around that same plan: all targets are prepared first, exact cache hits
retain their `Arc`, unique misses are verified in local staging, and insertion
occurs only after every position succeeds. Retained tests prove two inserts then
two pointer-identical hits, a one-hit/one-insert transaction, runtime preflight
before lookup, and rollback that preserves an unrelated cached artifact after a
late hidden deopt.

`sequence_runner.rs` consumes either ordered plan without fusing objects. Each
program/artifact pair passes through the exact safe single-step transaction.
Committed prefixes remain visible; guard miss returns the current zero-based
resume index and entry observation, while step failure reports committed count,
resume state, nested execution/preparation evidence, and retryable cleanup.
Retained VM snapshots prove complete cached/uncached rotate-output execution,
second-step guard resume, mutation rollback, and release failure after applied
or guard outcomes.

`NativeInterpreterContinuation` converts those admitted boundaries into one
immutable semantic handoff independent of executable lifetime. It supports both
cached and uncached plans plus ephemeral and already-loaded failures. Complete
and suffix `NativeExecutableSequenceKey` values retain exact artifact identity;
the continuation also clones only the remaining one-step programs and records
resume observation, expected final observation/outcome, and guard/failure
reason.
Construction rejects forged applied counts, final observations, resume indices,
resume observations, or inconsistent failure progress. Applied completion and

terminal cleanup failure yield no continuation. `advance()` rebases the same
complete-plan authority after additional admitted work from any tier. It keeps
expected exit/outcome, advances the absolute resume index, and derives the exact
remaining key/program suffix; verified completion yields no continuation, while
overshoot or boundary drift fails closed. Eleven deterministic cases cover all
constructor families, malformed evidence, partial rebase, completion, and drift.

No interpreter call, buffer transfer, or scheduling policy is performed here.

`application/interpreter_handoff.rs` consumes the continuation through the
normative safe-Rust `ProfileMachine`. Admission accepts either a validated full
checkpoint or owned memory/input plus the committed output prefix, then resolves
canonical profile identity/fingerprint/requirement and compares the complete
checkpoint observation and first remaining live-ins before mutation. Each suffix
step uses `step_traced()` and reprojects its trace to exact one-step IR.
Machine,
projection, program, or live-in drift returns the step-entry checkpoint with the
combined-plan resume index. Completion combines native and interpreter step

counts and validates the original plan exit and outcome.

`geometry_handoff.rs` keeps derived-width replay separate from that legacy
native-continuation contract. Its one-step `ExecutionGeometryInterpreterHandoff`
admits an explicit-geometry v5 program only beside a validated
`ProfileMachineState`. The checkpoint's opaque `ProfileExecutionGeometry` token
is the authority; the v5 N/capacity pair must equal its visible projection, and
canonical profile identity, entry observation, execution capacity, and live-ins
must agree before mutation.

Execution uses the normative `ProfileMachine` and reprojects the complete trace
back to v5. It publishes the final checkpoint only when that program is
byte-structurally equal. A forged v5 effect returns the untouched entry
checkpoint. This one-step primitive grants no native key, lowering, or cache
authority, and the existing native interpreter handoff continues to reject
derived checkpoint geometry.

`ExecutionGeometryInterpreterContinuation` composes those one-step replay
boundaries without changing the trust model. Construction rejects empty,
profile-mixed, geometry-mixed, discontinuous, over-capacity, or
terminated-prefix
v5 sequences and binds the first step to the supplied opaque checkpoint. Each
executed step rechecks checkpoint admission and exact normative reprojection.

A positive budget may suspend after any admitted prefix while retaining the
exact
checkpoint, absolute resume index, and v5 suffix; zero budget is a no-op. Final
completion preserves the original bounded outcome. A forged later step fails at
its exact index and returns the checkpoint after the last successful replay.
Tests cover byte and EOF input through N10 input-then-halt, N10/N11 geometry
mixing, suspension/resume, zero budget, and later-step forgery; no native
artifact identity or execution authority is introduced.

Native identity can now represent v5 without granting execution by itself.
`RegionEffectIdentity::new_execution_geometry()` retains the complete canonical
v5 bytes plus the explicit execution geometry, and
`NativeArtifactKey::new_execution_geometry()` combines that identity with the
ordinary host/backend assumptions. MBPF v5 metadata carries the unchanged
canonical profile envelope followed by the explicit N/capacity pair.

N10 and N11 therefore remain distinct under full cache equality even when their
canonical profile identity is the same. Existing v3/v4 constructors retain no
execution geometry field. This is identity plumbing only; direct selection and
invocation remain canonical-only until a reviewed v5 native subset admits the
geometry.

The first reviewed v5 native admission is now a guarded initial-halt artifact
only. `direct-execution-geometry-initial-halt` accepts an exact one-step v5 halt
whose sole live-in is the fetched code cell. Its x86-64 and AArch64 templates
reuse the proven halt-fetch guard sequence: exact entry observation, minimum
memory capacity, fetched-cell value, and clear termination are checked before
committing halt. The artifact uses the v5 native key and MBPF v5 metadata, so
N10 and N11 objects differ even though their machine-code template is otherwise
the same.

Verification reconstructs the exact v5 key and canonical COFF bytes. A different
geometry or tampered profile metadata fails closed.

This artifact is deliberately not a `VerifiedDirectNativeArtifact`. Existing
prepared-invocation, sequence, and cache-selection APIs therefore cannot execute
it accidentally. `VerifiedExecutionGeometryLoadImage` can independently extract
the verified relocation-free, ISA-aligned entry image while retaining the v5 key
and strict W^X policy, but no lifecycle API accepts that image for executable
mapping.

`geometry_native.rs` now owns the first checkpoint-to-native admission boundary.
`ExecutionGeometryNativeInitialHaltAdmission` consumes one exact v5 program, one
verified guarded initial-halt artifact, and one validated `ProfileMachineState`.
It reuses geometry-interpreter admission to bind the checkpoint's opaque
geometry
token, profile, entry observation, capacity, and live-ins, then independently
reconstructs the v5 native key before retaining the relocation-free load image.

N10/N11 checkpoint drift and artifact/program geometry drift both reject before
any executable mapping.

The same boundary now owns borrow-scoped ABI preparation for guarded initial
halt. `prepare()` accepts caller buffers only when memory, full input, and
committed output exactly equal the admitted checkpoint. It then uses a
crate-private v5 initial-halt constructor on `PreparedNativeRegionInvocation`;
the prepared geometry wrapper exposes neither the raw ABI state pointer nor an
executable-call method.

Completion still uses the existing exact native result verifier. A guard miss
returns the original checkpoint, while an exact applied halt reconstructs a
`ProfileMachineState` with the original opaque geometry token. Tests cover exact
applied completion, guard-miss rollback, and memory/input drift.

Executable lifecycle now has separate v5 typestates.
`StagedExecutionGeometryNativeExecutable`,
`SealedExecutionGeometryNativeExecutable`, and
`ReadyExecutionGeometryNativeExecutable` admit exact copied bytes, same-mapping
RW-to-RX protection, full instruction synchronization, entry-range/alignment,
and release identity while retaining `VerifiedExecutionGeometryLoadImage`. Code
drift fails closed, and the resulting ready type is distinct from legacy
`ReadyNativeExecutable`, so existing runners cannot invoke it.

Platform-adapter orchestration now accepts the v5 load image through a separate
entrypoint. `load_execution_geometry_native_executable()` reuses the existing
caller-owned memory adapter and phase-tagged failure/cleanup evidence for exact
allocate, copy, protect, and synchronization ordering, but returns only
`ReadyExecutionGeometryNativeExecutable`. Every post-allocation failure attempts
the exact release request; explicit v5 release retains the ready executable for
retry if cleanup fails.

`PreparedExecutionGeometryNativeInitialHalt::bind_executable()` consumes a
checkpoint-owned prepared call only when the synchronized v5 executable retains
the exact same verified load image. A mismatched N10/N11 executable aborts the
prepared frame and restores its entry snapshot.

A separate `ExecutionGeometryNativeRunner` port now admits the actual call
boundary without widening legacy `NativeExecutableRunner`. Its runner-facing
`PreparedExecutionGeometryNativeInvocation` can be constructed only inside the
crate after exact checkpoint/artifact/load-image/executable binding; only that
borrow-scoped view exposes entrypoint, mapping identity, and the mutable ABI
state pointer. The runner cannot manufacture v5 authority from a ready mapping.

`ExecutionGeometryNativeInitialHaltBoundCall::execute()` consumes the bound
call. Runner failure aborts and restores the complete entry snapshot. A returned
status still passes through exact native completion admission; applied-state
mutation drift is rejected and rolled back, guard miss preserves the checkpoint,
and an exact halt reconstructs `ProfileMachineState` with the original opaque
geometry token. Four runner cases cover those paths.

The admission also exposes `execute_transactionally()` for the complete guarded
halt path. It prepares checkpoint-exact buffers before mapping, then reuses the
v5 platform loader, exact executable binding, dedicated runner, completion
admission, and explicit release in order. Load failure never calls the runner;
post-ready runner/completion failures restore buffers before release. Cleanup
failure retains the ready v5 executable for retry, and cleanup failure after an
admitted halt additionally retains the committed opaque-geometry completion.

Four transaction cases cover successful load/call/release, copy failure before
runner entry, runner failure plus release retry, and committed completion plus
release retry.

Initial halt can now also own one reusable synchronized mapping directly.
`ExecutionGeometryNativeInitialHaltAdmission::load_owned` retains the exact
checkpoint-bound admission beside its ready executable. Repeated owner
execution reuses the existing prepare/bind/runner path without adapter work.
Runner failure still restores the full entry snapshot and leaves the mapping
reusable.

The owner reports one live mapping and derives resident bytes from the
platform mapping's `mapped_len()` report. Its cloned admission is heap-owned so
embedding this owner in larger pair/triple residents does not duplicate a large
checkpoint on stack. Release delegates to the existing exact ready-executable
cleanup contract, so failed release transfers retryable mapping ownership. Two
focused cases cover mapping reuse/weight and failure rollback followed by reuse.

The first state-changing explicit-geometry template is now admitted separately:
`direct-execution-geometry-no-operation` revision 1 accepts only v5 one-step
no-operation traces. Its selector derives C/D successor immediates from the
explicit execution geometry rather than the unchanged canonical profile
requirement, while reusing the reviewed fetched-cell guards and no-operation
machine-code primitive. Real `DP` proof traces admit N10 and N11 independently
on x86-64 and AArch64; keys/objects remain geometry-distinct and cross-geometry
verification fails closed.

`direct-execution-geometry-initial-jump-data` revision 1 admits the aliasing
first `j` step of the certified `(&O` theorem without granting execution
authority. At this entry checkpoint C and D are both zero, so fetch, semantic
data read, and self-encryption read refer to one physical cell; v5 trace
projection therefore carries one deduplicated live-in rather than the two
non-aliasing live-ins required by legacy `direct-jump-data`. The selector
requires C==D, decodes that sole cell as `j`, derives C' from C and D' from the
same live-in using explicit execution geometry, and verifies the exact
self-encryption-only memory delta.

After semantic selection, x86-64 and AArch64 reuse the reviewed no-operation
machine-code commit primitive because this particular aliasing jump has the same
caller-visible mutation surface: one fetched-cell guard, one XLAT2 write,
unchanged A, and precomputed C'/D'. The native key, backend identity, verified
wrapper, and semantic admission remain jump-specific. Real `(&O` N10/N11
traces produce distinct v5 keys/objects and cross-geometry verification rejects.

Initial jump-data now reaches native execution through its own checkpoint-bound
composition boundary. Admission first normatively replays the exact aliasing
`j` from the opaque entry checkpoint; that replayed exit is the only state
accepted for native `Applied`. Only after replay does admission reconstruct the
exact v5 artifact identity and derive a relocation-free load image.

Preparation requires exact caller memory/input/output and independently retains
the one-live-in C==D ABI shape. Exact executable binding precedes the dedicated
v5 runner; runner failure and completion drift restore the complete entry
snapshot, while guard miss preserves it unchanged. Transactional execution
maps, binds, runs, admits, and releases in order, retaining retryable executable
ownership after cleanup failure and preserving committed normative state when
final release fails. Eight focused cases cover those paths plus cross-geometry
binding and caller-memory drift.

`direct-execution-geometry-input` revision 1 now provides the matching
artifact-only boundary for one explicit-geometry input step. Its selector
accepts both theorem-derived byte input and end-of-input. The canonical profile
selects the input opcode, while explicit geometry supplies C/D successor wrap,
minimum memory guards, and the EOF accumulator through `eof_word()`.

The v5 input path reuses the reviewed x86-64/AArch64 input machine code only
after exact one-live-in, observation, cursor, self-encryption, and input-result
checks. N10/N11 keys and COFF bytes remain distinct, cross-geometry verification
rejects, and the legacy byte-exact direct-input fixtures remain unchanged.

Input now also has checkpoint-bound semantic admission before any mapping.
`ExecutionGeometryNativeInputAdmission` replays the exact byte or EOF step from
the opaque checkpoint, retains that replayed state as future Applied authority,
and only then reconstructs artifact identity and a relocation-free load image.
N10/N11 artifact and checkpoint drift reject independently.

Input now also reaches the dedicated v5 runner through checkpoint-exact ABI
preparation and
exact synchronized executable binding. Memory, complete immutable input bytes,
and output must equal the admitted checkpoint before preparation; the common ABI
input validator then distinguishes Byte from EOF through the checkpoint cursor.
Applied accepts only the replayed exit, GuardMiss preserves the checkpoint, and
runner/completion failure restores entry buffers. Transactional execution maps
only after preparation, attempts release on every post-load exit, and preserves
committed completion plus retryable executable ownership if final release fails.

Input also has a reusable one-mapping owner with heap-owned exact admission. It
loads once, executes Byte or EOF through the same prepare/bind runner path
without remapping, reports exact platform mapped bytes plus one live mapping,
and retains the ready executable across runner failure for later reuse. Release
uses the same retryable executable cleanup contract.

Input is now also a standalone heterogeneous resident. Exact admission is its
cache identity; load, execution, weight, release, and cleanup retry stay tagged
as Input while the existing LRU remains operation-agnostic. Exact hits reuse the
one mapping with no adapter work, and failed release removes cache authority
while transferring the typed ready-executable cleanup token for retry.

`direct-execution-geometry-output` revision 1 adds a byte-verifiable v5 output
artifact boundary with operation-specific execution authority composed below.
Its selector
consumes the real `<` trace reached after `/` in the independently verified
`ubO` input/output/halt theorem with byte input `0xA5`. Canonical profile
identity still selects the output opcode and emitted low byte, while explicit
execution geometry alone supplies C/D successor wrap and memory-domain guards.

The geometry-output selector reuses the reviewed x86-64/AArch64 output machine
code only after checking the exact entry observation, one fetched code live-in,
output byte/index/length transition, self-encryption delta, and geometry-derived
successors. N10 and N11 produce distinct v5 keys and object bytes.
Cross-geometry verification rejects, and legacy direct-output byte-exact tests
remain unchanged through a shared semantic derivation helper.

Output now also has checkpoint-bound semantic admission before any mapping.
`ExecutionGeometryNativeOutputAdmission` binds the exact verified artifact to
the opaque checkpoint reached after `/`, replays `<` through the normative
interpreter, and retains that replayed state as the only future Applied
authority. The N10 fixture preserves input cursor 1 and appends exactly `0xA5`;
N11 checkpoint geometry and N11 artifact identity reject independently.

Only after replay succeeds does admission reconstruct the exact native key and
extract a relocation-free `VerifiedExecutionGeometryLoadImage`. Output now also
reaches the dedicated v5 runner through checkpoint-bound preparation and exact
executable binding. Memory and complete input must equal the checkpoint. The
mutable output slice is physical capacity: only its logical checkpoint prefix
must match entry state, and the common ABI contract separately requires room for
the exact appended byte while preserving unused capacity.

The crate-private output invocation constructor independently requires one
fetched live-in, no input effect, one output append, and one-step v5 shape
before using the shared snapshot/write/output verifier. Applied completion
returns only
the normatively replayed checkpoint; GuardMiss returns the exact entry
checkpoint. Runner failure and completion drift restore memory, state, and the
complete physical output buffer. N10 prepared state cannot bind an N11 output
mapping.

`execute_transactionally()` prepares before mapping, then loads, binds, runs,
admits, and releases in order. Successful execution performs the exact `0xA5`
append in the theorem fixture. Final release failure retains both the committed
opaque-geometry completion and exact ready executable for cleanup retry. Eleven
focused output cases cover admission, capacity, cross-geometry binding, Applied,
GuardMiss, runner/completion rollback, normal release, and committed cleanup
retry.

Output can now also own one reusable synchronized mapping directly.
`ExecutionGeometryNativeOutputAdmission::load_owned` heap-retains the exact
checkpoint-bound admission beside its ready executable and reuses the existing
prepare/bind/runner path without adapter work. Exact mapped bytes come from the
platform mapping report, runner failure restores the complete physical output
buffer, and the same mapping remains reusable before explicit release.
Heterogeneous output residency remains separate follow-up work.

`direct-execution-geometry-rotate` revision 1 adds a second state-changing v5
artifact boundary without granting execution authority. The selector consumes
the real rotate trace reached as step two of the independently certified `(&O`
jump/rotate/halt theorem, requires two non-aliasing code/data live-ins, derives
the rotated A/data value plus C/D successors from explicit execution geometry,
and verifies the exact memory delta before emission. x86-64 and AArch64 reuse
the reviewed rotate machine-code primitive only after those values are fixed.

N10 and N11 retain distinct v5 keys/objects and cross-geometry verification
rejects.

Rotate now reaches execution through its own checkpoint-bound composition
boundary. `ExecutionGeometryNativeRotateAdmission` first binds the v5 program
to opaque checkpoint geometry and executes one normative interpreter replay;
that replayed exit checkpoint is the only state returned for native `Applied`.
Only afterward does admission reconstruct exact artifact identity and derive a
relocation-free rotate load image.

Preparation requires caller memory/input/output to equal the admitted entry
checkpoint and the crate-private rotate ABI constructor retains exactly two
live-ins. Exact executable-image binding precedes the dedicated v5 runner;
runner failure, completion drift, and guard miss use the same complete snapshot
rollback rules as no-operation without sharing its operation-specific policy.
The transactional path maps, binds, executes, admits, and releases in order,
retaining a ready executable for cleanup retry and preserving committed replay
state if final release fails. Eight focused rotate cases cover cross-geometry
binding, normative Applied state, preparation drift, completion drift, runner
failure, guard miss, successful release, and committed cleanup retry.

Rotate can now also own one reusable synchronized mapping directly.
`ExecutionGeometryNativeRotateAdmission::load_owned` heap-retains the exact
checkpoint-bound admission beside its ready executable and reuses the existing
prepare/bind/runner path without adapter work. Repeated Applied calls reproduce
the normatively replayed rotate memory/A/C/D state; runner failure restores the
entry checkpoint and leaves the mapping reusable.

The owner reports one live mapping and derives resident bytes from the platform
`mapped_len()` report. Release delegates to the exact ready-executable cleanup
contract. Two focused cases cover mapping reuse/weight and failure rollback
followed by successful reuse.

The real `(&O` theorem now also supplies a two-step native suffix after its
normative jump: rotate followed by halt. The suffix admits rotate from the
post-jump checkpoint, then uses rotate's normatively replayed exit as the sole
halt checkpoint authority before either step maps. Transactional execution
stops exactly at a guard miss and preserves a committed rotate if halt later
misses or fails.

The rotate/halt suffix can additionally prebind or own both synchronized
executables. Both images are checked before caller-state mutation; repeated
execution of a loaded pair performs no new mapping work. The loaded pair now
retains rotate and halt through their reusable one-step owners while preserving
the same ready-executable accessors. Partial halt-load failure releases the
owned rotate, and pair release delegates both exact cleanup contracts.

Its resident weight is likewise owned by the pair. It checked-sums the rotate
and halt owner weights rather than rereading their mappings. The no-op/halt
owner uses the same two-child accounting rule. Focused reuse tests override
platform mapping lengths and prove 28,672 bytes/2 mappings for rotate/halt and
12,288 bytes/2 mappings for no-op/halt without changing adapter operation
counts.

Twelve focused suffix tests cover geometry continuity, indexed
progress/failure, reusable prebinding, owned reuse, partial-load rollback, and
single/both-mapping cleanup ownership.

Initial jump-data can now also own one reusable synchronized mapping directly.
`ExecutionGeometryNativeInitialJumpDataAdmission::load_owned` retains the exact
checkpoint-bound admission beside its ready executable, and repeated owner
execution reuses the existing prepare/bind/runner path without mapping work.
Runner failure still restores the full entry snapshot while leaving the mapping
available for a later successful call.

The owner reports one live mapping and derives its resident bytes directly from
that mapping's `mapped_len()` report. Final release delegates to the existing
ready-executable release contract, so failed cleanup transfers the same exact
mapping ownership already used by transactional execution. Two focused cases
cover mapped-weight reuse and runner-failure rollback followed by successful
reuse. The heterogeneous boundary now consumes this owner directly.

The complete certified `(&O` path now composes initial jump-data, rotate, and
halt without executing the jump outside the native composition boundary.
`ExecutionGeometryNativeJumpRotateHaltSequence` first admits the aliasing jump
from the theorem entry checkpoint. Its normatively replayed exit is then the
sole checkpoint accepted by the existing rotate/halt suffix, so all three
steps are admitted before the first executable mapping can occur.

Transactional execution reports global indices 0/1/2. A jump guard miss skips
the complete suffix, a rotate miss retains the committed jump checkpoint, and
a late halt failure retains the committed rotate checkpoint. Mixed N10/N11
jump/suffix evidence rejects during admission.

Five focused tests cover exact three-step completion, both prefix guard cases,
late failure, and mixed-geometry rejection. This wrapper adds no generic v5
planner or three-entry cache authority.

The full path can now prebind three caller-owned synchronized executables before
any caller buffer is borrowed. Initial-jump image identity is checked directly,
while rotate/halt binding delegates to the already reviewed suffix prebinding
contract. Prebound execution then performs no executable-memory adapter work;
it only prepares each exact checkpoint, runs the dedicated v5 runner, and
remaps suffix-local failures to global indices.

Focused tests load one exact N10 triple once and execute it twice without any
additional mapping operations, reject an N11 jump executable before mutation,
and preserve the post-rotate checkpoint on a prebound halt failure.

The full path can now also own one exact loaded triple. The reviewed rotate/halt
pair loads first; only after both suffix mappings are ready does the reusable
initial-jump owner map. Triple loading now delegates that jump mapping to the
same `load_owned` lifecycle used by standalone and heterogeneous initial-jump
residency. A jump-load failure still releases the pair immediately, while failed
rollback returns the exact suffix cleanup ownership for retry.

Owned release delegates the jump mapping to that same reusable owner and still
attempts the suffix even when jump release fails. The returned triple cleanup
object retains only failed mappings and can retry all of them without
reconstructing identity. Existing full-path tests preserve clean jump-load
rollback, rollback cleanup ownership, reuse, and three-mapping release retry.

The complete `(&O` path now has its own single-resident lease cache around the
owned triple. Complete admitted jump/rotate/halt sequence equality is the only
cache identity; exact hits clone the same `Arc` resident without adapter work,
live leases block release or replacement, and N10/N11 mismatch rejects without
implicit eviction. Failed triple loads publish no resident state, while cleanup
failure empties the slot and transfers exact retry ownership.

Explicit replacement follows the same fail-closed rule as the pair caches: an
unleased old triple releases completely before a different identity can load,
and either release or new-load failure leaves the cache empty. Nine focused
cases cover hit reuse, lease blocking, identity rejection, failed publication,
cleanup transfer, and all replacement outcomes. The no-op/halt, rotate/halt,
and full-path single-resident caches remain intentionally separate.

`GeometryNativeJumpRotateHaltLruCache` adds the first multi-resident v5 policy
for the complete `(&O` path. It always has a nonzero entry limit and can now
optionally add an exact synchronized mapped-byte limit. Residents remain in
LRU-to-MRU order, and exact hits move to MRU without adapter work.

The entry-only constructor preserves the original behavior: a full cache scans
from LRU toward MRU and evicts the first triple with no external `Arc` lease.
If all residents are leased, acquisition rejects before release or load work.
Targeted release still acts on one exact identity and cannot cross a live lease.

Resident-weight authority is now hierarchical. Each one-step owner reads only
its own synchronized `mapped_len()` report. No-op/halt and rotate/halt pair
owners checked-sum their two child weights, and full-path checked-sums the
initial-jump owner with the rotate/halt suffix weight. The heterogeneous
boundary, active LRU, and retired drain consume those owner-reported weights
without rereading internal mappings or estimating from COFF/load-image lengths.

A byte-bounded miss therefore still loads the candidate first, measures its
exact composed weight, and releases it immediately if the candidate alone
exceeds the limit. The LRU also exposes checked aggregate entries, mapped bytes,
and mappings.

When projected published bytes exceed the limit, weighted admission can release
multiple unleased LRU residents until both entry and byte limits fit. Leased
residents are skipped; if no legal victim remains, the loaded candidate rolls
back. Failures report `removed_residents` so partial successful evictions cannot
be mistaken for a side-effect-free saturation.

A victim-release failure removes only that victim, retains its exact cleanup
ownership, and also attempts candidate rollback. Failed candidate rollback is
returned separately, while unrelated residents remain valid. Fifteen focused
N10/N11/N12 cases cover entry-only/accounting behavior plus seven weighted
capacity, lease, rollback, multiple-eviction, and ownership paths.

The same cache can now reconfigure its entry, mapped-byte, and mapping-count
limits at runtime. Expansion or an already-satisfied request publishes
immediately without adapter work. Shrink removes unleased residents in existing
LRU order until retained usage fits the requested limits, then publishes those
limits atomically.

If leases block shrink or a required release fails, the previously published
limits remain authoritative. Successfully removed residents are not
resurrected,
so failure evidence reports `removed_residents`; release failure additionally
returns exact cleanup ownership for the failed victim. Seven focused cases
cover expansion, entry/byte/mapping shrink, lease blockage, partial removal, and
cleanup retry.

Mapping-count admission uses the same exact resident weight already reported by
loaded triples. A limit below three rejects one candidate with rollback, while a
limit of six admits two full-path residents and evicts LRU authority before a
third can publish.

`GeometryNativeResidentPlan` now gives initial halt, initial jump-data, input,
no-operation, no-op/halt, output, rotate, rotate/halt, and full-path templates
one typed lifecycle boundary without merging execution semantics. The
loaded-resident enum preserves exact variant identity, derives
1/1/1/1/2/1/1/2/3 mapping weights from synchronized reports, and delegates
load, execution, release, and retry to each specialized owner.

`GeometryNativeCrossTemplateLruCache` now performs real cross-template
residency over that typed boundary. It always has a nonzero resident entry limit
and can additionally bound exact synchronized mapped bytes and live mapping
count. Hits still refresh MRU position without adapter work.

A resource-bounded miss loads the typed candidate first because its exact weight
comes from synchronized platform mapping reports. An oversized candidate rolls
back without publication. Otherwise the cache can remove multiple unleased LRU
residents, even across different template families, until entries, bytes, and
mappings all fit.

Leased residents are skipped and all-leased weighted saturation rolls the loaded
candidate back. Victim release failure removes only the typed victim, retains
its specialized cleanup ownership, and also attempts candidate rollback. Failure
evidence reports prior removals so partial successful eviction is observable.

The existing entry-only and weighted cases still mix no-op/halt, rotate/halt,
and full-path residents through recency, lease, saturation, byte/mapping
pressure, rollback, release-failure, and vacancy paths. Focused cases for
initial jump, initial halt, input, no-operation, output, and rotate add
single-mapping lifecycle, hit reuse, typed cleanup, and resource-accounting
coverage. Input and output join this policy only through the typed resident
boundary: their LRU insert/hit paths add no operation-specific eviction or
weighting logic.

A heterogeneous lease can now execute its resident directly without cache or
adapter work. The common execution boundary only tags the existing specialized
outcome/failure as full-path, initial halt, initial jump-data, input,
no-operation, no-op/halt, output, rotate, or rotate/halt; it does not translate
checkpoints, guard misses, committed state, or rollback semantics. The six
single-mapping templates therefore reuse their one-step completion and rollback
contracts.

`GeometryNativeCrossTemplateLruAcquisition::execute()` now consumes the
temporary
external lease and carries the acquisition disposition into the execution
result. Success therefore preserves whether the resident was inserted, hit, or
evicted into place; execution failure retains the same disposition beside the
typed template failure. In either case the cache's resident `Arc` remains
published with no external lease left behind.

Four focused cases cover `Inserted`, `Hit`, and `Evicted` execution plus an
inserted rotate failure that rolls back caller state while leaving the resident
available for later reuse.

The same heterogeneous cache can now reconfigure entry, mapped-byte, and mapping
limits. Expansion or already-satisfied requests publish with no adapter work;
shrink removes unleased residents in the existing cross-template LRU order until
retained aggregate usage fits.

If leases block shrink or a typed victim release fails, the prior limits remain
published. Residents already removed before failure are not resurrected, so the
failure reports `removed_residents`; release failure also returns the exact
variant-specific cleanup ownership. Six focused cases cover expansion,
entry/byte/mapping shrink, partial removal, lease blockage, and typed cleanup.

The heterogeneous LRU also supports an explicit `release_all_unleased` pass.
It attempts every releasable resident in LRU-to-MRU order while retaining leased
identities as active residents in their original relative order. Any release
failure removes that identity from cache authority and returns its exact plan
with variant-specific cleanup ownership; aggregate retry never restores lookup
authority.

`release_all_unleased` itself is intentionally not a retired-resident drain. A
live lease keeps its resident lookup-visible until the lease is returned and a
later pass can reclaim it. Focused cases cover full release, one retained lease,
and aggregate release failure with exact retry ownership.

The active heterogeneous LRU can now capture one coherent all-resident
snapshot before retirement. Each LRU-to-MRU entry records exact plan, external
lease count, and owner-reported weight, while the same snapshot carries current
limits and checked aggregate usage. A nonuniform three-resident fixture proves
12,288/2, 28,672/2, and 73,728/3 weights sum to 114,688 bytes across seven
mappings with the middle resident leased.

A separate consuming transition now provides true retired authority.
`GeometryNativeCrossTemplateLruCache::into_drain` performs no adapter work and
moves every active resident into a drain handle, so the original lookup cache no
longer exists. `reconcile` releases retired residents without leases, retains
leased residents only inside the drain, and transfers failed releases as the
same exact plan plus typed cleanup evidence used by release-all.

Three focused cases prove zero-work retirement, lease-retained reconciliation,
and failed-release transfer plus retry.

The drain now exposes exact retired identities and aggregate mapping usage using
the same `resident_weight()` authority as the active LRU. A deliberately
oversized mapping fixture observes 126,976 bytes across five mappings before
reconciliation, 114,688 bytes across three mappings while one full-path lease
remains retired, and zero usage after that lease is returned and reclaimed.

This shared mapping-report accounting gives a future synchronized
`Active -> Draining -> Closed` transition concrete closure evidence without
estimating executable-image sizes.

Drain inspection can now capture one coherent retired snapshot. Each entry
records the exact plan, external lease count, and resident mapping weight, while
the snapshot carries aggregate usage from the same drain epoch. The oversized
mapping case observes no-op at 12,288 bytes with zero leases and full-path at
114,688 bytes with one lease before reconciliation; after reclaiming no-op, the
snapshot contains only that leased full-path resident, then becomes empty with
zero usage after final reconciliation.

This avoids composing identity, lease, and usage reads from different retired
states and gives any future synchronized close state a single closure witness.

The synchronized owner now has an equivalent consuming transition without an
internal mutable close state. `into_drain(self)` consumes the whole cache owner,
moves its exact adapter and active LRU into a retired drain, and leaves existing
external leases valid only as retired mapping owners because no active lookup
cache survives the move.

The concurrent drain forwards retired snapshots, usage, reconciliation, and
aggregate cleanup retry through that same encapsulated adapter. A live lease is
retained across reconciliation and releases only after its acquisition drops;
a failed release transfers exact plan plus typed cleanup evidence and can retry
without recreating active authority.

Poison remains fail-closed during consumption. If poison is already visible,
`into_drain` returns the original poisoned owner unchanged; any poison evidence
from consuming the mutex is retained opaquely and never recovered through
`PoisonError::into_inner`. Focused cases prove lease retirement, cleanup retry,
and preservation of poisoned authority.

`GeometryNativeConcurrentCrossTemplateLruCache` now owns one heterogeneous LRU
and its executable-memory adapter under the same mutex. `ensure`, release,
reconfiguration, usage, and identity reads serialize through that authority;
returned acquisitions and leases outlive the guard, so native execution itself
is not serialized by cache mutation.

The synchronization boundary is fail-closed on mutex poisoning. A panic while
adapter/cache mutation is locked poisons future access instead of recovering the
possibly half-mutated authority with `PoisonError::into_inner`. Four focused
cases prove concurrent insert/hit serialization, lease-safe eviction blocking,
serialized shrink/usage, and poison rejection.

The synchronized owner also forwards `release_all_unleased` through the same
cache/adapter mutex. Leased residents remain active after the guard is released,
while attempted releases leave cache authority even when cleanup fails.
`retry_release_all_cleanup` later retries the aggregate token with the exact
owned adapter and never republishes identities represented only by cleanup
evidence.

Two focused cases cover a retained external lease and aggregate cleanup retry.
The pass therefore provides explicit bulk reclamation without claiming a retired
resident drain or weakening the existing lease contract.

Bulk reclamation also has nonblocking entry points.
`try_release_all_unleased` reports `Busy` before adapter work, while
`try_retry_release_all_cleanup` returns the aggregate cleanup token untouched on
`Busy` or poison. Once the mutex is acquired both delegate to the exact blocking
release-all or aggregate-retry transaction.

Focused contention proves the aggregate plan/failure evidence survives `Busy`
and later retry unchanged. No separate cancellation or partial-release policy is
introduced by the nonblocking surface.

The concurrent owner also exposes acquire-then-execute as one typed request.
Only `ensure` runs under the mutex; the returned acquisition executes after the
guard is dropped. Acquire failures remain distinct from native execution
failures, and both preserve the original typed cache evidence.

A blocking-runner case proves the separation directly: while the first native
step is stalled, another thread acquires the mutation mutex and receives
`Leased { leases: 1 }` from `release_if_unleased`. Two additional cases prove
that acquisition failure never calls the runner and native failure leaves the
resident published for reuse.

Nonblocking execution now composes the same two phases through `try_execute`.
`Busy`, poison, or cache admission failure is reported as an acquire-phase error
before the runner can mutate caller buffers. A successful try-acquire executes
the lease outside the mutex; completion preserves its cache disposition, while
native failure remains a distinct typed execution-phase error and keeps resident
authority published.

Concurrent inspection can now use one coherent snapshot instead of composing
separately locked reads. `snapshot(plan)` captures exact residence, external
lease count, published limits, and aggregate mapping usage under one guard, and
publishes nothing if the lock is poisoned or resident-weight aggregation fails.
A focused case proves lease-count transition from one to zero without changing
the same snapshot's limits or usage.

`snapshot_all()` extends the same single-lock rule across the complete active
resident set. It forwards the LRU all-resident snapshot under one mutex guard,
including LRU order, exact identities, lease counts, owner weights, limits, and
aggregate usage. The three-resident fixture matches the direct LRU snapshot
without exposing the adapter or composing separate reads.

Telemetry can request the same observation without waiting for mutation.
`try_snapshot(plan)` uses `Mutex::try_lock`: `Busy` reports live lock
contention,
`Poisoned` preserves fail-closed authority, and success delegates to the exact
same snapshot constructor as the blocking read. `try_snapshot_all()` applies the
same `try_lock` rule to the all-resident view. A blocking-adapter case proves
both nonblocking forms report `Busy` while `ensure` owns the mutex, followed by
a coherent snapshot after the load completes.

Mutation callers can likewise use `try_ensure(plan)` when waiting for the cache
mutex is undesirable. `Busy` is reported before any adapter work, while a
successful `try_lock` runs the complete existing `ensure` transaction; load,
eviction, rollback, and cleanup failures therefore retain their original typed
evidence. Focused cases also prove poisoned authority stays distinct and a retry
after transient contention reuses the completed resident as a normal hit.

Nonblocking release and limit changes now use the same generic try-mutation
contract. `try_release_if_unleased` and `try_reconfigure_limits` report `Busy`
before adapter work, distinguish `Poisoned`, and otherwise run the complete
existing release or reconfiguration transaction under the acquired mutex.

Their operation failures remain unchanged. Release still transfers exact cleanup
ownership, while failed shrink keeps prior limits published, reports completed
removals, and exposes its typed victim cleanup for `retry_cleanup`.

Cleanup retries also have nonblocking forms. `try_retry_cleanup` and
`try_retry_load_cleanup` report `Busy` without consuming or modifying their
resident-release or primary-load token; `Poisoned` likewise returns untouched
ownership. Once the mutex is available, both delegate to the existing exact
adapter retry path and preserve its normal success or refreshed-failure result.

Transferred resident-release cleanup can now return to the same synchronized
adapter through `retry_cleanup`. The cache no longer owns the mappings
represented by that token; retry runs only their existing variant-specific
release contract under the mutex. Repeated failure returns refreshed cleanup
ownership, and later
success does not republish resident authority.

Primary executable load failures now retain retryable rollback without losing
the primary failure. `NativeExecutableLoadFailure::retry_cleanup` preserves its
phase, cause, and exact release request while refreshing only the secondary
cleanup error.

No-op/halt, rotate/halt, and full-path load failures propagate that contract
through their nested rollback owners. The common heterogeneous resident load
failure preserves its template variant and can retry every retained rollback
through one adapter.

The synchronized owner now forwards those resident load rollbacks through
`retry_load_cleanup` with its exact encapsulated adapter. Retry returns
`Pending`
or `Clean` while preserving the primary load failure; neither state republishes
resident authority, and a later normal acquisition can insert after cleanup.

Concurrent read-side scaling beyond one mutation mutex remains separate policy
work.

A separate rotate/halt single-resident lease cache now owns reusable loaded
pairs behind cloneable `Arc` leases. Complete admitted rotate/halt sequence
equality is its sole identity authority; it does not share resident state or
legacy canonical keys with the no-op/halt cache. Exact hits perform no adapter
work, live leases block release/replacement, and different N10/N11 identities
reject without implicit eviction. Inserted and hit leases expose the exact
rotate/halt owner weight without rereading mappings or remapping code.

Explicit replacement is allowed only after every external lease is gone. The
old pair releases fully before the new pair loads; release or load failure
leaves
no resident authority and transfers exact cleanup ownership to the caller. Nine
focused cache cases cover hit reuse, lease blocking, identity rejection, failed
load publication, cleanup transfer, and all replacement outcomes.

The no-operation artifact retains its own verified wrapper and now reaches
execution only through a separate checkpoint-bound composition module.
`VerifiedExecutionGeometryLoadImage::from_no_operation()` admits its exact
relocation-free image, while `PreparedNativeRegionInvocation` exposes a
crate-private v5 no-operation constructor that reuses the common snapshot,
live-in, memory-write, I/O, and rollback machinery without routing through
canonical IR.

`ExecutionGeometryNativeNoOperationAdmission` goes further than initial halt:
before any mapping, it normatively replays the exact v5 step from a cloned
opaque checkpoint and stores the resulting checkpoint as the only admissible
`Applied` state. Exact artifact identity and load-image extraction occur only
after that
reprojection succeeds. Preparation requires caller memory/input/output to equal
the entry checkpoint; Applied must match exact ABI observation, self-encryption,
and C/D advance, while GuardMiss returns the untouched entry checkpoint.

The bound-call runner and transactional load/call/release path reuse the
v5-specific runner and executable typestates. N10 prepared state cannot bind an
N11 no-operation executable; runner failure and completion drift restore the
entry snapshot; cleanup failure retains exact ready-executable ownership for
retry; and cleanup failure after Applied retains the already normatively proven
completion. Eight focused cases cover these admission, binding, rollback, and
transaction properties. Broader state-changing templates remain separate work.

No-operation can now also own one reusable synchronized mapping directly.
`ExecutionGeometryNativeNoOperationAdmission::load_owned` heap-retains the exact
checkpoint-bound admission beside its ready executable, then reuses the existing
prepare/bind/runner path without mapping work. Repeated Applied calls reproduce
the same normatively replayed self-encryption and C/D successor state, while a
runner failure restores the entry snapshot and leaves the mapping reusable.

The owner reports one live mapping and derives resident bytes from the platform
`mapped_len()` report. Release delegates to the exact ready-executable cleanup
contract. Two focused cases cover repeated mapping reuse/weight and mutation
failure followed by successful reuse.

The first multistep geometry-native composition is the verified `DP` no-op/halt
pair. `ExecutionGeometryNativeNoopHaltSequence` admits the no-operation from the
entry checkpoint first, then uses its normatively replayed opaque checkpoint as
the sole authority for admitting the following halt. Mixed N10/N11 evidence
therefore rejects before either executable can map.

Transactional execution preserves affine prefix progress across the two native
steps. A guard miss at step zero stops before loading the halt suffix; a guard
miss at step one retains the applied self-encryption and C/D advance from the
no-operation. A later runner failure likewise reports index one and returns that
same last committed checkpoint after rollback. Exact two-step Applied reaches
the normative halted `DP` checkpoint.

Five cases cover completion, both guard positions, late failure, and
mixed-geometry admission.

The same sequence can now prebind an externally loaded no-operation/halt pair
before caller buffers are exposed. Both ready images must equal the two admitted
load images, so a mixed N10/N11 ready pair rejects before the first no-operation
can commit. The resulting bound sequence performs no executable-memory adapter
operations and can be reused across independent caller buffers that equal the
admitted entry checkpoint.

Two repeated `DP` executions therefore reuse the same synchronized mappings
while preserving exact native completion checks. A late runner failure still
restores only the failing halt step and retains the committed no-operation
prefix.

`load_pair()` now supplies an optional owner for those same two mappings. It
loads no-operation first through the reusable no-operation owner and halt second
through the reusable initial-halt owner. Halt-load failure immediately releases
the owned no-operation, while failed rollback retains that exact mapping beside
the primary halt error. Repeated pair execution performs no adapter work, and
release delegates both mappings to their specialized cleanup contracts.

If either or both releases fail, the returned pair cleanup failure retains every
still-owned ready executable and can retry only those failures. Four cases cover
successful reuse/release, partial-load cleanup, retryable partial cleanup, and
dual release failure.

`geometry_cache.rs` adds the first v5-only lease cache without reusing canonical
sequence keys. It owns at most one `Arc`-backed loaded no-operation/halt
pair and compares the complete admitted
`ExecutionGeometryNativeNoopHaltSequence` before
every hit. The first acquisition loads both mappings, exact later acquisitions
clone the same resident allocation, and a different N10/N11 identity rejects
without eviction or adapter work.

Resident cleanup is explicit because the adapter is caller-owned. Live leases
return a counted `Leased` disposition without release attempts; after all leases
are dropped, cleanup consumes the unique `Arc` and releases the pair. Release
failure empties cache authority and transfers both retryable mapping owners to
the caller. Failed pair load never publishes resident state.

Both inserted and hit leases expose the exact pair-owner resident weight without
adapter work. Cache observation therefore uses the same hierarchical mapping
authority as heterogeneous residency.

Nine cases cover insert/hit reuse and weight, lease blocking, identity
rejection, failed-load publication, cleanup ownership transfer, and replacement
outcomes.

`replace_if_unleased()` adds an explicit single-resident identity transition.
Equal identity remains an ordinary hit. A different identity with any live lease
fails before adapter work; once unleased, the old pair must release completely
before the requested pair can load and publish a `Replaced` acquisition.

Replacement failure never restores stale cache authority. Old-pair release
failure transfers its exact cleanup owners and leaves the slot empty; if old
release succeeds but new loading fails, the slot likewise remains empty. Real
N10-to-N11 tests cover lease blockage, successful replacement, old-release
failure, and new-load failure.

`execute_with_budget()` limits each invocation to an explicit semantic-step
budget. Exhausting the budget before the suffix completes returns an affine
`NativeInterpreterHandoffSuspension` with the original continuation, cumulative
interpreter progress, complete-plan resume index, exact artifact-key/program
suffix, and validated checkpoint. `into_handoff()` resumes that owned boundary
without repeating external admission. A zero budget performs no transition and
preserves prior progress; an oversized budget completes normally. Ten cases now
cover both transfer forms, admission drift, completion, zero/partial/oversized

budgets, repeated zero after progress, and rollback before or after suspension.

`application/scheduler.rs` adds the first explicit scheduling owner above that
bridge. One affine handoff is consumed with one closed decision: complete in the
interpreter, execute one positive interpreter slice, or yield zero steps to the
caller or for possible native retry. Suspensions retain the exact checkpoint,
complete-plan index, key/program suffix, and cumulative interpreter progress,
plus a stable `BudgetExhausted`, `CallerYield`, or `NativeRetry` reason.
`resume()` consumes the same owner under a later decision. `NativeRetry` never
replans, loads, or invokes native code and no scheduler branch converts a hard

execution failure into fallback. Five cases cover both yield reasons,
slice/completion, direct completion, cumulative progress, and failure
propagation.

`application/native_retry.rs` consumes a `NativeRetry` suspension together with
one caller-replanned `VerifiedDirectSequencePlan`. Before any buffer movement it
requires the exact retry reason, ordered remaining programs, complete artifact
key, and checkpoint entry observation. Rejection returns both supplied affine
owners unchanged, so the caller may correct the plan or resume interpretation.
Five cases cover initial and progressed suffix admission, caller-yield
rejection, full-plan drift after progress, and cross-ISA key drift. This
boundary
still does

not automatically select native code. Once admitted, the owner now executes
through the existing uncached sequence runner with buffers copied from its exact
checkpoint. Success and failure retain plan/suspension plus exact memory, input,
output capacity, and admitted observation; the transfer can reconstruct a
validated `ProfileMachineState`. Indexed native failures and release-retry
ownership pass through unchanged. Five execution cases cover initial/progressed

completion, guard miss, runner rollback, and committed cleanup failure.
Successful retry evidence now rebases against the original complete-plan
continuation. Applied suffixes publish the original verified outcome and final
checkpoint. Guard miss advances absolute progress by prior interpreter plus
newly committed retry steps, then admits a new `NativeInterpreterHandoff` ready
for the scheduler. Rebase rejection retains the complete successful execution

owner. Three cases cover pure retry completion, mixed interpreter/retry
completion, and progressed guard fallback through normative scheduling. Failed
Failed retry executions now pass through the same semantic evidence path and
split into independent disposition plus indexed native failure ownership. Runner
failure before or after committed retry progress yields a scheduler-ready
normative handoff. Terminal cleanup failure may publish verified semantic

completion while retaining the exact release-retry owner. Rebase rejection keeps
the complete failed execution intact. Three cases cover zero-progress fallback,
progressed fallback, and completion followed by cleanup retry. Semantic
publication now lives in `application/native_retry/rebase.rs`; admission,
transfer, and execution remain in `native_retry.rs`, with unchanged reexports
and
owner transitions.

`application/leased_retry.rs` binds one admitted retry to an exact immutable
lease-cache acquisition. Complete key identity is checked before buffers move;
rejection restores both owners. Loaded execution performs no allocation or
release and retains cache hit/insertion evidence plus the same lease through
success, guard miss, or runner failure. Both execution paths rebase against the
original complete continuation while lease return remains explicit. Five cases
cover insertion completion, pointer-identical hit reuse without adapter work,
progressed guard fallback, runner-failure fallback, and cross-ISA lease

rejection.
`application/cached_retry.rs` composes exact lease-cache acquisition, leased
binding, and one loaded attempt. Cache hit performs no executable-memory work;
inserted acquisition retains FIFO eviction and live-retirement evidence. Load
failure restores the admitted retry plus exact load/cleanup ownership, while
binding or runner failure retains the acquired lease. Five cases cover inserted
completion, hit reuse, pre-runner load failure, mixed live-retirement insertion,

and runner-failure fallback. Semantic rebase and lease return remain
caller-owned.

`application/cached_cycle.rs` applies the immutable attempt policy to
cache-aware
execution. Every successful attempt records its one-based number, committed
native
steps, and exact `Inserted`/`Hit` evidence, then drops only the external lease;
active cache authority remains available. Unchanged guard suffixes therefore hit
the same resident sequence, while progressed suffixes acquire distinct exact
keys. Acquisition, binding, routing, or runner failure terminates immediately
with exact owners and every successful prior attempt. Seven cases cover
zero-limit fallback, `Inserted/Hit/Hit` guard reuse, progressed suffix
insertion,
initial and late pre-runner failure, initial routing failure, and runner failure

with normative fallback.
`application/cached_cycle/telemetry.rs` now provides one exact source view for
attempt slices, native completion, and normative fallback owners. Its pure
summary counts attempts, native steps, hits, insertions, evictions, and
retirements and fails closed on arithmetic overflow. `telemetry_window.rs`
retains summaries in a positive-capacity process-local FIFO with monotonic
sequences and exact aggregate totals. `telemetry_window/aggregation.rs` owns
checked arithmetic, while `telemetry_window/reconfiguration.rs` publishes

capacity changes with explicit oldest-first removals.
`telemetry_assessment.rs` applies caller-owned inclusive count thresholds
after a positive attempt gate and returns every simultaneous miss without
choosing a policy. `telemetry_snapshot.rs` transfers complete window state
and validates capacity, eviction count, contiguous sequences, and aggregate
totals before reconstruction. `telemetry_codec.rs` defines canonical
revision-one little-endian bytes and rejects magic, version, reserved, length,
representation, and semantic drift before returning a snapshot.
`telemetry_latency.rs` records explicit caller-measured nanoseconds into

inclusive buckets and publishes checked totals and extrema transactionally.
`telemetry_latency_snapshot.rs` transfers complete histogram state after
validating bucket/sample counts, occupied-bin extrema, and exact possible total
ranges. `telemetry_latency_merge.rs` combines identical bucket schemas only
after every merged count, total, and extremum is checked.
`telemetry_latency_codec.rs` defines canonical revision-one little-endian
histogram bytes with exact extrema flags, `u128` totals, bound/count pairs, and
repeated snapshot validation. Rebinning, distributed/durable merge, automatic
policy recommendation or publication, runtime clock acquisition, asynchronous

ownership, and durable storage remain outside this boundary.

`application/retry_planner.rs` adds explicit host routing above those owners. It
consumes one `NativeRetry` suspension plus runtime capability, OS, and ISA,
selects the exact remaining verified sequence, and admits it as a retry on
supported Windows hosts. Only direct `TargetFormat` absence becomes a normative
handoff. Profile, program shape, observation continuity, deoptimization,
emission, and verification failures are classified as stable hard errors and
retain the exact suspension. A legitimate retry suffix cannot newly fail profile
capacity: every retained program was already selected inside the verified direct

sequence that created retry authority. A regression rejects an overflowing step
as `MALBOLGE-PROFILE-002` before sequence-plan publication. Four cases cover
Windows native routing, Linux fallback before/after interpreter progress, hard
profile failure, and invalid schedule reason.

`application/retry_policy.rs` adds an immutable caller-configured maximum
attempt
count before host planning. If budget remains it returns the exact suspension
with completed and one-based next-attempt evidence. At or beyond the limit it
converts the owner to either complete normative interpretation or one configured
positive interpreter slice. A zero limit falls back immediately. Attempt counts
are always caller-supplied; non-`NativeRetry` reasons fail without losing the

suspension. Four cases cover attempts one/two, complete fallback, zero-limit
sliced fallback, and reason rejection.

`application/retry_router.rs` composes attempt policy and exact host planning as
one affine routing request. Exhausted attempts bypass host planning. Remaining
budget selects a one-based native attempt, while missing target format applies
the configured complete or sliced normative fallback without incrementing the
attempt count. Policy and hard planning failures return the exact suspension.
Five cases cover Windows native routing, exhausted-planner bypass, sliced format

fallback, hard profile rejection, and invalid scheduler reason.

`application/retry_turn.rs` executes exactly one selected route. Interpreter
routes run the configured scheduler decision and do not touch native adapters.
Native routes execute one admitted attempt and immediately rebase successful or
failed evidence. Both native outcomes expose the one-based attempt plus semantic
disposition; failed execution separately retains indexed runner/release
ownership.

Rebase rejection keeps the complete execution owner. Five cases cover normative
completion, native completion, guard fallback, runner failure, and semantic
completion with retryable cleanup.

`application/retry_cycle.rs` closes the first bounded multi-turn loop. Only a
successfully rebased native guard miss is rescheduled as a new `NativeRetry`;
immutable attempt policy guarantees eventual native completion or configured
normative fallback. Runner or release failure exits immediately with independent
semantic and native owners, so no hard failure is retried automatically. Seven
cases cover immediate and missing-format fallback, repeated guards to bounded
fallback, guard then native completion, runner and cleanup failure termination,
and hard routing rejection before adapters. Cached execution is owned by
`cached_retry.rs` and `cached_cycle.rs`; adaptive telemetry, asynchronous

ownership, and broader product scheduling remain outside.

`ReadyNativeExecutableSequence` provides the first persistent executable-chain
owner without fusing objects. It derives all load images before platform work,
loads every mapping before the first call, and releases a partial ready prefix
in reverse after a later load failure. Aggregate cleanup attempts every mapping
and
retains only failures for retry. Loaded execution first validates exact mapping
count and complete load-image equality for every position, so cross-ISA or
reordered chains fail before caller buffers change. One admitted chain can run

repeatedly without further memory-adapter operations. The adapter contract owns
unique mapping identities and non-overlapping live ranges. Seven deterministic
cases bind reuse, cached guard resume, partial cleanup, aggregate release,
prevalidation, and rollback.

`NativeExecutableSequenceCache` adds weighted process-local reuse above that
owner. One positive entry limit is always present; optional positive limits
bound
live mapping count and exact admitted mapped bytes. Exact identity remains the
ordered vector of complete artifact keys. A hit borrows the retained chain,
preserves FIFO age and usage, and performs no adapter operation. A miss loads
completely before accounting so candidate weight comes from admitted mapping

reports rather than object estimates. Candidates that exceed a mapping or byte
limit alone are fully released without changing existing authority. Otherwise
oldest entries are released repeatedly until projected entries, mappings, and
bytes all fit; insertion evidence retains every evicted key in order. Usage
publication is transactional: a late mapped-byte overflow leaves entry, mapping,
and byte counters unchanged. Failed later insertion eviction removes that victim
and prior successful victims from cache authority, attempts candidate cleanup,

and returns still-owned releases for retry. Exact invalidation and full drain
update usage before cleanup,
preventing stale budget retention after release failure. Rust borrowing still
prevents mutation while a returned chain is in use.
`reconfigure_limits()` stages weighted-limit publication against current usage.

Expansion and already-satisfied requests publish without adapter operations.
Shrink requests release oldest entries until all requested limits fit, but the
previous limits remain active until every required release succeeds. A failed
release removes that victim and prior successful victims from authority and
usage, retains the previous limits, reports every removed key, and returns exact
release ownership. After retry, the same request publishes without repeating
completed cleanup. Seventeen cases bind original reuse, weighted admission, and

cleanup plus expansion, entry/mapping/byte shrink, and second-eviction failure.
Transactional transition results, diagnostics, and FIFO shrink now live in
`executable_cache/reconfiguration.rs`; exact lookup/admission remain in the
parent cache module.

`NativeExecutableSequenceLeaseCache` adds cloneable immutable `Arc` leases above
that lifecycle. Active lookup and retired residency are separate queues. A hit
shares the exact ready sequence across threads without adapter work or FIFO age
change. Eviction, invalidation, and full drain end lookup authority, but a live
lease keeps its mappings and exact weighted usage resident. Lease clone/drop is
pure ownership accounting; platform release remains explicit through

`return_lease()` or `reconcile_retired()`. Reconciliation attempts every retired
entry with no external owner, preserves still-leased FIFO residents, and returns
keyed release failures for exact retry. If retired weight blocks a new
candidate, the candidate is cleaned and the failure exposes exact limits, usage,
active removals, and retired blockers. `reconfigure_limits()` publishes
expansion
or already-fitting requests without adapter work. Shrink removes active FIFO
authority, releases unleased victims, retires leased victims with exact resident

weight, and never implicitly reconciles prior retired entries. Blockage or keyed
release failure retains previous limits; final lease return or cleanup retry
then
permits the same request to publish without duplicate release. Fourteen cases
cover the original lease lifecycle plus entry/mapping shrink, live entry/byte
blockage, post-return publication, and release-failure retry. Mappings remain
independent; no durable or cross-process executable store, direct jumps, or
unsafe call shim is implied. Explicit retired reclamation and keyed cleanup
retry now live in `executable_lease_cache/reconciliation.rs`; resident-limit
transitions live in `executable_lease_cache/reconfiguration.rs`; lookup and
lease

publication remain in the parent module.

`select_preflighted_execution_tier()` is the first planning boundary above
direct
selection. It maps only top-level direct `TargetFormat` absence to the normative
interpreter after profile preflight. Windows returns the exact verified direct
artifact; noncanonical profile envelopes, `MALBOLGE-PROFILE-002`,
`MALBOLGE-PROFILE-001`, and any backend, emission, or admission failure remain
errors. This boundary performs no cache
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
all twelve current templates match uncached selection byte-for-byte and reuse
the
same immutable `Arc` allocation rather than cloning verified object bytes. A
populated
cache cannot bypass canonical-envelope admission, `002`, `001`, or non-Windows
interpreter selection, and those outcomes leave cache cardinality unchanged.
Exact-key invalidation removes one
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

Combined-region emission, native-retry orchestration beyond bounded
process-local cached cycles, asynchronous/product scheduling, executable-memory
platform implementations and foreign invocation, durable cache
serialization/storage and cross-process leasing, cache-aware AOT/JIT policy
beyond verified direct process-local reuse, and performance policy remain open.
The
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
  differential results against independent interpreter-compatible
  implementations; the original C source is compared only where its behavior is
  defined and reproducible.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`,
  `self-modification-state-graph-optimizer`.
- Current executable foundation is covered by `tests/state_graph_research.rs`
  and `tests/tiered_execution.rs`: artifact tampering fails closed, verified
  effects/deoptimization match their normative baselines, canonical IR matches a
  byte-exact independent fixture, forced bucket collisions keep process-local
  cache entries independent, cache-aware direct planning reports insert/hit
  with pointer-identical immutable artifacts, transactional sequence planning
  stages misses and rolls back late rejection, profile/host preflight remains
  authoritative, and profile-invalid IR cannot gain
  cache/bootstrap/direct identity, version-matched direct MBPF binds exact
  region memory, bootstrap source is
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
