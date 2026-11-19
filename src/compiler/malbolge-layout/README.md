# Malbolge layout and encoding

The initial executable target encoder admits only bounded straight-line
machine operations: `NoOperation`, profile `InputWord`/`OutputByte`, and final
`Halt`. It also emits verified `RelocateDataPointer` (`j`) operations,
real `RotateData` (`*`) and `CrazyData` (`p`) operations, and bounded
chains of strictly forward `JumpForward` (`i`) code jumps. The jumps
may precede the relocation when its dynamically read data word proves that
subsequent writes target either expanded memory or past source cells strictly
behind the executing instruction. Later forward jumps are also admitted if
D reads a known graphical source word or untouched loader-expanded word;
input-tainted and unproven-written operands still refuse. There is no
automatically emitted conditional branch, backward jump, or helper.

### Repeated physical loader-word rotations (fixed pointer-reset geometry)

`build_repeated_loader_rotation_source` now produces a 91-cell graphical N15
candidate for each count from 1 through 15 reached rotations of M[95]. The
`,H` tail loads 7,174,457 at M[95] and 72 at M[96]. Three genuine `j`
operations return D through 73 and 62 to 95 between rotations; C40 is a
source-dependent pointer constant, so exactly ten rounds need an extra
reached jump before the final output. Each candidate outputs the resulting
word's low byte with real `<` and halts. Fifteen independent normative VM
runs check every reached `*`, source pointer, data read, intermediate
accumulator, final memory word, byte and halt. Counts zero and 16 refuse.

This is real repeatable guest arithmetic, **not** signed C23 normalization.
The required first C23 operand begins at 7,174,404 (`Iy`), whereas this
reset chain requires the distinct `,H` loader seed. Substituting `Iy`
changes the pointer reset from M[95] to M[158] after the first rotation.
Neither EOF branching nor source-C checksum linkage has been implemented.

`build_seeded_repeated_loader_rotation_source` now validates a caller-supplied
pair of graphical source-tail bytes against the *actual* loader recurrence and
the same fixed physical reset. An exhaustive 94-by-94 tail admission check
finds exactly eight loadable seeds, all ending in `H`: first bytes `,`, `-`,
`C`, `I`, `V`, `g`, `h`, and `z`. Their first expanded operand words at M[95]
are respectively 7,174,457, 7,174,462, 7,174,480, 7,174,489, 7,174,418,
7,174,435, 7,174,436 and 7,174,454; M[96] remains 72. Eight normative VM
runs each prove nine real same-cell rotations, read identity, output byte and
halt against an independent scalar oracle. Unloadable tails, including `Iy`,
refuse before source publication; the original `,H` API remains unchanged.
This broadens physical operand seeds, not signed-C23 conversion or C lowering.

### Physical nine-rotation signed-input arithmetic chain (not C23)

`build_seeded_rotated_input_crazy_source` reuses the eight source-loadable
91-cell N15 rotation seeds and performs **nine actual same-cell `*` writes**
at M[95]. After an executed three-`j` reset, `/` reads the actual signed
input/EOF word. C40 then executes as `j` (and remains the required source
constant 94); two more `j` operations reset D for consecutive `p` writes
using M[95] and M[96]. A real `<` emits the final low byte, and `v` halts
after exactly 47 VM steps. No host output substitutes for target arithmetic.

The independent 15-trit oracle and normative VM agree on 307 complete paths:
all 257 first-input classes plus an unread suffix for the `,H` seed, and
seven representative paths for each of the other seven seeds. Every path
checks all nine rotation reads/results, six relocation steps, the physical
input event, both `p` reads/results, emitted byte, halt and consumption.
The first operand's rotated value depends on the loader seed, but every
admitted seed leaves M[96]=72, while C23 needs the **different** pair
`[7,138,732, 121]`. The real `,H` EOF output is `0x24`, **not** `0xff`;
this is a composition primitive, not a working signed C23 converter, loop,
or the source-locked mutable checksum. P2 remains open.

### Two physical `p` writes from C23 converter loader words

`build_c23_operand_probe_source` constructs a 279-cell graphical N15
source ending in `Iy`. A real `j` at C=8 relocates D, `/` at C=164
reads the target byte or EOF word, and `p` at C=165 and C=166 reads
and writes the loader-derived operands M[283]=7,174,404 and M[284]=121.
The following `<` emits the actual accumulator byte; C=168 halts after
169 steps. The normative VM and an independent trit oracle agree for all
256 input bytes, EOF, and an input with an unread suffix. The test checks
both writes even when a write has an unchanged value.

This does **not** implement C23 signed byte conversion: the first operand
must undergo nine *physical* rotations to 7,138,732 before the two crazy
operations can produce C23-compatible output. No such rotations execute
in this source; EOF currently emits `0x55` instead of `0xff`. The source
is a verifier-visible operand-placement precursor, not published C code,
and has no C state, arithmetic loop, or checksum output.

### Two actual signed guest-input echoes on one forward path

`build_two_signed_guest_echo_source` uses the existing 132-cell N15
classifier source but replaces its later rotate with a second physical `/` at
C=104, outputs the first input word at C=54 and the second at C=114, and
suppresses the former fixed class marker. All paths halt after 130 steps,
with physical input attempts at steps 53 and 104 and outputs at steps 54 and
114. Successful reads preserve all 256 possible binary bytes; EOF attempts
emit the target sentinel low byte `0x6a`, **not** the C23 EOF-to-unsigned-char
value `0xff`. An unread suffix is not consumed.

Six distinct real VM streams now pass source/profile-bound complete path
admission, independent trit arithmetic/store witnesses and exact I/O event
oracles. A separate 256-case normative test varies the second byte for every
possible first byte and proves ordered read/echo effects with 130-step halts.
Forged output, shifted I/O, a tampered final physical rotation and duplicate
path evidence refuse. Unlike the guarded helper, this source's
forward C=127 rotation writes M[156]; it **collides** with the previous
`[153,196)` future C-state placement, so any linker must reserve and re-place
C state for this exact source. It is two unconditional reads, not a guest
EOF loop, a C23 signed conversion, or the original mutable C checksum.

### Guest-controlled second read after a successful signed input

The exact 132-cell signed EOF classifier has an additional source
construction, `build_guarded_signed_eof_second_read_source`. It replaces
C=101 with a position-checked dual-phase graphical instruction: the first
pass executes `p`, and post-step encryption turns that code cell into `/`
on the successful-byte arm's revisit. EOF on the first input skips the
revisit, terminates after 119 steps and consumes no second input.
Exhaustive normative runs for all 256 successful first bytes instead
execute the second `/` at C=101 and halt after 175 steps. Samples with
a second byte, second EOF and an unread input suffix preserve exact
guest input provenance and the byte/EOF marker outputs.

This is not a guest C input loop. It reads at most twice, computes no
checksum, and has not relocated C state or generated a C backedge. Any
further instruction changes need fresh source/VM admission.

### Physical first-byte echo before the guarded second read

`build_guarded_signed_eof_echo_and_second_read_source` adds a real `<`
at C=54 immediately after the first `/` at C=53. The first N15 input
word, not a host-supplied output, is emitted before arithmetic destroys its
original accumulator value. Post-step encryption makes C=54 an inactive
opcode on the byte-arm revisit, so it cannot emit an extra stale byte.
The original byte/EOF classification and second input at C=101 survive:
an initial EOF produces `[0x6a, 0x1e]` and stops after one input attempt
at 119 steps; a successful first byte `b` produces `[b, 0x9a]` and makes
a second real input attempt before halting at 175 steps.

Six bounded binary/EOF streams match actual traced inputs, outputs, step
positions, and complete independent `p`/`*` instruction-write oracles.
An exhaustive 256-case normative guest run separately varies both input
bytes and proves the first-byte echo, second read and exact 175-step halt
for every successful first-byte value.
Forged output bytes and shifted I/O effect positions fail source-bound
admission, and the future 43-word C frame remains isolated. The new source
must not reuse the old source-bound state placement without fresh admission.
This is one input-dependent guest output plus conditional read sequencing,
not C23 EOF normalization, arbitrary echo, checksum arithmetic or a loop.

### Independent admission of guarded second-input paths

The guarded second-input source now passes a six-stream mixed forward/revisit
batch with externally constructed per-step source paths, signed input/EOF
attempts, ordered output effects and complete trit arithmetic write oracles.
On both arms, the first traversal of C=101 executes a `p` that writes
M[7,174,353]; the byte arm alone revisits C=101 as the second `/`. Missing or
shifted reads and forged physical writes refuse. Exact helper/source/profile
identity remains necessary; no checksum state mutation or EOF loop is linked.

The two-pass source encoder requires a loader-valid first opcode. In
particular, C=103 could encrypt into `<` only from a non-loadable first
opcode, so it cannot simply echo the second input in the current layout.
The real guest output remains the *first* byte/EOF arm marker, not C23 output.

### Bounded physical helper and future C-frame isolation

A complete path also retains each reached `p`/`*` instruction's
pre-encryption word result and operand, even if the store was idempotent or
its data destination was subsequently encrypted as code. The independent
`verify_bounded_guest_instruction_writes` gate requires an entire ordered
oracle rather than trusting changed-value deltas. The actual signed EOF
helper has an idempotent `p` (step 82, M[143]=125), and a separate genuine
36-step graphical guest rotates its own M[34] code cell before XLAT2.
Neither physical effect is a C-state write or a linked checksum operation.

A complete finite path admitted by the nonlinear normative N15 guest verifier
now records exact data-memory **read** addresses in addition to code fetch,
encryption, and reached `p`/`*` destinations (including unchanged writes).
`verify_bounded_guest_state_isolation` checks that a future mutable C frame
lies outside all of those accesses. Unlike the helper's own writable scratch,
this state region must not be read by the helper: the real EOF branch reads
untouched loader M[148], which becomes unsafe if reused for mutable C state.

`place_bounded_guest_state_frame` derives a deterministic lowest-addressed
candidate from the union of up to eight source/profile-identical, bounded
paths **and a required, independently verified helper scratch reservation**.
It first checks that the declared helper intervals cover every reached
physical write without touching fetched/encrypted code. Every declared
helper-owned word stays unavailable to C state even if the supplied paths
did not use it; helper scratch plus future state share a 4,096-word ceiling.
A focused test reuses the original checksum's independently verified 43-word
SSA/phi requirement, verifies a safe candidate across five VM paths, then
proves that adding unused helper scratch shifts the candidate. Invalid,
incomplete and unsorted helper declarations refuse.
`place_source_bound_guest_state` now joins these two independently
admitted boundaries for the *exact physical source*. It re-derives the
source-authenticated typed CFG and its complete frame width, checks physical
source/profile identity across all supplied normative paths, allocates the
full frame outside helper scratch, and relocates all seven checksum blocks,
19 typed operations and four phi-copy edges at that actual candidate base.
The integration regression uses five normative source-identical paths and
checks every relocated operand/control/copy address, source drift, altered
canonical bytes, missing scratch, and deterministic path reordering.

This is a **placement-only** witness: the typed program's C-source identity
was checked upstream, not derived from the helper's Malbolge characters.
The 132-cell source is still an EOF/byte marker program, not checksum code.
The frame is uninitialized; neither its literal writes nor its arithmetic,
phi transfers, loop backedge or final C output is physically implemented.
Changing the source or adding new helper accesses invalidates the witness.
The original mutable C checksum still cannot run in the guest.

### EOF versus byte control-word prerequisite

An independently checked current N15 two-`p` **data-only** proposal uses
operand words `14,348,906` then `486`. Exhaustive scalar admission and a
separate digit-table oracle prove that every successful signed C23
`getchar()` byte (0 through 255, including 255) yields word `243`, whereas
the exact profile EOF word yields `486`. These could become distinct `i`
operand words for code addresses 244 and 487 **only after** a real linker
places the original operands, proves both input-dependent data writes,
relocates `D` to the resulting word and verifies both jump destinations.

The source loader alone cannot supply these operands: all graphical tail
bytes have trit index 5 (place 243) equal to 0, and the loader's digit
recurrence never produces 2 from the initial pair of zero trits. Any
complete two-`p` byte-collapse plan necessarily needs at least one operand
with a 2 in that position because successful bytes 0 and 243 differ only
there. The accepted pair needs **two** pre-`p` guest writes. The checked
plan reports this necessary condition through
`mandatory_runtime_operand_writes`; it does not synthesize those writes.

`admit_c23_eof_control_word_plan` checks all 257 cases for any proposed
operand/target pair. Its result is not a guest, does not prove valid code
at either destination and cannot compile the mutable EOF checksum. The
frozen P2 checksum still refuses dynamic target lowering. The focused
`compiler_eof_branch_plan` regression checks the independent arithmetic,
profile mismatch and altered-data/target rejection without guest publication.

An alternative exact 257-case pair `[7,174,332, 728]` yields byte
control word 728 and EOF control word 485, requiring a trit-5 mutation
of only the second operand. A 38-cell genuine N15 guest with source-tail
seed `Q}` proves the first operand at expanded address 38: after a real
signed `/`, `j` at position 3 relocates `D`, and `p` at position 4 reads
and writes that word for empty/NUL/high-byte input. It does **not** place
the second operand or execute an `i` branch. `compiler_eof_guest_control`
checks that first physical write with normative VM traces.

The one-write EOF proposal's second operand **728** cannot come from
rotating any virgin loader word, however many times. It has six ternary
2 digits; each graphical source byte and every untouched loader recurrence
word has at most four, and rotation preserves that count. The exhaustive
seed/phase/rotation regression in `compiler_eof_branch_plan` independently
checks this position-free obstruction. An additional guest `p`-based
preparation or a genuinely different arithmetic plan is needed.

A separate 91-cell normative N15 guest now physically synthesizes the
missing `728` word with eleven real `*` rotations, thirty `j`
pointer resets and a final reached `p` on loader word `7,174,493`.
The digit-table result is `crazy(7,174,493, 7,174,777) = 728`;
48 VM steps emit `0xd8` without consuming input. This guest uses
loader tail `44/72`, distinct from the `Q}` tail that directly
supplies the proposed first operand `7,174,332`. A second, independently
executed 91-cell source now physically prepares **both** operands in
one 82-step N15 guest. After writing `728` at M[97], one further
rotation and four real `p` writes prepare `7,174,332` at M[95] while
preserving M[97]. Four normative runs verify both final words, source
self-encryption and relocation, and emit `0xbc` without input. The
previous fourteen-rotation/two-`p` algebraic path was not used.
The joint source still has no input-dependent `p`, conditional `i` or
source-C dynamic lowering; P2 remains open.

### Real all-byte versus EOF output classifier (no jump)

A distinct 132-cell N15 guest uses a source-valid `-}` loader tail,
twelve actual rotations of expanded cell 135 and two `j` relocations
per rotation to prepare word `3,618`. A signed input and three genuine
`p` instructions read `[3,618, 7,174,350, 125]`. An independent
15-trit oracle proves that all 256 successful bytes yield word
`7,174,223` (`0x4f` output) and EOF yields `377` (`0x79` output).
Five real 61-step normative VM traces confirm those effects for empty,
NUL, `0x01`, `0x80`, and `0xff` input. The `compiler_eof_guest_control`
test verifies each rotation, relocation and input-dependent data write.

Unlike the earlier two-`p` plan that requires operand 728, this
three-`p` plan physically executes its arithmetic. It does **not**
execute a conditional `i`, preserve a loop-carried C checksum, or
lower the source-C program. Linking its final control word into a
validated branch and then the frozen C checksum remains P2 work.

A further independent top-trit proof bounds direct branch linkage: the
classifier results have trit 14 equal to `1` and `0`. For **any** one
additional `p` operand, the crazy table leaves at least one resulting
word at or above `3^14 = 4,782,969`. A single post-classifier `p` cannot
turn both outcomes into nearby graphical code destinations.


### Physically executed input-dependent branch, restricted to two bytes

A separate 136-cell current N15 graphical guest shows that nonlinear input
control *can* execute on the normative VM, independently of the unplaced
EOF discriminator. An initial `i` enters code at 99 and encrypts a skipped
source cell; one real input `/`, two earlier-code operand `p` writes, and
three actual `j` relocations place the final dynamic result under `D`.
A reached `i` at C=135 reads 6 for NUL and 7 for byte `01`, selecting
previously skipped C=7 or C=8 respectively. A 40-step trace emits `00 06`
for NUL; a 39-step trace emits `00` for `01` and both halt. The test checks
every intermediate guest data read as well as the real divergent paths.

These **two tested input words** are not C23 EOF control. The raw guest is
not a compiled C source, and arbitrary binary inputs cannot be admitted by
this witness. The tested operand pair is 81/43, not the required
7,174,332/728, so all 257 signed `getchar` results, byte/EOF branches,
and the mutable checksum remain unimplemented. This is an instruction-level
branch-enabling result, not a change in the linear emitter's supported API.

### Position-constrained loader seed selection

`select_rotated_loader_seed(profile, length, data_address, rotations, pair)`
searches at most 8,836 printable final-source-byte pairs. It requires that
both bytes decode as loader-valid instructions at their *actual* physical
source positions, and that the normative loader recurrence produces the
requested adjacent data words after the specified number of **hypothetical**
rotations of the first word. An impossible geometry, out-of-range word or
unloadable target pair fails explicitly. The search is deterministic and
profile-width-aware; the selected tail may then be passed to the independent
forward-padding encoder, which still verifies the complete source and VM.

For the N15 conversion target `(7,138,732, 121)`, source length 91, first
operand address 95 and nine rotations, the search returns `Iy`. This agrees
with the checked 91-cell guest that performs **one** actual rotation.
A tempting repeat-rotation geometry would instead use length 118 and data
addresses 122/123, because the second word `121` would let `j` reset `D`
to 122. The search correctly refuses that source: byte `y` at physical
position 117 decodes as `)` and cannot be loaded. No operand revisit, nine
rotations or signed C EOF conversion has been emitted by this selector.

### Exact post-halt loader seeds

The independently checked linear encoder admits an optional **exactly two**
`SkippedDataByte` cells after the reached terminal `Halt`. Both cells must
be printable and decode as a loader-valid opcode at their source addresses.
They are not executed instructions: the verifier terminates at the first
halt and rejects any other early halt, partial seed or unclaimed skipped
cell. Unlike a forward-jump padding gap, these trailing bytes deliberately
set the two original source words that determine every loader-expanded
cell. Original source identity and full physical source length still govern
data placement and write nonaliasing.

`tests/compiler/layout/trailing_loader_seed.rs` exercises one 91-cell
N15 source: an actual `j` at position 40 reads code byte 94 and places
`D=95`, a real `*` at position 41 changes loader word 7,174,404, and
the program halts at position 88 before its `Iy` seed at 89..90.
The normative VM proves the write at 95 and untouched adjacent word 121
at 96 with empty and binary input. The independent signed-EOF algebra
shows that nine rotations of word 95 yield a valid adjacent two-`p`
conversion pair, but the layout executes only the first rotation. No
nine-write loop, operand revisit, or source-C conversion is claimed.

The forward-padding planner also exposes
`encode_auto_padded_forward_layout_with_loader_seed(profile, logical, seed)`.
It takes a **reached** logical path ending in `Halt` and exactly two physical
loader seed bytes. They are position-validated and incorporated into the
final loader image without becoming reached logical steps. Their source-map
origin is `LoaderSeed`, distinct from both executed and skipped padding;
manual `SkippedDataByte` tokens in a logical path are refused. The same
91-cell N15 program is reproduced using both a fixed `j` and
`AutoRelocate`, then checked against the normative VM. An additional
forward-jump witness proves both forms of unreachable source provenance
remain distinct with correct code and data execution in both VM profiles.
This is source layout, not repeated-operand synthesis or signed C
`getchar` lowering.

A final `j` immediately before the reached `Halt` may relocate D to a
source address without a subsequent data-dependent operation. That remains
safe when the physical source continues with the two unreachable loader-seed
bytes: the last *reached* step, not source length minus two, determines
whether relocation can affect later guest behavior. Both profiles execute
this 128-step no-output boundary with and without the extra seed, and the
padded planner preserves identical code/data positions and seed provenance.
`AutoRelocate` selects this final `j` without extra filler when its operand
is known; a subsequent actual `OutputByte` makes that shortcut unsafe and
is rejected. Earlier relocations still require the usual exact
scratch/expanded-memory proof; the final-`j` exception does not admit a
data write into pending code.

### Opt-in bounded revisiting source admission

`composition/bounded_revisit.rs` separately admits an independently supplied
raw graphical program for **one explicit binary input** and its exact finite
normative-VM path. This is not a new automatic layout or source compiler:
`admit_bounded_revisit_layout` requires canonical profile ID/fingerprint,
2..4096 loader-valid source cells, at most 512 steps and input bytes, complete
ordered code addresses (including halt), expected output bytes and successful
input-consumption count.

Actual VM transitions must agree on every code address, terminate at the
final supplied step, revisit at least one code address, and match
output/input-consumption exactly. A successful result
exposes the genuine code/D/encryption positions and raw source; malformed,
unbounded, altered, incomplete or nonrevisiting witnesses fail closed.

`tests/bounded_revisit_layout.rs` pins a 104-cell graphical guest for both
current/historical profiles. A real `j` and forward `i` reach a 16-cell body;
a subsequent `i` jumps **backward** to the already executed body. Its first
pass performs actual byte input and echo; after XLAT2 self-encryption its
second pass leaves those two operations inert and exits by reading a
different live D memory word. The entire 35-step VM path, D addresses,
encryption targets, binary output for NUL/128/255, and EOF sentinel output
with zero successful reads are verified.

The tests also refuse tampered
jump operands, forged paths, incomplete termination, wrong output/reads,
nonrevisiting candidates and exceeded bounds. This is input-specific
machine-control evidence, **not** runtime-conditional branching, repeated
successful reads, compiled C state, or EOF-driven checksum termination.

The same independent gate now exposes `admit_bounded_guest_path` for an
exactly supplied *complete* path without a mandatory code revisit. The
existing `admit_bounded_revisit_layout` retains the stricter revisit rule.
Both entrypoints require the same profile-bound source, input, expected
complete code path, ordered input/output events, and exact arithmetic data
writes; neither emits a source artifact or proves arbitrary input streams.

`admit_bounded_guest_path_batch` applies the general finite path gate to
2..8 distinct binary streams against one source. It permits a forward-only
EOF exit and a revisiting byte arm in the **same** all-or-nothing batch;
`admit_bounded_revisit_batch` deliberately retains its revisiting-only
contract. Each case independently checks its own complete path and machine
I/O/data-write oracle. The mixed-arm source-bound regression uses five
streams, but it does not supply the missing C checksum code or its five
normative guest parity traces.

`verify_bounded_guest_data_regions` separately checks actual, admitted
nonlinear guest paths against 1..8 ordered, disjoint memory intervals (at most
4,096 reserved N15 words total). Every reached `p`/`*` operand is protected,
including an idempotent write omitted from changed-word VM deltas. The check
rejects source overlap, memory overrun, a reached code/encryption collision,
and any write outside the declared intervals. It uses the memory geometry
retained from the normative guest admission rather than trusting caller
capacity. On the physical two-arm classifier, the five-stream batch needs a
near-source helper bank `[132,146)` **and** a remote loader bank
`[7,174,344,7,174,386)`. Removing either one refuses. These are helper
scratch writes, not the checksum's 43-word C-state frame, and the gate proves
neither initialization nor semantic correctness of guest C operations.

`build_signed_eof_branch_source` separately constructs a 132-cell graphical
current-N15 **candidate**, with all 256 byte classes entering C=45 and EOF
entering C=126. The builder is not a source-C compiler, a general conditional
layout solver, or an independent verifier. Its real 257-class VM regression
checks the complete machine actions, and an additional four-case independent
nonlinear admission verifies both terminal arms using a separate 15-trit
arithmetic oracle, frozen code paths and I/O positions. In particular EOF
passes the general path gate but still fails the revisiting-only gate, while
the backward byte arm passes both path validity and the source VM checks.
Successful byte input preserves its unread suffix on the same bounded run.
The outputs are **fixed markers**, not the dynamic checksum acceptance bytes.

### Canonical effect-free function

The opt-in `--empty-void --typed-file PATH` (or `--ternary-file PATH`,
`--typed-stdin`, `--ternary-stdin`) accepts one fully canonical no-effect
void-return function. The complete MCTI-to-MCTR path is re-decoded and
independently compared against the same two-cell `nop`/`halt` Malbolge
program. The publisher preflights the real VM with empty and nonempty input,
requires exact two-step termination and zero effects, and publishes a raw
source or selected-profile capsule without overwriting existing artifacts.

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 --output .temp/empty.malbolge \
  --capsule -- --empty-void --typed-file .temp/empty.mcti
```

Other typed effects, non-void returns, foreign profiles, and malformed wire
reject. This is a finite compiler subset, not an arbitrary C frontend,
return-code implementation, or proof of a complete source-C program.

The no-clobber publisher verifies the synced stage through its original
open descriptor before creating the final hard link. It also rereads the
newly published path through that descriptor and rechecks the exact bytes,
regular inode and timestamps before reporting success. A concurrent rewrite
after link creation cannot be mistaken for successful publication; if it is
detected, the command returns an error and retains the already-visible
target rather than deleting a path which may now belong to another writer.
The validation is bounded by the exact proposed artifact length, and does
not claim a perpetual filesystem snapshot against later external mutation.

The encoder assigns code addresses starting at zero and uniquely inverts the
normative profile decoder over all 94 graphical source bytes. Independent
admission checks every emitted code byte, selected profile ID/fingerprint,
exact positions, length, and terminal halt. No translation table is copied.

Data relocation is necessary before rotate/crazy: without it, code and
data pointers advance together and mutate the currently executing cell.
The single `j` may occur after no-op/raw byte I/O or forward jumps, but must
precede rotate/crazy. A later forward jump must read an exact known past
source word or an untouched loader-expanded word, and skipped cells must
remain graphical no-op padding. Its operand comes from the *actual
current data-pointer memory word* at that step, not necessarily the `j`
graphical code byte. After an earlier jump, `C` and `D` have diverged;
the operand can reside in a skipped no-op cell
whose value has already been XLAT2-encrypted. The source-memory shadow
models those prior encryptions before checking `j`.

For an ordinary initial relocation, the verifier requires D **after `j`
increments it** to reach at least the entire source length. A source-backed
`j` operand one less than that length is safe: its next D points to the
first loader-expanded word. A smaller destination still refuses unless
protected graphical scratch is strictly behind reached code. After a
forward `i` jump, the verifier additionally
accepts `j` reading an original or already-modified graphical source word
strictly behind the reached C and moving D to another source cell strictly
behind that same C. Subsequent data writes must remain behind their reached
code positions; any write into pending instructions fails closed. Both the
source operand and destination are independently derived from the exact
shadowed memory, not a declared destination or guessed byte. Source-length
extension past an encrypted operand still fails before publication.
Earlier jump/no-op source positions remain fully graphical and uniquely
encoded. Missing, premature arithmetic and potentially aliasing relocation
are rejected. This narrow source-scratch placement does not make dynamic
jumps, repeated data writes, or general guest byte streams universally safe.
A separate exhaustive decoder-phase test enumerates all safely addressable
rotate/crazy placements at positions 1 through 93, under both declared
profiles, and independently checks the encoded instruction and execution
witness lengths. It complements the longer real-VM boundary regression.

Forward jumps (`i`) can now form a bounded strictly increasing code path.
The **first** jump, while `D == C`, reads its own graphical code cell as a
target word. Each later jump instead reads the memory cell selected by the
*evolving data pointer*, potentially in an earlier skipped no-op region.
The checker models the exact XLAT2 mutation after every nonhalt step,
including `target - 1` after a jump. This matters because the next jump may
read a cell **encrypted by an earlier jump**, rather than its original source
byte. The independently admitted claimed target must equal the current data
word plus one, be strictly forward, and stay inside emitted source.

Every gap between a jumped-from and jumped-to source address must contain only
canonical graphical no-op padding. A skipped jump, skipped I/O, backward edge,
forged target, an unknown post-relocation operand, or inconsistent modified
operands reject before publication. No reachable source instruction is
revisited; full mutable code-state or conditional branching remains open.
The original one-jump 94-phase checks remain, and tests now execute real
2- and 3-jump chains under both canonical VMs, including an encrypted operand
read by the third jump and adversarial wrong-target/gap probes. A separate
regression verifies that a later jump may also read an already *executed*
no-op that has since been XLAT2-encrypted; the original code-cell byte is not
a trustworthy jump operand after execution.

An opt-in library-level forward-padding planner,
`encode_auto_padded_forward_layout`, accepts logical
`PaddedForwardStep::{Instruction, Jump}` and inserts the exact graphical
no-op gap for each independently admissible forward jump. Its output includes
both the verified linear layout and the mapping of logical operations to
physical source positions. Each target is derived from the evolving
`D`-pointer memory word, including earlier XLAT2 encryption; no caller-supplied
jump destination is trusted. The planner rejects backward/short targets,
unproven post-relocation operands, oversized code and unsupported plans. The
original machine-op CLI still requires concrete `jump:TARGET` tokens;
the opt-in `--auto-layout` mode uses this solver explicitly.

The library planner also accepts `PaddedForwardStep::AutoRelocate`. It inserts
*reached* no-ops to find the earliest safe decoder phase within 94 positions
for a `j` data-pointer relocation, taking the remaining logical suffix,
current data pointer and previously encrypted jump operands into account.
After an earlier forward jump, `AutoRelocate` accepts an *existing*
graphical source operand behind reached code, pointing either to safe past
source scratch or beyond the minimum remaining emitted source length. It
selects the first such safe phase or a sufficiently distant operand;
it does not rewrite skipped padding to invent a better operand. The final
independent admission still checks every real data-write address. A
current/historical VM regression compares the automatically chosen source-
scratch layout with a separately encoded manual plan and verifies actual
scratch mutation and byte output with empty and nonempty stdin. A separate
current/historical step-traced VM replay checks two consecutive `p`/`*`
operations on past source scratch: exact code/data pointers, data mutations,
XLAT2 code encryption, and independently calculated output bytes.

After a source-backed relocation, `AutoRelocate` can select a second
`j` from a known past source operand by inserting reached no-ops until
the new data destination lies strictly behind C or beyond the estimated
final source length. An explicit later `j` uses the same known-source
proof, subject to the full independent layout verifier. The planner refuses
input-written scratch and expanded words whose final loader seed or write
history cannot be proven. A fixed logical suffix permits a narrower case.
The current/historical VMs replay both relocations, a real input-dependent
`p` source write and binary output parity against the scalar oracle.
An equivalent explicit-phase `j` plan emits the same admitted guest source.

A separate 98-cell real guest first jumps from code 6 to 93, relocates D
from skipped source cell 7 to 62, then reads the known graphical word 100
at cell 62 to relocate into expanded address 101. Both canonical VMs
execute a real loader-word rotate and emit the independent scalar oracle on
empty and binary input. The automatically padded source is byte-identical
to the explicit layout; extending the source to overlap the write rejects.
The planner never guesses untouched expanded loader operands before it can
prove the final source tail.

A red-first 99-cell guest now adds a third `AutoRelocate` after two
source-backed `j` moves. Its D operand is the untouched expanded loader word
at address 101. The planner derives that word only when every remaining
logical step is a fixed instruction and the last two encoded graphical cells
uniquely determine the final source seed. It excludes previously written
expanded addresses and refuses a future symbolic jump, whose padding would
change the seed. The independent encoder reproduces the identical source;
current and historical VMs match scalar loader rotation, source/write traces
and binary-input independence. This bounded proof does not infer unknown
expanded writes, dynamic control or runtime C arithmetic.

The symbolic planner can also reuse a **deterministically written** past source
word as a later control operand. Its exact shadow tracks a known accumulator
and the effects of source-backed `*`/`p`; unreadable loader words and
input-dependent `p` results remain unknown. A three-relocation guest first
jumps past its own graphical source cell at address 81, rotates that word
from 111 to 37, returns D to the modified cell and uses a third `j` to
relocate D to 38. The separately encoded plan and automatic planner agree;
both normative VMs emit byte 37 under EOF and nonempty binary input, with
exact source-write and control witnesses. Replacing the rotate with an
input-tainted `p` refuses in both independent and automatic admission. This
is deterministic machine-state proof, not C runtime state or arbitrary
self-modifying control flow.

The independent encoder also proves deterministic writes to loader-expanded
memory. In a 59-cell guest, a real `*` or `p` updates address 127, a second
`j` returns D to that address, and a third `j` reads the **updated** value
rather than the original loader word. The current and historical VMs match
an independent scalar recurrence and exact output under empty/binary input;
an input-tainted `p` still refuses as a control operand. The symbolic
planner now keeps value-aware expanded writes when their initial loader
word is proven from a fixed final source suffix. With fixed subsequent
instruction addresses, its two later `j` operations reproduce that same real
59-cell guest byte-for-byte, including `*`/`p` output and source maps on both
VM profiles. It refuses an input-derived `p` result and a later unknown write
that invalidates a previously proven value. Unfixed tails and symbolic jumps
still cannot assume the expanded loader seed. This is verified machine layout,
not general C lowering.

The independent linear encoder also admits a later forward `i` jump after
a source-scratch `j`/`p` sequence if the jump reads a separate known
cell. A seven-step real VM fixture uses binary input to modify source
address 67, then reads address 68 to jump forward, outputs the
independently checked byte, and halts on both historical/current
profiles. Forged targets and a later jump reading the input-tainted cell
reject. A second real VM fixture verifies a forward jump
whose D operand is an untouched expanded-loader word at address 127. Its
value 38 determines code target 39 under both profiles. The 44-cell guest
consumes and
emits `0x00`/`0xff`, matching the scalar recurrence and traced C/D/XLAT2.
A 59-cell guest independently writes expanded address 127 using input-
dependent `p`, returns D to it using a known expanded relocation operand,
and then refuses to treat the written word as a new jump target. The
symbolic padding planner now accepts a post-relocation `Jump` only when
its operand is past source memory whose current value is proven.
Real VM witnesses compute the next code address from an untouched skipped
no-op, a no-op already XLAT2-encrypted during execution, and a different
untouched cell after an input-dependent scratch write. All retain binary
I/O parity. Automatic `Jump` from untouched expanded memory is now admitted
only when a finite candidate-gap search proves the actual loader operand
from the final two fixed graphical source cells. A distinct 44-cell source
with `j` at code 8, `i` at 9 and a loader word of 38 at address 127
is reproduced byte-for-byte from symbolic steps. Current/historical VM
traces and both binary input values agree with the independent source.
Additional future symbolic padding, previously written expanded operands
and unknown input-dependent control values still refuse. This is not
unbounded branching, runtime state or a complete C compiler.

The planner also returns an exact source-cell origin table alongside
logical-to-physical code positions: each graphical cell is either an
original logical step, inserted *reached* relocation padding, or skipped
jump padding. The table is constructed only after independently admitted
VM path evidence; this is a bounded machine-step map, not a C source map.
The resulting source and data-write witness undergo the normal independent
layout check. Current/historical VM tests cover a long suffix and a two-jump
chain followed by safe rotate/crazy writes; unsafe repeated relocations,
post-relocation jumps and impossible source-length bounds reject. The CLI
accepts a symbolic relocation token only after `--auto-layout`.

Every admitted layout returns deterministic, step-indexed witnesses for
**four** facts: reachable code pointer, data pointer at the start of each
step, code cell encrypted after each nonhalt step, and the *planned guest
data-write address* for each rotate/crazy step (none otherwise, including
halt). Every data write must be either beyond source or strictly behind the
executing code pointer on a proven forward-only path. Current/historical
normative VM tests compare all four against actual
per-step control state, XLAT2 memory changes, and data-cell reads/writes
from the independent transition trace. Actual data-write **values** depend
on guest input and earlier arithmetic, so these layout witnesses do not
claim to predict values or arbitrary guest semantic equivalence.

Input-dependent guest arithmetic is now permitted on past source-scratch
cells without claiming a known resulting word: the independent admission
tracks unresolved source memory explicitly. Real `input` followed by a
behind-code `p` write and `output` produces different VM bytes for `0x00`
and `0xff` on both canonical profiles. The checker refuses any later `i`
or `j` that would use an unresolved source word to change control flow or
D placement.

A paired real-VM fixture admits the same multi-relocation
geometry when its input-dependent write is replaced with a known operation.
This is machine-level input-dependent arithmetic, not lowering of C
`getchar`, C arithmetic or a full stream program.

The source has two to 4096 cells (with a stricter bound for relocated data),
contains exactly one final halt, and carries the canonical selected profile
identity. Real current and historical profile-VM tests prove byte I/O,
rotate/crazy execution, forward skip-to-target semantics, halting, and
invalid placement rejection. A focused current/historical guest test also
proves a forward `i` jump followed by a source-backed `j`, one real `p`
source-scratch write, exact output on empty and nonempty stdin, and
rejection of a relocation into pending code or a forged source byte. This
expands placement verification, not the bounded byte-stream synthesizer;
the original unmasked twelve-byte Fibonacci output remains unsupported.

This is **not** a C-to-Malbolge compiler. Arbitrary ternary-IR operations,
general control-flow jumps, data/global layout, calls, runtime linkage,
source maps, full mutable code-state planning, and final capsule production
remain open.

## Explicit-profile source file emitter

The first source-producing command is a **bounded machine-op subset tool**,
not the C frontend or the complete compiler:

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-1998 \
  --output .temp/echo.malbolge -- input output halt
```

The same publisher now has an explicit symbolic layout mode. Only after
`--auto-layout` does `jump` mean a forward target chosen from the live
`D`-pointer word; `auto-relocate` asks for the earliest safe `j` phase.
`--auto-layout` also accepts the other ordinary machine tokens (`nop`,
`input`, `output`, `rotate`, `crazy`, `halt`, and explicit `relocate`), but
refuses numeric `jump:TARGET` and any ternary-file operand:

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 \
  --output .temp/auto-jump.malbolge -- \
  --auto-layout jump input output halt
```

For relocated guest ternary arithmetic, place `auto-relocate` before
`rotate`/`crazy`, followed by the final `halt`. The planner expands
unreachable source cells with inert no-ops for jumps, and inserts *reached*
no-ops to find a safe relocation phase within 94 decoder positions.
The expanded plan is **independently re-admitted** and run in the normative
profile VM before the same atomic, no-clobber raw or capsule publisher.
The reported VM step count excludes unreachable padding, while the
`.malbolge` byte count includes all physical source cells. The default
machine-token mode remains unchanged and still requires `jump:TARGET`.

The real external-process regressions compare symbolic output byte-for-byte
against the original concrete-token publisher, reload both profiles' files
in their independent VMs, and verify input/output, XLAT2 jump behavior and
relocated rotate/crazy data writes. A separate process-level round trip
executes a generated historical raw source and modern profile capsule through
`malbolge <path> --input-stdin`; the general runner must return the exact
binary bytes `0x00 0xff` from two successful input/output pairs.
A separate three-hop symbolic-chain fixture verifies that a later `i` reads
an XLAT2-encrypted operand rather than its original source byte. The
resulting historical raw and modern capsule programs are byte-identical to
the concrete three-hop baseline and execute exact `0x00` or `0xff` through
the real general runner with guest stdin.
Unsupported paths, malformed options, unsafe data moves and occupied
output paths reject before publication.
Neither mode provides conditional branching, loops, guest storage, EOF
semantics, or source-C lowering.

For a self-describing modern-profile `.malbolge` that the general command
runner can load directly, request the existing version-one capsule format:

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 \
  --output .temp/modern-echo.malbolge --capsule -- input output halt
```

The compiler can also consume a **canonical pre-layout ternary wire file**,
provided its already-validated effect trace is one or more adjacent
successful `ByteInput`/`ByteOutput` SSA echo pairs and a void return:

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 \
  --output .temp/echo-from-ternary.malbolge --capsule -- \
  --ternary-file .temp/echo.mctr
```

The original `--ternary-file` form retains strict adjacent-pair echo
admission. A separate explicit mode accepts a *latest-successful-read* trace:

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 \
  --output .temp/latest-read.malbolge --capsule -- \
  --latest-byte-trace --ternary-file .temp/latest-read.mctr
```

In this opt-in mode, every output must reference exactly the latest read's
SSA result. Reads may be unused and a read can be output more than once.
Replaying an older SSA byte after another input, writing before the first
input, scalar operations and non-void returns remain unsupported. The
successful-byte condition excludes EOF and failed I/O; no guest byte storage
or transformation is synthesized. Both modes produce identical bytes for
admitted adjacent echo programs.

### Direct canonical typed-IR file publication

A third bounded input form skips the caller-managed MCTR file. It accepts a
complete canonical `malbolge-typed-ir-v1` (`MCTI`) module and runs the existing
`typed-echo-adapter` inside the **same** artifact publisher:

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 \
  --output .temp/from-typed.malbolge --capsule -- \
  --typed-file .temp/echo.mcti
```

The default `--typed-file` retains strict adjacent echo. The separately
opt-in `--latest-byte-trace --typed-file .temp/latest.mcti` admits repeated
output of the latest successful byte and ignored consumed reads under the
same narrow semantic restrictions as the ternary-wire route. **This is not
source-C compilation**: the input must already be an independently admitted,
canonically serialized typed module with one void, zero-argument function,
no globals or proof obligations, and only the supported successful `u8`
byte operations. Source digest/ID and ABI identity remain copied provenance.

A typed input is a regular, nonempty file of at most 1 MiB. The adapter
independently revalidates the MCTI module, generates MCTR bytes, and admits
the graphical source. The publisher then **separately restores those MCTR
bytes and re-encodes the complete source** using its original independent
ternary bridge, requiring byte-for-byte identical source, execution-step
count and exact selected profile ID/fingerprint before the normative VM's
empty-input and two successful-byte-pattern preflights. Raw and capsule
artifacts use the existing atomic no-clobber publisher. Tests verify that
direct MCTI output equals the previous MCTI-to-MCTR-to-file route for both
modes, malformed/cross-profile/stale SSA/oversize inputs refuse publication,
and existing output is never modified. A separate process regression
executes a directly published typed latest-read capsule through the real
`malbolge --input-stdin` runner, verifying binary `0x00`, `0xff` and `0x80`
input with repeated outputs `0x00 0x00 0x80 0x80`. Hostile mode ordering,
missing path and extra operands also reject before target publication.
No EOF/error/guest ABI is added. Canonical typed-IR v1 binds its target
identity to **`malbolge-2026`**, even though the standalone machine-layout
CLI supports historical and immutable versioned profiles. Typed-file mode
therefore rejects profile selection drift (including those four other
registered identities) before target effect projection; successful current
profile capsules execute through both the normative VM and general runner.
The direct typed file mode also passes the physical 4096-cell cap with one
successful read and 4094 outputs, while the next cell is refused without a
published artifact.

Both canonical file modes accept only bounded nonempty regular files.
On **Linux and Android**, the publisher opens the candidate with native
`O_NONBLOCK` and checks the resulting **file descriptor** before reading,
so a named pipe (even one substituted for a regular symlink just before
open) cannot block on an absent writer. The open uses only safe Rust
`OpenOptionsExt`; no new FFI or dependency is required. The 1 MiB limit,
exact read length and canonical MCTI/MCTR admission still apply to the
actual opened bytes. Ordinary symlinks to regular files remain supported.
On other platforms the earlier resolved-path metadata check precedes open,
followed by an independent descriptor check: it rejects stable FIFOs but
does **not** close the pathname-swap window.

Real subprocess tests reject FIFO and FIFO-symlink inputs in both wire
modes, preserve valid regular symlinks, and repeatedly switch a candidate
symlink atomically between a bounded invalid file and a writerless FIFO
while both publisher modes execute. No swapped invalid input may block or
publish. This is bounded race stress, not exhaustive scheduling proof or
an authenticated stable pathname; a replaced regular file still requires
independent canonical byte admission.

### Canonical initial-zero byte output

An additional explicit opt-in `--initial-zero-output` prefix now publishes
the independently checked initial-accumulator-zero subset. The canonical
MCTI or MCTR source must contain exactly one `u8` zero constant followed by
one or more outputs of that identical SSA byte and final void return, with
at most 4095 output cells. The guest's initial accumulator is already zero:
the source contains actual Malbolge `OutputByte` operations and one halt,
not a host-side print or a hidden typed byte emulation. It consumes zero
input even when the guest runner has pending bytes.

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 --output .temp/zeros.malbolge \
  --capsule -- --initial-zero-output --typed-file .temp/zeros.mcti
cat .temp/zeros.mctr | cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 --output .temp/zeros-piped.malbolge \
  -- --initial-zero-output --ternary-stdin
```

`--initial-zero-output` works with both canonical file and stdin modes;
it cannot be mixed with `--latest-byte-trace` or machine-op tokens. The
publisher checks the typed source and exact re-decoded MCTR target again,
then separately executes the normative VM with empty and nonempty guest
inputs and requires exact zero output and zero input consumption before
atomic raw/capsule publication. The strict default, latest-read flow,
bounded wire sizes, and refusal to overwrite an existing output remain.
Real MCTI and MCTR stream tests keep their output paths absent both while
the canonical prefix is incomplete and after all bytes arrive but before
EOF; only closing the pipe permits final atomic publication.
This subset supplies no nonzero constant realization, guest EOF/status,
libc calls, heap operations, or complete C compilation.

### Zero-prefixed successful-byte traces

The opt-in `--zero-prefixed-byte-trace` mode accepts one canonical MCTI or
MCTR function with `u8` zero SSA output **before** successful byte reads,
then only latest-read SSA outputs. Unlike zero-only and latest-read modes
in isolation, this emits the leading guest zeros and subsequent input bytes
in **one** real Malbolge execution. No guest byte is evaluated or emitted
by the publisher host; the normative VM starts with A=0, then real input
instructions overwrite the accumulator. The first phase requires at least
one zero output, the second at least one successful input and corresponding
output; a later output of the old zero SSA is refused.

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 --output .temp/mixed.malbolge \
  --capsule -- --zero-prefixed-byte-trace --typed-file .temp/mixed.mcti
cat .temp/mixed.mctr | cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 --output .temp/mixed-pipe.malbolge \
  -- --zero-prefixed-byte-trace --ternary-stdin
```

`--typed-file`, `--ternary-file`, `--typed-stdin` and `--ternary-stdin` each
admit bounded canonical wire, re-decode complete MCTR, recheck the exact
position-sensitive source and profile, then execute the normative VM on
two successful-byte patterns. The preflight checks zero prefix, output
ordering, and exact read count before publishing a raw source or capsule
atomically without clobbering an existing target. The option is mutually
exclusive with strict echo, `--latest-byte-trace`, and
`--initial-zero-output`; no nonzero scalar, guest EOF, heap or C ABI is
represented. A real split-wire regression confirms MCTI and MCTR mixed
source remains unpublished both after partial data and after complete bytes
until the input pipe closes with EOF. Only then may the exact target appear.

### Explicit canonical byte identity-bitcast trace

`--identity-byte-trace` accepts independently admitted canonical MCTR or
MCTI input containing exact eight-bit signed/unsigned representation
bitcasts. Bitcast SSA definitions are compile-time proof of identical
accumulator bits, **not** emitted instructions. Only outputs referencing
live aliases of the latest successful input can publish; a subsequent
input invalidates earlier aliases.

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 --output .temp/identity.malbolge \
  --capsule -- --identity-byte-trace --typed-file .temp/identity.mcti
```

This mode also supports `--ternary-file`, `--typed-stdin`, and
`--ternary-stdin` with the shared one-MiB canonical read bound. The CLI
independently re-decodes MCTR, re-encodes target code, checks profile and
output/input-consumption patterns under the real VM, then atomically
publishes raw/capsule output without overwriting an existing path. Strict,
latest-read, initial-zero and zero-prefixed modes remain unchanged and
cannot be mixed with this flag. No general signed-byte computation, EOF,
failed I/O, memory, arbitrary C, or guest ABI is realized.

### Guest-computed finite nonzero byte literals

An explicit `--seeded-byte-literal` canonical MCTI or MCTR file/stdin mode
admits one source `u8` constant followed by one to thirty-three same-SSA
outputs.
The exact output counts have independent current-profile witness tables:
14 distinct bytes with one output, 10 with two, 21 with three, 24 with four,
18 with five, 19 with six, 18 with seven, 21 with eight, 21 with nine
and 25 with ten, plus 17 with eleven, 20 with twelve, 19 with thirteen,
22 with fourteen, 17 with fifteen, 24 with sixteen, 19 with seventeen and
20 with eighteen, 19 with nineteen, 21 with twenty, 20 with twenty-one
and 25 with twenty-two, 21 with twenty-three, 21 with twenty-four,
19 with twenty-five, 22 with twenty-six, 18 with twenty-seven and
22 with twenty-eight, 19 with twenty-nine, 20 with thirty and
19 with thirty-one, 20 with thirty-two and 18 with thirty-three.
For each count from three through thirty-three, a bounded source-prefix
scan confirms that 21 to 26 tested phases emit identical nonzero bytes.
The admission keeps the shortest prefix per value; the 24- and
25-output scans exclude phase seven, the 26-output scan excludes
phases six and seven, the 27-output scan excludes six through eight,
both the 28- and 29-output scans exclude five through seven, and the
30- and 31-output scans each exclude four through seven (22 valid
phases per count); the 32-output scan excludes phases three
through seven (21 valid phases); the 33-output scan also excludes
three through seven (21 valid phases, 18 shortest byte values).
Every extra `<` changes source positions and loader-expanded data, so
seeds cannot be shared across counts.
The admitted `j`/`*`/`<`/`v` layout computes bytes through actual
guest data rotation, never a host literal-output callback.
Each candidate source is re-admitted, then the *real normative VM* verifies
exact termination, every requested output byte and zero input consumption before
the existing atomic no-overwrite raw/capsule publication. A current-
profile capsule selects `malbolge-2026` in the general runner. Raw source
has no profile identity: do **not** execute it under the runner's default
historical profile and mistake that result for current-profile evidence.

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 --output .temp/seeded.malbolge \
  --capsule -- --seeded-byte-literal --typed-file .temp/seeded.mcti
```

This mode is separate from strict echo, identity-bitcast, latest-read,
initial-zero and zero-prefixed traces. Unknown constants, thirty-four
or more writes, input consumption, guest heap, EOF and general C
arithmetic still reject.

### Bounded canonical wire streaming on standard input

Canonical MCTI and MCTR can also be supplied directly from a producer process
without a caller-managed intermediate file:

```sh
cat .temp/echo.mcti | cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 --output .temp/streamed.malbolge \
  --capsule -- --typed-stdin
cat .temp/latest-read.mctr | cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 --output .temp/trace.malbolge \
  --capsule -- --latest-byte-trace --ternary-stdin
```

`--typed-stdin` and `--ternary-stdin` are **explicit**, mutually exclusive
source modes, each requiring zero path operands. Both accept a nonempty
canonical binary wire of at most **1,048,576 bytes**, read through the input
stream until EOF or the first overflow byte. Empty/truncated/noncanonical,
wrong-profile, unsupported SSA/effect flow and oversized streams refuse
publication. The default modes remain strict adjacent echoes; opt into the
latest-read subset only with `--latest-byte-trace` directly before the stdin
mode. These are compiler-input pipes, **not** executable guest byte stdin
(`malbolge --input-stdin` is a separate runtime action). Neither new mode
makes raw C source or a C ABI executable.

The publisher reuses the exact independently re-decoded MCTR source, normative
VM termination and two successful-byte trace checks, optional profile capsule
and atomic no-clobber output stage already used for regular-file inputs.
Tests compare real subprocess stdin and file outputs byte-for-byte across
MCTI/MCTR strict and latest-read examples; error cases do not create or
overwrite the final file. A writer must eventually close its pipe: an
unclosed stdin stream can legitimately wait for its upstream producer, unlike
the forbidden implicit opening of FIFO paths in the regular-file modes.
A separate process regression writes the first 16 MCTI bytes, checks that
no target exists while the producer keeps stdin open, then streams the
remaining bytes individually and closes the pipe. Only after EOF may the
publisher emit the exact target source; the source is independently
compared with canonical typed compilation.

`--ternary-file` is mutually exclusive with individual decoded machine-op
tokens. Its sole operand must be an existing, nonempty regular file with at
most 1,048,576 bytes. The complete MCTR version-one stream is independently
restored through `canonical_ternary_program` and passed to the separate
`byte-echo-bridge` admissibility checker; invalid/truncated/noncanonical
wire, wrong profile, or unsupported effect/control/data flow fails before
publication. The returned source is loaded and executed by the normative
profile VM at its declared execution-witness step count and then published
through exactly the same raw/capsule and no-clobber file path as machine-op
mode. Real external-process tests validate a successful three-byte trace
(including `0x00`/`0xff`) and reject canonical but semantically unsupported
SSA output, profile drift, corrupted wire and oversized files. Before any
publication, the emitter additionally runs two deterministic *successful*
input-byte patterns through the real normative VM and checks output
according to the admitted ordered read/write effect trace, consumed-input
count, and terminal instruction step. This is a bounded
execution regression, not a proof of all possible input traces or I/O errors.
Missing/empty input files, extra operands, and existing target paths also
fail without changing the output directory.

The source contains exactly the successful-input-byte interpretation of the
admitted ternary operations; it does **not** encode the source-C runtime ABI,
EOF or failed-I/O behavior, and the empty-input preflight checks VM
reachability/termination only; the additional successful-byte preflight checks
two concrete effect traces. `MCTR` metadata including its source hash is
copied provenance, not independent cryptographic source authentication.
A full C-to-Malbolge frontend and general guest-runtime realization remain
out of scope.

Independent process tests also publish real raw/capsule jump-then-`j`
rotate/crazy programs for both canonical profiles, reopen the files and
confirm VM data-pointer changes and an actual guest data-word mutation.
A second fixture reads an earlier jump's XLAT2-encrypted data operand and
rejects a lengthened source crossing its exact relocated-data bound.

A separate external-process regression now passes a three-jump instruction
list through the actual `malbolge_layout` emitter in both canonical profiles.
It verifies raw and version-one capsule bytes independently, reloads and
executes the resulting real VM source with successful input, and rejects a
forged later jump destination without publishing an output file.

The optional `--capsule` flag follows `--output PATH` and precedes the `--`
separator. The producer verifies the raw graphical machine code first, then
wraps it in the canonical historical-safe fallback/space-tab sideband using
the existing VM `build_capsule` API. Before publication it independently
parses the capsule and checks canonical profile ID, fingerprint and exact raw
payload bytes. The normal `malbolge` command runner then selects the embedded
profile and executes the payload; the historical classic interpreter instead
sees the fixed safe fallback (output `!`). External process tests verify both
paths. The raw format remains available by omitting `--capsule`.

It accepts an exact canonical `--profile` ID, a *new* `.malbolge` output path
whose parent directory already exists, and `--` followed by 2–4096 closed
opcode tokens: `nop`, `input`, `output`, `rotate`, `crazy`, `relocate`, `halt`,
and `jump:<unsigned-decimal-code-address>`. The latter is a **claimed**
post-increment jump target that must equal the graphical source-cell byte
plus one at that exact address. Only the previously verified one-shot jump
and data relocation shapes are allowed. Unsupported opcodes, unsupported
control/data flow, noncanonical profiles, malformed arguments and unsafe
source layouts fail before output publication.

The producer independently re-admits its emitted graphical bytes and loads
and executes them with the normative `ProfileMachine` for the selected
profile using empty input. It requires a halt at the exact admitted step
count before any source is published. This execution check validates the
bounded machine subset's shape and control flow, **not** arbitrary input
semantics or equivalent C computation. It stages the complete byte stream
in the output directory, reopens and byte-compares the stage, then uses an
atomic hard link to publish without replacing an existing target or symlink.
An interrupted producer can leave an ignored, hidden `.stage-<pid>` file,
but it cannot expose a partially written final target. A successful command
prints a short informational diagnostic to stderr and writes no stdout.

Raw `.malbolge` bytes still do **not** embed a modern target-profile
identity: consumers must supply the same explicit profile, or select the
`--capsule` option. The general-purpose runner treats *raw* files as classic,
whereas recognized capsules carry a pinned canonical profile/fingerprint and
use the profile-aware interpreter. The initial publisher is a machine-subset
emitter only; even with a capsule it does **not** claim C/ternary lowering,
source maps, guest-runtime linkage or support for general control flow.

### Verified bounded two-distinct-byte producer

The current-profile `--distinct-literal-pair` producer accepts a canonical
two-constant/two-output typed or ternary trace. It searches a finite
94-phase layout with one relocation and two real `p`/`*` data writes rather
than admitting only three hard-coded pairs. The publisher independently
re-admits the emitted graphical code against this precise grammar, checks
two disjoint out-of-source writes, and runs the normative VM with two input
cases. The real C conditional-loop experiment now emits binary `02 cf`.
Unsupported sequences, source drift and unsafe layouts refuse publication.
This is not general byte-stream compilation or dynamic C state execution.

### Verified three-distinct-byte producer

An opt-in canonical `--distinct-literal-triple --typed-stdin` or
`--distinct-literal-triple --ternary-stdin` mode accepts only three separate
source-proven byte constants and output uses for `Z%H`, `Q.O`, `Y-P`,
`T"O`, and `T"Q`.
The bridge proposes a linear guest source with one relocation and three
separate `p` writes. The publisher independently decodes MCTR, proves
profile/SSA and exact 8/9/10/12/14 source-step geometry, and reruns the
current-profile VM before raw/capsule publication. Unproved output traces
never publish; no general C code generation is claimed.

### Four-distinct-byte current-profile witness

The separately selected `T=4>` literal-output mode preserves four distinct
source-bound `u8` constant definitions and four exact SSA byte outputs. Its
independently verified positional target uses eleven no-ops, one data-pointer
relocation and four separate guest `CrazyData`/output pairs before halt. The
normative current-profile VM emits `T=4>` in exactly 21 steps with no input
consumption. Partial prefixes, other four-byte values, stale SSA identities,
foreign profiles and unproved arithmetic remain unsupported; this is not a
general C string-output implementation.

### Five distinct guest-computed bytes (bounded binary witness)

The opt-in `--distinct-literal-quint` mode admits five source-proven byte
constants only for `51 22 1b 37 39` (hex: `Q`, quote, ESC, `7`, `9`).
The eleven-nop relocated target performs five disjoint guest `CrazyData`
writes and executes five actual byte outputs in 23 normative VM steps.
Canonical typed/MCTR identity, all five SSA bindings, profile, input-free
execution, and the raw/capsule publisher are independently rechecked.
Incomplete prefixes, different five-byte outputs, and additional effects
fail without output; this witness is not general C string compilation.

### Six distinct guest-computed bytes (bounded binary witness)

The opt-in `--distinct-literal-six` bridge retains its original
current-profile `51 1c 4f 1d 50 1b` 15-step guest witness. A finite,
source-independent state-space solver now admits independently validated
nonhistorical six-effect streams with **either** zero or nonzero leading
bytes. The pinned Clang pipeline proves a complete two-trip C `while`
recurrence with branch-selected output triples and intervening local writes.
Its independent source oracle is `35 36 35 00 50 1b`, including an
interior NUL and repeated byte; actual normative VM execution emits that
stream in 19 steps for empty and nonempty input. The older zero-prefix
`00 51 22 1b 37 39` 23-step witness is also preserved.

Every admitted C effect remains bound to distinct source/SSA identities.
The compiler re-admits typed/MCTR and graphical source, validates safe
relocated guest data writes and exact output bytes in the normative VM,
and publishes no artifact if any stage fails. The search is bounded, not a
proof that arbitrary output sequences are synthesizable. C branches and
state are evaluated at compile time, not executed as guest control flow.

### Seven distinct guest-computed bytes (bounded binary witness)

The opt-in `--distinct-literal-seven` path admits only the independently
verified current-profile C output trace `36 3e 35 02 54 1f 18` (hex). Seven
source-bound `u8` SSA definitions survive canonical typed/MCTR admission.
Five inert no-ops and one data-pointer relocation precede seven separate
guest `CrazyData` writes and outputs, with data cells outside the source.
Both raw and capsule publication require normative VM output of these exact
seven bytes in 21 steps, independent of unused input. Incorrect prefixes,
reordered bytes, extra output and altered SSA are rejected without publication.
This remains a finite witness, not general C byte-string lowering.

### Eight distinct guest-computed bytes (bounded mixed arithmetic witness)

The opt-in `--distinct-literal-eight` C path admits exactly eight separate
source `putchar` constants with the independently verified current-profile
binary stdout `53 20 17 3c 36 01 52 06` (hex): `S`, space, ETB, `<`, `6`,
SOH, `R`, ACK. Three no-ops and one data-pointer relocation precede seven
real guest `CrazyData` writes and a final `RotateData` write, each followed by
guest output, then halt. The normative VM proves all eight distinct bytes in
21 steps with disjoint post-source data writes, independent of unused input.
Incomplete prefixes, reordered bytes, duplicate SSA and foreign profiles
reject without publishing an output. This is one finite source witness, not
arbitrary binary C output or general lowering.

### Nine distinct guest-computed bytes (bounded mixed arithmetic witness)

The opt-in `--distinct-literal-nine` C path admits exactly nine separate
source `putchar` constants with proven current-profile binary output
`54 3d 8d d1 c0 b4 bf d2 a2` (hex). One reached no-op and explicit
relocation precede eight real guest `CrazyData` writes and one `RotateData`
write (the third arithmetic step); each data write is followed by output.
The normative VM verifies nine distinct bytes, 21 total steps, nine disjoint
post-source data writes and zero consumed input before publication. Incomplete
prefixes, reordered bytes, altered SSA, foreign profiles and extra writes
reject; this is a finite source witness, not generic byte-string lowering.

### Ten distinct guest-computed bytes (bounded mixed arithmetic witness)

The opt-in `--distinct-literal-ten` C path admits exactly ten separate
source `putchar` constants with proven current-profile binary output
`51 22 fd ce a5 98 ba b6 87 cb` (hex). One reached no-op and explicit
relocation precede nine real guest `CrazyData` writes and one `RotateData`
write (the third arithmetic step); each data write is followed by output.
The normative VM verifies ten distinct bytes, 23 total steps, ten disjoint
post-source data writes and zero consumed input before publication. Incomplete
prefixes, reordered bytes, altered SSA, foreign profiles and extra writes
reject; this is a finite source witness, not generic byte-string lowering.

The eleven-byte C witness is separately admitted as an exact source-bound
`P`, GS, SUB, `6`, ENQ and six binary values. Eleven guest writes
produce 11 distinct bytes in 24 VM steps; the normative VM verifies
raw and capsule outputs without host computation substitution. This
finite trace is not general C byte-stream lowering.

The `--distinct-literal-twelve` C path admits the exact twelve-byte
`51 37 34 38 fb ce 9f 98 b8 b4 83 cd` witness. One reached no-op,
explicit relocation, eleven disjoint `CrazyData` writes and one
`RotateData` write at the fifth arithmetic position emit twelve guest
bytes in 27 VM steps. The normative VM independently verifies both
source-bound outputs and input independence before publication. Other
byte sequences, incomplete prefixes, and forged SSA are not admitted;
this is not general binary-stream lowering.

The separately selected twelve-byte source-scratch verifier also admits a
single **source-backed** data-pointer relocation after a proven guest
arithmetic write, without requiring the two-relocation source-revisit
pattern. It independently re-decodes the forward code jump and skipped
source, checks the exact data-pointer trace (including the j operand and
landing strictly inside past graphical scratch), rejects j operands touched
by earlier writes, and requires distinct data-write addresses strictly
behind reached code. A red-first guest test rotates one skipped source byte,
outputs it, relocates to a fresh source operand, rotates a second byte, and
outputs it eleven more times. Both binary-input and empty-input VM replays
agree with the independent scalar-byte oracle. A one-j trace without a
preceding arithmetic write still refuses. This is only an added *publisher
admission* for source-backed, write-disjoint twelve-byte traces, not a new
arbitrary C guest compiler, a claim that all source streams fit, or an
independent proof that arbitrary VM self-modification is safe.

The `--distinct-literal-thirteen` C path admits only the exact thirteen
source-ordered bytes `42 43 30 16 54 09 bf c6 c8 87 e3 ab a4` (hex).
One reached no-op and a data-pointer relocation precede twelve disjoint
guest `CrazyData` writes and one `RotateData` write (the sixth arithmetic
position), each followed by guest output. The normative current-profile VM
replays the thirteen binary bytes in 29 steps with no consumed input before
raw or capsule publication. Any incomplete, reordered or forged effect trace
rejects; this finite witness does not provide general C byte-stream lowering.


The `--distinct-literal-fourteen` C path admits only the exact fourteen
source-ordered bytes `59 45 2c 48 53 17 4c 4f 3d 40 5b 31 19 34` (hex).
One reached no-op and a data-pointer relocation precede twelve disjoint
guest `CrazyData` writes and two `RotateData` writes (the sixth and thirteenth
arithmetic positions), each followed by guest output. The normative
current-profile VM replays all fourteen binary bytes in 31 steps with no
consumed input before raw or capsule publication. Any incomplete, reordered
or forged effect trace
rejects; this finite witness does not provide general C byte-stream lowering.


The `--distinct-literal-fifteen` C path admits only the exact fifteen
source-ordered bytes `51 2e 19 38 3e 89 d2 ad a3 b7 c8 88 08 d5 c6` (hex).
One reached no-op and a data-pointer relocation precede thirteen disjoint
guest `CrazyData` writes and two `RotateData` writes (the sixth and thirteenth
arithmetic positions), each followed by guest output. The normative
current-profile VM replays fifteen binary bytes in 33 steps with no consumed
input before
raw or capsule publication. Any incomplete, reordered or forged effect trace
rejects; this finite witness does not provide general C byte-stream lowering.

The `--distinct-literal-sixteen` C path admits only the exact sixteen
source-ordered bytes `3f 49 36 13 5a 0a ba b3 c3 86 cc aa 01 07 d5 c5` (hex).
One reached no-op and a data-pointer relocation precede thirteen disjoint
guest `CrazyData` writes and three `RotateData` writes (the sixth,
thirteenth and fourteenth arithmetic positions), each followed by guest
output. The normative current-profile VM replays sixteen binary bytes
in 35 steps with no consumed input before raw or capsule publication.
Incomplete, reordered or forged effect traces reject; this finite
witness is not general C byte-stream lowering.

The `--distinct-literal-seventeen` C path admits only the exact seventeen
source-ordered bytes `59 3f 2c 48 50 1b 18 32 15 4d 4b 3b 42 0f 44 30 17` (hex).
One reached no-op and a data-pointer relocation precede fourteen disjoint
guest `CrazyData` writes and three `RotateData` writes (the seventh, ninth
and fourteenth arithmetic positions), each followed by guest output.
The normative current-profile VM replays seventeen binary bytes in
37 steps with no consumed input before raw or capsule publication.
Incomplete, reordered or forged effect traces reject; this finite
witness is not general C byte-stream lowering.

The `--distinct-literal-eighteen` C path admits only the exact eighteen
source-ordered bytes
`54 22 19 3e 38 03 09 dd 87 d1 a5 99 bf 08 c7 c6 c2 91` (hex).
One reached no-op and a data-pointer relocation precede fifteen disjoint
guest `CrazyData` writes and three `RotateData` writes (the seventh, ninth
and fourteenth arithmetic positions), each followed by guest output.
The normative current-profile VM replays eighteen binary bytes in
39 steps with no consumed input before raw or capsule publication.
Incomplete, reordered or forged effect traces reject; this finite
witness is not general C byte-stream lowering.

The `--distinct-literal-nineteen` C path admits only the exact nineteen
source-ordered bytes
`53 21 1a 3c 38 03 17 55 0e 49 2b 10 46 16 40 4c 3a 19 58` (hex).
A first-instruction data-pointer relocation precedes sixteen disjoint
guest `CrazyData` writes and three `RotateData` writes (the seventh, ninth
and fourteenth arithmetic positions), each followed by guest output.
The normative current-profile VM replays nineteen binary bytes in
40 steps with no consumed input before raw or capsule publication.
Incomplete, reordered or forged effect traces reject; this finite
witness is not general C byte-stream lowering.

The `--distinct-literal-twenty` C path admits only the exact twenty
source-ordered bytes
`3e 14 35 12 3f 0a a4 9c ad a3 1a a8 a2 95 ab 9f 98 1d ac ae` (hex).
Twelve reached no-ops shift `j` to position twelve, relocating the data
pointer beyond the 54-cell source. Seventeen guest `CrazyData` writes and
three `RotateData` writes (the seventh, eleventh and eighteenth arithmetic
positions) compute distinct bytes on disjoint guest cells, followed by output.
The normative current-profile VM replays all twenty bytes in 54 steps with
no input consumed before raw or capsule publication. Incomplete, reordered
or forged effects reject; this remains a bounded C lowering witness.

The `--distinct-literal-twenty-one` C mode admits only the exact
twenty-one source bytes
`41 0e 3b 0f 3f 0a 40 8e 26 92 27 96 22 97 8d 15 31 18 35 1a 2f` (hex).
Fifteen no-ops relocate the data pointer at position 15. Eighteen
`CrazyData` and three `RotateData` writes (the eighth, fifteenth and
sixteenth arithmetic positions), plus one reached trailing no-op,
produce twenty-one distinct guest bytes in 60 real VM steps.
The exact C effects are verified without host-side output replacement;
unproved prefixes, reordered literals and forged artifacts reject.

The `--distinct-literal-twenty-two` C path admits exactly the twenty-two
source-ordered bytes `39 16 37 05 41 0c 30 8e 24 9f 1b a0 23 97 15 28
27 29 14 32 1e 1f` (hex). Ten no-ops move the relocating `j` to source
position ten; twenty `CrazyData` and two `RotateData` writes compute the
bytes outside the 57-cell source, with a reached no-op before halt. The real
VM independently verifies all 22 output bytes, zero consumed input and exact
57-step termination before raw or capsule publication. Arbitrary
twenty-two-byte source sequences remain unsupported.

The `--distinct-literal-twenty-three` source mode independently replays
23 guest-computed output bytes in 57 normative VM steps before raw or capsule
publication; it does not imply arbitrary C output support.

The `--distinct-literal-twenty-four` source publisher verifies the exact
24 guest-computed bytes under the normative VM in 72 steps. Unsupported
source traces still fail without publishing raw or capsule output.

The `--distinct-literal-twenty-five` source publisher requires exact
source-bound effects and independently replays all 25 guest-computed bytes
in 105 normative VM steps, with no consumed input, before publication.
Other 25-byte sequences fail without publishing an artifact.

The `--distinct-literal-twenty-six` source publisher independently
replays all 26 guest-computed bytes in 105 exact normative VM steps before
no-clobber raw or capsule publication. Other 26-byte traces refuse.

The `--distinct-literal-twenty-seven` source publisher proves the exact
27 source-bound effects against 105-step normative VM execution before
publishing any raw or capsule bytes. Unsupported sequences fail closed;
existing output files are never overwritten.

The `--distinct-literal-twenty-eight` publisher checks all 28 source-bound
byte effects against exact 105-step real VM execution, with disjoint guest
arithmetic writes, before raw or capsule no-clobber publication. Unsupported
byte streams fail closed without publishing an output artifact.

The `--distinct-literal-twenty-nine` publisher independently verifies all
29 guest-computed bytes and exactly 105 normative VM steps, consuming no
input, before no-clobber raw or capsule publication. This is a finite
source-proven guest trace, not general byte-stream compilation.

The `--distinct-literal-thirty` publisher replays all 30 guest-computed
bytes in exactly 97 current-profile VM steps, with no input consumed,
before raw or capsule no-clobber publication. Other 30-byte effect traces
reject; this finite mode is not general C byte-stream lowering.

A separate source-independent 31-byte witness now proves 31 distinct guest
arithmetic outputs in 73 actual current-profile VM steps. Eight leading
no-ops and one data relocation precede 31 output pairs; an additional
reached no-op before pair nine shifts the loader recurrence, and rotations
at zero-based pair indices 2, 7, 15, 22 and 26 avoid repeated values.
`tests/guest_thirty_one_distinct_literal_witness.rs` independently checks the
exact 31-byte result under two input streams, zero input consumption, and
31 distinct data writes at addresses 127..188 beyond all 73 source cells.
The physical witness alone does not admit a C source; the separately
validated 31-byte compiler path now binds this exact source-to-guest trace.

The `--distinct-literal-thirty-one` typed/ternary publisher binds those
31 source-proven effects to the separate 73-step machine witness, independently
replays the normative current-profile VM with zero consumed input, and
publishes only on complete agreement. Reordered or altered bytes reject,
without weakening existing no-clobber raw and capsule output requirements.

The independent `tests/guest_thirty_two_distinct_literal_witness.rs`
proves another physical guest trace: 32 distinct binary bytes from 29 crazy
writes and three rotations in 97 current-profile VM steps. All 32 writes
are disjoint from the 97-cell source, at positions 105..168, with no input
consumed. The separate `--distinct-literal-thirty-two` publisher binds the
exact source-proven typed and ternary effects to that trace and independently
checks raw/capsule publication against the real VM. This is finite witness
admission, not arbitrary byte-stream lowering.

The independent `tests/guest_thirty_three_distinct_literal_witness.rs`
proves a 97-step current-profile VM trace computing 33 different binary bytes.
All 33 guest arithmetic writes are outside source, at 107..117 and 120..172,
with no input consumed. `--distinct-literal-thirty-three` binds only that exact
source-proven typed/ternary trace and replays the normative VM before raw or
capsule publication. General C byte streams remain unsupported.

The source-bound `--distinct-literal-thirty-four` publisher requires the
exact 34 guest-computed bytes, 97 steps and disjoint data writes; malformed
source effects refuse artifact publication.

The source-bound `--distinct-literal-thirty-five` publisher requires the
exact 35 guest-computed bytes, 97 steps and disjoint data writes; malformed
source effects refuse artifact publication.

The `--distinct-literal-thirty-six` publisher accepts only the 36-byte
source-bound trace and independently replays 97 guest VM steps before atomic
raw/capsule output. Unsupported effects and altered bytes fail closed.

The `--distinct-literal-thirty-seven` publisher accepts only the exact 37
source-bound bytes and verifies 97 guest steps before raw/capsule publication.

The `--distinct-literal-thirty-eight` publisher binds only the proven 38-byte
source trace and checks exact 97-step VM output before raw/capsule release.


The `--distinct-literal-thirty-nine` publisher binds the exact 39-byte
source-proven trace and verifies real 97-step VM output before publication.

The `--distinct-literal-forty` publisher checks 40 exact source-bound
bytes and normative 97-step guest execution before no-clobber raw/capsule
publication; unrelated guest effects remain unsupported.

The explicit `--distinct-literal-forty-one` mode independently admits
the proven 41-output MCTR or typed projection, verifies 97 real guest VM
steps and zero consumed input before no-clobber raw/capsule publication.

The finite `--distinct-literal-forty-two` mode checks exact canonical
MCTI/MCTR effects, 42 distinct real VM bytes and 97 guest steps, with
zero consumed input before atomic raw/capsule publication.

### Verified forty-three-byte source bridge

The bounded `--distinct-literal-forty-three` mode independently admits
exact typed/ternary effects and replays 43 guest-computed bytes in 100 VM
steps with zero input consumption before raw or capsule publication.

### Verified forty-four-byte source bridge

The bounded `--distinct-literal-forty-four` CLI mode independently
revalidates exact typed and ternary effects and executes all 44
guest-computed bytes in 103 normative VM steps before publishing raw
or capsule output. It is not general binary-stream compilation.

### Verified forty-five-byte source bridge

The `--distinct-literal-forty-five` publisher independently re-decodes
canonical MCTR, checks all 45 guest-computed bytes and the 105-step VM
trace, then publishes raw or capsule output without clobbering files.

### Verified forty-six-byte source bridge

The bounded `--distinct-literal-forty-six` CLI mode independently
revalidates exact typed and ternary effects and executes all 46
guest-computed bytes in 106 normative VM steps before publishing raw
or capsule output. It is not general binary-stream compilation.

### Verified forty-seven-byte source bridge

The `--distinct-literal-forty-seven` mode verifies exact 47 typed/MCTR
constant/output effects, replays guest arithmetic in the normative VM, and
publishes raw or capsule output only after 118-step termination and exact
47-byte output. Unsupported traces and occupied paths refuse.

`--distinct-literal-forty-eight` publishes only the independently admitted
48-byte C trace after exact typed SSA, MCTR, source/data separation and
normative 121-step VM verification. Other bytes/profiles fail closed.
