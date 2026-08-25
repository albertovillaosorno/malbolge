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
