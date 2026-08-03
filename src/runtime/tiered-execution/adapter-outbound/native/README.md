# Native artifact bootstrap

## Purpose

Own the first host-code lowering boundary from portable verified-effect IR to
explicitly untrusted native compilation artifacts.

## Owns

- structural validation required before native lowering;
- deterministic C23 bootstrap lowering from `RegionEffectProgram`;
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

`profile_metadata.rs` owns the target-neutral `MBPF` v3 payload encoding shared
by bootstrap source, direct object construction, and structural validation. This
keeps object parsing in `coff.rs` and code generation in their emitters; neither
owns the schema it independently consumes.

`coff.rs` adds a narrower structural gate for Windows bootstrap objects. It
parses the object bytes directly in safe Rust, checks x86-64/AArch64 machine
identity against the native target key, requires one executable/non-writable
`.text`, requires the exact `malbolge_native_region_apply` entry, rejects other
external functions and undefined external dependencies, and permits relocations
only when they resolve to symbols defined inside the same object. Direct
backends
and `clang-c23-bootstrap` revision 2 must contain one initialized, read-only,
non-relocated `.mbprof` section. Its `MBPF` v3 payload carries the exact profile
ID/fingerprint plus published version, stable semantic features, word trits,
profile capacity, and derived `u64` region memory requirement; the complete
envelope must equal the native key. Missing, duplicated, executable, writable,
relocated, malformed, or mismatched required metadata fails structurally.
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
or writing the supplied state pointer. The exact x86-64 and AArch64 objects are
frozen by independently rendered hex fixtures. Each includes executable `.text`
and read-only `.mbprof` v3 bound to the same native key. Semantic promotion
requires
structural COFF admission plus byte-for-byte equality with the canonical object;
a one-byte opcode mutation remains structurally valid but fails semantic
admission. This establishes an executable native tier that is correct by always
falling back, before any direct region-effect instruction selection is trusted.
The deopt and initial-halt backends remain revision 4. The wider
`direct-halt-registers` observation contract is revision 5, while
`direct-halt-fetch`, `direct-non-graphical`, and `direct-no-operation` use
revision 2 after binding their runtime capacity guard to the exact IR footprint;
`direct-jump-code`, `direct-jump-data`, `direct-rotate`, `direct-crazy`,
`direct-input`, and `direct-output` start at revision 1. All twelve use `MBPF`
metadata version 3.

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
an exact `<` transition selects `direct-input`, an exact `/` transition selects
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

Neither sequence planner links objects, allocates executable memory, invokes
code, or claims that a guard miss can resume halfway through a sequence.

`select_preflighted_execution_tier()` adds the first product-neutral planning
boundary above direct selection. A supported Windows direct object returns
`PreflightedExecutionTier::Direct`; Linux/macOS format absence returns
`Interpreter` only after the same program/profile/runtime preflight. `002`,
`001`,
and all post-selection emission/admission errors remain errors. The planner does
not perform cache lookup, executable-memory allocation, linking, or execution.

`select_cached_preflighted_execution_tier()` composes the same boundary with a
caller-owned `VerifiedDirectNativeCache`. Profile capacity/runtime and explicit
`DirectHost` format selection happen before lookup. A private
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
unchanged. There is no automatic eviction or revocation. Persistence, eviction
policy, synchronization policy, linking, executable memory, and invocation
remain
outside; `Arc` supplies ownership only, not concurrent execution.

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
code-cell live-in must VM-decode as `/`; VM-owned `profile_low_byte()` derives
the appended byte. Both ISAs guard the complete entry, exact 9-word footprint,
`memory[5]=112`, non-null output storage, and capacity greater than output index
3 before committing `memory[5]:112->68`, `C:5->6`, `D:7->8`, byte `0xa8`, and
`output_len:3->4`. Independent complete objects are 642 bytes on x86-64 and 724
bytes on AArch64. x86-64 execution proves exact hit plus atomic code, capacity,
output-pointer, footprint, and memory-pointer misses.

`direct-input` revision 1 completes direct coverage of all eight instruction
families. One code-cell live-in must VM-decode as `<`. The byte form guards a
non-null input pointer, `input_len > input_consumed`, and the exact byte before
committing `A=65`, `input_consumed:2->3`, encrypted code 57, and `C/D=6/8`.
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
