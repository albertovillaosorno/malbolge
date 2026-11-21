# Malbolge layout and encoding backend

## Status

Active

## Purpose

Implement address-sensitive instruction layout, self-modification planning,
encoding, jumps, data placement, runtime linkage, and final `.malbolge`
emission.

## Scope

This document governs the following declared TODO scope:

- `compiler/`
- `src/`
- `tests/compiler/`

## Current Behavior

### Source-loaded, input-dependent one-word state (2026-11-21)

The independent P2 physical-state experiment now emits a **real N15 guest**
with graphical source `DCBA@?>=<;:98765eu,>=<` (22 cells). C0..C15 are
executed no-ops; C16 reads the genuine guest `/`, C17 executes `j`, C18
executes `p` and C19 halts. The jump uses its original graphical code word
to select D118. The untouched original source loader supplies M118=7,174,453;
no host data-cell initialization or output substitution occurs. In the
20-step normative VM trace, C18 actually reads and overwrites M118 with
`crazy(7,174,453, raw_input)` for each tested raw byte/EOF stream.

This *one-word intermediate representation* distinguishes every raw byte
0..255 and true N15 EOF (14,348,906) without a preselected input branch.
An independent 15-trit scalar truth table proves all **257 results distinct**.
It separately enumerates the finite exact 94 no-op-phase by 94²
graphical-tail grammar with strict decoder-admitted tail bytes and finds
24 such loadable candidates. The deterministic source emitter selects the
first candidate; its 22 source bytes, C16/C18 positions, M118 seed and
20-step guest behavior are pinned by tests. Seven isolated VM restarts
from authenticated copies of one source-loaded memory image cover empty
input, NUL, byte 02, 7f, 80, ff and a byte with unread suffix.
A write whose new value equals M118 (NUL) has no reported memory *delta*;
the reached `p`, exact data-word read, final memory and accumulator still
prove that physical write attempt. Post-instruction code encryption and
input consumption are checked.

**Not yet supported:** the written word is **not** the canonical signed C23
`getchar` C32 low/high pair (nor the EOF `-1` representation). It does not
place a source-SSA frame value, preserve a local across a second read, select
C23 EOF branches, execute checksum arithmetic/phis, or implement a repeatable
guest loop. It is an injective lower-level building block, not successful
source-C publication. The original seven-block mutable EOF checksum still
fails closed at physical linking. See
`tests/compiler_live_input_encoded_store.rs` and the new
`build_live_input_injective_store_source` helper.

### Actual zero word from source-loaded guest data writes (2026-11-21)

The graphical source `DCBA@?>=<;|32DT` (15 cells) executes ten
no-ops, `j;p;p;v`, and halts in 14 genuine N15 VM steps. The source's
own C10 jump operand selects D125. The untouched loader supplies
M125=7,174,397 and M126=84; these are **not zero seeds** and are not
host-created VM state. The first reached `p` writes 7,174,481 to M125;
its accumulator feeds the second `p`, which writes exactly zero to
M126. The finite independent search finds 43 zero-producing candidates
in 520 admitted phase/tail cases; the first is selected canonically.
Every graphical pair of loader source bytes (94 squared) and all six
recurrent phases yield **no virgin zero** (297 distinct expanded words,
minimum 27), independently confirming that this word was computed by
real guest arithmetic. Empty and nonempty stdin execute unchanged:
no guest `/` is reached, neither input consumption nor output is forged.
Exact data reads/writes, post-instruction encryption and final memory
are traced by `tests/compiler_zero_cell_source.rs`.

**Boundary:** this is only one N15 zero cell at program entry with the
real machine's initial A=0. A negative VM trace beginning with A=3
instead writes 3. Neither the adjacent high zero word of C32 `[0,0]`
nor an unknown-entry-accumulator-safe operation has been linked. The
seven-block mutable EOF checksum still refuses compilation. The
`build_zero_cell_source` helper therefore provides a physical precursor,
not a source-C initialization stage.

### Two retained raw input states across actual guest reads (2026-11-21)

The physical input-store builder now has a separate two-read variant. It
emits a real 36-cell N15 graphical source:
`DCBA@?>=<;:9876543210/.-,+*Zj!Wg|0"y`. After 27 reached no-ops,
C27/C30 read separate guest input events, C28/C31 execute actual `j`
relocations, C29/C32 perform real `p` writes, and C33 halts. The first
jump's original graphical word selects D107; the second jump reads the
**untouched loader word M109=124** and selects D125. Both initial data
words M107 and M125 are loader-produced `121`, with no host seed. The
second guest input replaces the accumulator but leaves M107 unchanged.

An independent finite oracle enumerates the exact 94 possible no-op
prefixes and all legal graphical two-cell tails. Of 4,032 examined
loader-admitted layouts, seven preserve both 257-class inputs in disjoint
memory cells; the emitter reproducibly selects the first. Each `p` maps
raw byte 0..255 and true EOF injectively under an independent ternary
oracle. Across both cells, **all 66,049 ordered raw-input pairs** remain
distinct. Eight actual normative-VM streams, including empty, single-byte
EOF, NUL, high bytes, repeated bytes and unread suffixes, halt at 34 steps.
Tests check input cursors, both jumps, operand words, data writes,
post-instruction encryption and unchanged first storage across the second
read. No host-calculated C output is substituted for guest execution.

This demonstrates two *encoded* physical input states; it is not signed
C23 `getchar`, a canonical C32 two-word SSA destination, an EOF-dependent
branch, dynamic arithmetic, source-checked phi movement, or a repeating
C loop. The original whole C23 checksum remains correctly unlinked. See
`build_live_two_input_injective_store_source` and
`tests/compiler_live_input_encoded_store.rs`.

### Three bounded physical 141-position guest backedges (2026-11-21)

The initial complementary 141-cell source experiment established two actual
C281 code-pointer returns, not a phase-independent state cycle. A separate
third-traversal candidate now changes six initially safe but third-visit-
unsafe graphical opcodes, retains 133 of the 140 matched half-turn pairs,
and derives a third real jump target from the source loader: M562=41,
M563=118, and the subsequent recurrence produces M639=119. A 640-step
normative N15 execution confirms C281 -> C100, C281 -> C106 and C281 ->
C120, the exact code and data pointers, executed/encrypted code and input/
output for five bounded streams. A changed graphical tail reaches C100
instead on the third jump. This does **not** prove a repeated state
contract, a usable C arithmetic block or a source-linked EOF loop. See
`docs/technical/compiler/141-half-phase-return-evidence.md` and
`tests/compiler_141_half_phase_returns.rs`.

### Real guest input before source-loaded C32 constant writes (2026-11-21)

`build_c32_literal_after_input_source` emits a current-N15 graphical guest
that actually executes `/; j; *; (*|p); v`, preceded by 0..93 reached no-ops
and followed by one unreachable graphical loader tail byte. The physical
`/` consumes a byte or observes true EOF. Its arbitrary accumulator is
replaced by the first `*` before the second store; both adjacent C32 words
are derived from **actual unmodified loader memory**, not host-seeded VM
state. The fixed `**` and `*p` grammars never admit a first input-dependent
`p`, because doing so would silently assume a known incoming accumulator.

An independent fifteen-trit decoder, loader and arithmetic census covers
both 94-prefix by 94-tail grammars: 163 distinct `**` literals, 297 `*p`
literals and 409 in their union. A deterministic spread of 25 source
lookups matches the canonical independent source chosen for each sample.
Two selected graphical sources run on the normative N15 guest with empty,
NUL, high-byte `80`, byte `ff` and unread-suffix `01 02` input. All ten
bounded paths terminate at the physical `v`, consume only the available
first byte, produce no output, and execute two actual adjacent C32 writes
with exact loader operand reads and post-instruction encryption. Isolated
VM trials restart from validated copies of one authentic source-loaded
memory image per candidate, without retaining mutations across inputs.

This demonstrates a live **input effect followed by input-independent C32
state materialization**. It intentionally does **not** store the C23
`getchar` result, classify signed EOF, preserve a mutable local, implement
source CFG branches, or complete the EOF checksum. In particular C32 zero,
byte `ff` and signed EOF remain outside this grammar and fail closed.
The unchanged five-input source checksum still refuses guest publication
at the missing physical operation/control linker.

### Raw-input adjacent C32 store locality counterexample (2026-11-21)

An additional independent N15 test executes the first two physical data
writes after raw `/; j` using either `p; p` or `*; p`, on byte `02` and
EOF separately. All four traces verify actual input, fetched code, exact
loader-derived operands, adjacent writes, and self-encryption. The first
written low word has the same units trit for both raw input cases, while
canonical C32 signed `getchar` requires different units trits. Thus the
restricted direct two-word layout cannot store both canonical values.
This does not rule out source-controlled branches, trit-moving operations
before the store, or revisits; it narrows the next physical linker search.

### Profile-bound C32 constant-write operand plan (2026-11-20)

The current N15 target now exposes `plan_c32_literal_crazy_writes` from the
layout composition boundary. Given an exact 32-bit C bit pattern, including
signed EOF `0xffffffff`, it derives six full-width data operands for six
consecutive *physical* `p` instructions. The instruction result after steps
2 and 5 is independently proven to equal the canonical low/high C32 words,
regardless of the incoming accumulator. A real VM trace executes all six
writes and confirms C23 EOF's two words `[4644102, 299]` from seven
representative entry states, while a separate operand oracle covers all 257
signed-converted input classes and all ternary input digits. A wider
259-value C32 matrix also preserves `0xff` as `[255, 0]`, **not** EOF.

This is a **prelink recipe**, not completed source-guest state storage. The
initial six operand words are manually seeded for the VM trace; the exact
source loader has not been shown to produce them. The two physical results
land at *nonadjacent* entry-data offsets `2` and `5`, so the future linker
must also establish a sound transfer to the original C32 frame's adjacent
SSA cells. Neither conditional input dispatch, phi transfers, repeated loop
control, arithmetic, nor the complete seven-block mutable C23 EOF checksum
is published. Historical/forged target profiles refuse the plan.

### Bounded source-loaded C32 literal emitter (2026-11-21)

`build_c32_literal_loader_rotate_source` now turns an exact C32 literal
into a position-sensitive graphical N15 candidate. Its finite search
tries 0..93 reached `o` prefix instructions, then a physical `j; *; *; v`
and one unreachable graphical tail cell. The `j` reads its own graphical
source byte and sets D to that word plus one; the two `*` instructions
must write separate adjacent data addresses outside the source envelope.
The candidate is returned only when the normative six-phase loader
recurrence supplies **both** inverse-rotated target words without any
host-seeded memory. Unsupported profiles and literals return typed errors.

An independent scalar oracle derives all graphical address decodings,
loader-tail recurrence values and trit rotations for the entire 94 by 94
prefix/tail grammar. Exactly 66 prefixes fit nonoverlapping data memory,
with 528 legal graphical suffixes, 180 successful layouts and **164 distinct
canonical 32-bit literal values**; duplicate representations select the
first deterministic source. The source emitter reproduces every distinct
oracle candidate. Five selected prefix phases (0, 1, 2, 7 and 8) execute
`j; *; *; v` in the real normative N15 VM, with both empty and binary
unread stdin. Their traces prove exact expanded seeds, reached code
positions, pointer transfer, consecutive data reads/writes, output-free
halt and post-instruction code encryption. The original five-cell source
`(&%N$` is one member; other verified outputs include `284586666` and
`337199311`, rather than a sequence of longer literal-byte examples.

This **does not cover all C32 literals**. In particular C32 zero, byte
`0xff` and signed C23 EOF `0xffffffff` are all refused by this closed
graphical-loader/rotate grammar. Those missing values require different
loader preparation or actual guest synthesis. These fixed constants do
not perform `getchar`, select a data-dependent branch, update source SSA
state, copy phi edges, or loop. The original seven-block mutable C23 EOF
checksum remains unlinked; the source-input state verifier is unchanged.

### Mixed two-instruction source-loaded C32 constants (2026-11-21)

`build_c32_literal_loader_arithmetic_source` extends the bounded literal
emitter to four real data-operation templates: `**`, `p*`, `*p` and `pp`.
A source-loaded `p` folds the actual accumulator with the untouched
loader word at its own data address; `*` rotates its own word. Both
operations therefore still write the canonical C32 low and high cells
**adjacently**, without host-seeded data or source-C runtime input.

An independent 15-trit oracle checks all 94 graphical no-op phases and
94 possible tail bytes separately for each template. The template-specific
unique C32 literal counts are 164 (`**`), 156 (`p*`), 298 (`*p`) and
222 (`pp`), with **750 distinct values in their union**. Source emission
chooses the first exact template, prefix and source suffix in that order,
then reproduces all 750 independently enumerated candidate sources.
Three new representative literals (`351548260`, `911155607`, `509386234`)
execute actual N15 guest `p*`, `*p` and `pp` paths; traces verify both
source-expanded data reads, adjacent writes, data-pointer relocation,
post-operation code encryption and output-free halt. The earlier `**`
source family and original checksum refusal remain intact.

**This remains a fixed literal writer**, not runtime C32 computation:
zero, successful signed byte `0xff`, and C23 signed EOF `0xffffffff`
are all outside the admitted source/loader grammar. The missing signed
input conversion, C32 runtime branching, mutable arithmetic, phi copies
and checksum backedge still prevent complete P2 compiler publication.

### Printable loader-tail rotation exhaustion for C32 EOF (2026-11-21)

An independent bounded ternary-oracle regression enumerates all
`94² = 8,836` ordered printable source-tail pairs. For each tail it
checks the established six recurrence phases and all 15 distinct
right-trit rotations of each expanded-memory word:
`8,836 × 6 × 15 = 795,240` candidate values. Neither EOF literal
preseed word `13,932,306` or `897`, nor the successful-byte `0xff`
high-cell preseed `0`, occurs. The positive control **does** observe
the successful-byte low-cell preseed `765`, so the enumeration is not
a vacuous rejection of loader-derived words.

Because the loader's six-phase recurrence and a 15-trit rotation cycle
are independently verified, this rules out preparing the required
signed-EOF C32 constant cells through **untouched graphical-tail
expansion and rotations alone**, at *any* expanded-memory address.
It does **not** rule out guest `p` synthesis, active writable-memory
transformations, additional arithmetic, branch-specific code, or
a future general signed input result linker. Those remain necessary
compiler work and cannot be replaced by the enumeration.

### Source-loaded, adjacent physical C32 constant witness (2026-11-21)

A minimal five-byte graphical N15 source `(&%N$` now takes a physical
`j; *; *; v` path at C0-C3, with C4 (decoded `j`) **unreached**.
The initial C0 `j` reads M0=40 and resets the data pointer to D41
after the VM's mandatory increment. The real loader, not a manually
edited guest-memory vector, provides untouched M41=7,174,492 and M42=72
from the C3-C4 source tail `N$`; the period-six loader recurrence is
independently checked against M5/M6 and an exact scalar trit oracle.

The reached C1/C2 `*` instructions rotate and physically overwrite
those adjacent cells with M41=7,174,466 and M42=24, encoding the
canonical 32-bit value `351548234`. A four-step normative VM trace
checks source positional decode, the `j` data read and pointer target,
both `*` data reads, writes, accumulator results, and self-encryption;
the program halts at C3 with no I/O effects. The established loader
tail selector also finds exactly `N$` for these seed requirements.
The same fixed five-byte grammar refuses the distinct byte `0xff`
and signed EOF `0xffffffff` initial seed pairs: neither is generated
by a graphical two-byte tail at D41/D42. This is a bounded grammar
result, not proof that arbitrary loader/guest initialization is
impossible.

This is the first source-loaded **adjacent C32 literal write** under
this contract; it does not read or classify `getchar`, route runtime
C32 results, implement phi transfers, or satisfy the original mutable
EOF-checksum program. Its signed-EOF fail-closed gate remains active.

### Adjacent two-rotate C32 literal write plan (2026-11-20)

A second current-N15 prelink plan uses two physical `*` operations rather
than six `p` operations. Each `*` rotates and overwrites its own D cell,
independently of incoming A. The inverse one-trit rotation gives the exact
two required initial operands at consecutive data addresses. The canonical
signed C23 EOF `0xffffffff` uses the seed pair `[13932306, 897]` and
physically produces adjacent cells `[4644102, 299]`; successful `0xff`
instead uses `[765, 0]` and produces `[255, 0]`.

Independent ternary permutation checks cover 259 selected C32 patterns.
The normative N15 VM confirms both reached `*` instructions, their own
data reads, destination cells, accumulator updates, and code encryption,
for five target bit patterns and seven initial accumulator states. If a
rotation leaves a cell unchanged (for example `0 -> 0`), its executed
instruction still counts as a physical store but a *change-only* VM delta
is correctly absent; the source input-state verifier already distinguishes
these cases by observing the reached data operation itself.

This closes the **adjacency gap for a pre-seeded literal**, not the larger
guest linker. Both full-width operands were supplied manually in an
isolated `from_state` VM; no executable graphical source or prior guest
operations have yet established them. A real source-C input-result store
still requires actual input-dependent data, source-selected EOF/byte
control, disjoint source frame layout, and full SSA/loop verification.
The complete original C23 checksum remains unlinked and unpublished.

### Bounded physical 282-phase copies and data reset (2026-11-20)

`tests/compiler_282_phase_blocks.rs` now verifies a restricted two-block
composition in the canonical current N15 VM. It constructs two 282-cell
source envelopes (564 source cells total), each with the same first 281
source bytes and source-relative operations: a physical `j` data reset,
signed raw `/` input, ternary `p` memory update and `<` output. Each of the
five frozen streams (empty, NUL, high bit, `ff`, and `01 02`) executes the
full two-block path and halts after precisely 564 actual steps within a
4,096-step ceiling. Independent scalar 15-trit `crazy` oracles verify both
full data writes and the exact input/output effects; the trace checks every
fetched instruction and its XLAT2 self-encryption, not only final bytes.

The experiment keeps the same two input/fold/output site *phases*, but cannot
simply copy the data-pointer state. In straight-line continuation from C281,
the two writes land at M128 and M127: the later C482 `j` reads an earlier
encrypted code byte (M404=121) rather than the C200 raw byte (122). Changing
**only** C281 to `j` resets D via the previously encrypted M203=45, so C482
instead reads M246=89 and the second fold writes M95. On `01 02`, the first
case emits hex `36 34` and the data-reset case emits `36 36`. These are two
specific positive *execution* paths and one meaningful distinct-state
counterexample, not a repeatable 282-step semantic cycle. Both continue
through distinct physical code addresses. A third one-cell C281=`i` return
candidate is rejected by actual VM trace: it reads encrypted M203=45 and
jumps to C46 rather than C0 or C282, while re-encrypting previously executed
M45 from 111 to 120. All five 282-step prefixes agree on the wrong target.
Only this frozen return grammar is disproven; other return mechanisms are
still open, and the seven-block C23 EOF checksum remains unpublished.

### Repeated live writes to one mutable guest cell (2026-11-19)

A 91-cell, current-profile source generated by
`build_seeded_repeated_state_write_source` runs nine actual loader rotations,
then executes one signed `/` at C39 and two `p` operations **against the same
M95 cell**. A three-`j` chain at C44..C46 resets D via M96=72, M73=61 and
M62=94. Consequently the second `p` at C47 reads and overwrites the first
`p` result from C43, rather than a distinct untouched operand. C48 emits the
new accumulator and C49 halts after 50 VM steps. A scalar independent
15-trit truth-table oracle checks every data read/write and all guest output
for EOF, all 256 bytes, and an unread-suffix case; invalid profile and reset
tails refuse construction.

This is real guest mutable state, but it is *not* C32 arithmetic, source-C
state initialization, a two-read loop, a linked phi copy or executable
checksum. The written M95 is a loader helper cell, not a source-C local.

### Two consecutive live guest crazy operations (2026-11-17)

A 29-cell, source-loadable current-profile guest now executes nine actual
`*` data rotations, each followed by an actual `j` pointer reset, before
performing a real `/; p; p; <` sequence and halting in exactly 27 steps.
The two `p` instructions read different, still-unmodified loader words at
addresses 42 and 43 (`40` and `7174413`), then independently mutate or
idempotently rewrite those cells using the incoming byte or the profile EOF
word. Both manual encoding and symbolic `AutoRelocate` with an exact two-byte
loader seed produce the same source and reverse source map.

Eight bounded binary/EOF input streams run in the normative N15 VM with
independent scalar base-three oracles for all nine rotations, both distinct
crazy operations, both memory before/after values, the single output, the
committed input count and exact halt. The VM's delta represents *changed*
cells, so an idempotent `p` intentionally has a data read but no data delta.
This extends the prior one-`p` live arithmetic path to a genuine two-stage
input-dependent guest computation. It does **not** implement source-C
`putchar(getchar())`: this particular pair maps EOF to byte `0x0d` rather
than the required C23 `0xff`. The fully correct 257-value operand proposal
still lacks executable placement, and mutable EOF-checksum C remains refused.

### Bounded revisiting guest input evidence

A finite multi-input gate now replays **one identical guest source** against
2..8 distinct, independently supplied binary input/path/effect witnesses.
Duplicate streams and oversized batches refuse before any guest execution.
Each case starts a fresh normative VM and the gate returns no partial batch
when any case disagrees. This does not extrapolate one finite trace to other
inputs or prove unbounded streaming behavior.

The input-specific verifier now records **instruction-indexed I/O order**:
`Input(Byte)`, `Input(EndOfInput)` and `Output(byte)` carry their exact
zero-based guest step. It also checks instruction-caused data-memory writes,
including the address and full profile-width before/after words, separately
from automatic XLAT2 code encryption. Missing, moved or forged effects reject
even when the final output, consumed-input count and visited code path match.
The expectation is finite and must provide ordered, in-range event steps.

A separate 104-cell executable experiment now runs real input-dependent
Malbolge `p` arithmetic before an output and a genuine backward-code revisit.
It reads a byte or EOF at step 2, computes the ternary crazy operation with
original memory word 119 at address 43 at step 3, emits its low byte at step
4, then rotates the independent word 97 at address 65 at step 25 before
halting at step 34. All source paths revisit code cells.

The expected values come from an independent scalar 3-by-3 trit table and
rotation equation, not from the VM under test. Five frozen streams (empty,
NUL, 0x80, 0xff and a two-byte stream with unread suffix) agree on both modern
and historical profiles. This establishes actual guest input-dependent
arithmetic, memory mutation and backward control on one fixed path; it
**does not** synthesize an arbitrary EOF loop, mutable C locals or source-C
conditional branches.

The separate backward-control admission path checks a complete finite guest
execution against exact source/profile, code visits, self-encryption, output,
successful input consumption and **ordered input events**. These distinguish
successful `getchar`-equivalent byte reads from actual guest EOF input attempts;
a matching byte count alone cannot prove whether EOF was ever tested.

A 104-cell self-modifying guest visits sixteen code cells twice and exits after
its real backward jump. Two source variants perform one input/output or two
input instructions followed by one output on the first pass; encryption makes
the revisited input/output cells inert. The two-read variant proves empty,
byte-then-EOF, two-byte and extra-unread-input cases on the current and frozen
historical VMs. Replacing only the second EOF read with an inert instruction
preserves the empty-input path, output and successful-byte count; the gate
rejects the altered program solely on its missing EOF event. The API accepts
only complete, input-specific paths, not arbitrary input streams or
data-dependent control synthesis. The frozen mutable
EOF checksum remains uncompiled.

### Implemented linear code-layout slice

`src/compiler/malbolge-layout/composition/lib.rs` owns a bounded position-
sensitive source encoder for profile `InputWord`, `OutputByte`, `NoOperation`,
`RotateData`, `CrazyData`, an optional first `RelocateDataPointer` after
jump-free or forward-jump code, later `j` instructions with independently
proven fresh loader operands (including before live arithmetic/output), and
final `Halt`. The encoder assigns code positions from zero and inverts the
normative VM instruction decoder over all 94 graphical source bytes,
requires exactly one encoding at each address, and independently re-admits
the emitted source with canonical profile ID and fingerprint.

This slice requires two to 4096 code cells and one final halt. It admits
a sequence of strictly forward code jumps before a terminal halt.
Rotate/crazy are admitted only after one `j` data-pointer relocation;
earlier instructions may perform no-op, raw byte I/O, or strictly forward
jumps, but not data mutation. After a jump `D` and `C` diverge, so the
relocation base is read from the **current data-pointer memory cell**, not
the original encoded `j` source byte. The verifier replays prior XLAT2
mutation of source-memory cells before checking that the resulting base is
at least the complete emitted source length. This exact bound keeps all
later rotate/crazy writes disjoint from source code. Source-scratch
relocation also permits writes behind C; unknown control operands,
unsafe initial relocations and pending-code aliases reject. Each later `j`
reads the exact current D word: a tracked XLAT2 source-memory cell if D has
wrapped into code, or an expanded-memory cell otherwise. The checker derives
untouched expanded words from the original final source cells, not encrypted
source memory; it separately tracks known and unknown guest data writes. The
nine single-trit crazy-recurrence seeds all repeat every six words starting
with the first expanded cell, so an untouched loader word at any address
requires at most six recurrence steps instead of long-prefix checkpoints.
The rule applies componentwise to both 10- and 15-trit profiles; direct
normative VM comparisons cover near, middle and final memory addresses.
The independent scalar regression now exhausts all 8,836 printable
source-tail pairs on each canonical profile, checks the first twelve exact
loader words and their six-step cycle, and proves fixed-phase far-address
queries agree with the production shortcut. Four real source-loaded VM cases
(lengths 91 and 118 on both profiles) additionally compare near, distant and
final guest-memory words against that scalar oracle, then reach genuine halt.
This checks unchanged loader words, not an executable signed-EOF C loop.
Every new D pointer uses exact profile-memory wraparound. Subsequent
arithmetic writes must remain in expanded memory or behind executing C.
A penultimate `j` may point inside source, because only halt remains.
Arbitrarily many source-bounded `j` operations may be admitted when these
per-move checks pass. A later forward jump is safe when its D operand is
either a known graphical source cell or an untouched loader-expanded word
proven by the profile's six-step recurrence, or a deterministically
computed guest write. Input-tainted source or expanded operands still reject.
Every admitted
code/D/write/encryption position is independently replayed in traced VM
regressions. A red-first 59-cell machine fixture now writes expanded
address 127 with real `*` or `p`, repositions D using a separate untouched
loader operand, and reads the deterministic written word for a third `j`.
Both historical/current guest VMs agree with independently calculated loader
and arithmetic values under empty and nonempty binary stdin. Substituting an
input-derived `p` refuses at the unproven control word. This proves bounded
expanded-memory control values, not arbitrary guest-side C arithmetic.
The automatic forward-padding planner remains stricter than the independent
verifier. It creates later `j` moves from known graphical source operands
strictly behind reached C, or from untouched expanded loader memory when
all remaining logical instructions have fixed positions and their last two
encoded cells prove the final loader seed. It now also retains proven `*`/`p`
expanded-memory writes under that fixed-tail condition, so later explicit
`j` operations can read the updated word instead of the original loader seed.
Input-derived writes and overwritten proofs remain unknown. It can also
prove a symbolic `i` reading untouched expanded memory by searching bounded
forward destinations:
for each candidate, the fixed suffix determines both the eventual source
length and the exact two-byte loader seed, and that seed must yield the same
jump target. Unproven expanded writes, input-tainted operands and unknown
further jump padding are never guessed.

A separate red-first 100-cell guest extends this proof from expanded
loader memory **back into already-passed graphical source scratch**. After
a forward `i` and two source-backed `j` operations, the third `j` reads
untouched expanded address 101. The exact final graphical suffix yields
word 67, so D moves to skipped source address 68, strictly behind the
executing code address 95. A subsequent real `*` writes scratch address
68 and `<` outputs the rotated word. The independent encoder and automatic
`AutoRelocate` planner now admit this read-only expanded-to-source move;
source length and the loader-derived operand remain independently checked.
Both current/historical normative VMs match a scalar loader/rotation oracle,
full execution trace, memory mutation and output under empty/binary input.
Extending source into address 101 still rejects as an unsafe alias. No
unknown operand or pending-code write is accepted. The original complete
unmasked Fibonacci C program remains outside the proven guest grammar.

A distinct red-first 59-cell guest demonstrates the limit of prefix-only
expanded-memory proofs. Source-addressed `j` first reaches expanded word 127;
a real `*` and `p`, separated by relocations through loader word 128, write
the deterministic value 37 at address 127. A later symbolic `i` reads that
*written* word and jumps to code 38, but the initial arithmetic could not be
proved until the final jump gap fixed the full graphical suffix. An optional
single-jump planner fallback now tries at most 256 final source cells and
requires a fully fixed remaining instruction tail and at least one
preceding relocation and arithmetic effect. Input before the jump is allowed
only when the independent full-source checker proves the control value is
input-independent. Every proposed source is independently encoded and
admitted; the fallback never guesses input-dependent values. Both current
and historical normative VMs agree on
exact data/code/encryption witnesses, the written word and output byte 37 under
empty/binary input. A forged target, input-tainted arithmetic and an extended
source alias fail closed. A second red-first 59-cell program reads a byte
before the expanded `*` and `p`, which restore a deterministic accumulator;
its symbolic jump still selects 38 and outputs 37 with EOF, 0x00 and 0xff.
The independent encoder, both normative VMs, exact guest memory and input
consumption agree; replacing the initial `*` with input-tainted `p` rejects.
Multiple unresolved jumps, input-dependent control, and unbounded layout
search remain unsupported; this is not dynamic C arithmetic.

A red-first 59-cell fixed-instruction guest now has identical symbolic
and independent encoding with two later `j` operations following a real
expanded-memory `*` or `p` at address 127. Both current/historical VMs,
empty/binary input, a separate scalar loader/arithmetic oracle, output and
source maps agree. An initial input-tainted `p` and a later input-dependent
overwrite both refuse without stale control values. This is not arbitrary
expanded-memory or input-dependent control synthesis.

A known past source operand may also select expanded D beyond the minimum
remaining planned length. Independent full-length admission rejects any
source alias introduced by later padding. A 98-cell red-first program jumps
from 6 to 93, relocates via source cell 7 to 62 and via source cell 62
(graphical word 100) to expanded address 101. Both normative VMs execute a
real rotate, output its independently computed loader result under both
input conditions, and match the explicit layout. Extending the source into
the data-write address refuses. A further 99-cell red-first guest adds a
third `j` that reads the untouched loader word at expanded address 101. The
same explicit source, the automatic layout, independent scalar loader/rotate
oracle and two canonical VMs agree under empty/binary input. Replacing a
future fixed operation with symbolic `Jump` refuses the unproven final seed
for that relocation. A distinct 44-cell binary-I/O guest demonstrates the
newly admitted single symbolic expanded `i`, whose independent operand 38
from expanded address 127 selects code 39. Both canonical VMs match the
concrete source, exact trace and input-output parity for 0x00/0xff; a second
future symbolic jump remains unsupported. This does not prove general
expanded-control synthesis or the original C Fibonacci program.

A real VM boundary regression selects a later inverse-decode phase with a
greater encoded data address than position zero, admits a longer safe layout
including rotate/crazy, compares every code-position/encryption witness, and
rejects an otherwise identical layout extended one cell past the bound.
An exhaustive phase matrix independently rechecks every safely placeable
rotate/crazy opcode between positions 1 and 93 for both canonical profiles,
including the exact output phase and the execution/encryption witness sizes.

Forward code jumps (`i`) can occur after relocation and real source-scratch
arithmetic when the current D word is proven source, expanded loader data,
or a deterministic guest write. The first
jump normally reads its own code cell through `D == C`; after it jumps,
`D` and `C` diverge. Every later jump reads
through the evolving data pointer instead, so its target **cannot** be
inferred from the jump's own graphical code cell. The independent validator
tracks an exact bounded source-memory shadow, applying canonical XLAT2 after
each step at the real encryption address (`target - 1` for `i`, fetched code
position otherwise). It accepts each claimed post-increment target only when
that exact **current** data word plus one matches; targets must be forward and
inside the output source. All skipped code cells must be no-op padding, so no
future instruction is silently lost, and executed code is never revisited.

The admitted artifact retains four aligned deterministic execution witnesses:
code-pointer positions, data-pointer positions, post-step code encryption
addresses and optional rotate/crazy guest data-write addresses. The static
checker rejects source-cell data writes at or ahead of executing C.
Normative traced VM steps independently check the write address against its
actual semantic data read and any changed-cell delta, including when a
write commits an unchanged value, as well as code XLAT2 encryption. This
proves the bounded address separation, **not** input-dependent guest values.
Real current/historical VM programs prove two forward jumps whose second
target is read from skipped no-op data, then three jumps where the final
target reads a **previously encrypted** no-op operand. Adversarial tests
reject forged later targets, backward destinations and effectful skipped
regions. A distinct real VM witness now executes one forward jump followed by a
`j` relocation, rotate and crazy; another fixture reads a `j` operand from
the earlier jump's **encrypted** target-minus-one cell. Independent source
extension beyond that dynamic operand rejects as unsafe. The actual CLI
emits both raw and versioned capsule files, reopened and run under both
canonical VMs to confirm byte I/O and guest memory mutation.

A new seven-step source-backed witness first jumps past skipped padding,
reads one input byte, relocates D into source scratch and executes a real
`p` data write at address 67. A later `i` reads the untouched graphical
operand at address 68, skips ahead, outputs the independently calculated
byte, and halts. Both canonical VMs match exact code/D/write/encryption
witnesses and `0x00`/`0xff` output and memory effects. A forged target
rejects, and moving D back to the input-tainted scratch word makes the
following `i` fail closed. A separate 44-cell program first relocates D to
expanded address 127, then proves the untouched loader word 38 and jumps
forward to code 39. Independent scalar recurrence and both normative VMs
confirm exact step pointers, XLAT2, input and output for `0x00`/`0xff`;
a forged target refuses. A second 59-cell real-VM program reads binary
input, writes expanded address 127 with `p`, then relocates D back to the
written word. Its next `i` is refused as unknown, even though untouched
loader operand 128 was independently proven to equal 126. The symbolic
padding planner now accepts a post-relocation jump only from a known past
source cell; arbitrary runtime-dependent jump operands are unsupported,
as is the original unmasked Fibonacci C source.

Another real VM regression demonstrates the distinct case where a
later jump reads a code cell whose normal no-op execution already encrypted
it. This evidence is not arbitrary branch lowering, a general data
memory-write proof, or unbounded semantic equivalence.

The exhaustive 94-phase inversion matrix now requires both input and output
decoding at every address phase under all five registered profiles, rather
than only historical/current. Versioned profiles include swapped I/O decoder
identities, so this proves both opcodes independently at odd and even phases.

A complete 513-cell alternating input/output/halt layout now runs each byte
`0x00` through `0xff` under all five registered normative profiles, including
the immutable 10-/14-trit profiles with swapped I/O opcode identities. Its
independent step witness checks every reached code/data address and XLAT2
mutation; actual guest input consumption and output bytes must match the entire
binary domain. A separate seven-cell input/output/halt
layout uses one real `0xff` input followed by two exhausted reads on all five
profiles. Guest output retains the valid final byte, then twice exposes the
selected profile's EOF accumulator word modulo 256 without consuming phantom
input bytes. These tests cover successful byte I/O and raw VM EOF behavior,
not C `getchar`/`feof` semantics or arbitrary typed-IR program lowering.

`tests/malbolge_layout.rs` exercises 94 decode phases for profile byte I/O,
executes real byte I/O, early and later-phase relocated rotate/crazy, and
single and multi-forward-jump skip programs under the canonical normative
`ProfileMachine`. It rejects malformed lengths, halts, profile identity,
altered source and aliasing placements.

This is a *first machine-code slice*, not C-to-`.malbolge` compilation:
no guest data/global layout, general IR lowering, backward code jumps,
code-state revisits, calls or runtime linkage is implemented yet.

### First real source-artifact publication

A dedicated `malbolge_layout` Cargo executable now accepts an exact canonical
`--profile`, an explicitly fresh `.malbolge` output path, and a bounded closed
list of machine-op tokens (`nop`, `input`, `output`, `rotate`, `crazy`,
`relocate`, `halt`, or `jump:<target>`). This is not a substitute for typed
ternary or C lowering. It invokes the same verified position-sensitive layout
encoder, separately re-admits the complete emitted bytes, and loads/runs the
result under the selected normative `ProfileMachine` with empty input. A halt
must occur at the exact admitted execution-witness step count before the
source is published.

Canonical typed and ternary file inputs use an opened regular descriptor with
a strict nonzero 1 MiB limit. The publisher admits descriptor/path metadata
before and after its bounded read, rejecting observed inode replacement or
same-sized in-place rewrites even if the original byte count still matches.
On POSIX the admission compares device/inode and nanosecond modification and
change stamps; Windows uses available file identity and write/change stamps.
A stable symlink to a regular source remains valid. On Linux the reader
also resolves the initial canonical wire path and checks the actual opened
file pathname through `/proc/self/fd` before and after the bounded read. This
rejects parent-directory symlink redirection to an outside hard link of the
same original inode during an injected read, even when every timestamp, byte
and inode check remains equal. The bounded reader also requires the returned
byte count to equal the collected buffer length; an injected short, zero, or
exaggerated receipt cannot authorize otherwise unchanged compiler-wire bytes.
After that count check, the publisher rewinds and independently rereads the
same opened descriptor within the 1 MiB cap. Four red-first typed/ternary
reader substitutions that returned exact counts with foreign equal-length
bytes now reject, both without reading and after reading the original bytes.
The unchanged regular-file reader remains admitted. Descriptor/path metadata
and Linux pathname checks repeat after the corroboration read. This guards
buffer/source consistency at admission, not source authentication or races
after the last check.
The requested path is also resolved again after the read: rebinding an
initially stable parent symlink to a second hard link
of the same inode now rejects even if the original open-descriptor path is
unchanged. Unavailable descriptor-path evidence rejects; other platforms
retain their metadata-based contract. These checks reject observed concurrent
drift, not changes after the final admission check or atomic source snapshots
against a racing writer.

The publisher creates a new same-directory staging file, flushes/syncs and
rereads its exact graphical bytes through the original read/write descriptor,
with an allocation budget of the expected source length plus one byte. It
independently rechecks the synced descriptor's size, timestamps and identity
against the nonfollowing staging pathname both before and after the bounded
reread; the published hard link must still name the original staged inode.
A pathname replaced with an equal-byte file or symlink cannot be certified,
and cleanup only removes a still-matching original stage, preserving foreign
substitutions. The publisher also requires exactly one hard link to the opened
staging inode before publication and exactly two (staging and final target)
while verifying the newly published target. An extra hard link before the first
link blocks target creation; an extra alias observed after publication rejects
success while retaining the already-visible target. On Unix the link count is
read from inode metadata; on Windows it uses the native optional link count and
fails closed if that evidence is unavailable. Independent injected-alias tests
cover both stages and retain any unrelated hard-link pathname. The stage's
original resolved pathname is also pinned before publication and rechecked
before and after both bounded rereads. Renaming a parent and installing a
symlink back to the *same inode* changes that resolved pathname, so it rejects
before publication or before declaring an already-published target successful.
Stable parent symlinks present at initial opening remain permitted. The final
inode and path checks detect observed substitutions but do not establish an
atomic filesystem snapshot against ongoing writers.
The no-overwrite hard link atomically reveals the final `.malbolge` only after
staged content admission. On Unix, the publisher now also opens and syncs the
original resolved parent directory *after* independently verifying the linked
final bytes and inode, so successful publication includes a directory-entry
durability barrier. The opened sync descriptor must itself be a directory:
`fsync` on an unrelated regular file can succeed without persisting that
entry, so a wrong-kind sync rejects. On Linux the descriptor is opened
nonblocking so a substituted writerless FIFO cannot stall the barrier.
Red-first wrong-kind and wrong-object sync tests prove that false success,
while a writerless-FIFO test proves prompt rejection; legitimate directory
sync remains admitted. A failed parent sync returns an error and retains the
already-visible linked target; the stage is removed only if still owned.
If removing that still-owned stage fails after a verified publication, the
publisher reports a cleanup error while retaining the already-linked final
artifact rather than claiming success with an extra hard-link alias. An earlier
publication failure remains primary if cleanup also fails. A stage pathname
substituted after final admission is preserved and rejects success; a stage
already unlinked is accepted only when the original inode has exactly the
published target's remaining link.
An injected sync failure and an altered final byte separately verify these
ordering gates. After the directory-sync boundary, the original staging
handle and final pathname are re-admitted with the same identity, exact byte,
link-count and resolved-path checks. Injected in-place rewrites and equal-byte
inode substitutions during sync now refuse success, retaining any already
visible target rather than claiming its contents are verified. After staging
cleanup, the original descriptor and final pathname undergo one more exact
byte, inode, resolved-path and single-link check. A foreign hard link added
after final pre-cleanup verification, a rewritten final byte, or equal-byte
final inode substitution must not report success; tests inject all three
changes immediately before cleanup. The already-visible final file is retained
on rejection. On Unix, the original resolved publication directory is
synced again after cleanup, so successful publication also has a durability
barrier for stage unlink. A failed second sync refuses success while retaining
the already-visible final target; a crash before this barrier can leave a
hidden stage. The final descriptor/path/byte/single-link check follows this
second barrier. These checks narrow observable publication races but do not
make ongoing foreign writes an atomic snapshot. Windows retains file-sync
and no-overwrite guarantees but does not claim parent-directory crash
durability through portable `std::fs`.
Existing targets and symlinks are never replaced; invalid profiles, operands,
paths or layout shapes fail closed. Process-level integration tests execute
the built binary, reopen emitted files under historical/current canonical
profiles with real byte input, test forward jumps and relocated arithmetic,
compare exact output bytes across independent runs, reject unsupported input
and symlinks, and
exercise concurrent writers to one target. A separate three-jump external
process fixture publishes both raw and capsule sources under both profiles,
reopens and executes the exact outputs, and rejects a forged later destination
without creating a final file. On abrupt interruption a hidden
staging file may remain; it cannot expose a partial final target. A later
producer preserves any occupied `.stage-<pid>` staging pathname and retries
fresh sequence-suffixed names via exclusive creation, with 32 total attempts.
For output filenames whose full staging suffix would exceed a conservative
128-byte basename budget, the publisher uses a compact, reproducible
64-bit FNV-1a digest of the complete UTF-8 target filename instead of embedding
the original name in the stage. The digest is only a collision-prone name hint:
exclusive creation and bounded retries still prevent overwriting any existing
stage, including a digest collision. Distinct valid long output filenames
publish independently without overflowing a common 255-byte filesystem
component limit. An occupied hashed staging name is preserved and retried.
Only its own newly created stage is removed; exhausted collisions reject
before touching the verified source or an existing target.

An optional `--capsule` mode now wraps verified raw source using the
existing version-one historical-fallback capsule builder. The producer
independently parses the result before publication and requires an exact
canonical profile identity/fingerprint and byte-for-byte payload equality.
Independent CLI integration now publishes raw and version-one capsule files
for immutable `malbolge-2026.1`, `.2`, and `.3` profile IDs. It compares
byte-identical raw/capsule payloads, checks canonical profile fingerprints,
re-decodes each graphical instruction using the selected swapped or unchanged
I/O opcode identity, and replays three binary bytes `0x00`, `0xff`, `0x80`
through the normative VM for both published forms. The independently built
`malbolge --input-stdin` product runner additionally opens and executes each
versioned capsule using the same binary bytes, proving that capsule profile
selection survives into general execution instead of falling back to the
current profile. This is an actual process-level source/publication boundary,
not just in-memory encoder evidence. An additional immutable-profile runner
fixture feeds only one valid `0xff` byte to a seven-instruction capsule and
closes stdin: each real runner must emit that byte, then the selected profile's
EOF accumulator low byte twice rather than invent additional successful reads.
This tests raw machine EOF propagation through product execution, not C stdio.

Real external-process integration invokes the *general* `malbolge` runner on
a modern-profile capsule, and separately runs the historical-safe fallback
through the classic interpreter. The unframed raw mode remains unchanged:
modern raw `.malbolge` alone carries no profile and needs an explicitly
selected profile-aware loader. Neither mode implements source maps, general
C/ternary lowering or guest-runtime linkage.

### Library-level automatic forward-jump padding

The independent encoder also exposes `encode_auto_padded_forward_layout` for
logical instruction sequences with symbolic forward-jump slots. It computes
the target from the live `D`-pointer memory shadow (including XLAT2 updates),
expands only safe no-op padding cells, records logical-to-source address
mapping, then calls the same exact-profile independent layout admission.
The returned `source_cell_origins` vector labels every physical graphical
cell with its original logical index, generated reached relocation no-op,
or skipped forward-jump no-op. This provenance is computed from an admitted
VM execution witness rather than assumed reachable positions; it does not
represent source-C line mapping.
The planner fails closed on nonforward targets, unproven post-relocation
operands or layout overflow. Real VMs exercise one-, two- and three-hop
witnesses and jump-then-data-relocation; the first-jump phase matrix covers
all 94 address-sensitive decoder phases under both canonical profiles. The
current source CLI continues accepting concrete `jump:TARGET` tokens by
default. Opt-in `--auto-layout` accepts symbolic `jump` and `auto-relocate`
tokens, using the library planner as an untrusted candidate producer. This
is not conditional branch lowering or a general guest code-state solver.

`PaddedForwardStep::AutoRelocate` chooses the earliest safe `j` placement
among at most 94 reached source phases. It inserts reached no-ops while
checking dynamic `D` state, future source length and previous XLAT2
mutations, then delegates data nonalias proof to independent admission.
Current/historical VMs cover long suffixes and a two-hop jump followed by
relocated rotate/crazy. A second symbolic relocation uses only a past
source operand whose current value is proven and must again point behind
reached code;
its earliest admitted phase matches a separately supplied explicit `j`.
Two real VMs replay both moves with binary input, a source-scratch `p`
write and scalar-oracle output. Impossible placements, unknown control
operands and unsupported duplicate relocations still reject. This helper
is available only through the opt-in symbolic CLI grammar, not the default
concrete-token mode.

The symbolic planner now preserves known source-scratch writes from `*` and
`p` when their necessary input words are proven. It carries a known/unknown
accumulator and the exact altered source cell across later `j`/`i` operand
proofs; a guest input makes A unresolved, but rotation of a known D word
remains deterministic. In a red-first fixture, a first forward jump leaves
source cell 81 behind, `*` rotates its graphical value 111 to 37, and a
second relocation returns D to cell 81. An independent exact-layout proof
accepts a third `j` reading that value and moving D to cell 38. The original
symbolic planner rejected the same executable geometry; the updated planner
reproduces the independently encoded source. Both canonical VMs confirm
byte 37 output, input consumption, and exact source write under EOF and
binary input. Replacing `*` with input-tainted `p` rejects in both
checkers. Expanded-loader values and unresolved guest-written values still
cannot be used as symbolic control operands; the original complete C
Fibonacci target remains unsupported.

A subsequent symbolic `Jump` reads an exact past source operand strictly
behind C, including prior XLAT2 mutation and deterministic scratch writes.
Three current/historical VM fixtures prove untouched skipped and previously
executed encrypted operands, plus jumping past a separate input-written
scratch cell. All consume binary `0x00`/`0xff` and emit independently
checked output. A forged target refuses. Loader-expanded and unresolved
written operands remain unavailable to the planner; the independent encoder
continues checking its separately proved broader subset.

### Opt-in symbolic layout artifact publisher

After the CLI `--` delimiter, `--auto-layout` chooses the symbolic input
mode. It accepts `jump` and `auto-relocate` together with the ordinary
bounded non-jump machine tokens, rejecting the numeric `jump:TARGET` token
and any ternary-file operand. The default concrete mode and both MCTR wire
modes are unchanged. Every parsed symbolic step uses the already verified
`encode_auto_padded_forward_layout` library planner. The emitted operation
plan and raw bytes are then **separately** passed to
`admit_linear_layout` with the exact selected profile fingerprint and ID;
only independently re-admitted code is sent to the normative VM and the
same raw/capsule no-overwrite publisher. The VM execution length is the
number of reached code steps, not the number of padded source characters.

External-process regressions compare raw/capsule output against the original
manual concrete layout for a first forward jump, a two-hop encrypted-data
operand plus `j`, and automatically placed `j` with real rotate/crazy.
Both 1998 and 2026 profile VMs replay the published source and check
successful I/O or data-pointer relocation.

An additional process-level test runs the actual general
`malbolge --input-stdin` command on the generated
historical raw source and modern version-one capsule, requiring exact
`0x00 0xff` output for two non-EOF guest inputs. A second general-runner
fixture proves a symbolic three-hop jump chain whose last target is read
from an already XLAT2-encrypted operand. Raw and capsule outputs match the
independent concrete-token source exactly; a normative VM witness verifies
the data cell changed to the expected encrypted word before the real
binary-input process replay. Unsupported symbolic shapes,
invalid arguments, and occupied paths fail without accepted new artifacts.
This is source layout for a closed machine subset, not general control flow,
source-C compilation, guest ABI, or total I/O equivalence.

### Canonical ternary-IR-to-file bridge

The separate `byte-echo-bridge` now connects to the same artifact publisher
using `--ternary-file <canonical-MCTR-file>` after the CLI's `--` delimiter.
The input must be a regular nonempty file of at most 1 MiB. The publisher
uses the canonical MCTR version-one restorer, not a permissive ad hoc decoder,
and calls the independently validated bridge to admit one exact
successful-byte-input/output SSA echo trace with a final void return. The
bridge, not the file publisher, owns all semantic effect restrictions.

The resultant graphical Malbolge bytes receive the existing normative-profile
VM load/halt check and either raw or version-one capsule publication with
independently validated identity/payload and atomic no-overwrite behavior.
End-to-end tests invoke the real binary with a serialized canonical ternary
program, reopen both types of output under the normative VM, and compare
an actual multi-byte echo trace (including zero and 255). For this ternary
subset the publisher also replays two fixed successful-byte input patterns
on the normative VM, requiring byte-exact output, consumed-byte count and
witness-length termination before publication. Forged profiles, corrupted
wire bytes, valid but unsupported SSA output, missing or oversized inputs,
extra operands and existing targets fail without a new final artifact.
An explicit `--latest-byte-trace --ternary-file <canonical-MCTR-file>` mode
extends this same checked file publisher to latest-read SSA traces with a
single void return. Each output must refer to the most recent successful
byte input; repeated output and consumed-but-unused input are allowed. The
original `--ternary-file` option stays strict adjacent echo, and the two
modes emit byte-identical raw/capsule artifacts on the echo intersection.
The publisher derives the exact expected output for each of two fixed
successful-byte input patterns from the validated ordered MCTR effects, then
compares the normative VM's output, consumed count and exact halting step.
Missing/wrong-profile/corrupt wire, stale SSA output after a later read and
misordered mode options reject before publication. A real external-process
fixture reloads both new artifact formats and independently verifies
repeated outputs and ignored inputs, including zero and byte 255.

The source hash in MCTR is copied provenance, not independent source
authentication; VM preflight with empty input verifies
termination, and two chosen successful-byte traces are only bounded evidence,
**not** total successful byte-I/O equivalence including EOF.

This is a **bounded, working ternary-stage-to-file path**, but it does not
admit arbitrary ternary operations, source-C programs, guest heap, ABI return
values, EOF, failed I/O, or unbounded control-flow/layout code-state revisits.

### Canonical input-file nonblocking descriptor admission

`--typed-file` and `--ternary-file` share one bounded regular-file reader.
On Linux/Android it calls a safe Rust `OpenOptionsExt` reader with the
platform's `O_NONBLOCK` status bit, and admits the *opened descriptor*
only if it is a nonempty regular file no larger than 1 MiB. Consequently
stable FIFOs and writerless FIFOs substituted for a regular path immediately
before open cannot stall; a regular-file symlink remains permitted. The
handle's exact bounded bytes are canonical-admitted separately, irrespective
of how its path name was changed concurrently. On other platforms, a
resolved-path metadata check still precedes ordinary open, followed by the
same descriptor check; it cannot guarantee no blocking under pathname swaps.

Watchdog-protected subprocess tests verify immediate refusal for raw and
symlinked writerless FIFOs in MCTI/MCTR modes; a regular linked typed file
still executes under the VM. A Linux stress regression atomically alternates
a candidate symlink between a corrupt regular file and a writerless FIFO
while 32 separate publisher instances check both modes. Every instance
rejects before output and finishes without blocking. The stress test does
not exhaustively force every possible race interleaving, nor does the
publisher authenticate that an input retained the same pathname throughout
validation. Independent canonical-byte checks and atomic no-clobber final
publication remain distinct guarantees.

### Genuine Nonzero Byte Constant Artifact Pilot

The explicit `--seeded-byte-literal` mode admits one verified nonzero
`u8` literal and one to thirty-three matching outputs via canonical MCTI
or MCTR file/stdin. The expanded 34-value current-profile seed table
remains exclusive to single-output sources. Twenty new values were
independently witnessed in a 26..93 no-op prefix scan and rechecked by
source admission and the normative VM. Ten different byte values
`55, 64, 65, 66, 163, 164, 165, 182, 183, 200` have a separately
verified two-output seed table. Third- through thirty-third-output phases
add 21, 24, 18, 19, 18, 21, 21, 25, 17, 20, 19, 22, 17, 24,
19, 20, 19, 21, 20, 25, 21, 21, 19, 22, 18, 22, 19, 20, 19, 20 and 18
independently re-executed
distinct byte values, respectively. All 26 reviewed phases for counts
three through fourteen and sixteen through twenty halt with equal nonzero
bytes. Fifteen outputs have 25 verified phases; phase 20 is excluded.
Twenty-one outputs admit 25 of 26 phases: phase fourteen fails, while
20 distinct byte values remain.
Twenty-two outputs pass all 26 phases, retaining 25 shortest distinct
byte witnesses. Twenty-three outputs also pass all 26 phases, retaining
21 distinct bytes after duplicate phases are dropped. Twenty-four outputs
pass 25 of 26 phases (phase seven fails), yielding 21 shortest witnesses.
Twenty-five outputs likewise succeed in 25 phases (not phase seven),
retaining 19 shortest distinct byte witnesses. Twenty-six outputs
succeed in 24 phases (six and seven fail), retaining 22 shortest
distinct byte witnesses. Twenty-seven outputs succeed in 23 phases
(excluding six, seven and eight), retaining 18 shortest distinct bytes.
Twenty-eight outputs pass 23 real VM phases (not five, six or seven),
retaining 22 shortest witnesses; typed/capsule runner proves 63 and 19.
Twenty-nine outputs pass 23 independent real-VM phases (not five
through seven), retaining 19 shortest distinct witnesses; typed/runner
fixtures prove 12 and 25.
Thirty outputs admit 22 of 26 phases (four through seven fail), retaining
20 distinct nonzero byte witnesses; typed/real runner proves 55 and 150.
Thirty-one outputs pass 22 of 26 VM phases (not four through seven),
retaining 19 distinct shortest nonzero values; typed/runner proves 22 and 160.
Thirty-two outputs pass 21/26 phases (not three through seven),
retaining 20 distinct shortest nonzero values, with phase 16 preferred
over later phase 25 for byte 139; typed/runner proves 200 and 15.
Thirty-three outputs pass 21/26 phases (not three through seven),
retaining 18 distinct shortest nonzero values, with shortest witnesses
for repeated bytes 160/164; typed/real runner proves 136 and 158.
Separate VM scans for sixteen through thirty-three outputs and real CLI
fixtures prove 41/194, 6/133, 66/59, 20/6, 192/48, 140/252, 64/18,
251/27, 65/155, 18/44, 196/137, 138/41, 63/19, 12/25, 55/150,
22/160, 200/15 and 136/158 at distinct source positions, respectively.
The admission table retains only the shortest phase per witnessed byte,
not inferred values for untested source lengths.
Each additional `<` changes source position decoding and loader-expanded
guest memory, so reusing an older seed could print the wrong byte. Both
the linear layout admission and independent normative VM must prove safe
code/data separation, exact repeated-byte outputs and zero consumed input.
Raw and version-one capsule publication retains the existing atomic
no-overwrite semantics. General-runner process tests select the current
profile through a capsule; raw graphical source carries no profile ID and
can produce different values under the runner's historical default.
The guest computes the byte without a host-provided result. Other profiles,
unknown literals, zero/thirty-four-or-more outputs, additional effects and
arbitrary arithmetic reject.

### Signed/unsigned byte identity-cast artifact publication

A distinct `--identity-byte-trace` canonical MCTI/MCTR file/stdin mode
verifies exact eight-bit `IntegerBitcast` SSA aliases of the most recent
successful input, preserving source spans and identity while emitting no
opcode for the casts themselves. The independently checked bridge emits
real input, output and halt instructions only; all old aliases invalidate
at each later read. The publisher recomputes exact successful-byte
output and consumption under two normative VM patterns, with the same
4096-code-cell bound, independent layout/profile check and atomic
no-clobber raw/capsule framing. Legacy echo, latest-read, initial-zero
and zero-prefixed modes reject casts without the explicit opt-in.

This realizes no host guest computation, byte-register storage, EOF/error
handling, branch flow, arbitrary C lowering or callable guest ABI.

### Zero-prefixed successful-byte artifact publication

The distinct `--zero-prefixed-byte-trace` mode accepts canonical MCTI or
MCTR file/stdin only when it contains an independently validated zero
constant SSA, one or more leading same-SSA byte outputs, followed by real
byte inputs and outputs of only the most recent input SSA. The initial
zero comes from the real VM accumulator, not host evaluation. The target
contains actual Malbolge output/input/halt cells, with the same 4096-cell
maximum. A post-read output of the original zero SSA is explicitly
rejected as unsound without guest memory. The canonical typed adapter
reconstructs exact MCTR provenance; the separate publisher re-decodes and
re-encodes the ternary target before any artifact write. Two distinct
successful-byte VM patterns confirm literal zero prefix, latest-read
output order, exact input consumption and termination. The existing
atomic no-clobber raw/capsule publisher is unchanged. The opt-in prefix
cannot mix with any other canonical mode or machine-op tokens.

Real MCTI/MCTR split-wire tests require the target path to remain absent
while a producer holds the stream open, both with partial and complete
canonical bytes. Publication occurs only after actual EOF and complete
independent admission.

This is not arbitrary constant lowering, I/O EOF handling, callable guest
ABI, or general dataflow/control-flow code generation.

### Initial-zero typed and ternary source publication

An explicit `--initial-zero-output` prefix for `--typed-file`,
`--ternary-file`, `--typed-stdin` and `--ternary-stdin` enables the
independently admitted `MaterializeU8(0)` plus one or more same-SSA guest
byte outputs and void return. The VM starts with accumulator zero; the
verified graphical code executes only actual output operations and halt.
No source operation is executed by host software. MCTI first undergoes
full canonical module admission, typed-source projection, canonical MCTR
re-encoding and independent re-decoding. Both wire kinds are then checked
by the same independent zero-output bridge, real VM empty/extra-input
termination and exact guest-output oracle, and the existing atomic raw or
capsule no-overwrite publisher. This differs deliberately from successful
byte-input preflight: zero output consumes no input and rejects any extra
source effects. The CLI grammar makes this flag mutually exclusive with
`--latest-byte-trace`, leaving default strict echo unchanged. An external
MCTI/MCTR zero-output stream test checks that partial and completely written
canonical wires remain unpublished until their producer supplies EOF; after
closing the pipe the exact independently verified source is published.

Only a bounded initial-zero constant is implemented: no general nonzero
constant materialization, guest C ABI, libc, dataflow, EOF or C compilation.

### Canonical wire streaming publication

The verified file emitter now has explicit `--typed-stdin` (MCTI) and
`--ternary-stdin` (MCTR) source modes, with optional preceding
`--latest-byte-trace`. Each takes zero path operands and reads up to
1,048,577 bytes through standard input, rejecting empty wires and byte
counts above 1 MiB before parsing or publishing. The input producer must
close the stream to supply EOF. Neither regular-file mode accepts FIFOs;
streaming is deliberately opt-in so callers cannot accidentally block on a
path that merely looks file-like.

Both streams rejoin the *existing* canonical module/ternary decoder,
profile admission, independently re-encoded position-sensitive source,
normative VM execution and two deterministic successful-byte input checks.
Raw and capsule outputs reuse the original staged no-overwrite publisher.
External process regressions compare stdin and regular-file output bytes,
reopen capsules, execute the generated source under the real normative VM,
and reject empty, oversized, malformed, wrong-kind and trailing-option
inputs without final artifacts or overwrites. This is a bounded producer
interface, not a generic guest runtime, C compiler or unbounded stream
transformer; it does not implement EOF I/O semantics inside the guest.
An additional fragmented-input process fixture feeds a partial canonical
MCTI header, verifies no output path exists while the producer keeps the
pipe open, supplies the rest in single-byte writes, then closes the pipe.
Only after EOF does the publisher create target bytes independently equal
to typed-module lowering. This demonstrates complete-source publication,
not partial stream execution.

### Direct canonical typed-IR publication

The same `malbolge_layout` executable now exposes explicit `--typed-file`
mode for canonical `MCTI` version-one typed modules. The original default
continues accepting only one zero-argument void adjacent successful-byte
echo function. An opt-in `--latest-byte-trace --typed-file` mode supports
repeated output of the latest read and ignored intervening successful
inputs. Valid SSA output from an older overwritten read still rejects.
The file is checked as a regular nonempty bounded input at most 1 MiB,
restored via canonical typed-IR admission, projected/lowered by the existing
typed-echo adapter and independently encoded into canonical MCTR source.

The publisher does **not** trust the adapter's Malbolge layout directly:
it separately decodes the generated MCTR and uses the original ternary
byte-trace bridge to re-derive code, requiring identical bytes, execution
witness length and exact target-profile identity. It then applies its
ordinary normative VM reachability and two successful-byte I/O traces,
optional canonical capsule wrapping and atomic no-overwrite artifact
publication. Process tests compare strict and latest-read direct MCTI
output byte-for-byte against independent MCTR-file publication, reopen
published raw/capsule payloads and verify real VM output/consumption, and
reject malformed input, profile mismatch, stale-SSA use, oversize and
occupied output paths. A second integration test executes the directly
published MCTI capsule through the real `malbolge --input-stdin` process,
requiring exact repeated byte output for input 0, 255 and 128. Invalid
mode order, absent typed path and mixed trailing machine tokens are refused.
This closes one artifact-adapter integration gap, not arbitrary C lowering,
guest-runtime ABI, EOF or I/O failure semantics.

The typed-file publisher remains bound to the original canonical MCTI-v1
`malbolge-2026` profile, unlike the lower-level layout library which admits
five registered VM identities. Selected historical/immutable profiles
fail before source lowering and publication, rather than silently replacing
the typed source's profile. Current-profile strict/latest-read capsules
are independently reopened and executed by the normative VM and real
binary-stdin runner. A physical source-capacity regression publishes an
exactly 4096-cell MCTI trace and verifies all 4094 identical byte outputs;
adding a single output cell fails without a final file.

### Independently verified bounded four-output guest arithmetic

Four source-distinct C output effects can now select a bounded four-write
Malbolge grammar, with each relocated `p`/`*` effect followed by a real
`<` instruction. The bridge searches prefix phases below twelve and
no-op strides of at most eight per write, using a loader-memory tail cache
only to reject impossible proposals. Exact positional decoding, four
out-of-source and distinct writes, and two normative VM input replays
remain mandatory before the artifact is accepted. The independent file
publisher re-decodes the complete source and enforces the same structural
bounds without trusting the proposer. The source-derived four-iteration
Fibonacci probe emits `18 3e 38 12` under both input streams; the older
exact `T=4>` capsule is preserved. Other streams may still be unsupported;
this is not general Malbolge runtime arithmetic or a complete guest linker.

### Bounded source-backed revisiting execution admission

A separate opt-in library gate, `admit_bounded_revisit_layout`, checks a
complete caller-supplied graphical source against a single input-specific
normative VM execution witness. The ordinary `LinearOpcode` encoder and
forward-only automatic padding planner are unchanged.

The gate requires exact canonical profile identity, 2..4096 loader-valid
source cells, at most 512 guest transitions and supplied input bytes, an exact
ordered code path
ending in halt, and independently expected guest output and successful byte
consumption. It checks every fetched guest C address, captures D and
post-step XLAT2 encryption addresses, requires at least one actual repeated
code address, and fails closed on any discrepancy.

There is no guessed guest branch or host-performed output. One accepted
input does not authorize any other stream.

A finite 104-cell fixture loads on both canonical profiles, executes `j`
and a forward `i`, reads and outputs one binary byte, and performs a genuine
backward `i` transfer that revisits code positions 77..92. The first pass's
`InputWord` and `OutputByte` cells become inert after their real XLAT2
mutations; the second pass's jump reads a distinct D word and exits to a
real halt. All 35 steps and exact D/encryption positions are pinned, with
NUL, 128, 255, and extra unread input vectors. Empty input separately
produces the selected profile's EOF-word low byte with zero consumed bytes.
Negative witnesses cover profile drift, malformed graphical source,
loader-valid backedge tampering, forged paths, premature witness end,
incorrect output/consumption, a strictly nonrevisiting valid program, and
input/path size overruns. See `tests/bounded_revisit_layout.rs`.

This completes only one finite machine-control **verification** prerequisite.
It neither synthesizes a backward layout from ternary IR, nor implements
runtime C comparisons, mutable local storage, repeated `getchar`, EOF
branches or the accepted mutable checksum program.

### Remaining implementation

Map admitted typed ternary operations and runtime/heap helpers onto real target
instructions, solve data and code placement with self-modification constraints,
handle jumps/calls and control-flow labels, prove admissibility and runtime
behavior of complete code-state transitions, and publish verified final capsule
or raw `.malbolge` artifacts with source maps. This work remains active.

## Invariants

- Layout solves address-sensitive decode and self-modification constraints
  reproducibly and emits only verifier-accepted `.malbolge` for the declared
  profile.
- The stage has deterministic input/output form, rejects malformed or
  unsupported input explicitly, and preserves source/profile provenance needed
  downstream.

## Failure Behavior

Malformed IR, unsatisfied proof obligations, impossible layout, or unsupported
profile requirements fail closed before emitting accepted target code.

### Six loader-controlled arithmetic regions (2026-11-11)

A red-first 32-cell graphical guest alternates twelve real `p` data writes
and twelve outputs while six live `j` relocations read untouched,
source-derived loader words. Its emitted bytes are
`3e 0b 4a 29 5c 32 53 50 3d 0a 49 31` in the canonical
current-profile VM. The independent positional encoder admits the source,
all twelve write addresses are distinct and outside code, and both EOF
and nonempty binary input produce identical output with zero input consumed.

The former five-region proposer rejected this independently admitted source.
A generalized six-region search now recovers exactly the source and the
production twelve-byte byte-stream bridge publishes a VM-verified layout;
a forged expected byte is rejected. Existing shorter-stream search limits
are retained, and search results are never accepted without independent
source and normative VM proof. These fixed guest effects are not dynamic
C branches, arbitrary byte synthesis or a resolution of the original
unmasked Fibonacci `02 59 5f ...` target.

## Verification

- Expected durable artifact surface: `compiler/`, `src/`, `tests/compiler/`.
- Required evidence: golden/round-trip or normalized stage fixtures,
  deterministic hashes where promised, and end-to-end lowering regression cases.
- Prerequisite completion evidence: `ternary-machine-lowering`,
  `canonical-malbolge-target-profile`.

## References

- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Deterministic C Surface And Clang
  Tooling](../adr/deterministic-c-surface-and-clang-tooling.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/verification-trust-boundary.md`

### Quad publisher with bounded extra-write effects

For source-proven four-byte streams, the independent publisher now admits a
closed 94-cell linear grammar with one relocation, up to 30 prefix no-ops,
four real guest outputs, and four to 32 distinct guest arithmetic writes.
The final code cells remain output and halt; no input, jumps, another
relocation or unsupported opcode is admitted. The verifier re-decodes the
actual staged source, re-admits address-sensitive layout and proves every
write lies outside source and has a distinct address. Both empty and
nonempty guest input must terminate with exactly the source-proven bytes.
The five-write `35 c0 09 e3` guest proves the added interleaving grammar;
older four-write witnesses remain supported. Search proposals never publish
without this separate normative VM check.

### Independent publication of bounded four-relocation byte effects

The five-effect source publisher now recognizes a source-independent
nonzero-first byte stream only when its staged source exactly decodes as a
maximum-32-no-op prefix, an initial `j`, five real crazy/rotate-and-output
pairs, three further `j` moves between the pairs, and a final halt. The
publisher independently admits that positional source for the canonical
profile and proves five disjoint data-write addresses outside all source
code before normative VM replay with two different input streams. The
complete five-iteration source-C recurrence now emits `35 08 dc 08 a3`,
where the earlier five-effect fixed whitelist rejected the valid candidate.
The legacy five-byte teaching witness and previously accepted leading-zero
shape remain intact. This is bounded byte-output synthesis, not general
C execution or arbitrary data-pointer control flow.

### Unreachable source cells as valid guest data

A strictly forward `i` jump may skip graphical source cells that remain
behind the executable code pointer, while guest `p`/`*` instructions
subsequently read and write those cells through D. The linear layout now
represents an explicit `SkippedDataByte` carrying its exact graphical word.
This variant must lie in the unreachable gap of a checked forward jump,
not in an executed position. Its word must decode to a *loader-valid*
canonical opcode at its own source phase, even though no VM instruction
fetch ever occurs there. Encoding, independent admission, the data shadow,
source write footprints, and normative VM replay use those same bytes.

A new source-scratch search exploits the extra positional data freedom
without modifying the VM loader or bypassing its input validation. One
complete twelve-iteration masked Fibonacci C program now emits its twelve
expected bytes in 49 normative guest steps. Invalid skipped opcodes and
reachable pseudo-data cells reject during layout. The original unmasked
Fibonacci output remains outside the proved finite search language.
