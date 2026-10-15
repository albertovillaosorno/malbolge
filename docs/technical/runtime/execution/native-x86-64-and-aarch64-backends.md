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
`.rdata` constants are allowed. Relocations must reference an existing
one-based section or the COFF-defined absolute-symbol sentinel; undefined,
debug-only, and out-of-range section references fail closed.

The COFF file header must identify an object module: image-only flags such as
`RELOCS_STRIPPED`, `EXECUTABLE_IMAGE`, and `DLL` are rejected even when the
optional-header size is zero. Image-only large-address, aggressive working-set,
removable/network-media, system, and uniprocessor-policy flags also fail
closed. The `32BIT_MACHINE` flag conflicts with the admitted AMD64/AArch64
identities.

Relocation-free extraction shares this
file-characteristics gate. COFF object sections also require `VirtualSize`
to be zero rather than accepting the image-only loaded-size field.

The obsolete stripped-line-number, stripped-local-symbol, and byte-order
reversal file flags are rejected as unsupported object representations.
The image-only separately stored debug-information flag is also rejected.
The reserved file-characteristic bit is also rejected rather than ignored.

The callable `.text` section also cannot be marked as linker-only
information or linker-discarded, even when its code/read/execute bits are set.
COMDAT-selected code is also unsupported because the loader owns no COMDAT
selection semantics. The `.mbprof` identity section likewise cannot be
linker-only information, discarded, or COMDAT-selected. Neither the callable
`.text` section nor `.mbprof` can be marked `MEM_DISCARDABLE`, because both
must remain independently available during native execution and admission.

The callable `.text` cannot simultaneously claim initialized or uninitialized
data content. Likewise, `.mbprof` cannot claim code or uninitialized data
content while presenting itself as read-only initialized identity metadata.
These permission and required-content checks are shared with relocation-free
COFF extraction, which cannot independently verify the key-bound metadata.

Both `.text` and `.mbprof` also reject non-cacheable, nonpageable, and shared
memory flags because these image-loader policies have no object-level owner.
Legacy `NOLOAD`, 16-bit/purgeable, locked, and preload flags are likewise
unsupported on these two required loadable sections.
Obsolete no-padding, reserved linker-OTHER, and GP-relative section bits
are unsupported for the same two sections. Auxiliary sections likewise
cannot claim these unsupported section-format or linker behaviors.

All COFF sections must declare at most one of the code, initialized-data,
and uninitialized-data content kinds. Sections with no content-kind bit remain
admissible where the compiler uses them for linker or debug bookkeeping.
Executable-memory permissions require a section to declare code content;
linker bookkeeping without a content kind cannot silently become executable.
Conversely, every code-classified section must be both readable and
executable, not just the required callable `.text` section.

Data-classified sections cannot also claim executable-memory permissions.
Uninitialized-data sections cannot claim file-backed raw bytes. Zero-fill
uninitialized storage still requires read permission even when it has no raw
bytes in the object. Even empty
`.bss` sections must reject legacy loader hints and image-only memory policies;
those bits have no object-level loading authority.

Initialized-data sections, including empty COMDAT bookkeeping sections,
reject obsolete load hints and image-only memory policies regardless of raw
size. Every initialized-data section must be readable, including the empty
compiler bookkeeping COMDATs with no file-backed bytes.
They cannot request legacy `NOLOAD`,
16-bit/purgeable, locked, or preload treatment from an image loader.
They also reject non-cacheable, nonpageable, and shared-memory policies.

Code-classified auxiliary sections reject the same legacy loader hints and
image-only memory policies even when they have zero raw bytes. They cannot
be marked linker-only information, removed before linking, or declared
memory-discardable, since none provides persistent executable code.
Discardable compiler debug data remains admissible as non-code storage.

Relocations originating in executable code cannot depend on discardable,
linker-only, or linker-removed sections; debug-origin relocations remain
subject to ordinary COFF symbol closure rather than executable residency.
Code-origin relocations require targets to advertise a code, initialized-data,
or BSS content kind. They reject zero-byte targets without a BSS content kind;
only zero-fill storage can own a loadable empty section.

Code-origin references to empty BSS COMDATs also require explicit valid
selection, instead of treating unselected bookkeeping as a defined target.
Code-origin relocations cannot reference `.mbprof` identity metadata; only
admission reads those key-bound bytes, not executable native instructions.

Nonempty relocation patches cannot overlap within any COFF section, including
compiler debug-data sections. Zero-width metadata relocations claim no patch
bytes and remain valid. Relocation spans are checked section-relative.

ARM64 branch, page-relative, and immediate relocations in code sections must
patch four-byte-aligned instruction offsets. Relocations in data and debug
sections retain their separate width rules without instruction alignment.
A code-kind section does not gain loadable-object semantics by leaving the
callable `.text` section unchanged.

Ordinary (non-COMDAT) section definitions with an auxiliary record must
match the owning section name, use static storage class, and have a
zero-valued, null-typed primary symbol;
its geometry must agree with the
section header's raw length and relocation count, declare zero line numbers,
and own exactly one auxiliary slot. No ordinary section may have two
matching auxiliary section definitions.

Combined name and storage-class disguises of a null-valued, null-typed
definition fail closed. The first auxiliary-backed symbol cannot hide
its ordinary section ownership by changing its name together with its
value or symbol type.
The validator uses a single forward symbol pass for that ownership check.

An auxiliary-backed null-valued, null-typed static or external symbol
cannot use UNDEFINED, ABSOLUTE, or DEBUG section sentinels. Altering
its name or switching between these storage classes does not bypass closure.

Unused selector and big-object-only high section-number bytes, and the COMDAT
selection byte, must be zero.
Otherwise a compiler object could conceal contradictory or unsupported
auxiliary data outside COMDAT validation.

Populated auxiliary COMDAT sections require a matching static section
symbol with a defined PE/COFF selection code (`1` through `7`). Invalid or
missing section-definition selectors fail closed. Each populated COMDAT
section-definition symbol must own exactly one auxiliary record.

Its primary symbol must have a zero section-relative value and null COFF
symbol type. It must also precede every other symbol defined in that COMDAT
section.

The auxiliary section length and relocation count must match the owning
header; the auxiliary line-number count must remain zero. The unused
selector byte and big-object-only high section number must also be zero.

Unselected empty COMDAT sections without relocations remain admissible,
matching legitimate pinned Clang output. An empty COMDAT with an explicit
nonzero selection must satisfy the same section-definition and association
checks as a populated COMDAT. Another null-typed auxiliary-backed symbol
cannot claim the selected owner's section under a mismatched name, even
if the extra symbol's value is nonzero.

Renaming or reclassifying an auxiliary-backed
selected empty section does not bypass selector validation.

When an associative section references an unselected empty parent, admission
rejects its missing selection. Referenced empty COMDATs may themselves be
associative; their entire parent chain is checked for valid selection and
cycles.

Unselected empty COMDATs with an auxiliary section-definition record must
also have a zero-valued, null-typed primary section symbol, matching length
and relocation geometry, zero line numbers, exactly one auxiliary slot, and
zero reserved auxiliary bytes. Renaming or changing the storage class of a
null-valued, null-typed auxiliary-backed section definition also fails closed.
The first auxiliary-backed symbol in an empty COMDAT cannot hide its
section identity by changing its name and value together. Duplicate
zero-selected section definitions are rejected.

The first-symbol check tracks ownership during one forward scan of the
symbol table.

Associative selection (`5`) must refer to a distinct, existing one-based
section number; zero, self-association, and out-of-range section references
are rejected without calling a linker. The referenced parent must itself
be a COMDAT section; associating to ordinary executable `.text` is invalid.
Associative COMDAT chains must also be acyclic; a valid immediate parent
does not make a circular dependency admissible.

Defined function-typed symbols must designate an actual byte of executable
code, never an empty COMDAT section or data-only storage. Such malformed
symbols cannot acquire a function body merely through auxiliary records.
Static function symbols also cannot claim the undefined, absolute, or debug
section-number sentinels in place of an executable definition.

Unreferenced symbols are also checked for valid one-based section numbers or
the three COFF-defined sentinels (`0`, `-1`, `-2`), preventing hidden
invalid sections.

Pinned ARM64 compiler-object mutation regressions also check that relocation
addresses fall within the owning section's virtual-address origin and raw byte
extent. Admission recognizes only defined relocation kinds for the object's
x86-64 or AArch64 machine ID and bounds the complete relocation patch width
(e.g., two-, four-, or eight-byte fields) to its owning section. Undefined
relocation kinds and patches crossing a section boundary fail closed.

Relocation-count overflow encoding is deliberately unsupported and rejected:
its first record stores a count rather than a symbol relocation. x64
span-dependent `SREL32`/`SSPAN32` and their required `PAIR` records also fail
closed until the native adapter owns their paired linker semantics.

The COFF object layout is further required to have disjoint on-disk regions
for headers, initialized section bytes, relocation records, symbol slots, and
long-name storage. The long-name string table must end at a NUL
terminator, even when its final entry is not referenced by any symbol.

A section cannot alias its own headers or borrow symbol or
string-table bytes as executable code. Zero-size sections own no bytes.
Unowned trailing overlays are also rejected; an explicitly referenced
relocation table after the string table remains owned and admissible.
Interior gaps may hold zero-valued alignment padding, but nonzero bytes
outside declared headers, section data, relocations, and tables are rejected.

COFF line-number debugging records are not implemented by this validator.
Section alignment uses defined PE/COFF codes only. Alignment code `15`
(the reserved all-ones encoding) is rejected even if raw data is in bounds;
normal compiler alignment encodings remain valid on both target ISAs.

Both the section's line-number pointer and count must be zero; orphan pointers
and advertised debug tables fail closed rather than bypassing layout checks.

Relocation table pointers and counts must also agree about table presence:
zero count requires zero pointer; a nonzero count requires a nonzero pointer.
This forbids unowned relocation pointers as well as records at offset zero.

Raw section pointers are bounded even when a section owns zero raw bytes;
such sections may retain in-file offsets emitted by the compiler. Populated
sections must use a nonzero file offset rather than aliasing the COFF header.

Every symbol defined in a section with raw bytes must point no farther
than one past the section's end. Zero-raw-size sections remain exempt because
uninitialized COFF data can contain logical symbols without file-backed bytes.
This bound applies to unreferenced static symbols, not only the public entry.

The required public entry symbol must use exactly COFF's external function
type (`0x0020`); other base or derived type bits are rejected rather than
mistaken for a valid callable entry.

Short COFF section and symbol names must have zero-filled padding after
their first NUL byte; nonzero bytes hidden past a terminator are rejected.
This also applies to slash-prefixed section string-table offsets.
Those offsets must contain ASCII decimal digits only: an integer-parser
sign prefix such as `/+12` is not a valid COFF name reference.

Long COFF section and symbol names must terminate inside their declared
string-table extent. Referenced offsets must designate the start of a string
rather than an embedded suffix of another name. A NUL-terminated suffix by
itself does not grant an independent name identity. Structural admission stops
before semantic equivalence or execution authority; it is not a linker or
instruction verifier.

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
both ISA implementations.

A tracked POSIX x86-64 harness extracts the frozen fixture `.text`, stages it
RW, seals the same mapping RX, synchronizes instructions, and invokes the entry
with Clang `ms_abi`. Hit, byte-identical miss, and null-state execution are
covered; ARM64 object linkage remains verified independently.

The Rust regression separately requires the production emitter to reproduce the
complete frozen object. This host harness remains independent development
execution evidence; the concrete process-backed POSIX adapter and runner are
described below. The direct template remains a deliberately tiny subset rather
than general instruction selection.

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
profile successor functions independently derive the required IR.

Each ISA reuses the fetched-cell guards, then atomically writes the encrypted
code cell and exact next `C/D`. Independent complete objects are 557/658 bytes.
A tracked POSIX x86-64 harness extracts the frozen `.text`, stages it RW, and
seals the same mapping RX. It synchronizes instructions and invokes it through
Clang `ms_abi`.

It proves `memory[5]:77->65`, `C:5->6`, `D:7->8`, preserved unrelated ABI
fields, and atomic live-in/capacity/null-memory/null-state misses. Independent
AArch64 decoding confirms the same commit and one common miss target. This
remains development execution evidence rather than the production platform
adapter.

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

Host-independent v6 semantic admission also recognizes traced no-operation,
rotate, Crazy, and output shapes. No-operation reads/writes C/D while A remains
dead; rotate reads C/D and writes A/C/D; Crazy reads and writes A/C/D. Output
reads A/C/D but writes only C/D. Mask drift fails closed before host-code
authority.

Distinct revision-1 object families currently emit no-operation, rotate, Crazy,
and output on x86-64 and AArch64. Output guards A/C/D, output length, code
live-in, memory extent, prior termination, and output capacity. Input history
remains key-bound without entering machine text.

Output v6 now also has a distinct relocation-free load image and dedicated
staged/sealed/ready lifecycle typestates. They retain exact identity, ISA
alignment, strict RW-to-RX/full-sync policy, and exact release evidence. A
dedicated platform path loads and releases the mapping transactionally, cleans
post-allocation failures, and retains exact ready ownership for release retry.

Prepared Output calls require exact live A/C/D and output length while allowing
only input-history rebasing. Exact ready-image equality binds the call to one
synchronized mapping and restores the full entry snapshot on mismatch. A
dedicated Output runner port now admits Applied/GuardMiss and restores the full
snapshot on runner or completion failure.

A reusable Output owner now retains
the verified program, artifact, and ready mapping across rebased calls. It uses
platform mapped length for residency weight and preserves release-retry
ownership.

A single-resident Output lease cache now reuses that exact owner without adapter
work, rejects different identity while occupied, and blocks release under live
leases. Failed loads publish nothing, while release failure transfers exact
retry ownership.

A one-shot Output transaction now composes exact load, bound call, completion,
and release. Load or call failure restores the prepared snapshot and attempts
exact cleanup; committed release failure retains both outcome and ready mapping
for retry.

A weighted multi-resident Output lease cache now reuses exact owners under FIFO
limits without refreshing hit age. Live victims retire while retaining charged
weight; invalidation, release, return, reconciliation, and limit changes retain
keyed cleanup retry ownership.

Exact Output sequence planning now admits continuous same-profile/same-target
one-step chains, preserves ordered artifact identity, and rejects terminated
prefixes or identity drift before mapping.

Loaded Output sequence ownership now publishes only complete plans, cleans ready
prefixes in reverse after late load failure, and retains exact failed executable
ownership for retry.

Loaded Output sequence execution now advances exact output observations through
retained mappings without adapter work. Guard miss returns the current resume
boundary; current-step failure rolls back memory/output while preserving the
committed prefix and reusable residency.

A weighted FIFO Output sequence cache now reuses exact loaded chains without
adapter work on hits, preserves FIFO age, and enforces entry, mapping, and
mapped-byte limits. Eviction, invalidation, reconfiguration, and release-all
failures retain exact retryable cleanup ownership.

Rotate guards C/D, exact memory extent, both code/data live-ins, and prior live
termination before committing the reviewed data/code writes and A/C/D results.
Dead A and I/O history remain bound in the full v6 key without changing rotate
machine text. Crazy uses the same reviewed two-write commit but additionally
guards live A. I/O history remains key-bound but absent from Crazy machine text;
a changed entry accumulator changes the canonical object.

Independent Crazy verification structurally admits COFF and regenerates exact
canonical bytes. A Crazy-specific relocation-free image retains exact
key/target identity, ISA alignment, and strict RW-to-RX/full-sync policy.
Dedicated Crazy typestates now admit exact copied bytes, same-mapping RX
transition, full-range synchronization, and exact release evidence.

A dedicated Crazy platform path now loads/releases that ready mapping
transactionally with post-allocation cleanup and exact release-retry ownership.
A distinct prepared Crazy call requires exact live A/C/D while permitting only
I/O-history rebasing, and it admits exact Applied/GuardMiss completion.

The prepared call binds only to the identical synchronized Crazy image and
restores its entry snapshot on identity drift. A dedicated loaded Crazy runner
now consumes only that bound view, admits exact Applied/GuardMiss outcomes, and
restores the entry snapshot after runner or completion failure.

The loaded boundary performs no adapter work. A one-shot Crazy transaction now
composes exact load/call/release, restores the prepared snapshot on load or call
failure, and retains committed outcome plus exact ready mapping on release
failure. A reusable Crazy owner now retains that exact synchronized mapping
across rebased calls and runner failure without remapping, and reports platform
mapping weight.

A single-resident Crazy lease cache now reuses that exact owner without adapter
work, rejects different identity while occupied, blocks release under live
leases, and transfers retryable cleanup ownership.

An exact Crazy sequence planner now admits
non-empty continuous same-profile/same-target one-step chains, preserves ordered
artifact-key identity, and rejects terminated prefixes or identity drift before
any mapping.

Loaded Crazy sequence ownership now publishes only fully loaded plans, cleans a
ready prefix in reverse after late load failure, and retains exact failed
executable ownership for release retry.

Loaded Crazy sequence execution now preserves exact committed-prefix evidence,
returns guard misses at the current resume boundary, and reuses loaded mappings
after current-step runner failure.

A weighted FIFO Crazy sequence cache now reuses exact loaded chains without
adapter work on hits, preserves FIFO age, and enforces entry, mapping, and
mapped-byte limits. Eviction, invalidation, reconfiguration, and release-all
failures retain exact retryable cleanup ownership.

A Crazy sequence lease cache now shares immutable loaded chains, retires live
leased FIFO victims without hiding their weight, blocks unsafe limit shrink,
and reclaims retired residents only through explicit return or reconciliation.
Release and reconfiguration failures preserve keyed retry ownership.

A multi-resident Crazy lease cache now reuses exact owners under weighted FIFO
limits without refreshing hit age. Live leased victims retire without hiding
their entry, mapping, or mapped-byte weight; unleased victims release
immediately. Invalidation, release-all, explicit lease return, retired
reconciliation, and limit reconfiguration preserve keyed cleanup retry
ownership.

A rotate-specific relocation-free image now retains exact key/target identity,
ISA alignment, and strict RW-to-RX/full-sync policy. Dedicated rotate typestates
admit exact copied bytes, same-mapping RX transition, full-range
synchronization, and exact release evidence.

A dedicated rotate platform path now loads/releases the ready mapping
transactionally with post-allocation cleanup and exact release-retry ownership.
A distinct prepared rotate invocation requires exact live C/D, permits dead
A/I/O rebasing, and admits only exact Applied/GuardMiss completion with complete
snapshot rollback on rejection. Binding now accepts only the identical
synchronized rotate image and restores the entry snapshot on identity drift.

A dedicated loaded rotate runner consumes only that bound view, admits exact
Applied/GuardMiss outcomes, and restores the entry snapshot after runner or
completion failure. A one-shot rotate transaction now composes exact
load/call/release with cleanup and committed release-retry evidence.

A reusable rotate owner retains one exact synchronized mapping across rebased
calls, reports platform mapping weight, and remains reusable after runner
failure. A single-resident rotate lease cache admits only exact
program/artifact hits, returns immutable shared leases without adapter work, and
blocks release while leases remain live. Failed loads publish no resident, and
release failure transfers exact retry ownership.

Exact rotate sequence planning now admits continuous ordered v6 program/artifact
topology and preserves host-target-sensitive ordered identity without granting
mapping or runner authority. Loaded rotate sequence ownership now maps every
admitted step before publication, reports aggregate mapped weight, releases in
reverse semantic order, cleans complete loaded prefixes on later load failure,
and retains failed releases only for explicit retry.

Indexed loaded-sequence execution now advances exact observations through
retained rotate owners without adapter work, returns exact guard-miss resume
boundaries, and preserves committed-prefix evidence on later runner failure.

A rotate-specific weighted FIFO now reuses exact ordered artifact-key chains.
Hits preserve insertion age and perform no adapter work; misses load completely
before entry/mapping/mapped-byte admission and evict oldest entries until every
limit fits. Oversize candidates and failed eviction retain exact cleanup retry
ownership without publishing the candidate. Explicit limit reconfiguration
expands without adapter work and shrinks through the same FIFO release boundary
while prior limits remain published on failure.

A separate weighted rotate sequence lease cache now shares immutable loaded
sequences on exact hits. Active victims with live leases retire without reducing
their entry, mapping, or mapped-byte weight; unleased victims release
immediately. Invalidation, full drain, explicit lease return, and retired
reconciliation retain keyed cleanup retry ownership. Lease-aware limit changes
shrink active FIFO authority through the same release-or-retire path while prior
limits remain published on blockage or release failure.

A separate relocation-free load-image type retains exact key/target identity,
ISA alignment, and the strict RW-to-RX/full-sync policy. Dedicated lifecycle
typestates admit exact copied bytes, same-mapping RX transition, full-range
synchronization, and exact release evidence. A dedicated platform path now
loads/releases the ready image transactionally with post-allocation cleanup and
exact release-retry ownership.

A distinct prepared call requires exact C/D while allowing dead A/I/O
rebasing, validates exact completion, and binds only to an identical ready
image. A dedicated no-operation runner consumes only that bound view, admits
exact Applied/GuardMiss outcomes, and restores the rebased snapshot after
runner or completion failure. One-shot orchestration now composes exact
load/call/release with cleanup and committed release-retry evidence. A reusable
owner retains the exact no-operation mapping across rebased calls and runner
failure without remapping.

A distinct single-resident lease cache shares that
owner on exact hits, blocks release while leased, rejects different identity,
and transfers cleanup retry ownership.

A distinct no-operation sequence plan now validates non-empty/count,
one-effect v6 shape, profile/observation continuity, common target, exact
artifact identity, and early termination before any mapping. A separate loaded
owner maps the complete admitted plan only after every exact owner load
succeeds, retains exact mapped-byte evidence, and releases mappings in reverse
with aggregate retry ownership. A dedicated loaded-sequence executor now calls
only retained no-operation owners and performs no adapter work. Applied and
guard-miss outcomes retain exact progress; current-step failure rolls back and
keeps the loaded mappings reusable.

An ordered sequence key derives the exact artifact-key chain from the admitted
plan. A weighted FIFO cache reuses exact loaded sequences through borrowed
entries: hits perform no adapter work, misses load completely before
oldest-first entry/mapping/byte admission, and overflow or oversize candidates
fail closed with retryable cleanup ownership. Explicit limit reconfiguration
expands without adapter work and shrinks through the same FIFO release path;
failed shrink keeps prior limits published.

A separate weighted sequence lease cache now shares immutable loaded sequences
on exact no-I/O hits. Active victims with live leases retire without reducing
their entry, mapping, or mapped-byte weight; unleased victims release
immediately, and admission reports exact retired-resident blockage when no
active FIFO release can fit the candidate. Invalidation, full drain, explicit
lease return, and retired reconciliation retain keyed cleanup retry ownership.

Lease-aware limit reconfiguration now publishes expansion or already-fit
requests without adapter work and shrinks active FIFO authority through the
same release-or-retire path. Existing retired mappings are never reconciled
implicitly; blockage or release failure retains prior limits plus exact blocker
or keyed retry evidence.

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

A separate weighted multi-entry cache preserves exact-hit FIFO age and
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

The tracked `native/native_region_abi.h` now supplies the same C scalar, status,
call-frame, and opt-in POSIX Windows-x64 bridge declarations to bootstrap source
generation and both executable development harnesses. This removes duplicated C
layout and function-pointer authority without adding executable-memory ownership
or a production foreign-call implementation.

`native/process_call.rs` now converts one already-bound direct invocation into
pointer-free owned state, memory, input, and output evidence for the
process-isolated host. Returned mapping identity, immutable capacities, buffer
shape, and child pointer-integrity evidence are checked before caller buffers
change; the existing invocation verifier still owns final status and semantic
admission. No process transport, executable-memory syscall, or foreign call is
implemented by this transfer boundary.

`native/process_call_wire.rs` now defines the transport-neutral `MBNPC1`
little-endian framing for that pointer-free transfer. Requests have a stable
77-byte prefix before exact memory/input/output payloads, while responses have
a 74-byte prefix before memory/output payloads; response allocation bounds are
derived from the original request rather than child-reported capacities. The
request decoder also checks overflow and the exact full frame length before
allocating its attacker-declared memory/input/output payloads; even a
`u64::MAX` word count cannot trigger unchecked allocation.

The response word reader likewise checks the complete request-sized memory span
before reserving the output vector, even if the child omitted all memory bytes.
Truncated response-word fixtures bind this preallocation policy. The
response decoder also checks the entire request-bounded frame before allocating
memory words, including the output suffix and any trailing bytes. The codec
rejects malformed magic, zero mapping identity, noncanonical pointer flags,
shape drift, truncation, and trailing bytes without spawning a process or
gaining semantic authority.

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
runner-failure, completion-drift, and release-failure cases pass.

This generic safe port itself performs no OS operation or foreign call; the
concrete process-backed POSIX implementation follows below.

`execute_verified_native_with_host` now provides an ownership-safe orchestration
path when one stateful host implements both executable-memory and runner ports.
The same mutable owner performs load, bind, call, admission, and release without
requiring aliased mutable references or shared-lock indirection, while
preserving
the existing rollback, cleanup, and committed-outcome contracts. This is the
intended seam for a persistent child process whose mapping IDs must remain valid
through the later native call.

`native/process_session.rs` now retains one configured child process across
multiple bounded byte exchanges. Each request and response uses an outer
little-endian `u64` payload length; child-announced response size is checked
against both the host's allocatable vector length and the caller limit before
allocation. Lengths above `isize::MAX` fail as typed `ResponseLength` errors,
not capacity-overflow panics, even with an unlimited caller bound.

Even smaller representable lengths can exceed available host address space.
Response buffers now use fallible exact reservation, returning typed
`ResponseAllocation` rather than aborting on failed allocation. A child that
announces a 4-EiB response exercises this rejection without reading payload.

Any I/O, truncation, or size failure poisons and terminates the session.
Deterministic workers prove one
child survives multiple exchanges and that oversized/truncated responses fail
closed. The session does not interpret MBNPC1 or yet implement executable-memory
commands or the foreign call itself.

A real Python-child configuration fixture now checks exact argument boundaries,
including an empty argument and an argument containing spaces. The same
fixture checks last-write-wins environment overrides and the configured
working directory under both timed and untimed retained sessions.

Transport boundary tests now also distinguish a valid zero-byte response from
partial header framing. A Python child sends three consecutive empty response
payloads to zero-limit exchanges (including empty requests) without session
poisoning; a separate child emits only four of the required eight response-
length bytes and triggers `Read(UnexpectedEof)` and permanent session poisoning.

A caller may now configure an explicit per-exchange deadline on the retained
native child session; the default remains unlimited for compatibility.
The deadline covers both framed request writes and response reads. When it
expires, the owning direct child is killed and the session is poisoned.

Timed native sessions also reject child-announced response lengths of 2^63
or 2^62 bytes without panicking, despite a caller limit of `usize::MAX`.
Those failures retain the same typed `ResponseLength` or
`ResponseAllocation` outcome as untimed exchanges and permanently poison the
owning child rather than treating a malformed length as a deadline timeout.

A zero-duration budget now deterministically expires before request cloning,
pipe ownership transfer, or worker-thread creation. Both empty and one-megabyte
requests return `ExchangeTimeout` immediately, poison the owning session, and
cannot be retried through that child.

Positive exchange budgets now also start before request cloning and transport
thread startup. The receiver waits only for the unused remainder, so setup
cost can no longer silently grant a second full deadline. A host-real
one-megabyte request with a positive nanosecond deadline fails closed and
poisons only its retained session, while zero budgets retain early rejection.

A descendant can inherit the child's response pipe. Joining the blocked read
thread after killing only the direct child formerly extended a 300-ms deadline
to roughly four seconds in a host-real adversarial fixture. Timed sessions now
transfer owned pipe handles to a detachable transport thread, return promptly
on deadline expiry, and never reuse the poisoned stream. A fallible request
copy avoids parent-process allocation aborts before the timed exchange begins.

The transport worker also uses fallible thread creation: a failed spawn is
returned as typed `WorkerSpawn` instead of panicking the parent, and the owned
child session is terminated and poisoned on that failure.

A symmetric test has a descendant inherit the request pipe without consuming
bytes. A one-megabyte request now returns within the same 300-ms deadline even
when the descendant still holds the read end after direct-child termination.

A sibling-session regression runs a separate responsive echo child before and
after a failed deadline exchange with a descendant-held response pipe. The
timeout is isolated to its own poisoned session; the healthy sibling retains
response order, original stream identity, and its full exchange deadline.

A separate concurrent fixture rendezvous-starts a stalled-response exchange
on a background thread alongside an active sibling echo exchange. The stalled
child expires its independent 650-ms deadline and becomes poisoned while the
echo child returns ordered frames both during and after that timeout.

Host-real Python fixtures sleep instead of consuming a large request or
answering a completed request. Both return typed `ExchangeTimeout` within
the configured bound, while a responsive echo child completes three exchanges
and retains its session under the same optional deadline policy.

Partial-response fixtures further stall after four response-header bytes or
after announcing four payload bytes but delivering only two. Both time out,
terminate the direct child, and refuse subsequent exchange on the poisoned
session; neither partial frame becomes an admitted response.

A drip-feed fixture emits one response byte every 120 ms, separately for the
header and payload. Each 350-ms exchange deadline expires despite partial
forward progress; no sequence of short successful reads renews that budget.

Request-side adversarial fixtures progressively drain a one-megabyte request
at 4,096 bytes per 120 ms or fill stdout before reading stdin, producing a
two-pipe deadlock. Both expire under the same cumulative 350-ms deadline,
terminate the child, and refuse further use of the poisoned session.

A timed transport parity fixture also checks truncated headers, truncated
bodies, and oversized response announcements against the untimed error kinds.
A retained timed child handles three consecutive zero-length responses with a
zero-byte limit without becoming poisoned; only failed frames end its session.

The session-backed `NativeProcessHost` preserves those errors across its
memory-adapter boundary. A stalled allocation reports typed `ExchangeTimeout`,
while an oversized response reports `ResponseTooLarge`; neither failure admits
later allocation requests on that now-poisoned child.

Another retained child returns a complete successful first response, then
stalls on its second request. The deadline resets per exchange: the first
response is admitted, the second expires, and subsequent use is refused.

`native/process_memory_wire.rs` now defines the transport-neutral `MBNPM1`
little-endian command protocol for writable allocation, exact code copy, RX
protection, instruction synchronization, and release. Mapping/address/length/
permission reports and copied bytes remain untrusted evidence; the existing safe
lifecycle still owns every identity, W^X, range, capacity, and byte-exact
admission check.

Copy response size derives from the original copy request, while failure
encoding reserves only its 14-byte prefix regardless of copy size. Child
failures carry only an opaque `u32` platform code.

Successful response encoding validates the command/response variant and copy
length before reserving any bytes. Drifted success evidence returns typed
`ResponseShape` without allocating the request-sized copy buffer.

Successful MBNPM1 frames now also match the exact original request before
admission. Allocation reports must preserve length, permission, and required
base alignment; copy reports must preserve mapping ID, start address, and
byte-exact code; protection and synchronization must preserve their mapping
and range identities. Forged command-specific fields fail as `ResponseShape`
without accepting a new executable mapping or changing caller-owned memory.

Successful allocation evidence now additionally requires a nonempty RW
allocation, power-of-two requested alignment, and representable reservation
length. A forged exact-match response cannot turn zero-byte, zero- or non-
power-of-two-aligned, or initially RX allocations into admitted successes.
Failure responses remain independently framed and may report invalid requests.

Other successful lifecycle transitions now also require their preconditions:
code can be copied only into a nonempty RW mapping, and protection success
requires an existing nonempty RW mapping to transition into RX. Release and
instruction-cache synchronization must describe nonempty mapped ranges.
The codec rejects matching but impossible child success evidence instead of
letting it reach trusted mapping lifecycle admission.

Invalid lifecycle requests still admit the worker's independent 14-byte
failure response without allocating successful-copy evidence. A codec test
round-trips failures for invalid allocation, copy, protection, release, and
synchronization requests while leaving their forged success forms rejected.

Allocation and protection success reports also reject address ranges whose
base plus mapped length wraps `usize`. Such otherwise-aligned child evidence
fails as `ResponseShape` before the trusted executable lifecycle sees it.

Successful synchronization responses likewise reject ranges whose start plus
requested byte count overflows `usize`. Even byte-exact matching of forged
request and child report cannot confer authority over an impossible range.

Copied-code success reports also require the code bytes to fit inside the
original mapping capacity, and the complete mapped interval to fit `usize`.
Matching a forged request is insufficient when the mapping geometry is
impossible, even if the child returns the exact requested code bytes.

Release success has no returned address fields, so its only geometry evidence
comes from the exact original release request. The MBNPM1 success codec now
rejects that request when the base plus mapped length would wrap `usize`,
even if the child replies with an otherwise correctly framed release tag.

The copied-code request decoder and successful response decoder now check the
complete framed payload before allocating owned copies. Truncated payloads and
trailing bytes fail closed without duplicating otherwise valid code first.
No syscall or mapping ownership is implemented by this codec.

`native/process_host.rs` now binds both MBNPM1 and MBNPC1 to the retained
child session. The same `NativeProcessHost` implements executable-memory and
runner ports, so one child owns allocate/copy/protect/synchronize, the pointer-
free call exchange, and release. MBNPC1 responses are request-bounded, then
structurally applied before the existing semantic completion verifier runs;
mapping drift is rejected before caller mutation.

Response admission now also rejects an input-consumed cursor beyond the
original input length or an output length beyond its original capacity. These
failures precede copying any returned memory, output, or scalar state into
caller-owned buffers. Hostile-response fixtures prove both overflow paths
leave the caller's original state unchanged.

A wire-to-verifier regression now forges each immutable MBNPC1 response count
for guest-memory words or input capacity to `u64::MAX`. The exact response
payload remains bounded by the original request during decoding, then scalar
admission rejects the mismatched capacity before modifying caller buffers.

Deterministic persistent workers prove the complete load/call/release
transaction plus remote-memory and call-response rejection paths.

A host-real verifier-rollback fixture runs native stubs that mutate guest
memory, output, or one of the accumulator, code-pointer, and data-pointer
registers before returning `GuardMiss`. The worker reports the real mutation
over MBNPC1; Rust semantic completion rejects every non-atomic miss as the
appropriate state, memory, or output violation, restores caller buffers, and
leaves each mapping releasable on the retained child.

The same real-worker rollback fixture now also changes the output cursor
from one to two within capacity, or replaces `Running` with the normative
`HaltInstruction` termination tag. Both are structurally valid state fields,
but neither may be committed by a failed native guard; Rust rejects both as
`NonAppliedMutation(State)` and preserves the original caller snapshot.

A complementary host-real success-forgery regression invokes a native entry
that returns `Applied` while leaving the required register, memory, and output
transition incomplete. The semantic verifier rejects that false status as
`AppliedObservation`, restores the original caller buffers, and retains the
same worker for cleanup and subsequent allocation. A second stub returns
an unknown native status (`9`), which is rejected as an explicit status error
with the same rollback and retained-worker recovery.

`native/native_process_worker_posix.c` now supplies the first concrete child
implementation. On Linux x86-64 it allocates anonymous RW mappings, copies exact
verified image bytes, transitions the same mapping to RX, performs full-range
instruction synchronization, invokes the retained entry through the reviewed
Windows-x64 ABI bridge, and releases the mapping. Mapping identity remains
child-owned while every platform/state result returns as untrusted evidence to
the existing Rust lifecycle and semantic verifier. A host-real Rust regression
compiles the tracked worker with pinned Clang and drives the admitted
direct-output artifact through the complete process host; the exact
`memory[5]:94->57`, output append `0xa8`, and `C/D:5/7->6/8` transition is
accepted before release.

Independent host-real malformed-frame tests now launch the POSIX worker with
partial headers, truncated declared payloads, unknown protocol tags, and short
native-call requests. Each terminates with the specified framing/dispatch error
and emits no response bytes, without publishing any guest execution state.

The framing regression also rejects an announced `u64::MAX` byte length
without payload as a read failure, and a zero-length payload as an unknown
protocol. Neither case emits a response or grants native-call authority.

A positive host-real stream fixture sends five valid MBNPM1 commands to one
POSIX child using one-, two-, three-, five-, and seven-byte pipe writes.
The worker retains one 64-KiB-aligned mapping through allocate, exact code
copy, RX protection, full-range synchronization, and release; each bounded
response decodes against the corresponding original request. Closing input
after release produces clean EOF with no surplus output or mapping leak.

A separate host-real isolation regression runs two independent POSIX children.
Sending an unknown outer protocol poisons and terminates only the first child;
the sibling session remains able to allocate and release native memory.

A further two-child regression invokes `ud2` trap bytes from an executable
mapping, exercising a real illegal-instruction fault rather than a framing
failure. Only the executing worker terminates and poisons its session; the
independent child still allocates and releases memory successfully.

An over-aligned variant preallocates separate 64-KiB-aligned mappings in both
children. After an RX `ud2` traps and poisons only the first session, the
second child still copies, seals, executes, and releases its existing mapping.
That child can also allocate again; fault cleanup does not cross process or
reservation ownership boundaries.

A separate pair of host-real cases executes `mov byte ptr [rip - 7], 0xcc`
from an RX mapping, deliberately writing to its own executable entry byte.
The write triggers protection failure in both ordinary and 64-KiB-aligned
mappings, poisoning only the executing child; the sibling retains live code,
mapping release authority, and further allocation capability.

A host-real MBNPC1 payload-shape fixture also sends valid outer framing but
forged `u64::MAX` guest-memory, input, and output lengths. Truncated and
trailing-byte call payloads fail the same dispatch boundary. Each child exits
with no response or native guest-state publication.

A separate host-real regression sends a structurally malformed MBNPM1 allocate
command, checks the exact remote failure response, and then allocates and
releases a valid mapping through that same persistent POSIX child. Rejected
memory commands do not silently desynchronize or poison a healthy transport.
The same session also checks an unknown inner MBNPM1 command tag: the worker
returns a command-tagged failure frame and retains synchronization.

A further real-worker framing regression truncates and extends all five MBNPM1
command payloads, checking their exact command-specific failure frames. None
can alter an active mapping or poison the retained transport: a valid code
copy and release still succeed afterward.

Another host-real regression sends a well-formed MBNPC1 call for an absent
mapping. The child returns the native invalid-argument status with unchanged
state, memory, output, and pointer identity; that retained child then allocates
and releases memory successfully. A missing mapping cannot invoke foreign code
or corrupt the subsequent session.

A host-real x86-64 pointer-integrity regression also invokes three deliberately
mutating native stubs: each replaces the memory, input, or output pointer in
its reconstructed ABI state. The worker sets the pointer-change flag while
serializing memory and output through its original owned buffers, then
releases each RX mapping without losing the retained child session.

A stronger host-real pointer-integrity fixture first mutates a guest memory
word or output byte, then overwrites the native memory, input, or output
pointer while falsely reporting `Applied`. Although the POSIX child reports
the modified owned buffers, Rust structurally rejects `PointerIntegrity`
before copying them into caller memory. The original caller snapshot survives
all three cases, and each mapping remains independently releasable.

Five further x86-64 native stubs overwrite memory-word count, input length,
input consumption, output capacity, or output length with `u64::MAX`. The
retained POSIX worker serializes its originally allocated guest-memory and
output buffers rather than trusting the mutated ABI lengths. Each child call
returns bounded shape evidence and leaves future allocations operational.

The same five real responses now pass through a bound Rust invocation: each
is rejected with its exact structural capacity or progress error before any
caller memory, output, or scalar state is copied. The caller snapshots remain
unchanged and the retained POSIX child continues accepting valid requests.

Both C workers now check native-call input and output progress counters against
the transmitted capacities before invoking an RX entry. A host-real POSIX
regression reproduced the prior failure with a trap-byte mapping, then verifies
that counters just beyond capacity or at `u64::MAX` return invalid-argument
status with unchanged buffers and a healthy session. Valid code remains under
independent semantic verification by the Rust host.

The POSIX and Windows worker entry checks now also require the C ABI's three
normative termination tags (`Running`, `HaltInstruction`, or
`NonGraphicalCell`). Host-real testing reproduced native trap execution for
an unknown incoming tag before the fix; tags `3` and `255` now return
invalid-argument evidence without entering the executable mapping or
poisoning the retained session. A non-mutating real RX entry also accepts
all three normative incoming tags, returning unchanged buffer evidence and
remaining releasable on the same session.

A separate real-call regression checks returned termination evidence: a native
entry writes an unknown tag (`255`) into its ABI state and falsely returns
`Applied`. The worker returns that untrusted state as data; Rust semantic
verification then rejects the unknown termination, restores original caller
buffers, and permits clean worker release and reuse.

A complementary host-real call uses a non-mutating guard-miss test stub with
input consumed exactly equal to input length and output length exactly equal
to capacity. The worker invokes that RX entry for both empty input and a
one-byte input fully consumed. It retains the original buffers and releases
the mapping. Rejection uses strict overflow comparisons, not an overly broad
denial of valid end-of-buffer progress.

A separate real x86-64 entry reads a nonempty input byte through the native
ABI pointer, copies it into output storage, and advances input-consumed and
output-length cursors to one. Its `GuardMiss` result preserves guest memory,
reports the exact changed output byte, and retains all three reconstructed
pointer identities before normal mapping release and session reuse.

A second real entry uses nonzero native cursors: with two input bytes and one
output byte already committed, it reads `input[1]`, appends to `output[1]`,
and advances both cursors from one to two. The returned MBNPC1 response keeps
the original output prefix, untouched guest memory, and all pointer identities
before clean release and reuse.
A separate hostile x86-64 entry writes through its nominally immutable input
pointer within the POSIX child's private call-frame copy, then exposes the
modified byte through output. Replaying identical original request bytes
returns the same mutation without changing the caller's input or frame,
confirming child-local ownership and continued worker reuse.


A separate real POSIX call transfers zero guest-memory words, zero input, and
zero output capacity to a guard-miss stub. The worker reconstructs empty
buffers without changing pointer identities, returns the exact 74-byte call
response, and releases the RX mapping on the retained child.

A host-real W^X regression also allocates one still-writable mapping and sends
a valid call frame with that mapping ID. The child returns invalid-argument
status without executing bytes or changing state, memory, output, or pointer
identity, then releases the same mapping over the healthy session.

A separate host-real RX regression protects a writable mapping as executable,
then attempts to copy new code into it. The worker returns a typed protocol
failure without writing into the sealed mapping or losing the retained child;
the same RX mapping can still be released normally.

A second transition regression rejects cache synchronization while the mapping
remains writable and denies a second protect operation after it becomes RX.
Once sealed, full-range synchronization returns the exact expected report and
the retained worker releases the executable mapping without losing its session.

An aligned variant repeats the stale release, protection, and execution-ID
denials with two successive 64-KiB-aligned allocations. The current mapping
retains copy, RX protection, and release authority despite prior reservation
address reuse; stale IDs confer no authority in the retained child.

A host-real stale-identity regression releases one allocation, creates another,
and proves the original mapping ID cannot release or protect the new mapping,
even when the OS reuses its address. A valid RW copy succeeds for the new ID,
then a deliberate native trap installed in the new RX mapping cannot be
executed through a stale MBNPC1 call ID. The child returns invalid-argument
status with intact guest buffers and releases the live mapping normally.

Host-real forged-geometry requests also try to release an active mapping with
a correct ID but an incremented base address or reduced mapped length. Both
are rejected as remote mapping failures, preserving the real allocation for
exact release by its original geometry.

The same forged base and truncated length are also rejected by RW-to-RX
protection in a host-real fixture. The mapping stays writable, allowing a
subsequent exact code copy and release on the same unpoisoned child session.

A separate host-real permission-tag regression forges read-execute and unknown
permission values in code-copy and protection commands. The worker rejects
both tags without modifying a writable mapping; exact copy and RX sealing
then succeed on the retained child before clean release.

A two-live-mapping regression also combines one live mapping ID with another
live mapping's original address and length. The POSIX worker rejects mixed-ID
copy, RX-protect, release, and cache-sync commands; both mappings retain their
separate code-copy, protection, synchronization, and release authority.

A distinct host-real dispatch regression keeps two RX mappings alive with
separate return-code stubs (`GuardMiss` and unverified `Applied`). Alternating
native-call mapping IDs always selects the matching stub. Releasing the first
mapping invalidates only its ID; the second remains executable and releasable.

A separate two-process fixture deliberately obtains the same mapping ID in
each independent POSIX child, but installs distinct raw-status stubs. Every
interleaved call dispatches to its own child's code. Releasing one child's
mapping does not disable the other, and a fresh mapping in the first child
receives a non-recycled ID before both sessions release cleanly.

A further host-real regression seals a mapping and attempts instruction-cache
synchronization with a forged start, truncated range, or unknown mapping ID.
Each remote command fails; exact synchronization then succeeds for the retained
mapping before final release. Partial and foreign-range cache sync fail closed.

A host-real call-bound regression attempts to invoke a sealed RX mapping with
its entry offset at the mapped byte length, one byte beyond, or `u64::MAX`.
The child returns invalid-argument status without changing memory, output,
state, or pointer identity; that child then releases the mapping normally.

A complementary host-real offset regression places invalid-opcode trap bytes
at mapping offset zero and a non-mutating guard-miss entry at byte offset 16.
Invoking offset 16 returns the expected native status and unchanged buffers,
proving the worker uses the selected byte address rather than the map base.
That same child releases and reallocates normally.

The exact upper-entry fixture fills a 64-byte executable mapping with a trap
at byte zero and a six-byte guard-miss stub at offsets 58–63. Executing at
byte 58 succeeds with unchanged buffers; offset 64 and later offsets are
rejected without execution, and the child remains releasable and reusable.

A shared worker pre-dispatch check rejects misaligned AArch64 entry offsets
before invoking an executable mapping. Native AArch64 instruction slots
require four-byte alignment; x86-64 still permits byte-addressable entries.
A dual-mode Windows-handler simulation rejects all 48 non-four-byte-aligned
entry offsets in a 64-byte mapping under AArch64 admission, including sanitized
host test runs; the
AArch64 worker objects still cross-compile, without hardware execution claims.

A separate real POSIX x86-64 fixture protects an executable mapping with an
illegal instruction at offset zero and a six-byte native return stub at byte
three. Calling offset three succeeds as a guard miss and leaves the child
releasable, proving the ARM-only alignment rule does not restrict x86-64.

A larger RX-mapping fixture uses 8,192 bytes and copies code through the
4,096-byte page boundary, leaving a trap at the base and a guard-miss entry
at offset 4,096. After whole-range instruction-cache synchronization, the
worker executes the second-page stub with intact transfer buffers and can
release and allocate memory again on the retained child.

Six concurrent POSIX mappings now exercise the worker's dynamic mapping-table
growth and middle-entry removal. Every survivor remains individually writable
and releasable after compaction; the retained child admits another allocation
once the table is empty. A separate regression forges a copied-code length of
`u64::MAX`, rejects it as a remote failure, then copies valid bytes and releases
the same mapping without session poisoning.

The table-compaction fixture now also uses six 64-KiB-aligned mappings,
removes an interior entry, and confirms all survivors retain their exposed
addresses, copy authority, and full backing-reservation release ownership.
A fresh allocation still works on the same retained worker after cleanup.

A mixed-geometry real POSIX worker fixture retains eight simultaneous RX
mappings ranging from 64 to 8,198 bytes and alignments from 1 to 256 KiB.
Each copies a native return stub, seals, synchronizes, and dispatches before
mappings are released in a scrambled order. Every surviving ID still executes
its own stub after each release; the same child can allocate again afterward.

That POSIX fixture now also denies each mixed-ID synchronization while all
eight varied mappings remain live. After every scrambled release it rejects
stale memory commands and native-call dispatch on the former ID, while each
remaining mapping still executes its own valid entry on the retained worker.

An independent Win32-shim fixture now retains eight mixed-size mappings,
from 64 to 16,384 bytes and alignment from 1 to 256 KiB. It performs exact
code copy, RX protection, and full-range cache synchronization on all eight,
then releases in scrambled order. Every surviving ID retains its address,
length, RX status, and successful synchronization after table compaction.

While all eight Windows mappings are live, the same fixture forges 48 cache
synchronization and release requests. It combines each valid ID with another
mapping's base address, length, or both; every mixed-geometry request fails
without synchronizing or freeing any reservation, before legitimate releases.

After each of the eight releases, the Windows fixture also retries that stale
ID against its former geometry and each still-live mapping's geometry. All
stale synchronization and release requests fail while the surviving mappings
retain their separate ownership and remain synchronizable.

A separate two-mapping POSIX regression seals only the first mapping as RX.
Code copy fails on that executable mapping but succeeds on the still-RW second
mapping, while full-range synchronization succeeds only for RX. Both mappings
are then released and a fresh allocation remains available on the same child.

Host-real allocation validation also rejects zero mapped length, zero
alignment, non-power-of-two alignment, and RX-only allocation permissions
before creating a mapping. Both POSIX and Windows child handlers explicitly
require power-of-two alignment before reserving executable storage.

The POSIX worker now reserves enough address space to align mappings beyond the
OS page boundary, retaining the original reservation for full release and
teardown while exposing only the requested aligned code range.

A host-real regression reproduces rejection of 64-KiB alignment before the
fix and checks eight simultaneous aligned mappings through copy, RX protection,
native dispatch, and independent release. Reservation-length overflow rejects
without creating a mapping or poisoning the retained child.

The Windows worker now mirrors checked over-reservation: it exposes an aligned
subrange of a committed `VirtualAlloc` reservation and keeps the original base
for `VirtualFree` in both explicit release and child teardown. Native Windows
execution remains unverified on this host; pinned x86-64 and AArch64 COFF
cross-compilation checks that the worker stays warning-clean and CRT-free.

A separate pinned C23 host simulation exercises the Windows worker's actual
memory-command handlers against mock Win32 allocation APIs. Its fake
`VirtualAlloc` deliberately returns a 64-KiB-aligned base that is not aligned
to the requested 128 KiB; checked over-reservation still produces a usable
aligned mapping through copy, protection, synchronization, and release.

A further simulated 8,198-byte native code image crosses multiple pages
inside a 128-KiB-aligned Windows mapping. Its full copy response matches
all source bytes, and `FlushInstructionCache` receives the exact exposed
base and entire span before the original backing reservation is released.

The same simulation checks a second mapping lifecycle, reservation arithmetic
overflow before allocation, and cleanup of a still-live mapping during worker
teardown. Mock `VirtualFree` accepts only original allocation bases, so these
checks exercise backing ownership, but they are not native Windows execution.

An extended simulation grows the Windows mapping table to six concurrent
128-KiB-aligned reservations, removes an interior mapping, then copies, seals,
and synchronizes each survivor. Worker teardown invokes `VirtualFree` only on
the original backing bases for all five remaining mappings, including entries
shifted during compaction. Native Windows execution remains a separate gap.

The Windows MBNPC1 staging simulation now also fails the independent guest
memory and output allocations before dispatch. Each failure frees the other
allocated staging buffer, returns no partial response, and leaves the RX
mapping and native invocation count unchanged. A valid call on the same
mapping still executes and returns its exact expected state.

A deterministic POSIX stdio fixture now exercises the actual outer framing
handlers with complete, empty, and truncated requests, plus short writes and
failed flushes. Before the fix, simultaneous EOF and stream-error indicators
at the first header byte were misclassified as clean termination. The worker
now admits clean EOF only when the stream has no error; all other simulated
transport failures remain fatal, with C23 and ASan/UBSan evidence.

The same host-controlled fixture exercises the complete POSIX worker loop
with a live 64-KiB-aligned allocation before shutdown. Clean EOF, unknown
second frames, truncated second headers or payloads, failed response writes
or flushes, and contradictory EOF/error indicators all exit with the expected
status. Each path unmaps the original reservation; only clean EOF succeeds.

Two more cases fail to encode the first successful allocation response or to
allocate a second incoming frame body after one published allocation. Neither
publishes a partial frame; both exit with the required failure status and
release the one live backing reservation without double-unmapping it.

A host-real broken-output-pipe fixture also reproduces the POSIX default
`SIGPIPE` process death while an allocated mapping's response is written.
The worker now ignores `SIGPIPE` so a broken stdout pipe fails the framed
write with exit code 3 and executes normal mapping-table cleanup instead of
terminating at the signal boundary.

A second real-subprocess test first acknowledges an aligned allocation,
then closes stdout before sending another valid allocation command. The worker
reports exit code 3 rather than signal death after its mapping has remained
live across a successful prior frame.

A separate Linux x86-64 C23/ASan fixture links the real POSIX call handler
with deterministic allocation faults at those same two staging steps. Each
failed call frees the counterpart buffer, emits no partial MBNPC1 response,
and leaves executable mapping identity unchanged. A subsequent successful
call applies an input/output and memory transition without changing the
caller-owned request frame.

The POSIX harness now also fails `calloc` while encoding the MBNPC1 response
after native execution has already happened. The handler emits no partial
frame, frees both staging buffers, and retains executable mapping identity;
a direct-handler retry can re-execute the expected transition. A persistent
session must treat the absent frame as fatal rather than replaying implicitly.

The sanitized POSIX harness now also injects `mprotect` and `munmap` failures
against a real 64-KiB-aligned reservation. Failed protection leaves the
mapping writable; failed release preserves the exact mapping address and ID.
Both operations succeed when retried, and the original reservation is unmapped.

The same sanitized harness also injects one `mmap` failure and a failed
`realloc` during growth from four to five live 64-KiB-aligned mappings. Both
failures preserve the next mapping ID; table-growth failure releases only the
new reservation. Subsequent growth succeeds, and mapped/unmapped counts balance.

Independent POSIX lifecycle response-allocation failures now cover the gap
between a completed syscall and its success frame. Failed allocation response
encoding retains the live reservation for teardown; failed protection response
encoding retains RX state; failed release response encoding frees the mapping
once without reporting success. No orphaned reservation survives cleanup.

The simulated Win32 heap also injects response-buffer allocation failures
after real memory operations. Failed copy response encoding leaves the staged
RW bytes and ID intact; failed sync encoding retains RX ownership and permits
a later exact retry; failed release response encoding removes the mapping and
frees its backing reservation once. None publishes a success frame.

A distinct Win32 `VirtualAlloc` failure fixture verifies platform-error
propagation, including the explicit internal fallback when `GetLastError`
returns zero. Neither failed request consumes a mapping ID nor creates a
reservation. Retrying succeeds with the original next ID, and release frees
the only newly allocated backing region exactly once.

The simulation additionally injects one failed `VirtualProtect` and one
failed `VirtualFree` for an aligned mapping. The failed protection preserves
RW copy authority, the failed release preserves table ownership, and both
operations succeed on retry without losing the original reservation base.

The controlled Windows heap-shim fixture also rejects a mapping-table growth
failure at the fifth live reservation. A failed `HeapReAlloc` frees only the
newly reserved backing span, preserves four live mapping IDs and copy rights,
and leaves the next ID unchanged. Retrying growth succeeds and teardown
releases every original backing reservation exactly once.

A growth-retry regression forces `HeapReAlloc` to move the mapping table,
rather than relying on allocator-dependent in-place growth. It verifies that
all four pre-existing mapping IDs and addresses survive the relocation,
remain writable, and release their original backing reservations.

A Windows simulation also tests initial mapping-table heap allocation failure.
The first reserved region is released, no mapping ID is consumed, and a
subsequent allocation obtains ID one and releases its region on teardown.

The same Win32 heap simulation fails the 35-byte mapping response allocation
after a successful `VirtualAlloc`, and separately after a successful RX
transition. Neither path fabricates a success response: worker teardown
releases the still-owned backing reservation, including the RX case.

The simulated Win32 call handler now also fails its 81-byte MBNPC1 response
allocation after a host-ABI native entry has run. It returns no partial frame
and retains the mapping's identity and RX authority. A direct-handler retry
produces the expected original-request-derived response on the same mapping;
this does not claim that the production process loop retries failed framing.

A separate Win32 simulation returns a successful `VirtualProtect` with an
unexpected previous page-protection report. That contradictory success still
means the OS has installed RX; the worker now records RX before returning the
platform failure, denies further RW copies, and retains release ownership.

A further injected `FlushInstructionCache` failure returns a remote failure
without counting synchronization or demoting the existing RX mapping.
A retry succeeds on that same mapping before release, distinguishing a
recoverable cache API error from an admitted synchronized native entry.

The simulated Windows RX sync boundary now rejects nine forged request
variants: stale ID, addresses one byte outside the mapped start, short,
long, empty or overflowing lengths, and short/long wire frames. None calls
`FlushInstructionCache` or changes mapping ownership. The original full-span
synchronization and subsequent release still succeed on the same mapping.

A sealed Windows mapping also rejects a second protection transition and an
empty code-copy request without making another platform protection call or
reviving writable rights. The same RX mapping still synchronizes and releases
normally, retaining its original backing reservation.

The controlled Win32-host compilation also runs the actual Windows call
handler against Clang `ms_abi` C entries on Linux x86-64. Its MBNPC1 response
captures one changed memory word, input/output cursor progress, an output byte,
register updates, exact buffer lengths, and unchanged pointer identity.

The same MS x64 stub now also sets a distinct code pointer, data pointer,
and normative halt termination tag. The MBNPC1 frame must round-trip every
scalar state field exactly; denied entries retain the originally requested
register and termination values without invoking native code.

The pinned host test now runs the complete simulated Win32 handler suite both
as plain C23 and under AddressSanitizer/UndefinedBehaviorSanitizer. Instrumented
runs cover the same over-aligned backing ownership, MS x64 entry calls, pointer
drift, framing failures, and resource cleanup without sanitizer findings.

The same Windows-handler simulation now invokes a native C entry with zero
memory words and empty input/output buffers. All three reconstructed pointers
are null, and the response has only its fixed header. A zero-capacity call
with a nonzero input or output cursor is rejected without entering the stub.

The same fixture denies dispatch for non-RX or unknown mappings, out-of-range
entry offsets, impossible I/O cursors, and unsupported termination tags.
Request bytes remain intact, and the denied calls never execute the host
entry. This checks the Microsoft x64 entry ABI on Linux, not actual Windows
kernel behavior or independently verified guest semantics.

A second Microsoft x64 host entry receives already-consumed input and a full
output buffer (`2/2` input bytes and `3/3` output bytes). Exact upper-bound
progress still admits the call, preserves all original buffers and pointer
identities, and returns a stable `GuardMiss` rather than an invalid argument.

Two additional Microsoft x64 entries return a nominal `Applied` result without
mutating machine state, or an unknown raw code 127. The worker preserves the
exact raw status, untouched state, buffer contents, and pointer identity.
Trusted Rust verification, rather than the untrusted worker, decides whether
the native result is semantically admissible.

A separate hostile Microsoft x64 entry returns `Applied` while replacing the
termination tag with unknown value 255. The Windows worker preserves the raw
termination byte and original buffers; it does not claim to validate the
post-call machine semantics before the independent Rust verifier runs.

A deterministic Win32 shim now recycles the exact `VirtualAlloc` backing
address after release into a new 128-KiB-aligned mapping. The stale mapping
ID cannot copy, protect, release, or dispatch native code through the reused
address, while the new ID retains ordinary copy and release authority.

An independent-state Windows simulation issues mapping ID one in each of two
worker tables with different backing addresses. Releasing the first leaves
the second fully writable, sealable, synchronizable, and releasable; the first
can allocate a fresh ID two without affecting its sibling's ownership.

A further host-simulated Windows table owns two simultaneous 128-KiB-aligned
mappings with distinct IDs and backing addresses. Mixing one ID with the
other mapping's geometry fails copy, RX protection, release, and RX cache sync
without mutating either mapping or releasing either reservation. Both mappings
then copy, seal, synchronize, and release independently with their own IDs.

The controlled Win32 C-ABI dispatch simulation also binds distinct entry
functions to two live RX mapping IDs. Interleaved calls return their own
raw statuses and accumulator changes. Releasing the first mapping denies its
stale ID while the second continues to execute and release after table shift.

The Win32-host memory handler also admits a zero-byte code copy without
changing its backing buffer or mapping identity. A subsequent 65-byte copy
into 64 mapped bytes is denied without writes; a full 64-byte copy succeeds
on the same mapping before RX sealing, synchronization, and clean release.

The Windows host simulation also sends ten malformed MBNPC1 frames to the
same worker: short or excess payloads, incorrect magic, impossible large
memory/input/output lengths, and too few words or bytes for the frame.
Each fails during shape parsing before native dispatch or response allocation.
A subsequent valid call on the same mapping still executes normally.

Seventeen malformed Windows MBNPM1 commands also return exact failure frames
without changing a live RW mapping. They include illegal allocation geometry,
forged code-copy identity and lengths, premature cache synchronization,
invalid protection and release fields, and unknown commands. The worker then
releases the original reservation and successfully reuses the same child.

The Windows memory shim now also exercises exhaustion of the monotonically
allocated 64-bit mapping ID. The final valid ID remains writable and can be
released after the counter becomes zero; later allocation attempts fail with
no ID reuse and no new platform reservation on either POSIX or Windows.

The same host simulation drives the concrete Win32 framed I/O loops using
partial two-byte `ReadFile` and `WriteFile` transfers. It verifies exact frame
reconstruction, empty-frame handling, and rejection of truncated headers,
truncated bodies, and failed writes without accepting incomplete responses.

Simulated broken-pipe errors 38 and 109 count as clean EOF only before the
first header byte; the same errors after partial header input fail closed.
This verifies Windows transport control flow under mocks, not Windows kernel
pipe behavior on an actual Windows host.

The controlled Win32 shim also reports broken-pipe failure 38 or 109
with a contradictory nonzero byte count at header start. This formerly
looked like clean EOF, but now fails closed: only a zero-byte error report
can signal clean EOF before any header bytes are received.

An adversarial fake `ReadFile` that reports more bytes than requested exposed
a classification bug: the worker previously treated that impossible count
at header start as clean EOF. Only a genuine zero-byte read now admits clean
EOF; overreported reads and writes fail closed without accepting a frame.

Additional deterministic Win32 shims now overreport transfer counts after
two header bytes or immediately after a complete header, at the beginning
of the payload. Neither read nor write can treat those mid-frame reports
as successful progress or clean EOF, and the partial transfer is rejected.

The same Windows shims now fail `ReadFile` with a nonzero reported byte count
after two header bytes and immediately after a complete header. Broken-pipe
codes 38 and 109 cannot promote either failed transfer into valid progress;
these partially received frames are rejected even if the API reports bytes.

The fake broken-pipe codes also deny an otherwise clean-looking zero-byte
failure once the header is complete: before the first payload byte and after
one payload byte. Both positions fail framing and cannot be interpreted as a
normal stream close, even though the error codes match header-start EOF.

The Windows worker now defines `DWORD` and `BOOL` as explicit 32-bit ABI
scalars instead of relying on the host's `unsigned long` width. The host C23
simulation checks that a transfer larger than `UINT32_MAX` is capped to a
single maximum-DWORD request before any buffer access or failed I/O return.

The controlled allocation-failure shim also returns a high-bit Win32 error
(`0x80000001`), and the worker retains the exact unsigned 32-bit value in
its failure response. The mapping count, next ID, and reservation count
remain unchanged, and both the ordinary and sanitizer-hosted tests pass.

The Windows host simulation now assigns separate input, output, heap, and
process handles and checks the 32-bit `GetStdHandle` selector values.
Wrong-channel reads and writes, bad heap handles, and invalid process handles
fail in their mock APIs rather than silently passing the lifecycle tests.

The host simulation now exercises the complete Windows worker process loop,
not only its individual handlers. Clean stream EOF exits successfully, while
an unrecognized second frame, a truncated header, or interrupted response
writing exits with the appropriate failure code. Every path releases its
live over-aligned mapping through the original `VirtualAlloc` reservation.

Two further end-to-end frame sequences first allocate a live mapping. A short
second MBNPC1 call frame then exits as malformed and releases that mapping;
a complete call to unknown mapping ID zero instead receives exact
`InvalidArgument` framing and reaches clean EOF before the same cleanup.

The seventh process-loop case instead fails the complete unknown-ID call's
74-byte response allocation after the first mapping allocation succeeded.
No second response bytes escape; the loop exits with a framing error and
releases the original backing reservation exactly once.
An eighth case fails allocation of the initial 35-byte mapping response
after `VirtualAlloc` has already succeeded. The worker publishes zero bytes,
exits as a failed command, and releases that hidden backing reservation on
process-loop teardown rather than leaking an allocation with no public ID.

Two longer Windows process-loop simulations issue five valid allocation frames
through fragmented pipe reads and writes, exercising table growth and all five
serialized mapping identities. Clean EOF releases the five original backing
reservations; an alternate malformed sixth call frame also releases all five
while returning the expected failure status without a sixth response.

Three late-stream failure cases now retain those five successful allocation
responses while exercising a sixth frame. A truncated sixth request body and
a broken pipe after two header bytes both exit with framing failure, releasing
all five reservations without emitting a sixth response.

The same stream now injects a `HeapAlloc` failure when reserving the sixth
request payload, after the first five allocation responses are fully emitted.
The Windows loop exits with a transport failure, emits no sixth response, and
releases all five backing reservations rather than retaining hidden mappings.

A sixth-frame length of `u64::MAX` is also rejected on the simulated 64-bit
Windows host before attempting to read a body. The controlled heap shim
denies that unreservable byte count; the worker retains the preceding five
valid responses, emits no sixth frame, and releases every live reservation.

An interrupted write ten bytes into a sixth valid allocation response exits
with a transport failure and releases all six backing reservations. These
checks distinguish a partially published response from a leaked mapping.

A full five-frame Windows memory lifecycle now uses the mapping identity and
aligned address returned by allocation to drive later copy, RX protection,
instruction synchronization, and release through the process loop. The
simulated pipe verifies each successful response, exact copied code bytes,
and exactly one protection, synchronization, and backing release operation.


Three additional host stubs respectively replace native memory, input, or
output pointers before returning `GuardMiss`. The Windows call handler reports
pointer mismatch while encoding from the original memory/output backing
buffers; none of the substituted pointers is trusted for response bytes.

A hostile simulated entry now also replaces all five buffer-size and progress
fields with `u64::MAX` after modifying one memory word and output byte. The
Windows worker reports the untrusted scalar changes but bounds its encoded
payload by the pre-call allocations (one word and three output bytes). This
proves post-call scalar corruption cannot enlarge the worker response frame.

A 128-KiB-aligned 8,198-byte mapping also spans multiple pages, copies a
native entry at byte 8,192, seals and synchronizes the whole range, then
executes that entry before releasing the original backing reservation.

A separate full-copy boundary fixture admits a zero-byte code copy without
losing writable mapping identity, rejects 65 bytes for a 64-byte RW mapping,
then admits an exact 64-byte copy and release on the same unpoisoned child.

The source includes an AArch64 call/cache-sync path; a separate tracked
`native_process_worker_windows.c` mirrors the same MBNPM1/MBNPC1 lifecycle
through `VirtualAlloc`, exact copy, `VirtualProtect(PAGE_EXECUTE_READ)`,
`FlushInstructionCache`, native Windows calling conventions, and `VirtualFree`.
Pinned Clang cross-compiles that source warning-clean into x86-64 and AArch64
Windows COFF worker objects. The regression checks both COFF machine IDs and
requires the exact 13-symbol Win32 undefined-import set on each target while
rejecting accidental compiler-runtime or CRT dependencies.

Host-real AArch64 and Windows execution are non-blocking compatibility follow-
ups. Cross-compilation is not represented as host-real evidence, but exact
object/import admission plus host-independent semantic verification is
sufficient for backend acceptance. A later hardware execution failure remains a
compatibility defect to fix.

`native_process_protocol.h` now mirrors the reviewed MBNPM1/MBNPC1 version-one
magic, command/outcome tags, fixed sizes, field offsets, and little-endian
scalar helpers for C23 workers. A strict pinned-Clang conformance harness checks
those declarations independently. Both concrete child sources consume this
header rather than duplicating wire literals.

The pinned C23 harness also verifies the native call-state structure's exact
80-byte size and all twelve field offsets against the Windows-x64/AArch64
shared ABI. It locks the three raw native status codes and three normative
termination tags, so worker entry checks cannot silently drift from the
semantically admitted Rust observations.

The canonical C ABI header now additionally asserts its 64-bit pointer size,
80-byte state size, and all twelve field offsets at compilation. The same
checks therefore run when the POSIX and Windows workers compile for x86-64
or AArch64, not only when the host C23 conformance fixture executes.

The first multistep planner composes already verified one-step artifacts without
changing either ISA encoder. Complete VM traces are projected to one-step IR,
then exact profile and observation continuity are checked before every artifact
is selected. The retained rotate/output fixture yields two reviewed artifacts on
both ISAs and rejects empty, discontinuous, profile-mixed, hidden-deopt, and
post-termination sequences.

`DirectFusedSequenceAdmission` derives one canonical multieffect region from
that already verified plan. Ordered memory evidence becomes exact region-entry
live-ins; a distinct revision-1 fused target binds the region-wide
`NativeArtifactKey`. Retained source provenance now consists of reviewed direct
kinds, exact ordered artifact keys, one-step IR, entry/exit observations, and
outcome. Cached and uncached verified plans normalize to the same provenance, so
cache hits can enter fused admission without cloning verified object bytes and
subsequent re-admission remains independent of cache lifetime.

Single-step plans are rejected.

The fused emitter now covers forty-nine reviewed two-step regions on
x86-64 and AArch64: rotate/output, rotate/jump-code, rotate/jump-data,
crazy/output, crazy/input, input/input, input/output, input/crazy,
input/rotate, input/jump-code,
input/jump-data, input/no-operation,
crazy/jump-code,
crazy/jump-data,
no-operation/output,
no-operation/no-operation, no-operation/input, no-operation/jump-code,
no-operation/jump-data,
jump-code/crazy, jump-code/no-operation, jump-code/jump-code,
jump-code/jump-data, jump-code/input,
jump-code/output, jump-code/rotate,
jump-data/crazy, jump-data/no-operation, jump-data/jump-code,
jump-data/input, jump-data/output,
jump-data/jump-data, jump-data/rotate, no-operation/rotate,
no-operation/crazy,
crazy/no-operation, crazy/rotate,
crazy/crazy, rotate/jump-code, rotate/jump-data, rotate/no-operation,
rotate/crazy, rotate/rotate, rotate/input, output/crazy, output/rotate,
output/jump-code,
output/jump-data,
output/input, output/no-operation, and output/output. Every fused
guard
completes before
the first store,
including region-entry live-ins, exact byte/EOF input preflight where input is
present, and output capacity where output is present.
Independent semantic promotion reconstructs admission, structurally admits COFF,
rebuilds canonical bytes, and rejects text-byte drift. The
no-operation-containing templates preserve ordered guest-memory writes while
publishing only the final region register state, without exposing an
intermediate one-step observation.

VM-derived traces exercise all seven reviewed no-operation-containing templates
plus crazy/output, crazy/rotate, crazy/crazy, rotate/crazy, rotate/rotate,
input/input, input/output, input/crazy, input/rotate, input/jump-code,
input/jump-data, input/no-operation, crazy/input, rotate/input,
output/crazy, output/rotate, output/jump-code,
output/jump-data,
output/input, output/no-operation, and output/output
on both ISAs through
emission,
semantic promotion,
relocation-free load-image extraction, and whole-region state comparison with
the profile VM.

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

The latency retry now also accepts the shared synchronous retry directive. A
small immutable request carries source telemetry plus byte/attempt bounds so the
controlled entry point stays within the runtime API shape rules. After a
retryable conflict, the caller receives the exact completed-attempt count and
may return `Continue` or `Stop`; stopping preserves that conflict unchanged.
Continued attempts still perform a fresh bounded load/merge/CAS, with no runtime
clock read, wait, backoff, or fairness action.

Two focused cases cover continue and stop directives.

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


The retention-journal retry now also accepts the shared synchronous retry
directive. A small request carries the positive byte and attempt bounds. After
a retryable conflict, the caller receives the exact completed-attempt count and
may return `Continue` or `Stop`; stopping preserves that typed conflict
unchanged. Continued retries feed the exact current journal into caller
reconciliation again, with no runtime clock read, wait, backoff, or fairness
action.

Two focused cases cover continue and stop directives.


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


The same retry-control boundary now centralizes exact attempt accounting for all
of these synchronous loops. A private cursor starts after the first one-shot
attempt, exposes the completed-attempt evidence used by control hooks, advances
only while the caller-selected positive maximum permits it, and never supplies
policy beyond that accounting. Two focused cases cover exact advancement and
attempt-limit exhaustion; the existing retry suites retain their prior counts.


Terminal retry evidence is centralized at the same boundary. One generic
container owns the exact attempt count plus the subsystem-specific terminal
outcome, while ordered-count, ordered-pair, latency-merge, retention-journal,
and retention/reclamation APIs retain their existing public names as type
aliases. A focused case covers borrow/consume access without changing any
terminal outcome semantics.


Callers that need explicit stop provenance can now retain an opaque typed reason
without changing the retry loops. A generic decision carries `Continue` or
`Stop(reason)`, and a small stop-state adapter translates that into the existing
runtime directive while preserving the exact triggering conflict and caller
reason. The runtime defines no cancellation/yield taxonomy and never interprets
the reason. Two focused cases cover reasonless continuation and typed stop
retention.

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

Merge backoff/cancellation/fairness policy, native object fusion, host-real
AArch64 and Windows invocation, asynchronous timing, reclamation scheduling/
automatic durable retention policy, and general N-object transactions remain
open.

A persistent executable sequence now loads every reviewed one-step image before
execution and retains all ready mappings across repeated calls. Partial load
failure cleans the ready prefix in reverse; aggregate release attempts every
mapping and keeps failed ownership for retry. Complete image identity is checked
before buffers change, so an x86-64 chain cannot execute an AArch64 plan. The
memory adapter must provide unique, non-overlapping live allocations.

The concrete Linux x86-64 process worker now supplies host-real sequence
evidence as well. One retained child owns two distinct RX mappings, applies the
reviewed rotate/output chain exactly, and releases both mappings through the
aggregate sequence owner.

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
implemented for both ISAs; atomic fused rotate/output,
no-operation/output, no-operation/no-operation, no-operation/jump-code,
no-operation/jump-data, jump-code/crazy, jump-code/no-operation,
jump-code/jump-code,
jump-code/jump-data, jump-code/output, jump-code/rotate,
jump-data/crazy, jump-data/no-operation, jump-data/jump-code,
jump-data/output,
jump-data/jump-data, jump-data/rotate,
no-operation/rotate,
no-operation/crazy,
crazy/jump-code, crazy/jump-data, crazy/no-operation, crazy/output,
crazy/rotate,
crazy/crazy, rotate/jump-code, rotate/jump-data, rotate/no-operation,
rotate/crazy, rotate/rotate, input/input, input/output, output/input,
output/no-operation, and
output/output
objects are
also emitted, independently
verified, and
extracted as relocation-free load images on both ISAs, with dedicated safe
lifecycle
typestates, transactional platform loading through synchronized RX readiness,
and a borrow-scoped whole-region prepared invocation contract. Wider
fused-template coverage, concrete
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
- Initial backend-pipeline performance evidence now retains 15 release-profile
  samples per ISA at repetition scales 1, 2, and 4 for one equivalent
  VM-derived rotate/jump-code workload. The measured pipeline is direct
  selection, fused admission, COFF emission, and semantic verification. The
  retained bundle records raw samples, source/workload hashes, exact host and
  toolchain identity, process resource usage, success/failure counts, the
  retain-all outlier policy, observed-range uncertainty, and scaling
  statistics. Because this benchmark does not load or execute generated code,
  end-to-end native execution performance remained pending at this stage.
- A second retained phase-attribution run uses the same workload and sample
  matrix: selection accounts for about 37-38% of summed phase medians across
  both target ISAs and scales, semantic verification about 27-28%, COFF
  emission about 21-22%, and fused admission about 13-14%. Per-stage timers add
  overhead, so the phase run is attribution evidence rather than a replacement
  for uninstrumented total-pipeline latency.
- A retained cold-versus-warm exact-cache run uses the same workload and scales
  with 15 samples per mode/ISA/scale. Fresh warm caches are seeded outside the
  timer, and every timed warm selection records exact hits with zero insertions.
  Median warm selection is 2.606-2.885x faster than cold selection across the
  six ISA/scale comparisons; total preparation improves 1.305-1.390x, while
  fused-admission medians remain within about 3%. Generated code is still not
  executed, so this remains preparation evidence rather than native throughput.
- A multi-workload follow-up adds a reviewed no-operation/output trace beside
  rotate/jump-code with the same modes, ISAs, scales, and 15-sample groups.
  Across all twelve comparisons, warm exact-cache selection is 2.561-2.855x
  faster by median and total preparation improves 1.314-1.380x. Admission
  cold-over-warm ratios stay between 0.997x and 1.028x. This corroborates the
  selection-cache effect without extending the claim to machine-code execution.
- A final preparation-only corroboration adds crazy/crazy, covering accumulator
  and data-memory mutation beside output and control-transfer workloads. Across
  all eighteen workload/ISA/scale comparisons, warm exact-cache selection is
  2.516-2.881x faster by median and total preparation improves 1.267-1.407x.
  Admission cold-over-warm ratios stay between 0.984x and 1.018x. Further
  preparation-only workload widening is deferred until native execution exists.

- Initial host-real process-execution evidence is retained under
  `benchmarks/interpreter/evidence/` in
  `2026-09-18-native-process-execution-linux-x86_64/` from source
  commit `dba5fd50a3d198539624f28c543ca2629cc5aeb9`.
  The Linux x86-64 benchmark executes the normative fused rotate/output object
  through the tracked process worker with 15 samples per mode at scales 1, 2,
  and 4; all 90 retained samples complete exact semantic admission.
  Lifecycle medians are 79,718/152,607/427,110 ns while resident-call medians
  are 23,233/40,000/104,934 ns, yielding 3.431x/3.815x/4.070x ratios.
  This is concrete Linux x86-64 process evidence only and at this stage did not
  compare interpreter throughput; no host-real AArch64/Windows measurement was
  taken, and neither is required for backend acceptance.

- Equivalent-workload interpreter comparison is retained under
  `benchmarks/interpreter/evidence/` in
  `2026-09-18-native-process-vs-interpreter-linux-x86_64/` from
  source
  commit `ee5b3e88b72c8cee437ed7f022bf59825975f276`.
  The same normative two-step rotate/output workload completes 135/135
  retained samples across interpreter, resident process-native, and one-shot
  lifecycle modes with exact semantic checks.
  Resident/native median time is 14.219x, 17.559x, and 26.492x the direct
  interpreter median at scales 1, 2, and 4; ratios above one therefore mean
  the current process-native boundary is slower for this micro-workload.
  This negative result is not generalized to larger regions, in-process calls,
  future JIT/AOT policy, AArch64, or Windows.

  The tiered runtime now has an exact 1.1x minimum JIT-promotion gate for paired
  aggregate latency evidence. Summing the 15 retained raw samples per mode gives
  interpreter/resident totals of 34,236/466,215, 46,159/755,040, and
  64,447/1,538,451 ns at scales 1, 2, and 4. Every paired aggregate therefore
  fails the exact 11/10 promotion gate, matching the negative median result.

- Host-real Windows execution is intentionally deferred as a non-blocking
  portability follow-up. Warning-clean x86-64/AArch64 COFF generation plus exact
  machine/import admission remains the current Windows evidence boundary; this
  is not represented as host-real execution. Host-real AArch64 remains open.

## References

### Host Architecture Baseline

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`

- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
