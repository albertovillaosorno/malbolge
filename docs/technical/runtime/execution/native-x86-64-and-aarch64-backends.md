# Native x86-64 and AArch64 backends

## Status

Active bootstrap; direct ISA backends proposed

## Purpose

Implement native-code emitters for x86-64 and AArch64 behind one execution-IR
backend contract. Architecture-specific register allocation, instruction
selection, calling conventions, executable-memory handling, instruction-cache
synchronization, and hardening remain adapters rather than VM semantics.

## Scope

This document governs the following declared TODO scope:

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`native-x86-64-and-aarch64-backends`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

A shared bootstrap host-code path is now implemented under
`src/runtime/tiered-execution/adapter-outbound/native/main.rs`. It consumes
portable effect IR, validates structural
state/input/output/memory flow, renders deterministic freestanding C23, and
binds the candidate to the same collision-safe `NativeArtifactKey` used by the
cache identity layer. Pinned Clang 22.1.8 compiles that source into real Windows
COFF object candidates for both x86-64 and AArch64.

A safe-Rust COFF parser now structurally admits those compiler outputs without
invoking LLVM inspection tools. Admission binds the COFF machine to the target
ISA, requires the exact callable entry in executable/non-writable `.text`, and
rejects unresolved external dependencies. Internal ARM64 relocations to defined
`.rdata` constants are allowed. Structural admission deliberately stops before
semantic equivalence or execution authority.

A first direct backend now exists for the safe fallback case. It emits canonical
minimal COFF directly in Rust for x86-64 and AArch64, with machine code that
only
returns guard-miss status `1`. Complete object bytes are independently frozen;
semantic admission requires exact object equality after structural COFF checks.
The direct stub therefore cannot mutate guest state and always deoptimizes. It
is

not the region-effect fast-path backend required to complete this TODO.

A second direct template now admits the exact initial-halt subset and is the
first
state-applying fast path. It verifies zero entry registers/counters and live
termination before writing only the halt termination byte. Any mismatch returns
guard miss without mutation. Complete independently rendered COFF fixtures bind
both ISA implementations; x86-64 execution evidence covers hit, miss, and null
state, while ARM64 object linkage is verified on the development host. This

remains a deliberately tiny subset rather than general instruction selection.

`direct-halt-registers` revision 5 now covers the same halt-only effect across
arbitrary 32-bit entry registers and full 64-bit input/output counter
observations.
The x86-64 owner emits `mov rdx, imm64` plus exact counter comparisons; the
AArch64
owner emits all four reviewed `movz`/`movk` halfwords. Every guard branches to
one
non-mutating miss return and only termination is committed. Independent
495/564-byte objects bind counters above `u32::MAX`; counter, opcode, and
revision
mismatch fail closed. Development execution proves x86-64 full-width counter hit
and atomic counter miss; independent fixture decoding confirms AArch64
full-width

immediates and one common miss target. This widens admitted entry state, not the
guest-effect surface.

`direct-halt-fetch` revision 2 binds a VM-decoded graphical `v` live-in to halt
termination. Both ISA owners reuse the fetched-terminal template: full entry
observation, memory pointer, exact IR footprint, exact `memory[C]`, and prior
termination are guarded before writing only tag `1`. Independent complete
objects
are 535/628 bytes. x86-64 development execution proves hit and atomic
live-in/capacity/null misses; independent AArch64 decoding confirms the expected
guards, halt tag, and common miss target.

`direct-non-graphical` revision 2 is the first reviewed direct template with an
exact memory live-in. The VM-owned graphical-cell predicate admits one
non-graphical live-in at `C`; each ISA guards the full entry observation, memory
pointer, exact IR footprint, exact `memory[C]`, and prior termination before
committing only termination tag `2`. Independent complete objects are 538/631
bytes. x86-64 development execution proves hit and atomic live-in/capacity/null
misses; independent AArch64 decoding confirms the expected guards and common
miss
target. This reads verified memory evidence but still performs no guest-memory
or

I/O write.

`direct-no-operation` revision 2 is the first reviewed non-terminal template and
first guest-memory-writing fast path. VM-owned no-op classification, `XLAT2`,
and
profile successor functions independently derive the required IR. Each ISA
reuses
the fetched-cell guards, then atomically writes the encrypted code cell and
exact
next `C/D`. Independent complete objects are 557/658 bytes. x86-64 development
execution proves `memory[5]:77->65`, `C:5->6`, `D:7->8` plus atomic
live-in/capacity/null misses; independent AArch64 decoding confirms the same

commit and one common miss target.

`direct-jump-data` revision 1 adds the first instruction-specific semantic data
read. Two distinct live-ins bind code and data cells; VM-owned decode,
encryption,
and successor helpers derive the transition while `C == D` remains rejected.
Each ISA guards the complete entry, exact 125-word IR footprint, code live-in
35,
and data live-in 123 before atomically writing code 93 and `C/D` 6/124.
Independent complete objects are 564/699 bytes. x86-64 development execution
proves exact hit behavior plus atomic live-in/footprint/null misses; independent

AArch64 decoding confirms both reads, the commit, and one common miss target.

`direct-jump-code` revision 1 adds the exact post-jump encryption sequence.
Three
distinct live-ins bind entry code, entry data, and the graphical cell selected
by
`memory[D]`; VM-owned decode must classify the entry code cell as `i`. Each ISA
guards the complete entry, exact 13-word footprint, values 93/11/68 at addresses
5/7/11, and prior live termination before atomically writing `memory[11]=33` and
`C/D=12/8`. Independent complete objects are 622/731 bytes. x86-64 development
execution proves exact hit plus atomic code/data/encryption/footprint/null
misses
and twelve common-target `rel32` branches; independent AArch64 decoding confirms

three reads, the commit, and twelve branches to one miss. Address aliasing
remains
rejected.

`direct-rotate` revision 1 adds the first reviewed template with two
guest-memory
writes. Two distinct live-ins bind entry code and data cells; VM-owned decode
must
classify the code cell as `*`, while `profile_rotate()` derives the exact data
and
accumulator result. Each ISA guards the complete entry, exact 9-word footprint,
`memory[5]=34`, `memory[7]=10`, and prior live termination before atomically
writing data 1594326, encrypted code 122, and `A/C/D=1594326/6/8`. Independent
complete objects are 578/732 bytes. x86-64 development execution proves exact
hit
plus atomic code/data/footprint/null misses; independent AArch64 decoding
confirms

two reads, both writes, all register commits, and eleven branches to one miss.
Address aliasing remains rejected.

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

`direct-output` revision 1 adds the first reviewed output append. One live-in
binds the entry code cell and must VM-decode as `<`; `profile_low_byte()`
derives
byte `0xa8`. Both ISAs guard the exact 9-word footprint, `memory[5]=94`, output
pointer, strict capacity, and prior live termination before committing encrypted
code 57, `C/D=6/8`, byte index 3, and `output_len=4`. Independent complete
objects are 642/724 bytes. x86-64 execution proves exact hit and five atomic

miss classes; independent AArch64 decoding confirms one common miss target.

`direct-input` revision 1 completes direct instruction-family coverage. Its code
cell must VM-decode as `/`. The byte form guards a non-null input pointer,
strict `input_len > input_consumed`, and one exact byte before committing
accumulator and cursor. The EOF form guards
length equality, never dereferences the input pointer, and commits the VM-owned
all-two-trit EOF word without cursor advance. Independent complete objects are

659/744 bytes for byte input and 634/715 bytes for EOF on x86-64/AArch64.
Development x86-64 execution proves both hits and atomic misses; independent
AArch64 decoding confirms specialized pointer/length guards and common targets.

All memory-backed templates consume the exact key-bound IR footprint as their
ABI
capacity guard before any dereference. All eight instruction families now
have reviewed one-step direct templates.

Register-masked effect IR v6 now has reviewed C-only/no-write terminal shapes
for graphical halt fetch and non-graphical fetch. Both x86-64 and AArch64 use a
reduced guard sequence over C, exact required memory extent, `memory[C]`, and
prior termination while complete v6 identity still preserves masked semantics.
The non-graphical artifact has a distinct relocation-free image and rebased
prepared-call type that validates exact `NonGraphicalCell` application or atomic
guard miss. Dedicated lifecycle typestates admit exact copy, same-mapping RX
transition, and full-range synchronization.

A non-graphical-specific platform path owns transactional allocation, cleanup,
and release retry. Exact ready-image equality admits a distinct bound call view.
A dedicated runner executes only that view and restores the rebased snapshot
on runner or completion failure.

One-shot orchestration now composes exact load, bind, call, completion, and
release while retaining cleanup and release-retry evidence. A dedicated reusable
owner retains that exact non-graphical mapping across rebased calls and runner
failure without remapping.

A distinct single-resident lease cache shares that owner on exact hits, blocks
release while leased, rejects different identity, and transfers cleanup retry
ownership.

A separate fixed-limit multi-entry cache preserves exact-hit FIFO age and
processes active misses oldest-first. Unleased victims release immediately while
live victims retire and remain charged until explicit lease return or
reconciliation; invalidation and full release use the same ownership boundary.
Oversize candidates fail closed, and aggregate cleanup failure preserves keyed
retry ownership.

Explicit weighted-limit reconfiguration publishes expansion or already-fit
requests without adapter work and shrinks active FIFO authority through the same
release-or-retire path. Existing retired mappings are never reconciled
implicitly; blockage or release failure retains the previous limits and exact
retry evidence. The cache itself does not gain sequence execution authority.

A distinct non-graphical sequence plan now validates complete ordered topology
and exact artifact identity before any executable mapping may be allocated. It
checks count, one-effect v6 shape, profile and observation continuity, common
target identity, and termination only at the final position. Current terminal
coverage admits one executable semantic step.

A separate loaded owner maps the complete admitted plan transactionally, retains
exact mapped weight, and releases mappings in reverse while preserving aggregate
retry ownership. A dedicated loaded-sequence execution boundary calls only the
non-graphical runner through retained owners and performs no adapter work.
Applied or guard-miss outcomes carry exact progress, while current-step failure
retains indexed evidence and rolls back through the owner contract. Explicit
release remains separate.

The native call-frame ABI now has a format-neutral Rust authority in
`native/abi.rs`. `NativeRegionState` fixes the 80-byte `repr(C)` layout used
by both encoders, including offsets 0, 8, 16, 24, 32, 40, 48, 56, 64, 68,
72, and 76. Typed status and termination decoders reject unknown values, and
a borrowed call frame validates capacities before yielding a raw pointer for
future invocation. `PreparedNativeRegionInvocation` now derives the only valid
one-effect exit from portable IR, snapshots complete state/memory/output, and
admits only exact application or a mutation-free guard miss. Unknown status,

unexpected invalid arguments, topology drift, and partial commits fail closed.
Every rejected completion restores the complete entry snapshot.
`PreparedVerifiedDirectInvocation` reconstructs complete key identity using the
verified artifact target, rejects program drift, and denies the deoptimization
stub state-applying authority. `NativeRegionBuffers` keeps all caller loans in
that same artifact/call binding. `VerifiedDirectLoadImage` reparses verified
COFF, rejects relocations, extracts exact immutable code and entry offset,

retains full key/target identity, and validates ISA alignment. Its fixed policy
requires RW-to-RX transition plus instruction synchronization. This remains
load-plan evidence. Staged, sealed, and ready typestates now admit explicit
platform reports only after exact code copy into RW, the same mapping becoming
RX, and full-code instruction synchronization. Capacity, alignment, address,

identity, permissions, range, and sync drift fail closed. The ready state
retains an exact release request. Only an image-equal prepared invocation may
expose
entry address plus ABI state. Platform reports remain adapter evidence; no
linker, executable-memory owner, permission syscall, foreign call, cache-flush
implementation, or cleanup operation is introduced. The safe platform port now
orchestrates exact RW allocation, copy, RX protection, full-range instruction

synchronization, and release through a caller-owned adapter. Allocation is
admitted before copy, returned copy evidence is checked exactly, and every
post-allocation failure attempts release while preserving primary and cleanup
errors separately. Failed explicit release retains the ready executable for
retry. A deterministic adapter exercises all 24 direct images plus phase and
report failures. A separate runner port receives only the exact ready-image and

ABI binding. Safe orchestration now performs load, bind, runner call,
completion, and release, restoring the entry snapshot after runner or admission
failure. Cleanup failure retains the executable for retry; final-release
failure preserves the committed outcome. Applied, guard-miss, load-failure,
runner-failure, completion-drift, and release-failure cases pass. Concrete
Windows/POSIX memory

operations and foreign-call shims remain pending.

The first multistep planner composes already verified one-step artifacts without
changing either ISA encoder. Complete VM traces are projected to one-step IR,
then exact profile and observation continuity are checked before every artifact
is selected. The retained rotate/output fixture yields two reviewed artifacts on
both ISAs and rejects empty, discontinuous, profile-mixed, hidden-deopt, and
post-termination sequences.

`DirectFusedSequenceAdmission` derives one canonical multieffect region from
that already verified plan. Ordered memory evidence becomes exact region-entry
live-ins; a distinct revision-1 fused target binds the region-wide
`NativeArtifactKey`, while the complete source plan and ordered sequence key
remain provenance. Single-step plans are rejected.

The first fused emitter covers the retained rotate/output region on x86-64 and
AArch64. Every fused guard completes before the first store, and independent
semantic promotion reconstructs admission, structurally admits COFF, rebuilds
canonical bytes, and rejects text-byte drift.

`VerifiedDirectFusedLoadImage` now extracts the relocation-free fused entry
without granting execution authority. It retains exact key/triple identity,
validates ISA alignment, rejects machine drift or relocations, and requires the
same strict RW-to-RX plus instruction-sync policy.

Distinct fused lifecycle typestates now admit exact writable copy, same-mapping
RX transition, and full-code instruction synchronization while retaining fused
identity and release evidence. A fused-specific platform path now performs the
same caller-owned allocate/copy/protect/sync transaction, releases after every
post-allocation failure, preserves cleanup failure with the primary cause, and
retains exact ready state for explicit-release retry.

A fused-specific prepared invocation now independently reconstructs admission
from retained verified one-step provenance, validates whole-region entry
live-ins and capacity, and sequentially derives exact final memory, output, and
ABI state from every fused effect. Applied completion must match that complete
region snapshot; guard miss must preserve the complete entry, and every rejected
completion rolls back atomically.

Exact fused load-image equality now binds that prepared call to one synchronized
ready fused executable. The bound view retains only exact mapping/entry evidence
and the borrow-scoped ABI state pointer; image mismatch restores the complete
whole-region entry before failing.

A dedicated fused runner now accepts only that bound whole-region view. Loaded
execution performs no adapter work, admits exact Applied or GuardMiss outcomes,
and restores the complete region entry on runner or completion failure while
retaining exact Bind/Run/Complete failure evidence.

One-shot fused orchestration now composes exact load, bind, run, completion, and
release. Load or call failure restores the complete region entry and retains
cleanup failure independently from the primary cause. Final-release failure
preserves the committed Applied or GuardMiss outcome plus the exact ready
mapping
for retry.

A distinct fused executable owner now retains one verified fused artifact and
one synchronized mapping for repeated whole-region calls without adapter work.
Runner/completion failure restores the current call while residency remains
reusable; mapping-reported capacity defines resident weight, and explicit
release retains exact retry ownership.

A distinct single-resident fused lease cache now shares that exact owner through
immutable `Arc` leases. Exact artifact hits perform no adapter work, different
identity cannot replace the occupied slot, live leases block release, failed
load publishes nothing, and failed release transfers the exact ready mapping for
retry.

A separate fixed-limit fused lease cache now separates active lookup from
retired leased residency under entry, mapping, and mapped-byte limits. Hits
preserve FIFO age without adapter work; misses process active FIFO entries
oldest-first, releasing unleased victims and retiring leased victims while exact
weight stays charged.

Explicit invalidation, full drain, lease return, and retired reconciliation
preserve that ownership boundary without implicit reclamation on hit or miss.
Weighted-limit reconfiguration now publishes expansion without adapter work and
shrinks active FIFO authority through the same release-or-retire path.

Pre-existing retired residents are never reconciled implicitly; blocked or
failed publication keeps the previous limits plus exact blocker or keyed retry
evidence.

A distinct fused-region sequence plan now reconstructs each verified fused
admission before admitting an ordered common-target/profile chain. Exact
exit-to-entry continuity, total source semantic steps, regional entry/exit, and
the complete outcome are retained without mapping authority. A separate
loaded owner now publishes only after every exact fused region maps
successfully, retains exact mapped-byte evidence, and releases mappings in
reverse with aggregate retry ownership.

A dedicated loaded-sequence execution
boundary calls only the fused runner through retained owners and performs no
adapter work. Applied outcomes advance exact source semantic-step progress;
guard miss or current-region failure resumes before the complete current fused
region and leaves residency reusable.

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
leased sequence.

A one-attempt cached retry coordinator now acquires exact fused-region leases,
binds them to the admitted retry, and executes resident mappings. Exact hits add
no adapter work, while acquisition failure restores retry plus indexed cache
ownership.

Successful and failed resident retry executions now rebase through the same
verified semantic checker as uncached retries while retaining cache dispositions
and the independently reusable leased sequence. Applied work can complete the
original plan; guard miss and runner failure return normative resumptions
without consuming resident ownership.

An explicit post-rebase return boundary now drops every region lease together,
keeps active lookup authority intact, and runs one retired-resident
reconciliation pass. Release failure preserves semantic/native evidence beside
exact keyed cleanup retry ownership.

A pure bounded fused retry policy now accepts caller-supplied completed-attempt
counts, preserves exact one-based next-attempt evidence while budget remains,
and routes exhaustion to either complete normative fallback or one positive
source-step slice. Non-`NativeRetry` suspensions fail ownership-preservingly.
A bounded fused retry router now composes attempt policy with exact host
planning. Exhaustion bypasses planning, remaining budget produces a numbered
native route, and planner fallback applies the configured normative decision
without consuming an attempt.

Hard policy or planning rejection preserves the exact suspension and canonical
profile diagnostic. A bounded cached fused retry cycle now composes routing,
resident acquisition/execution, semantic rebase, explicit lease return, and
zero-step `NativeRetry` rescheduling.

Only successfully rebased guard misses continue. Unchanged suffixes reuse active
cache authority as exact hits, while exhaustion falls back normatively. Load,
runner, rebase, and reconciliation failures remain terminal with ownership.

A separate transactional fused cache-acquisition boundary now stages every miss
and preflights the complete FIFO/weighted fit before changing active or retired
authority. Late load, capacity, or live-lease blockage therefore preserves the
prior cache queues and usage, while staged cleanup failure remains retryable.
Post-publication victim cleanup failure reports committed acquisition plus exact
cleanup ownership rather than being misreported as rollback. The bounded
cached cycle may select this path explicitly; ordinary acquisition remains its
compatibility default.

A separate transactional one-attempt cached retry coordinator consumes that
whole-plan acquisition boundary before lease binding or native execution.
Pre-publication rollback and post-publication cleanup failure both stop before
the runner while restoring the admitted retry plus exact transaction ownership;
success binds the committed leased sequence through the existing resident retry
executor. The ordinary one-attempt cached retry remains unchanged.

An explicit one-attempt acquisition-mode request now selects ordinary or
transactional cache semantics without inferring policy from cache state.
Mode-tagged failures preserve the selected coordinator's exact ownership. Under
live FIFO blockage, ordinary mode retains its visible retire-before-block
effect, while transactional mode preserves active authority.

The bounded cached cycle now carries that explicit mode across every native
turn; `new()` keeps ordinary acquisition as the compatibility default.
Transactional acquisition or binding failure is terminal with exact transaction
ownership plus prior successful-attempt evidence. Execution failure in either
mode converges on the same semantic rebase and explicit lease-return path.
Transactional guard retries preserve active authority and exact-hit reuse across
turns.

Safe sequence execution now runs those reviewed
one-step artifacts in order through the loader/runner transaction. Applied
prefixes remain committed; a second-step guard miss resumes at index one with
the exact VM observation, and runner/completion failure restores only the

current step. Cleanup failure preserves applied or guard progress plus retry
state. Its cache-aware form preserves pointer-identical hits, stages unique
verified misses until complete success, and publishes no partial cache state
after a late rejection.

An immutable interpreter-continuation object now validates this resume evidence
against the complete cached or uncached plan. It retains exact complete/suffix
artifact keys, the cloned remaining one-step IR, resume observation, expected
exit/outcome, and a guard/failure reason. Constructors cover ephemeral and
preloaded execution failures; completed plans and terminal cleanup failures
produce no remaining work. Forged counts, indices, and observations fail closed.
`advance()` now rebases that same complete-plan authority after additional
admitted work from any tier, deriving an exact suffix or verified completion and

rejecting overshoot/boundary drift. Eleven cases bind both ISAs, every
constructor family, and rebase behavior. The separate application bridge now
restores either a complete checkpoint or native transfer
buffers into the normative profile machine. It admits exact profile and entry
state, executes each remaining traced transition, reprojects it to the retained
one-step IR, and rolls back a mismatching step to its entry checkpoint. Combined

native/interpreter progress must reach the verified exit/outcome. Explicit
semantic budgets now return an affine suspension containing cumulative progress,
complete-plan resume index, exact artifact/program suffix, and normative
checkpoint. Zero budget preserves state, partial budget resumes without
readmission, and oversized budget completes. Ten cases cover completion on both
ISAs, checkpoint/live-in drift, budget boundaries, and rollback after resume.
An explicit application scheduler now consumes that affine owner with complete,

positive interpreter-slice, caller-yield, or native-retry-yield decisions. Every
pause preserves exact checkpoint/suffix/progress plus a stable stop reason, and
rescheduling consumes the same owner. Native retry remains evidence only: no
backend is selected or invoked. Five scheduler cases cover both yields, sliced
and direct completion, cumulative progress, and hard-failure propagation. Native
A separate retry-admission boundary now binds one caller-replanned verified

sequence to the exact `NativeRetry` suspension. It rejects reason, ordered
programs, artifact key, or checkpoint-entry drift before buffer movement and
returns both owners on failure. Five cases include progressed suffix and
cross-ISA rejection. An admitted retry now runs through the existing uncached
sequence execution path from checkpoint-derived owned buffers. Both success and
failure retain exact transfer state; checkpoint reconstruction is validated and

cleanup ownership remains retryable. Five execution cases cover completion,
guard miss, rollback, and committed cleanup failure. Successful retry results
now rebase against complete-plan continuation authority: applied suffixes
produce
the original outcome/final checkpoint, while guard miss yields a scheduler-ready
handoff with absolute mixed-tier progress. Three cases cover pure and mixed
completion plus progressed guard fallback. Failed retry execution now splits
semantic disposition from indexed native failure ownership: runner failure
yields
an exact fallback handoff and terminal cleanup failure may complete semantics

while preserving release retry. Three cases cover zero/progressed fallback and
cleanup completion. Exact retry host planning now selects the remaining
verified sequence on Windows and converts only missing target format into a
normative handoff. Profile, IR, continuity, deoptimization, emission, and
verification failures remain hard and retain the suspension. Four cases cover
Windows routing, Linux fallback at two progress points, profile rejection, and

invalid reason. An explicit immutable attempt policy now preserves native retry
while budget remains and routes exhaustion to complete or positive-slice
normative fallback. Caller owns completed-attempt evidence; zero limit falls
back
immediately. Four cases cover attempt numbering, both fallback forms, and reason
rejection. A bounded router now composes attempt policy with host planning:
exhaustion bypasses planning, available budget produces a numbered native route,

and missing format uses configured fallback without consuming an attempt. Five
cases cover both routes and owned hard failures. One-turn execution now runs
the selected normative or native route, rebases every native result, and keeps
semantic disposition independent from indexed runner/release ownership. Five
cases cover interpreter/native completion, guard fallback, runner failure, and
cleanup completion. A bounded cycle repeats only successfully rebased guard
misses; fixed attempt policy terminates in native completion or normative

fallback, while runner/release failures stop immediately with owners intact.
Seven cases cover zero/format fallback, repeated guards, later native
completion,
runner/cleanup failure, and hard rejection before adapters. An admitted retry
can now execute through an exact immutable lease without allocation/release,
retaining hit/insertion evidence and the lease across semantic rebase. Five
cases
cover insertion, pointer-identical hit reuse, guard/failure fallback, and key
rejection. Exact cache acquisition can now precede one loaded retry attempt:
hits perform no memory-adapter work, insertions retain FIFO retirement/release

evidence, and load/runner failures preserve retry or lease ownership. Five cases
cover insertion, hit reuse, load failure, mixed retirement, and runner fallback.
A bounded cached cycle now records per-attempt native progress plus `Inserted`
or
`Hit`, drops successful external leases while retaining active cache authority,
and reuses unchanged guard suffixes without platform work. Progressed suffixes
remain distinct exact entries; acquisition, routing, and runner failure retain
owners plus prior successful attempts. Ten cases cover fallback, repeated
hits, transactional blockage and reuse, changed suffixes, initial/late load
failure, routing failure, and runner

failure.
A pure telemetry source now covers attempt slices, completion, and fallback
owners. Caller-bounded FIFO retention keeps monotonic sequence IDs and exact
totals,
transactional capacity changes, validated transfer snapshots, and canonical
revision-one little-endian snapshot bytes. Explicit inclusive thresholds
classify insufficient, meeting, or multi-signal miss evidence without selecting
policy.

The count window also accepts caller-authoritative ordered summary batches. Each
summary receives a fresh destination-local sequence, and the complete batch is
committed only after every append transition succeeds. Source-local sequence IDs
and cumulative eviction history are intentionally not merged because independent
windows have no canonical relative ordering. Three cases cover ordered append,
FIFO eviction, and rollback after sequence exhaustion.

A process-local ordered-window owner now couples those batches to an opaque
caller-authoritative `u64` order stamp. The first stamp may be arbitrary; later
stamps must strictly increase and gaps remain caller-owned. Duplicate or stale
stamps fail without touching retained telemetry.

FIFO failure likewise leaves the previous order unchanged. Four cases cover
arbitrary first order, gaps, stale rejection, and transactional failure. The
owner neither sources order nor reads a clock.

Ordered count ownership now also has a canonical revision-one outer frame. It
records explicit order presence plus the exact `u64` watermark and nests the
existing canonical count-window bytes with an exact length. Absent order
requires
a zero value, and nested count semantics are revalidated during decode. Five
cases cover ordered/unordered round trips, absent-order canonicality, reserved
flags, and nested corruption.

That combined ordered state now binds directly to the bounded durable blob
service as one document. Restart therefore restores the external watermark and
count FIFO together; missing state remains explicit, and post-publication sync
failure remains committed `Published` evidence. Three deterministic cases cover
round trip, committed durability failure, and missing state, plus one host-real
filesystem round trip.

One-shot ordered publication now loads that complete bounded document, decodes
it, applies one caller-ordered batch, and conditionally publishes against the
exact raw bytes originally loaded. Missing state uses a caller-supplied initial
capacity only until the first commit; persisted capacity remains authoritative
afterward. Stale order fails before CAS, while races return decoded current and
expected combined state without retry.

Five deterministic cases cover missing initialization, persisted-capacity
authority, stale rejection, race conflict, and committed sync failure. One
host-real case advances state through two independent filesystem-store
instances.

A separate synchronous retry layer accepts a positive caller-selected attempt
limit for ordered publication. Only typed CAS conflict retries, and every retry
starts from a fresh bounded load of the complete combined document. If that load
shows a watermark at or beyond the submitted order, normal stale-order rejection
stops the operation instead of rebasing the caller's order.

Four deterministic cases cover refreshed success, conflict-to-stale transition,
final conflict retention, and no retry after committed durability failure. No
sleep, backoff, or order rewrite is inferred.

The ordered-count retry now also accepts the shared synchronous retry directive.
After a retryable conflict, the caller receives the exact completed-attempt
count and may return `Continue` or `Stop`; stopping preserves that conflict
unchanged. Continued attempts still begin with a fresh bounded load, and the
runtime still performs no clock read, wait, backoff, or fairness action. Two
focused cases cover one continued conflict and one caller-stopped conflict.

A pure count-based recommendation boundary now maps ready assessments to
one of two caller-supplied retry policies while insufficient evidence defers; it
retains exact telemetry and miss violations and does not publish policy. A
separate request-scoped publication boundary consumes that recommendation plus
one future cached-cycle request. Deferral returns the request unchanged; ready
evidence replaces only its retry policy while retaining previous/current policy
and exact recommendation evidence.

Caller-supplied latency histograms preserve inclusive buckets, totals,
and extrema without reading clocks; validated snapshots transfer complete

histogram state and reject impossible count, range, or overflow-bin evidence.
Identical-schema histograms merge transactionally with exact rollback on any
schema or counter failure. Canonical revision-one latency bytes preserve exact
extrema flags, `u128` totals, and bound/count pairs while repeating snapshot
validation after decode.

A pure latency assessment now gates on a positive caller-required sample count
and applies inclusive maxima to exact arithmetic mean latency, largest observed
sample, and overflow-bin count. Mean comparison uses exact integer arithmetic
without floating point or truncating division, and all simultaneous misses are
retained. Four cases cover insufficient evidence, inclusive equality,
multi-signal misses, and a fractional mean boundary. A pure latency-driven
recommendation now maps ready assessments through the same caller-supplied
meets/misses policy table as count telemetry; insufficient sample evidence
defers, and exact latency evidence plus violations remain attached.

A parallel request-scoped publication boundary now consumes latency
recommendations. Deferral preserves the request unchanged, while ready evidence
replaces only its retry policy and retains previous/current policy plus exact
latency recommendation evidence.

Retry policies now expose an immutable canonical snapshot owned by the policy
boundary itself: exact maximum native attempts plus either complete normative
fallback or one positive sliced fallback budget. Reconstruction consumes that
representation directly rather than inferring fallback state from scheduler
behavior. The internal sliced form also carries `NonZeroUsize`, so invalid zero
slice state is unrepresentable.

Two cases cover complete and sliced round trips. This is transfer evidence only;
no durable/global policy owner is introduced.

A fixed-width revision-one policy codec now serializes that snapshot into 32
canonical little-endian bytes. Decode validates magic, revision, both
reserved fields, the explicit fallback tag, complete/sliced budget semantics,
host integer representation, and exact frame length before reconstructing
snapshot evidence.
Five cases cover canonical complete/sliced bytes plus semantic, framing, and
length rejection. The codec still owns no storage or publication authority.

Typed retry-policy persistence now binds that codec to the generalized opaque
blob service. Missing durable policy remains explicit, corrupt bytes fail codec
validation, byte limits reject before outbound publication, and durability
confirmation preserves either `Durable` or committed `Published` evidence. Five
adapter-neutral cases cover those paths; one host-real filesystem case
round-trips a sliced policy through canonical bytes and directory durability.

This persists one caller-selected policy document only. It does not create a
shared active-policy owner, automatically mutate future cached-cycle requests,
or provide cross-process compare-and-swap or locking semantics.

A separate process-local active-policy owner now carries one exact retry
policy plus a monotonic `u64` revision across cached cycles. New owners begin at
revision zero; matching expected revisions publish the candidate and advance
exactly once, while stale revisions return conflict evidence without mutation.
Revision
exhaustion also fails closed without changing active state. Four cases cover
initial state, successful publication, stale conflict, and exhaustion.

The owner can reconstruct validated `(policy, revision)` state for durable
restoration, but it does not itself persist state or coordinate another process.
The conditional blob port and filesystem coordination used for that publication
are separate boundaries described below.

A separate explicit request-binding boundary now consumes one immutable
active state plus one future cached-cycle request. It replaces only that
request's retry policy and retains the active revision, active state, and
previous request policy as evidence. One case binds a revision-one owner state
into a different request.
Nothing subscribes requests to the owner or mutates future requests implicitly.

Revisioned active state now has a separate fixed 52-byte revision-one codec. The
outer frame carries one exact `u64` owner revision and embeds the existing
canonical 32-byte policy frame; outer framing and nested policy validation both
fail closed. Two cases cover exact round trip plus outer/nested corruption.

Typed policy persistence can now durably publish and restore that revisioned
state through the same opaque blob service. One adapter-neutral case restores an
owner with the exact revision/policy, and one host-real filesystem case crosses
the state codec, bounded application service, staged file publication, and
directory durability confirmation.

The opaque blob boundary now also exposes optional conditional publication. The
application checks expected/replacement bounds, preserves exact conflict bytes,
and confirms durability only after a successful conditional commit. The
filesystem adapter serializes cooperating publishers through one persistent
sibling file lock that spans bounded compare plus staged rename; ordinary
replacement honors the same lock.

Two adapter-neutral cases cover match/conflict, one case preserves committed
durability failure, and one host-real race proves that exactly one missing-state
publisher commits while the loser observes the committed bytes as conflict
evidence. Non-cooperating filesystem writers remain outside this advisory-lock
contract.

Typed active-policy CAS now composes that conditional blob service with the
revisioned state codec and the existing owner transition. Missing state can
initialize revision zero; a present expected state advances exactly one
revision, while stale state returns the decoded current owner without mutation.
Four adapter-neutral cases cover initialization, update, conflict, and
exhaustion; a host-real two-store race proves that exactly one initializer
commits.

Count and latency recommendations can now publish ready policy into that
durable active-state CAS boundary. A shared typed result retains the exact
recommendation alongside durable, committed-with-sync-failure, or conflict
evidence. Deferred recommendations perform zero storage work.

Three count cases cover deferral, revision-zero initialization, and stale
conflict; one latency case advances an existing active revision. Request binding
remains a separate explicit operation.

Exact histogram coarsening now removes only caller-selected interior source
bounds while preserving exact bucket totals, extrema, overall samples, exact
nanosecond totals, and overflow-bin evidence. The target must be an ordered
subset of source bounds with the same final bound; missing boundaries and final
overflow-bound drift fail closed. Five cases cover identity, exact coarsening,
refinement rejection, overflow-bound rejection, and normalization before the
existing same-schema merge.

Exact refinement now requires an additional caller-supplied sample witness. The
finer histogram is rebuilt only from those samples, then coarsened back to the
source schema and required to equal every source count, total, extremum, and
overflow value. Persisted histogram state alone therefore still cannot invent a
finer distribution. Three cases cover valid refinement, incomplete witness, and
a target schema that does not preserve every source boundary.

A pure common-schema derivation now intersects two ordered source schemas when
their final overflow boundary matches. It returns
the greatest exact shared bound set plus per-side removal counts; four cases
cover identity, partial overlap with exact merge, final-bound-only reduction,
and incompatible final bounds.

A normalized exact merge now composes that common-schema derivation with both
coarsenings and the existing transactional same-schema merge. It retains how
many bounds each side removed and never mutates either source. Two cases cover
different compatible schemas and incompatible final overflow bounds.

One-shot durable latency merge now loads bounded raw bytes and decodes exact
current histogram state. It performs that normalized merge and conditionally
publishes against the same raw bytes originally observed. Missing state
initializes from the submitted source.

Conflict returns decoded current/expected state without retry. Durability
failure after CAS remains committed `Published` evidence. Five deterministic
cases cover
initialization, normalization, conflict, sync failure, and incompatible schema,
plus one host-real filesystem round trip.

A separate synchronous retry layer accepts a positive caller-selected maximum
attempt count. Only typed CAS conflicts retry, and every retry starts a fresh
bounded load/merge/CAS attempt; durable commits, committed sync failures, and
prepublication errors stop immediately. Four deterministic cases cover
first-attempt success, refreshed conflict success, final conflict retention, and
no retry after committed durability failure. No sleep or backoff policy is
inferred.

Cached-cycle composition now binds the existing canonical count/latency codecs
to an explicit persistence application service and reconstructs exact validated
owners after load. The application service itself treats payloads as opaque
bytes, enforcing a positive bound before publication and again after loads.

The storage-neutral outbound blob port now names only opaque single-blob
transport. It admits bounded loads and all-or-nothing replacement without
exposing paths, filesystem APIs, policy selection, or payload interpretation.
The bounded application service likewise owns only byte limits and publication
state; typed telemetry codecs remain composition clients. Six adapter-neutral
cases retain both telemetry round trips, missing state, byte guards, and store
failures across that generalized boundary.

A separate outbound capability now requires one preconfigured opaque blob pair
to load and replace atomically. Partial pair state is unrepresentable: failed
replacement must preserve the complete prior pair, and sequential single-blob
writes do not satisfy the contract. Its application service enforces independent
positive bounds before publication and after load, with post-commit pair
durability reported separately from rollback.

Six deterministic cases cover atomic replacement, preserved prior state on
failure, both write bounds, malicious oversized load output, missing state, and
committed durability failure.

Cached-cycle composition now binds canonical count-window bytes to the first
member and canonical latency-histogram bytes to the second member of that atomic
pair. Restoration atomically loads both members, then independently repeats each
existing codec and snapshot validation before reconstructing live owners.
Missing
pair state never invents one side. Post-commit durability failure retains the
complete newly encoded pair.

Five deterministic cases cover atomic typed round trip, missing state, count
corruption, latency corruption, and committed durability failure.

A concrete filesystem pair adapter now binds the atomic pair port to one
explicit
manifest path. Each publication writes and synchronizes two immutable
same-directory generation members, then writes and synchronizes a staging
manifest. Atomic manifest `rename` is the sole commit point; readers follow one
complete manifest to immutable members and therefore never combine generations.

A persistent sibling lock coordinates cooperating readers and publishers.
Readers hold a shared lock from manifest observation through both immutable
member reads; generation creation, conditional comparison, and manifest
replacement hold the exclusive lock. This removes the manifest-to-member race
that would otherwise make later generation reclamation unsafe.

Crashes before the manifest commit may still leave unreferenced generations,
but those are ignored and never become current pair state. Directory
synchronization remains a separate post-commit durability confirmation.

Explicit generation reclamation now runs under the same exclusive sibling lock.
It validates the current manifest and verifies both current members exist
before deletion, and considers only exact generation filenames reconstructed
through the adapter's own naming rule. Missing manifest state treats every
exact owned member as unreferenced; non-UTF-8 manifest basenames fail before
deletion.

The pass attempts every eligible deletion and retains completed removals beside
exact failed paths/error kinds. Directory sync after deletion is committed
durability evidence rather than rollback, and repeated passes rescan
idempotently. Publication itself still performs no automatic cleanup.

A caller may additionally preserve exact opaque revisions already in its
possession. The adapter compares those revisions for equality only; it does not
infer chronological order or choose a retention window.

An optional storage-neutral pair-reclamation port now carries opaque revision,
reclamation-evidence, and pre-cleanup-error ownership without naming the
filesystem. A dedicated application use case forwards one caller-selected exact
preserve slice unchanged and delegates exactly one pass. One adapter-neutral
case proves exact forwarding, while the host-real preservation case crosses the
application, port, and filesystem adapter together.

A process-local exact-retention owner now records only opaque revisions the
caller explicitly retains or releases. Duplicate retain is a no-op, release is
exact equality, and the exposed insertion order has no chronological meaning.
The resulting preserve slice feeds the reclamation request directly. One focused
case covers membership changes and the forwarding case consumes that owner.

Six focused reclamation cases cover current-generation preservation plus exact
foreign-name filtering, caller-preserved revisions, current-member
prevalidation,
missing-manifest idempotency, partial deletion evidence, and malformed-manifest
rejection before any eligible orphan is removed.

Pair CAS now compares an opaque publication revision rather than payload bytes.
Versioned load returns one bounded pair plus the revision observed from the same
manifest commit point. Conditional replacement matches only that revision, while
`None` matches only missing state; application orchestration rechecks both
returned member bounds and confirms durability only after a committed CAS.

The filesystem adapter uses an epoch/generation manifest token as the opaque
revision. Initial publication seeds the epoch once; later cooperating writers
preserve that epoch and derive the next non-wrapping generation from the current
manifest under the persistent sibling lock. Crash-orphan collisions are skipped
within that epoch. A stale revision therefore conflicts even when a newer
generation contains byte-identical payloads and returns the complete current
bounded pair plus its newer revision without retry.

Five adapter-neutral cases cover versioned load, missing-state initialization,
stale conflict, post-load bound rejection, and committed durability failure. Two
host-real CAS cases cover revision advance and byte-identical ABA rejection.

Three host-real generation-identity cases additionally cover orphan collision
skipping inside one epoch, generation continuation through reclamation with a
fresh adapter instance, and fail-closed `u64` generation exhaustion. The 24-byte
manifest layout remains unchanged; only the private meaning of its first `u64`
changes from per-writer process identity to the persisted store epoch.


The opaque filesystem revision now also has a separate canonical 24-byte
`MBPREV01` codec: magic plus little-endian epoch and generation. Decode rejects
wrong size, magic, and zero generation while preserving field opacity. Three
focused codec cases cover exact canonical round trip and fail-closed malformed
representations.


Exact retained-revision sets now also have canonical `MBPRET01` framing: magic,
a little-endian `u64` count, and canonical 24-byte revision members in caller
order. Both directions reject duplicates; decode also rejects malformed nested
revision bytes and count/length drift. Four focused cases cover canonical round
trip plus duplicate, framing, and nested-revision rejection. Ordering remains
caller evidence and is never interpreted as time or retention priority.


A typed composition journal now persists those exact retention frames through
the existing bounded durable blob application service. Missing storage remains
explicit, present state reconstructs the exact process-local retention owner,
and post-publication durability failure remains committed evidence. Three
focused cases cover missing state, durable round trip, and committed durability
failure without adding selection or scheduling policy.


That typed journal also supports one-shot conditional durable publication over
the generic blob CAS. Expected retention is encoded canonically; conflict
returns the exact current bounded bytes decoded into typed retention, malformed
conflict state fails closed, and only a successful conditional publication
performs durability confirmation. Four focused cases cover missing-state
initialization, typed conflict, corrupt conflict rejection, and committed
durability failure.

One host-real cross-instance case advances the journal through one file store,
then proves a stale second store receives typed conflict evidence for the
advanced retention and cannot overwrite it. The operation never retries,
merges, reorders, or selects retained revisions. Automatic conflict retry
remains out of scope because refreshing the expectation and replaying a
whole-set replacement would discard concurrent caller-selected retention unless
an explicit reconciliation policy chooses the new set.


A separate caller-directed reconciliation layer now supplies the safe retry
mechanism without choosing that policy. It performs one bounded typed restore,
invokes a caller callback before each CAS attempt, and uses each typed conflict
as the callback input for the next attempt. Five focused cases cover missing
initialization, fresh conflict reconciliation, exhausted-budget conflict,
callback rejection before CAS, and committed durability failure stopping after
one attempt. No union, intersection, revision ordering, backoff, or automatic
retention policy is inferred.


Durable retention state and generation reclamation still do not form one
transaction. The generic file-blob journal and filesystem pair adapter use
different stable sibling locks; therefore loading journal state and later
reclaiming with that preserve set can race a concurrent journal update and
remove a newly retained generation. No composition helper may treat the journal
as concurrent reclamation authority until both operations share one
serialization or transaction boundary. A process that exclusively owns all
retention mutation may still restore the journal and invoke explicit
reclamation under that stronger external authority.


The reviewed filesystem prerequisite is a reusable coordination object owning
one explicit lock path and returning non-cloneable shared/exclusive guard
tokens. Both the durable retention journal and pair adapter can bind to that
coordinator; internal prelocked read/CAS/reclamation primitives must require the
matching guard so a cross-object operation acquires the lock once rather than
recursively. This follows the compiler progress-sidecar pattern where one writer
lock spans predecessor read, validation, immutable-state checks, and pointer
replacement. Reusing only the same lock filename with today's independently
locking public methods is not sufficient because nested acquisition can
deadlock and does not prove that every participating mutation joined the same
transaction.


The first coordination slice is now implemented. One reusable filesystem
coordinator owns an explicit advisory-lock path and yields non-cloneable
shared/exclusive guards carrying that identity. Existing blob and pair
constructors retain their historical sibling-lock behavior; new
`with_coordination(...)` constructors let either adapter join one caller-owned
lock domain without changing publication or read semantics.

Two host-real cases cover shared-guard identity and unchanged blob/pair round
trips under one explicit coordinator.

The guarded prelocked seam is now implemented as well. Crate-internal bounded
blob load/CAS and pair-generation reclamation require one matching exclusive
guard and reject foreign guards before state access. One host-real case holds a
single exclusive guard across blob CAS/load and pair reclamation without nested
lock acquisition. Another proves a foreign guard is rejected by both adapters.

Journal-driven reclamation is now implemented in composition over that
primitive. One exclusive guard spans bounded journal load, canonical retention
decode, and pair-generation reclamation. Missing journal state performs no
deletion; a present empty journal is distinct and authorizes reclamation of
every
superseded generation except current. Two host-real cases cover missing-journal
no-op and exact durable preservation from a present journal; the adapters still
expose no retention-selection policy.


A separate guarded transition now advances durable retention before cleanup.
It performs canonical journal CAS under the same exclusive guard, confirms
journal-directory durability after publication, and only then invokes exact
pair-generation reclamation. Conflict is non-mutating; failed journal durability
stops before deletion, while durable journal publication followed by a
pre-deletion reclamation rejection is returned as committed journal evidence.

Three host-real cases cover successful durable transition/reclamation, stale
journal conflict with no generation deletion, and durable journal retention
after reclamation rejection. The transition still chooses no
retention set, retry policy, ordering, or cleanup schedule.

A caller-directed bounded retry layer now wraps only the conflict path. Exact
typed conflict retention becomes the next callback input; exhausted conflict is
terminal evidence. Callback failure and every committed journal or reclamation
outcome stop immediately, so retry adds no implicit merge or backoff policy.


That retry layer now also exposes a policy-neutral synchronous control hook.
After a retryable conflict releases its filesystem guard, the hook receives the
exact completed-attempt count and returns `Continue` or `Stop`; stopping returns
the same typed conflict unchanged. Callers may wait, yield, or inspect their own
cancellation state there, but tiered execution still owns no clock read, sleep,
backoff interval, or fairness policy.

Cached-cycle composition now binds that opaque pair revision to typed count and
latency owners. Versioned restore decodes both canonical members together and
retains the exact revision observed with them. One-shot durable typed CAS
encodes
the caller candidate, preserves the expected revision as conflict evidence, and
decodes any bounded conflict pair back into exact live owners before returning.

Six focused cases cover typed versioned restore, missing-state initialization,
stale conflict decoding, malformed conflict rejection, committed durability
failure, and a host-real cross-instance revision advance. Blind conflict retry
is
not provided: replaying the same whole-pair snapshot against a fresher revision
could overwrite concurrent telemetry. Any retry must first define an explicit
count/latency reconciliation or merge operation over freshly loaded typed state.

A separate ordered telemetry-pair contract now persists the existing canonical
`(external order + count FIFO)` document as member one and the canonical latency
histogram as member two. This does not reinterpret or migrate the earlier plain
count-window pair format. It provides the restart-safe ordering watermark needed
for future conflict reconciliation while keeping both telemetry channels atomic.

Four focused cases cover atomic ordered-pair round trip, explicit missing state,
committed durability failure, and a host-real cross-instance filesystem restore.
The persistence layer itself still infers no order from storage contention.

One-shot ordered-pair reconciliation now performs a fresh versioned load, then
transactionally appends one caller-ordered count batch and exactly normalizes
and merges its latency delta before one durable revision CAS. Missing state uses
the
caller capacity and submitted latency as its initial state. Existing persisted
capacity and external-order watermark remain authoritative.

Four focused cases cover missing-state initialization, exact existing-state
reconciliation, stale-order rejection before CAS, and committed durability
failure. Concurrent CAS conflict remains a typed non-mutating one-shot outcome.

Caller-bounded synchronous retry now repeats the complete fresh-load
reconciliation only after typed CAS conflict. Every attempt re-reads the durable
watermark and latency state before rebuilding the candidate; a newer watermark
can therefore reject the submitted order instead of being silently rebased.
Durable publication, committed durability failure, and every non-conflict error
stop immediately. No backoff, sleep, fairness, or cancellation policy is
inferred.

Four focused retry cases cover final conflict at the attempt limit,
conflict-to-fresh-load success, conflict followed by exact stale-order
rejection, and committed durability failure stopping after the first attempt.

The ordered-pair retry also accepts the shared synchronous retry directive.
After a retryable conflict, the caller receives the exact completed-attempt
count and may return `Continue` or `Stop`; stopping preserves that conflict
unchanged. Continued attempts still perform the complete fresh reconciliation,
and the runtime still performs no clock read, wait, backoff, or fairness action.
Two focused cases cover one continued conflict and one caller-stopped conflict.

The concrete filesystem adapter is also payload-neutral and binds that port to
one explicit destination. It probes one byte beyond bounded reads, stages in
the destination directory, synchronizes complete staging contents, and
publishes by `rename` without ever removing the previous destination first.
Host-real cases retain missing, overwrite-or-safe-failure, oversized-read, and
exact count/latency evidence while leaving the adapter reusable by other typed
composition clients.

A separate post-publication durability capability now confirms the destination
directory after replacement. Application orchestration returns `Durable` after
successful confirmation or committed `Published` evidence with the exact
durability error; two deterministic cases cover both states, and one host-real
filesystem case exercises directory sync without reclassifying commit as
rollback.

Cached-cycle composition now binds both canonical count-window and latency
histogram codecs directly to that durability-capable application service. It
preserves typed canonical write evidence in both `Durable` and committed
`Published` states; three adapter-neutral cases cover count/latency success and
post-publication failure, and one host-real count-window case crosses the full
codec/application/filesystem path.

A transport-neutral monotonic interval port now delimits caller-owned cached
retry work without exposing wall-clock time. A standard `Instant` adapter owns
interval observation and exact `u64` nanosecond conversion, while cached-cycle
composition turns the finished interval into the existing explicit latency
sample without recording it automatically. Two deterministic cases cover exact
sampling and finish failure; one host-real case records an `Instant` sample into
the existing histogram as a separate caller step.

Merge backoff/cancellation/fairness policy, native object fusion, foreign
invocation, asynchronous timing, reclamation scheduling/automatic durable
retention policy, and general N-object transactions remain open.

A persistent executable sequence now loads every reviewed one-step image before
execution and retains all ready mappings across repeated calls. Partial load
failure cleans the ready prefix in reverse; aggregate release attempts every
mapping and keeps failed ownership for retry. Complete image identity is checked
before buffers change, so an x86-64 chain cannot execute an AArch64 plan. The
memory adapter must provide unique, non-overlapping live allocations.

A weighted loaded-sequence FIFO now reuses exact ordered artifact-key chains on
both ISAs. Hits neither refresh insertion age nor call the memory adapter.
`new()` bounds complete entries, while explicit limits can additionally bound
live mappings and admitted mapped bytes. Candidate weight is derived from ready
mapping reports after load. Oversized candidates are released without changing

prior entries. Candidates that fit alone evict as many oldest entries as
necessary for every projected limit. Failed later insertion eviction removes
cache authority for that victim and earlier successful victims, cleans the
candidate, and retains failed releases for retry. Exact invalidation and full
drain update usage before cleanup.

Weighted limits can now be reconfigured in place. Expansion and already-fitting
requests publish without platform work. Shrink requests release oldest mappings
until current usage fits, while keeping the previous limits active until all
required releases succeed. Failure reports every removed key and retains exact
release ownership; retry followed by the same request publishes without
releasing completed victims again. Seventeen cases cover prior reuse/admission
behavior plus expansion, entry/mapping/byte shrink, and failure during the

second reconfiguration eviction.

A separate lease cache now shares exact ready chains through immutable `Arc`
ownership. Active FIFO lookup can retire an entry while external leases continue
to use the same mappings on other threads. Retired entries retain exact weighted
usage and cannot be released until explicit reconciliation observes no external
owner. Mixed eviction releases unleased victims immediately, retires leased
victims, and rejects a candidate when resident weight still cannot fit. Full
drain and invalidation follow the same rule; keyed cleanup failures remain

retryable outside cache authority. Resident limits can now expand without
platform work or shrink through active FIFO release/retirement. Leased victims
keep exact weight charged, prior retired entries are not reconciled implicitly,
and previous limits survive blockage or cleanup failure. Returning the final
lease or retrying keyed cleanup permits an idempotent repeated publication.
Fourteen cases bind the original lease lifecycle plus entry/mapping shrink, live

entry/byte blockage, post-return publication, and release-failure retry. This is
not a fused COFF object, durable or cross-process executable storage, a direct
branch chain, or a concrete foreign-call shim.

This does not complete this TODO. The bootstrap deliberately delegates
instruction selection to Clang and stores compiler output only as an
`UntrustedNativeObjectArtifact`.

Clang-produced structurally admitted COFF remains semantically untrusted.
Reviewed direct terminal, no-op, jump-code,
jump-data, rotate, crazy, input, and output emitters/verifiers are
implemented for both ISAs; the first atomic fused rotate/output object is also
emitted, independently verified, and extracted as a relocation-free load image
on both ISAs, with dedicated safe lifecycle typestates, transactional platform
loading through synchronized RX readiness, and a borrow-scoped whole-region
prepared invocation contract. Wider fused-template coverage, concrete
executable-memory and foreign-call adapters, runtime integration, and concrete
instruction-cache synchronization remain incomplete.

## Invariants

- x86-64 and AArch64 are first-class host targets, consume the same portable
  execution IR, and independently pass cross-backend differential suites
  including executable-memory and instruction-cache edge cases.
- Native cache identity includes host ISA and every assumption required by the
  compiled region.
- Bootstrap lowering performs all local guards before the first guest-visible
  write; guard failure never commits a partial output, memory, register, cursor,
  or termination transition.
- Compiler-produced object bytes remain untrusted until an independent native
  admission boundary proves behavior against verifier-owned effect evidence.
- Observable state, I/O, termination, and diagnostics match the declared
  semantic profile across positive, boundary, and adversarial fixtures.
- Performance conclusions use equivalent workloads and report raw-sample
  provenance, resource budgets, dispersion/uncertainty, and failure/success
  behavior rather than only a best-case number.

## Failure Behavior

Invalid programs, unsupported profiles, or broken native assumptions fail
deterministically without changing guest-visible state silently.

## Verification

- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- Required evidence: semantic fixtures, state/I/O traces where diagnostic, and
  differential results against independent interpreter-compatible
  implementations; the original C source is compared only where its behavior is
  defined and reproducible.
- Prerequisite completion evidence: `tiered-native-execution-engine`.
- Bootstrap evidence: `tests/tiered_execution.rs` verifies deterministic source,
  exact cache-key binding, collapsed repeated writes, preflight-before-commit,
  target/backend rejection, real x86-64/AArch64 COFF generation using pinned
  Clang 22.1.8, direct safe-Rust COFF parsing, ARM64 internal relocation
  closure,
  and fail-closed mutation rejection. Direct-deopt evidence additionally uses
  independent complete-object fixtures, rejects a one-byte opcode mutation after
  structural admission, links both ISA objects, and executes x86-64 guard miss
  without dereferencing its state pointer.
- Performance evidence pending: raw measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.

## References

### Host Architecture Baseline

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`

- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
