# Native artifact bootstrap

## Purpose

Own the first host-code lowering boundary from portable verified-effect IR to
explicitly untrusted native compilation artifacts.

## Owns

- structural validation required before native lowering;
- deterministic C23 bootstrap lowering from `RegionEffectProgram`;
- stable Rust representation of native call-frame ABI revision 1;
- exact binding to `NativeArtifactKey` target assumptions;
- untrusted native source/object artifact containers;
- fail-closed structural admission of self-contained Windows COFF objects;
- canonical versioned native profile metadata matched to exact native keys;
- canonical direct x86-64/AArch64 deopt-only objects with byte-exact semantic
  verification;
- target triples for the pinned Clang bootstrap backend.

## Does Not Own

- verification/admission of native machine code;
- executable-memory allocation or invocation;
- general x86-64/AArch64 region-effect instruction selection;
- deoptimization authorization or verifier lineage guards;
- durable native-cache storage.

## Contents

`main.rs` implements the bootstrap backend. It does not make C part of the VM
semantics: Clang is only an initial code-generation adapter used to cross the
first real host-object boundary while direct architecture backends remain open.

`abi.rs` owns the revision-1 call-frame representation shared by Rust and
the generated freestanding C. `NativeRegionState` is `repr(C)` and its
80-byte layout plus every field offset is fixed by tests on the supported
64-bit hosts. Typed status and termination values reject unknown foreign
integers. `NativeRegionCallFrame` binds raw ABI pointers to borrowed memory,
input, and output slices, rejects out-of-bounds cursors, and reconstructs an
exact normative observation after a future call. It does not allocate

executable memory, link objects, or invoke machine code.

`invocation.rs` owns the safe contract around one future foreign entry call.
`PreparedNativeRegionInvocation` requires one canonical one-effect program,
checks exact memory footprint, live-ins, input/EOF evidence, output movement,
and every memory-write before-value, then snapshots the full ABI state, memory,
and output surfaces. Completion admits `Applied` only when the resulting state,
memory, and output exactly equal the IR-derived transition. `GuardMiss` must
preserve every snapshot byte-for-byte; unknown status, unexpected
`InvalidArgument`, topology drift, and partial commits fail closed. Every

rejected completion restores the complete entry snapshot.
`PreparedVerifiedDirectInvocation` then binds that call contract to one
semantically admitted direct artifact. It reconstructs the full key with the
artifact's exact target, rejects canonical program drift, and refuses to grant
the deoptimization stub state-applying authority. `NativeRegionBuffers` groups
the memory/input/output loans, while verified COFF bytes, target identity,
target triple, and ABI pointer remain reachable only through the same binding.

`loader.rs` owns relocation-free load-image planning, not executable memory.
`VerifiedDirectLoadImage` reparses verified COFF, rejects relocations, extracts
only the exact `.text` bytes plus entry offset, retains the complete key and
target triple, and validates x86-64/AArch64 instruction alignment. Its fixed
policy permits RW staging followed by RX execution and requires instruction
synchronization after the permission transition. The prepared verified call
retains this image, so a future loader need not accept unrelated object bytes.
`lifecycle.rs` admits the future platform operations in one ordered typestate

protocol. `StagedNativeExecutable` requires exact code bytes in a sufficiently
large, aligned RW mapping. `SealedNativeExecutable` requires the same mapping to
be reported RX, and `ReadyNativeExecutable` requires synchronization of the
complete code range before exposing the non-zero entry address. It retains an
exact release request. `PreparedNativeExecutableInvocation` then compares the
ready image with the call-bound image before exposing entry address and ABI

state through one value. Platform reports are adapter evidence; no page
allocation,
permission syscall, instruction-cache operation, cleanup, or foreign call exists
yet.

`platform.rs` defines the caller-owned `NativeExecutableMemoryAdapter` port and
transactional orchestration. The loader derives an exact RW allocation request,
prevalidates the mapping before asking for a copy, verifies exact returned bytes
and copy identity, admits the same mapping as RX, and requests synchronization
of the complete code range. Every post-allocation failure attempts exact
release; primary adapter/lifecycle/evidence failure and cleanup failure remain
separately
inspectable. Explicit release consumes a ready executable only on success and
retains it for exact retry on failure. The retained fake adapter covers all 24
direct images, every operation failure, report drift, cleanup failure, and

retry. There is still no concrete Windows/POSIX executable-memory
implementation.

`runner.rs` defines `NativeExecutableRunner` around the already bound
`PreparedNativeExecutableInvocation`; implementations never receive unrelated
bytes, addresses, or ABI state. `execute_verified_native()` performs load, bind,
runner call, completion admission, and release as one safe transaction. Load and
runner failures abort the borrowed call snapshot, completion failures use the
same exact rollback, and cleanup failure retains the ready executable for retry.
If final release fails after admission, the committed outcome remains explicit.
Fake-runner evidence covers `Applied`, `GuardMiss`, load short-circuit, mutation
before runner failure, completion drift, cleanup retry, and committed release

failure. No concrete FFI runner or machine-code call is implemented here.

The generated function has a two-phase shape. It first validates its local ABI
state, exact entry observation, expected input bytes/EOF, memory live-ins, first
values of every written cell, and output capacity. Only after every local guard
passes does it append output, write each touched memory address once at its
final
value, and commit final registers/cursors/termination.

Those local checks are defense in depth, not verifier authority.
`RegionEffectProgram` deliberately lacks the complete Rust lineage identity used
by `VerifiedExactRegion::accepts_dependency_entry`; the host must cross that
verifier-owned guard before any future native runner can invoke this artifact.

Both source and compiler-output wrappers are named `Untrusted*`. Attaching bytes
to the correct cache key does not prove that those bytes implement the IR.
`NativeArtifactKey` construction nevertheless rejects
profile-capacity-inconsistent
IR before bootstrap source, direct deopt, or any state-applying object can be
created. This closes an impossible artifact identity without granting semantic
trust to otherwise unverified effects.

`profile_metadata.rs` owns the target-neutral MBPF payload encoding shared by
bootstrap source, direct object construction, and structural validation. MBPF v3
keeps the frozen `u32` profile-capacity field; v4, v5, and v6 carry capacity as
`u64`. V5 additionally carries explicit execution geometry, while v6 retains the
profile envelope and exact derived footprint for its complete masked IR key.
Object parsing and code generation consume this schema without becoming
authoritative over it.

`coff.rs` adds a narrower structural gate for Windows bootstrap objects. It
parses the object bytes directly in safe Rust, checks x86-64/AArch64 machine
identity against the native target key, requires one executable/non-writable
`.text`, requires the exact `malbolge_native_region_apply` entry, rejects other
external functions and undefined external dependencies, and permits relocations
only when they resolve to symbols defined inside the same object.

Direct backends
and `clang-c23-bootstrap` revision 2 must contain one initialized, read-only,
non-relocated `.mbprof` section. The MBPF version follows the IR identity: v3
uses `u32` profile capacity and v4 uses `u64`; both carry exact ID/fingerprint,
published version, semantic features, word trits, and derived `u64` region
memory. The complete envelope must equal the native key. Missing, duplicated,
executable, writable, relocated, malformed, or mismatched required metadata
fails structurally.

Bootstrap revision-2 source emits the payload as an external `const unsigned
char`
array allocated into a read-only custom section. Revision 1 remains structurally
admissible without metadata as a historical identity. The pinned Clang test owns
x86-64/AArch64 object confirmation. The resulting

`StructurallyAdmittedNativeObjectArtifact` is still not semantic authority. An
independent semantic validator must establish that boundary before executable
promotion exists.

The first direct backend is intentionally a deoptimization floor rather than a
fast path. `direct.rs` emits one deterministic Windows COFF object per ISA whose
only callable function returns native status `1` (`guard miss`) without reading
or writing the supplied state pointer. The exact x86-64 and AArch64 v3
objects are frozen by independently rendered
hex fixtures. V4 deopt objects use the same reviewed guard-miss machine code but
carry MBPF v4 bound to the v4 IR/key; tests require structural admission,
metadata tamper rejection, and byte-for-byte canonical semantic verification.

Semantic promotion requires structural COFF admission plus equality with the
canonical object; a one-byte opcode mutation remains structurally valid but
fails semantic admission. This establishes an executable native tier that is
correct by always falling back before direct region-effect selection is trusted.

Register-masked effect IR v6 now crosses a separate host-independent admission
boundary. `admit_register_masked_direct_native()` preserves full v6 identity and
required-profile preflight, then admits the normative C-only/no-write one-step
graphical halt-fetch and non-graphical terminal-fetch shapes.

`direct-register-masked-halt-fetch` revision 1 binds the graphical shape to
Windows x86-64/AArch64 objects and MBPF v6. Its machine code guards only C, the
required memory extent, the fetched code cell, and prior termination before
committing `HaltInstruction`; A and I/O history are not guarded directly.
Independent object verification reconstructs the full v6 key and canonical
bytes.

`direct-register-masked-non-graphical` revision 1 binds the non-graphical shape
to the same two ISAs and reduced guard sequence, committing only
`NonGraphicalCell`. Its distinct verified artifact wrapper remains outside the
halt executable lifecycle.

`VerifiedRegisterMaskedNonGraphicalLoadImage` now feeds distinct `Staged`,
`Sealed`, and `Ready` lifecycle typestates. They admit exact writable copy,
same-mapping RX protection, and full-range instruction synchronization while
retaining complete v6 identity and cleanup evidence.

The shared platform port now has a non-graphical-specific load/release path. It
transactionally allocates, copies, protects, synchronizes, and cleans up the
distinct ready type, preserving release-failure ownership for exact retry.

`PreparedRegisterMaskedNonGraphicalInvocation` binds exact v6 identity, C and
fetched-cell live-ins, rebased dead state, and atomic Applied/GuardMiss
completion. `bind_executable()` requires exact equality with the dedicated ready
image before producing the distinct bound non-graphical invocation view.

`RegisterMaskedNonGraphicalNativeRunner` now receives only that bound view. The
loaded-call wrapper admits exact Applied/GuardMiss results, restores the rebased
snapshot on runner or completion failure, and rejects ready-image drift before
runner entry.

`execute_verified_register_masked_non_graphical_native()` now composes exact
load, bind, run, completion, and release. Load/call failures restore the rebased
snapshot and attempt cleanup; final release failure preserves both the committed
outcome and exact ready mapping for retry.

`RegisterMaskedNonGraphicalNativeExecutableOwner` retains one exact program,
verified artifact, and synchronized mapping for repeated rebased non-graphical
calls without adapter work. Runner failure rolls back the call while preserving
that owner for reuse, and resident weight comes from the platform mapping.

`RegisterMaskedNonGraphicalNativeResidentLeaseCache` adds a distinct single
resident slot. Exact hits share one immutable owner without adapter work, a
different identity cannot replace it, live leases block release, failed load
publishes nothing, and failed release transfers exact retry ownership.

`RegisterMaskedNonGraphicalLeaseCache` now adds fixed-limit multi-entry
residency without widening the halt cache. Exact hits preserve FIFO age and do
no adapter work; misses process active FIFO entries oldest-first, releasing
unleased residents and retiring live leased residents while their exact weight
remains charged. Explicit invalidation uses the same release-or-retire rule,
`release_all()` ends all active lookup authority, and lease return or explicit
reconciliation reclaims retired mappings.

Oversize candidates fail closed, and both insertion cleanup and reconciliation
preserve aggregate keyed retry ownership.

Explicit weighted-limit reconfiguration now publishes expansion or already-fit
requests without adapter work. Shrink processes active FIFO authority through
the same release-or-retire path while prior retired mappings remain untouched;
blockage or cleanup failure retains the previous limits and exact evidence for
retry. The cache itself does not execute sequences.

`RegisterMaskedNonGraphicalNativeSequencePlan` adds plan-only sequence
admission without mapping authority. It validates exact count, one-effect v6
shape, canonical profile/observation continuity, common target, complete
artifact identity, and no termination before a later position. Current
non-graphical terminal coverage therefore admits one executable semantic step.

A separate loaded owner maps every admitted step only after complete success,
reports exact mapped weight, and releases in reverse with aggregate retry
ownership. `execute_loaded_register_masked_non_graphical_native_sequence()`
runs those retained mappings in semantic order only through the dedicated
non-graphical runner. Applied and guard-miss outcomes retain exact progress;
current-step failure restores through the owner contract and leaves the mapping
reusable. Loading and release remain explicit adapter operations outside
execution.

`VerifiedRegisterMaskedLoadImage` now extracts that verified object as a
relocation-free, ISA-aligned image under the shared strict W^X policy without
making it executable. `PreparedRegisterMaskedHaltFetchInvocation` binds the
image to a caller observation where dead A, D, and I/O cursors may be rebased.
C, the fetched-cell live-in, memory capacity, running termination, and buffer
cursor validity remain fail-closed.

Applied completion preserves the rebased dead state and changes only
termination; guard miss reuses the common atomic rollback contract.

Register-masked v6 now has dedicated `Staged`, `Sealed`, and `Ready` executable
typestates over `VerifiedRegisterMaskedLoadImage`. The shared platform adapter
still owns RW allocation, exact copy, RW-to-RX protection, instruction sync, and
release, but its v6 entrypoint returns only
`ReadyRegisterMaskedNativeExecutable`.

`PreparedRegisterMaskedHaltFetchInvocation::bind_executable()` requires exact
v6 load-image equality before producing
`PreparedRegisterMaskedNativeInvocation`.
The separate `RegisterMaskedNativeRunner` port can see the synchronized entry,
mapping identity, and ABI pointer only through that bound view. Loaded execution
keeps rebased state on Applied/GuardMiss and restores it on runner or completion
failure; a different v6 key fails before runner entry.

`execute_verified_register_masked_native()` now owns the complete one-shot v6
load/bind/run/admit/release transaction. Load or call failure restores the
rebased snapshot and attempts exact cleanup; release failure after a committed
result retains both that outcome and the exact ready v6 executable for retry.

`RegisterMaskedNativeExecutableOwner` now retains one exact program, verified
artifact, and synchronized mapping for repeated rebased halt calls without
adapter work. Its resident weight comes from the exact mapping report, and a
runner failure rolls back the call while leaving the mapping reusable.

`RegisterMaskedNativeResidentLeaseCache` adds one exact process-local resident
slot with immutable `Arc` leases. Exact hits do not remap, a different identity
cannot replace the resident implicitly, live leases block release, and cleanup
failure transfers the exact ready executable for retry.

`RegisterMaskedNativeLeaseCache` adds fixed-limit multi-entry v6 residency
without weakening that exact ownership. Active lookup is FIFO and exact hits
preserve age without adapter work. Entry, mapping, and mapped-byte limits use
admitted mapping reports; oldest unleased residents release immediately, while
leased victims retire and keep their exact weight charged until explicit return
or reconciliation.

A blocked miss cleans its loaded candidate, invalidation and full drain preserve
live leases, and failed eviction/reconciliation release transfers keyed
ready-executable ownership for exact retry. `reconfigure_limits()` publishes
expansion or already-fitting requests without adapter work and shrinks through
active FIFO release/retirement. Live leased victims keep their exact weight
charged; prior retired entries are not reconciled implicitly.

Blockage or cleanup failure keeps the previous limits published and returns
exact evidence for idempotent retry. Durable storage and cross-process leases
remain outside.

`RegisterMaskedNativeSequencePlan` now validates the complete ordered v6 chain
before mapping: non-empty/count exactness and one-effect v6 shape; canonical
profile continuity, exact trace observation chaining, common native target,
exact artifact identity, and no termination before a later position. Loading
publishes
all owners only after every mapping succeeds; loaded execution reports exact
Applied/GuardMiss/failure progress and explicit reverse release retains retry
ownership. Because halt-fetch is still the only admitted v6 template, every
currently executable plan has one terminal step; two halts are rejected as a
terminated prefix rather than treated as an artificial batch. Wider mask-aware
templates remain outside this sequence boundary.

The deopt and initial-halt backends remain revision 4. The wider
`direct-halt-registers` observation contract is revision 5, while
`direct-halt-fetch`, `direct-non-graphical`, and `direct-no-operation` use
revision 2 after binding their runtime capacity guard to the exact IR footprint;
`direct-jump-code`, `direct-jump-data`, `direct-rotate`, `direct-crazy`,
`direct-input`, and `direct-output` start at revision 1.

State-applying direct templates accept canonical IR/MBPF v3 or v4 when declared
profile capacity fits their `u32` word/address representation. The same geometry
gate protects native invocation. Direct-deopt can additionally carry N21 v4
because its code only returns guard-miss and never touches guest state.

The second direct template is the first state-applying fast path. The
`direct-initial-halt` backend accepts exactly one portable-IR shape: one effect
from zero registers/counters with no I/O, no memory live-ins/writes, and no
prior
termination to the same observation with `HaltInstruction`, one-step terminated
outcome, and budget one. Its machine code preflights those ABI fields before the
first write, sets only the termination byte to halt, and returns `applied=0`;
any
mismatch or null state returns `guard-miss=1` without mutation. Complete x86-64
and AArch64 COFF bytes are independently frozen. A changed commit immediate may

remain structurally valid but fails semantic admission. Development evidence
links both ISA objects and executes x86-64 hit/miss/null cases, with miss state
byte-identical before and after. General region-effect code generation remains
outside this reviewed subset.

`select_verified_direct_native()` now owns deterministic direct-template
selection for the implemented Windows surface. The caller supplies one explicit
`RuntimeCapability`; the selector derives exact region memory from the IR and
checks profile capacity before runtime capability, host validation, or backend
construction. An out-of-profile address returns typed
`MALBOLGE-PROFILE-002`; an unsupported runtime returns the shared typed
`MALBOLGE-PROFILE-001`. Neither is replaced by deopt or masked as a host-format
result.

After program/profile/runtime admission, the selector classifies IR before
creating a backend identity: exact zero-observation halt selects
`direct-initial-halt`, any other no-live-in one-step halt selects
`direct-halt-registers`, an exact graphical `v` fetch selects
`direct-halt-fetch`, an exact non-graphical fetch selects
`direct-non-graphical`, an exact non-aliasing `i` transition selects
`direct-jump-code`, an exact non-aliasing `j` transition selects
`direct-jump-data`, an exact non-aliasing `*` transition selects
`direct-rotate`, an exact non-aliasing `p` transition selects `direct-crazy`,
an exact transition using the selected profile input instruction selects
`direct-input`, an exact transition using its output instruction selects
`direct-output`, and an exact no-op
fetch/encryption/advance selects
`direct-no-operation`, and every remaining IR selects byte-verified deopt.
Profile, backend, emission, and verification errors are never reinterpreted as
fallback, and an unsupported host format still fails explicitly when the profile
is supported. This removes backend-ID choice from callers while keeping
unsupported IR safe.

`select_verified_direct_sequence()` adds the first multistep direct planning
boundary without inventing a combined object. The caller supplies exact one-step
programs projected from complete VM traces. Every step must preserve canonical
profile identity, contain exactly one effect with budget one, and begin at the
byte-exact prior exit observation. A non-final termination, any ordinary direct
selection/admission failure, or a selected deoptimization stub rejects the whole
sequence before a `VerifiedDirectSequencePlan` is returned.

`DirectFusedSequenceAdmission` now consumes only such a verified plan and
derives one canonical multieffect `RegionEffectProgram`. It folds ordered
read/write evidence into exact region-entry live-ins, binds the complete region
to the distinct `direct-fused-sequence` revision-1 target, and retains both the
full verified source plan and its ordered `NativeExecutableSequenceKey`.
Single-step plans are rejected so this identity cannot alias an existing direct
template.

`direct/fused.rs` now emits the retained rotate/output region as one atomic
x86-64 or AArch64 COFF candidate. Both ISA templates complete every fused
entry, memory, termination, and output-capacity guard before their first store;
a miss therefore preserves the original region entry rather than a step prefix.

Semantic promotion reconstructs the fused admission from the retained verified
source plan, structurally admits COFF, regenerates canonical bytes, and requires
exact equality. A structurally valid text-byte mutation fails this verifier.

`VerifiedDirectFusedLoadImage` now reparses only that verified fused object,
rejects relocations, validates ISA alignment, and retains exact key/triple plus
the strict RW-to-RX/full-sync policy. Distinct fused `Staged`, `Sealed`, and
`Ready` typestates then admit exact copy, same-mapping RX transition, and
full-range instruction synchronization.

A fused-specific platform path now runs allocate, copy, RW-to-RX protect, full
instruction sync, and explicit release through the caller-owned memory adapter.
Every post-allocation failure attempts exact cleanup while preserving primary
and cleanup evidence separately, and failed explicit release retains the exact
ready executable for retry.

`PreparedDirectFusedInvocation` now reconstructs retained fused admission before
borrowing caller buffers, validates the whole region entry, and replays every
ordered effect into the only accepted final state/memory/output snapshots. Exact
application and mutation-free guard miss are admitted; every rejected completion
restores the complete region entry.

Exact `VerifiedDirectFusedLoadImage` equality now binds that prepared call to
one synchronized `ReadyDirectFusedNativeExecutable`. The bound view exposes only
the exact entry address, mapping identity, executable evidence, and borrowed ABI
state pointer; image mismatch restores the complete region entry before failing.

A dedicated `DirectFusedNativeRunner` now receives only that bound whole-region
view. Loaded execution performs no memory-adapter work, admits exact Applied or
GuardMiss outcomes, and restores the complete region entry on runner or
completion failure.

One-shot fused orchestration now composes exact load, bind, run, completion, and
release. Load/call failure restores the complete region entry and retains
cleanup failure separately from the primary cause; final-release failure keeps
the committed Applied or GuardMiss outcome plus the exact ready mapping for
retry.

`DirectFusedNativeExecutableOwner` now retains one verified fused artifact and
one synchronized mapping for repeated whole-region calls without adapter work.
Runner or completion failure rolls back only that call while the owner remains
reusable; resident weight comes from the platform mapping, and explicit release
retains exact retry ownership.

`DirectFusedNativeResidentLeaseCache` adds one exact process-local resident
slot. Exact artifact hits clone immutable `Arc` leases without adapter work, a
different artifact cannot replace the resident implicitly, live leases block
release, failed load publishes nothing, and failed release transfers exact ready
retry ownership.

`DirectFusedNativeLeaseCache` now separates active lookup from retired leased
residency under one weighted capacity account. Hits preserve FIFO age without
adapter work; misses process active FIFO entries oldest-first, releasing
unleased victims and retiring leased victims while their exact weight remains
charged.

Explicit invalidation, full drain, lease return, and retired reconciliation end
lookup authority without hidden reclamation. Weighted-limit reconfiguration
now publishes expansion without adapter work and shrinks active FIFO authority
through the same release-or-retire path.

Pre-existing retired residents are never reconciled implicitly. Blocked or
failed publication keeps the previous limits plus exact blocker or keyed retry
evidence.

A distinct fused-region sequence plan now reconstructs every retained admission
and admits only common-target/profile chains with exact exit-to-entry
continuity. It retains region count, source semantic-step total, exact
entry/exit, and complete outcome before any mapping. A separate loaded owner
now publishes only after every exact fused region maps successfully, retains
exact mapped-byte evidence, and releases mappings in reverse with aggregate
retry ownership.

A dedicated loaded-sequence executor calls only the fused
runner through retained owners and performs no adapter work. Applied outcomes
advance exact source semantic-step progress; guard miss or current-region
failure resumes before that whole fused region and leaves the mapping reusable.

One-shot fused sequence orchestration now composes full-plan load, loaded
execution, and aggregate release. Load/execution failure keeps cleanup retry
evidence separate from semantic failure, while final-release failure preserves
the committed Applied or GuardMiss outcome.

Exact cache-region leases can now be bound to one admitted fused sequence only
when ordered lease keys match every admitted artifact. Admission rejection
returns every supplied lease, while execution uses the retained mappings with no
adapter work and preserves the same region/semantic progress contract.

Ordered cache acquisition now calls the existing per-region lease cache in
admitted order and returns exact dispositions plus indexed failure ownership.
Successful `ensure()` effects remain visible; later failure does not restore
FIFO or retired state and retains every earlier lease.

An immutable fused continuation now validates GuardMiss or indexed failure at
exact fused-region boundaries. It retains complete/remaining fused keys,
flattened verified source programs, canonical geometry, final outcome, and both
region/source-step resume indices; completed work yields no continuation.

A separate fused interpreter handoff now admits an exact checkpoint or native
transfer buffers, reconstructs the normative profile machine, and
executes/reprojects every retained one-step source program. Initial live-ins are
checked before work starts; later source-step mismatch restores that step entry
while keeping an already admitted prefix. Completion must reproduce the exact
fused plan exit and total outcome.

Explicit source-step budgets now return an affine suspension with cumulative
interpreter progress, complete-plan resume step, exact normative checkpoint, and
remaining verified source programs. Zero budget preserves state, partial budget
resumes without readmission, and oversized budget completes. Mid-region pauses
do not claim a new fused-region cache key.

An explicit fused scheduler now consumes that affine owner with complete,
positive interpreter-slice, caller-yield, or native-retry-yield decisions.
Pauses retain exact checkpoint/source suffix/progress plus a stable stop reason;
rescheduling consumes the same owner.

A separate fused retry-admission boundary now binds one caller-replanned fused
plan to an exact `NativeRetry` suspension before native work. Scheduler reason,
remaining source programs, ordered fused-region keys, and checkpoint entry must
all match; rejection returns both owners. A pause inside a fused region has no
fabricated region identity and therefore rejects the original whole-region plan.

Admitted fused retries now execute through the existing uncached fused sequence
transaction from checkpoint-derived owned buffers. Success and failure retain
the original plan/suspension plus exact transferred state; checkpoint
reconstruction is validated. Guard miss and runner failure preserve region-entry
state, while committed final-release failure preserves semantic state plus exact
cleanup retry ownership.

A separate semantic rebase now advances only across verified whole fused regions
and preserves original complete-plan authority. Applied retry work completes the
original outcome, while guard/load/runner failure returns a scheduler-ready
normative handoff; cleanup failure may complete semantics while retaining its
transaction/release owner independently.

Explicit host routing now replans one `NativeRetry` suspension for Windows
x86-64/AArch64, regenerates and verifies the exact fused object, and
readmits the reconstructed plan before native work. Missing target format and a
one-step
mid-region suffix route normatively to the interpreter; profile, IR, object, and
identity drift remain hard ownership-preserving failures.

Already-acquired fused sequence leases can now bind to one admitted fused retry
only when the acquired sequence plan exactly matches retry authority. Resident
execution performs no further memory-adapter work; cross-plan rejection restores
both owners, and runner failure preserves exact rollback state plus the reusable
leased sequence. Automatic retry cache acquisition, leased semantic rebase, and
transactional cache rollback remain separate.

The retained two-step fixture is produced by the normative VM from a rotate
followed by output. Trace projection deduplicates repeated fetch/encryption
reads, and both x86-64 and AArch64 plans contain verified `direct-rotate` and
`direct-output` artifacts with exact regional entry, exit, and two-step outcome.
`select_cached_verified_direct_sequence()` adds an explicit caller-owned cache
transaction around the same admission. It prepares every exact target first,
reuses full-key hits through their existing `Arc`, verifies all unique misses in
local staging, and inserts those misses only after the complete sequence

succeeds. A late failure therefore publishes no partial cache state. Retained
tests cover two inserts followed by two pointer-identical hits, one hit plus one
insert, preflight-before-lookup, and rollback that preserves an unrelated cached
`Arc`.

The planners still do not fuse objects. `sequence_runner.rs` executes their
one-step artifact/program pairs through the existing safe transaction in exact
order. Prior `Applied` steps remain committed; a `GuardMiss` leaves its current
step untouched and returns the exact resume index plus observation. Indexed
failures retain committed-step count, continuation state, nested one-step error,
and release retry evidence. Cached and uncached rotate/output plans match VM

snapshots after one and two steps.

`sequence_continuation.rs` turns that indexed evidence into an immutable exact
semantic suffix. Constructors cover cached/uncached plans and ephemeral/loaded
failures. They validate completed count, failing step, resume index, and the
next one-step entry observation before cloning remaining programs. The object
retains complete and suffix `NativeExecutableSequenceKey` identities, expected
exit/outcome, reason, and remaining one-step programs. Applied completion and

terminal cleanup failures return no continuation. `advance()` rebases the
same complete-plan authority after additional admitted tier progress, deriving
an exact suffix or verified completion. Eleven tests cover valid paths, forged
evidence, partial rebase, completion, and drift rejection. This boundary does
not invoke
the interpreter, borrow mappings, or transfer mutable VM buffers; the separate
application handoff owns that mutation.

`executable_sequence.rs` adds explicit persistent ownership for all mappings in
one exact plan. It derives every load image before allocation, loads all
mappings before execution, rolls back a partial prefix in reverse order, and
retains
aggregate cleanup failures for retry. Loaded sequence execution validates exact
mapping count and complete image equality before borrowing caller buffers. The
same chain can then execute repeatedly without new allocate/copy/protect/sync

operations. Final release attempts every mapping and keeps only failed releases.
The adapter must provide unique identities and non-overlapping ranges for all
simultaneously live allocations. Tests cover uncached reuse, cached guard miss,
partial-load cleanup, aggregate release, cross-ISA rejection, and runner
rollback.

`executable_cache.rs` and `executable_cache_capacity.rs` add a weighted
caller-owned FIFO over complete loaded sequences. Exact identity remains the
ordered list of full artifact keys. `new()` bounds whole entries only;
`with_limits()` can also bound live mappings and admitted mapped bytes. Weight
comes from exact ready mapping reports after load. Oversized candidates are

released without changing prior entries. Candidates that fit alone evict as many
oldest entries as necessary for all projected limits, and inserted dispositions
return every evicted key in FIFO order. Hits borrow the same mappings, preserve
insertion age and usage, and perform no adapter work. Failed insertion eviction
removes cache authority for that victim and earlier successful victims, cleans
the candidate, and retains failed release ownership. Invalidation and full drain

update accounting before cleanup, so errors cannot leave stale budgets.
`reconfigure_limits()` publishes expansion or already-satisfied requests without
adapter work. Shrink requests release oldest entries until current usage fits,
then publish atomically. Until all required releases succeed, the prior limits
remain active. Failure reports every key whose authority was removed and retains
the exact failed executable for retry; repeating the request after cleanup does

not release completed victims again. Seventeen tests cover original reuse,
weighted admission and cleanup plus expansion, entry/mapping/byte shrink, and
second-eviction failure. Transition result/diagnostic ownership and FIFO shrink
are isolated in `executable_cache/reconfiguration.rs`; lookup and candidate
admission remain in `executable_cache.rs`.

`executable_lease_cache.rs` adds shared immutable sequence ownership without
moving platform cleanup into `Drop`. Exact hits clone one `Arc` and can be read
from separate threads without adapter operations or FIFO refresh. Eviction,
invalidation, and full drain remove active lookup authority; a live lease moves
the entry to a retired FIFO where its exact weight remains charged. Explicit
`return_lease()` and `reconcile_retired()` attempt only residents whose final
external lease has gone, while aggregate keyed failures retain exact retry
ownership. A candidate blocked by retired resident weight is cleaned and reports

its limits, usage, active evictions, and retired blockers.
`reconfigure_limits()`
publishes expansion or already-fitting requests without adapter work; shrink
releases unleased active FIFO victims, retires leased victims with charged
weight,
and never implicitly reconciles prior retired residents. Blockage or keyed
release failure retains previous limits and exact ownership, while final lease
return or cleanup retry allows the same request to publish without duplicate
release. Fourteen tests cover the original lease lifecycle plus entry/mapping
shrink, live entry/byte blockage, post-return publication, and cleanup retry.
Retired reclamation and keyed cleanup retry are isolated in
`executable_lease_cache/reconciliation.rs`; resident-limit transitions are in
`executable_lease_cache/reconfiguration.rs`; lookup and lease publication remain

in the parent. Objects remain separate mappings; there is no durable loaded
state, cross-process leasing, direct inter-mapping jump, or concrete
foreign-call
shim.

`select_preflighted_execution_tier()` adds the first product-neutral planning
boundary above direct selection. It first requires the transported profile
requirement to exactly match the canonical envelope for its declared profile ID.
A supported Windows direct object returns `PreflightedExecutionTier::Direct`;
Linux/macOS format absence returns `Interpreter` only after the same canonical
profile/program/runtime preflight. Noncanonical profile envelopes, `002`, `001`,
and all post-selection emission/admission errors remain errors. The planner does

not perform cache lookup, executable-memory allocation, linking, or execution.

`select_cached_preflighted_execution_tier()` composes the same boundary with a
caller-owned `VerifiedDirectNativeCache`. Canonical profile-envelope admission,
profile capacity/runtime, and explicit `DirectHost` format selection happen
before lookup. A private
`PreparedDirectTarget` binds the selected specialization to one exact
`NativeArtifactKey`; that same key drives lookup and, on a miss, is consumed by
object emission before the admitted artifact key is inserted. Emission therefore
does not canonicalize the IR a second time. State-applying semantic verifiers
still reconstruct the expected key independently from IR, preserving their trust

check. The result is either `DirectCacheDisposition::Hit` or a newly admitted
`Inserted` artifact. Cache entries and returned plans share the same immutable
`Arc<VerifiedDirectNativeArtifact>`, so a hit does not clone object bytes. Only
verified direct artifacts can enter this wrapper; the generic cache remains
non-authoritative. `VerifiedDirectNativeCache::invalidate()` removes future
reuse

for one exact verified key. `invalidate_program()` constructs exact region
identity before mutation and removes every host/backend variant of that program;
profile-capacity-invalid IR returns `NativeIdentityError::ProfileCapacity`
without
changing the cache. `invalidate_target()` removes every region sharing one
artifact's exact OS/ISA/backend revision/native-ABI/features identity while
preserving other ISAs and backends. All invalidation operations leave
outstanding
`Arc` plans valid; reinsertion produces the same keys/bytes under new
allocations.
Unrelated regions/targets, interpreter selection, and profile failures remain

unchanged. There is no automatic eviction or revocation. Persistence,
eviction policy, synchronization policy, linking,
executable memory, and the unsafe foreign-call boundary remain outside; `Arc`
supplies ownership only, not concurrent execution.

The state-applying emitters and semantic verifiers also check the derived region
footprint against the profile capacity embedded in IR. Every memory-backed
direct
object additionally compares ABI `memory_words` against the exact
`NativeArtifactKey` IR footprint before any dereference or commit; output
pointers
therefore cannot escape the supplied backing image. Direct calls that bypass the
selector cannot promote `direct-initial-halt`, `direct-halt-registers`,
`direct-halt-fetch`, `direct-non-graphical`, `direct-no-operation`,
`direct-jump-code`, `direct-jump-data`, `direct-rotate`, `direct-crazy`,
`direct-input`, or `direct-output` when the declared
profile envelope is too small; they fail as out-of-contract program shape before
object promotion.

`direct-halt-registers` revision 5 generalizes the halt template across the
complete 32-bit `A`, `C`, and `D` domains plus full 64-bit `input_consumed` and
`output_len` observations, while still admitting no memory or I/O effects.
x86-64
loads each counter with `mov rdx, imm64` before exact comparison; AArch64
materializes all four counter halfwords with reviewed `movz`/`movk` sequences.
Both ISAs patch every guard branch to one non-mutating miss return and commit
only
the halt byte after all checks pass. Independent 495-byte x86-64 and 564-byte
AArch64 fixtures bind counters above `u32::MAX` plus the nontrivial
`0x12345678 / 0x00345678 / 0x0013579b` register case. Counter or opcode identity

tampering fails semantic admission, and revision-4 target identity is rejected.
Development execution now proves an x86-64 full-width counter hit plus atomic
counter miss; ARM64 full-width immediates and the common miss target are decoded
independently from the fixture. Executable invocation policy remains outside
this
module.

`direct-halt-fetch` revision 2 binds the halt termination to real verifier-owned
code memory. It accepts exactly one live-in at `C` whose VM-owned
`decode_profile_instruction()` result is `v`. Both ISAs reuse the
fetched-terminal
guard sequence: full entry observation, non-null memory, exact IR footprint,
`memory[C]`, and prior live termination precede the sole write of tag `1`.
Independent complete objects are 535 bytes on x86-64 and 628 bytes on AArch64.
Development execution proves x86-64 hit plus atomic live-in, capacity, and null
memory misses; independent AArch64 decoding confirms the full guards, halt tag,

and common miss target.

`direct-jump-data` revision 1 adds the first instruction-specific semantic data
read. It admits exactly two distinct live-ins at entry `C` and `D`; the VM-owned
decoder must classify `memory[C]` as `j`, and aliasing `C == D` remains
rejected.
The verifier derives code encryption, `C+1`, and `memory[D]+1` through VM-owned
helpers and requires the exact no-I/O exit observation and encryption delta.
Both
ISAs guard the complete entry, exact 125-word footprint, code live-in 35, and
data
live-in 123 before atomically committing `memory[5]:35->93`, `C:5->6`, and
`D:7->124`. Independent complete objects are 564 bytes on x86-64 and 699 bytes
on

AArch64. Development execution proves exact hit behavior plus atomic
code-live-in,
data-live-in, footprint, and null-memory misses; independent AArch64 decoding
confirms both reads, the exact commit, and one common miss target.

`direct-jump-code` revision 1 adds the exact post-jump encryption order. It
admits
three distinct live-ins: the entry code cell, the entry data cell, and the cell
addressed by `memory[D]`; VM-owned decode must classify the first as `i`. The
verifier derives encryption of the loaded target plus successors for loaded `C`
and entry `D`. Both ISAs guard the complete entry, exact 13-word footprint,
`memory[5]=93`, `memory[7]=11`, and `memory[11]=68` before committing only
`memory[11]:68->33`, `C:5->12`, and `D:7->8`. Independent complete objects are

622 bytes on x86-64 and 731 bytes on AArch64. x86-64 uses twelve reviewed
`rel32`
guards sharing one miss; development execution proves exact hit and atomic
code/data/encryption/footprint/null misses. Independent AArch64 decoding
confirms
three ordered reads, the commit, and twelve branches to one miss target.
Aliasing
among any of the three addresses remains rejected.

`direct-rotate` revision 1 adds the first reviewed transition with two
guest-memory
writes. It admits two distinct live-ins at entry `C` and `D`; VM-owned decode
must
classify `memory[C]` as `*`, and `profile_rotate()` derives the exact data
result
within the declared word domain. Both ISAs guard the complete entry, exact
9-word
footprint, `memory[5]=34`, and `memory[7]=10` before committing
`memory[7]:10->1594326`, `memory[5]:34->122`, `A:0xdeadbeef->1594326`,
`C:5->6`, and `D:7->8`. Independent complete objects are 578 bytes on x86-64 and
732 bytes on AArch64. Development execution proves exact hit behavior plus
atomic
code-live-in, data-live-in, footprint, and null-memory misses; independent
AArch64
decoding confirms two ordered reads, both writes, the three register commits,
and

eleven branches to one miss target. Aliasing `C == D` remains rejected.

`direct-crazy` revision 1 adds the second reviewed two-write arithmetic
transition. It admits distinct entry `C/D` live-ins, requires VM-decoded `p`,
and rejects data or accumulator operands outside the declared word domain. The
VM-owned `profile_crazy(memory[D], A, word_trits)` helper derives the exact data
and accumulator result. Both ISAs guard the complete entry, exact 9-word
footprint, `memory[5]=57`, and `memory[7]=10` before committing
`memory[7]:10->2391494`, `memory[5]:57->91`, `A:20->2391494`, `C:5->6`, and
`D:7->8`. Independent complete objects are 577 bytes on x86-64 and 731 bytes on

AArch64. Byte-exact fixtures and semantic tampering rejection bind the contract.
Aliasing `C == D` remains rejected.

`direct-output` revision 1 is the first reviewed direct I/O transition. One
code-cell live-in must VM-decode as `<`; VM-owned `profile_low_byte()` derives
the appended byte. Both ISAs guard the complete entry, exact 9-word footprint,
`memory[5]=94`, non-null output storage, and capacity greater than output index
3 before committing `memory[5]:94->57`, `C:5->6`, `D:7->8`, byte `0xa8`, and
`output_len:3->4`. Independent complete objects are 642 bytes on x86-64 and 724
bytes on AArch64. x86-64 execution proves exact hit plus atomic code, capacity,

output-pointer, footprint, and memory-pointer misses.

`direct-input` revision 1 completes direct coverage of all eight instruction
families. One code-cell live-in must VM-decode as `/`. The byte form guards a
non-null input pointer, `input_len > input_consumed`, and the exact byte before
committing `A=65`, `input_consumed:2->3`, encrypted code 68, and `C/D=6/8`.
The EOF form guards `input_len == input_consumed`, never dereferences the input
pointer, and uses VM-owned `profile_eof_word()` to commit `A=4782968` while
leaving the cursor at 2. Independent complete objects are 659/744 bytes for the

byte form and 634/715 bytes for EOF on x86-64/AArch64. Development x86-64
execution proves exact hits and atomic pointer, length, byte, footprint, code,
and null-memory misses.

`direct-no-operation` revision 2 is the first admitted non-terminal direct
effect
and the first direct guest-memory write. It accepts exactly one code-cell
live-in
at `C` that the VM-owned `profile_cell_decodes_to_no_operation()` classifies as
no-op. The verifier independently derives `encrypt_profile_cell(memory[C])` and
modular `profile_pointer_successor()` results for `C` and `D`, then requires the
IR memory delta and exit observation to match exactly. Both ISAs reuse the
fetched
cell guards and commit only the encrypted code word plus the two advanced
pointers. Independent complete objects are 557 bytes on x86-64 and 658 bytes on

AArch64. Development execution proves `memory[5]:77->65`, `C:5->6`, `D:7->8`,
and atomic live-in/capacity/null-memory misses; independent AArch64 decoding
confirms the same writes and one common miss target. Input effects, linking,
executable-memory ownership, and invocation policy remain outside this subset.

`direct-non-graphical` revision 2 is the first direct template whose eligibility
and machine code depend on verifier-owned memory evidence. It accepts exactly
one
non-graphical termination effect with one live-in at the entry code pointer. The
VM-owned `profile_cell_is_graphical()` predicate classifies the live-in; native
code does not redefine the graphical ASCII boundary. Both ISAs guard the
complete
entry observation, non-null memory pointer, exact IR footprint, exact
`memory[C]`, and prior live termination before writing only termination tag `2`.

Independent complete objects are 538 bytes on x86-64 and 631 bytes on AArch64.
Development execution proves x86-64 hit plus atomic live-in, capacity, and null
memory misses; independent AArch64 decoding confirms full observations,
capacity/live-in instructions, and one common miss target. No direct memory
write,
I/O effect, linking, executable-memory ownership, or invocation policy is added.
