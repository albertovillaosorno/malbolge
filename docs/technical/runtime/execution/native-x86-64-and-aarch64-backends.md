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
evidence. Fused sequence ownership remains absent.

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
owners plus prior successful attempts. Seven cases cover fallback, repeated
hits,
changed suffixes, initial/late load failure, routing failure, and runner

failure.
A pure telemetry source now covers attempt slices, completion, and fallback
owners. Caller-bounded FIFO retention keeps monotonic sequence IDs and exact
totals,
transactional capacity changes, validated transfer snapshots, and canonical
revision-one little-endian snapshot bytes. Explicit inclusive thresholds
classify insufficient, meeting, or multi-signal miss evidence without selecting
policy. Caller-supplied latency histograms preserve inclusive buckets, totals,
and extrema without reading clocks; validated snapshots transfer complete

histogram state and reject impossible count, range, or overflow-bin evidence.
Identical-schema histograms merge transactionally with exact rollback on any
schema or counter failure. Canonical revision-one latency bytes preserve exact
extrema flags, `u128` totals, and bound/count pairs while repeating snapshot
validation after decode. Rebinning, distributed merge, native object fusion,
foreign invocation, telemetry-driven policy, runtime clock acquisition, durable
storage, and cross-process coordination remain open.

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
prepared invocation contract. Wider fused-template coverage, fused executable
binding/runner integration, concrete executable-memory and foreign-call
adapters, runtime integration, and concrete instruction-cache synchronization
remain incomplete.

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
