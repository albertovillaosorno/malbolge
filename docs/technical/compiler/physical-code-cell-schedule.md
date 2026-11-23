# Bounded Physical Code-Cell Phase Schedules

## Status

Checked, necessary **physical-linker planning** primitive as of 2026-11-21.
It does not emit an executable CFG, restore guest state, or implement an EOF
loop. The original seven-block mutable C23 EOF checksum remains unlinked;
`tests/test_eof_checksum_pipeline.py` independently checks its native
oracles and explicit compiler refusal.

## Concrete Missing Link

A self-modifying source byte has a lifecycle defined by *reached effects*,
not by a count of apparent code-pointer visits. A normal reached N15
instruction (except `i` and terminal `v`) encrypts its fetched cell once.
A reached `i` instead encrypts its **target** cell. It can be fetched
repeatedly without ever changing its own code word, while the target changes
even when that target is not fetched. A code-site encoder that unconditionally
applies XLAT2 after every visit mis-models both cases.

`encode_code_cell_schedule` in
`src/compiler/malbolge-layout/composition/code_cell_schedule.rs` enumerates
94 graphical candidate source bytes under an ordered, address-bound schedule
of `Fetch(Decoded(opcode) | Inert)`, `JumpTargetEncryption`,
`FetchSelfWrite { opcode, after }` and full-width
`DataWrite { before, after }` events. `admit_code_cell_schedule` checks an
already-proposed source byte instead. Both return the resulting full-width
physical cell word, the initial graphical byte, and separate fetch, guest
data-write and jump-target XLAT2 counts. The *original* source byte must
decode to a loader-admitted opcode regardless of its first scheduled effect.
The first effect can be a fetch, a data write, **or an off-site jump-target
XLAT2** before any fetch. A source-valid `o` can also be the first inert
fetch. Subsequent effects must be in actual execution order. Data writers
bind exact before/after live memory versions (including non-graphical values).
A later fetch must decode a graphical cell; off-site XLAT2 on a non-graphical
cell is refused. A reached `v` cannot precede another event. The finite
budget is **64 chronological journal entries** (a coupled self-write counts
as one entry), and invalid guest-width words or physical addresses refuse.
No host state is installed into guest memory.

These functions deliberately **do not** guess whether a jump or data writer
can reach its claimed target, whether the source compiler's arithmetic
matches the supplied guest data write, or whether a proposed fetch occurs.
Those obligations remain with source-loader and normative VM tracing.
Consequently a proposed phase schedule is a necessary condition, not a
sufficient publication certificate. In particular a second `i` whose target
is the same physical instruction cell needs an explicit target-encryption
event. A same-step code/data self-alias requires whole-path proof of the
instruction's write-before-encryption order.

## Real VM Positive and Negative Witnesses

The 120-character source-locked fixture
`tests/compiler/fixtures/same-site-four-read.malbolge` runs exactly 83
committed current-N15 instructions on each of five distinct byte/EOF inputs:
empty, `00`, `ff`, `01 02 03 04 05`, and `80 00 00 ff`. Four physical
`/` instructions execute at C47; exhausted attempts retain EOF identity,
and a fifth input byte remains unread. The test independently obtains the
*actual* fetched cell, decoded operation, post-step encryption address and
final memory word from `ProfileMachine::from_source`.

- C47 is fetched **seven** times with alternating genuine `/` and inert
  instructions. Its seven real self-encryptions are represented as fetch
  effects; four consume or attempt stdin.
- C49 is fetched **seven** times as a genuine `i`. Its original graphical
  code byte remains unchanged, since the instruction encrypts its jump
  destination instead. A naive seven-self-encryption planner is wrong.
- C43 is fetched only once and receives later XLAT2 writes from `i` at
  another physical site. The phase scheduler carries those as separate
  `JumpTargetEncryption` events and reproduces the guest's final M43 word.
- C46's actual repeated reads and post-instruction XLAT2 phases agree with
  the schedule. For every site, an independently enumerated graphical
  proposal matches the original source byte and normative VM final word.

A negative case removes one **actually observed** off-site encryption from
C43's schedule. Its computed final cell then **differs** from the normative
VM final word; the omitted physical effect cannot be silently called a
verified target state. Separate refusals cover incompatible second-read
opcode, invalid source byte, invalid address, empty or over-budget schedule,
loader-forbidden initial source code, and physical events after a halt.
All 94 position phases under current and historical profiles permit repeated
`i` fetches
without changing the code word; one explicit target-encryption event then
changes the word by exactly XLAT2.

An additional source-loaded two-step N15 guest now proves a missing
first-effect case. A reached C0 `i` targets a future source cell, encrypts
that cell without fetching it, and transfers to an adjacent real `v` halt.
The first physical effect on the target is **only** XLAT2. The scheduler
accepts that initial `JumpTargetEncryption`, reproduces the VM's final word,
and refuses a following forged data write using the stale pre-XLAT2 value.
An independently loaded `o; v` source executes an inert first instruction:
`Fetch(Inert)` is equivalent to the reached `o` and must not be rejected
as an invalid first event. Both regressions were red before the admission
repair. The source loader still rejects initially invalid instructions,
even when a later data write or XLAT2 would mutate them; a printable byte
is not automatically loader-admitted. A proposed XLAT2-only schedule does
not uniquely determine its original graphical byte, so the encoder's
candidate must not be mistaken for the source's observed initial byte.

This repairs source-valid event scheduling, not target reachability proofs,
source-C control, reusable loop state or the complete checksum.

Reproduce the focused source-loaded and C23 regression checks with:

```sh
export TMPDIR="$PWD/.temp"
.dependencies/rust/1.98.1/bin/cargo.bin test \
  --test compiler_code_cell_schedule
.dependencies/python/3.14.7/bin/python3.14 -B -m unittest \
  tests.test_eof_checksum_pipeline -v
```

## Executed Code/Data Alias and Dynamic Input

The separate `tests/compiler_code_data_alias_guest.rs` uses a fixed **81-byte
current-N15** executable graphical source. C56's `j` moves D to M79, C57's
reached `*` changes M79 from 114 (`<` at C79) to 38 (`/` at C79), and
C79 later executes a genuine input instruction before C80 halts. Four
binary/EOF streams agree on actual trace writes, fetched code, input and
termination; a one-cell mutation replacing C57 with `o` instead causes C79
to execute its original `<`, emit a zero byte and leave stdin unread.

The phase planner admits the original source byte and the ordered
`DataWrite(114 -> 38); Fetch(/)` schedule. It refuses a forged before word,
out-of-range guest data, a non-graphical fetched cell and illegal XLAT2 of
such a cell. A separate three-step C0/C1/C2 guest leaves an unfetched
future code cell non-graphical after a legitimate off-site `p` or `*`.
This evidence covers a **real physical code/data alias** beyond XLAT2-only
scheduling, but not physical source-C EOF branching, phi writes or a loop.
See `docs/technical/compiler/physical-code-data-aliasing.md` for the full
bounded witness and its exact limitations.

## Normative Guest-Origin Journals, Including Unchanged Stores

`verify_source_code_cell_trace` in
`src/compiler/malbolge-layout/composition/code_cell_trace.rs` now replays a
source-loaded canonical VM for one binary input and bounded step budget. It
collects a single **source-backed code cell's** fetched instructions,
actual `i`-target XLAT2 and actual `p`/`*` data writes in chronological
order, then checks the source byte, resulting schedule and VM final memory.
It never accepts a caller-supplied effect journal as its evidence.

Changed-memory deltas intentionally omit writes where `before == after`.
The new verifier instead reads the VM's actual data operand and the actual
post-instruction accumulator on *every reached* `p`/`*`. A 59-cell graphical
N15 source with reached `j; p; j; p; v` first makes A=7,174,453 using M41=40.
The second `j` sets D to M57 using M42=56. The second `p` then computes
`crazy(60, 7,174,453) == 60`, writing source-backed M57 **idempotently**.
The normative trace records no changed-value data delta, but the verified
journal records exactly `DataWrite { before: 60, after: 60 }`. Replacing the
second `p` with an inert `o` removes the physical write and is refused as
`MissingEffect`. This proves why a delta-only source-cell journal is
insufficient even when the final memory word happens to match.

A separate two-step source-loaded `i; ...; v` guest verifies an initially
unfetched code-cell XLAT2 event; a truly untouched cell instead reports
`MissingEffect`. A zero/over-budget path is rejected before execution.
The verifier is capped at the preexisting 512 steps and 4,096 source bytes.
Same-step code/data writes now use the distinct coupled event described below;
a standalone `Fetch` is never sufficient to authenticate the data write.
The result is specific to one input and finite guest prefix; it proves neither
source-C arithmetic nor C23 branches, phi transfers, loops or output parity.

Reproduce the independent suite with:

```sh
.dependencies/rust/1.98.1/bin/cargo.bin test \
  --test compiler_code_cell_trace_guest
```

## Input-Site XLAT2 Orbit Census

A distinct exhaustive check of all 94 positional decode phases requires a
loader-valid graphical `/` before considering any source-body backedge. With
no guest data write aliasing that cell, the next fetched byte follows the
same XLAT2 orbit. There are **no** graphical source bytes that decode to
`/` on two consecutive self-encrypting visits at a fixed address. The first
return to `/` has periods 2, 4, 5, 6, 9 or 68, occurring at exactly 2, 4,
5, 6, 9 and 68 of the 94 decoder phases respectively.

Only positions **43** (source byte 74) and **47** (source byte 70), modulo
94, have a two-encryption input phase with an inert intermediate opcode:
`/`, inert, `/`. C47 is the independently executed four-input physical
witness above. A shorter apparent `/` loop cannot simply fetch the same
cell twice without intervening code modification. Longer orbits are not
guaranteed useful: intermediate code may have control/data effects, the
program still needs legal returns, and live D/A/guest storage must match
source semantics. This is a finite graphical-code fact, **not** an
impossibility result for self-modifying C loops or code/data writers.

## Still Missing for P2

This result fixes a **proposal-level code-version gap** only. A complete
physical linker must prove every `i` operand's actual source-memory version,
all data pointer and accumulator live-ins, signed EOF-to-C32 normalization,
branch arm selection, source phi edges, mutable checksum arithmetic and
`putchar` after EOF. A physical backedge with a matching graphical opcode
does **not** establish a reusable operation or the source C checksum.
EOF-dependent termination and byte-stream correctness require separate
independent guest/source semantic verification.

## Same-Step Code/Data Self-Aliases

A reached `p` or `*` can have **C == D**. In that case, the instruction
first fetches the old graphical code word, then uses that *same* word as its
data operand, writes the resulting accumulator into the code address, and
finally encrypts the **new data word** through XLAT2. A separate atomic
`Fetch` followed by a `DataWrite` is incorrect: it encrypts the old word
before the write. The phase planner now represents this coupled transition
as `FetchSelfWrite { opcode, after }`, counting one fetch and one physical
data-write attempt. The returned word is `XLAT2(after)`. An invalid opcode,
out-of-range result, or non-graphical post-write encryption target refuses.
The 64-entry journal limit counts **chronological entries**; one compound
self-write entry represents both its fetch and its reached data operation.

`verify_source_code_cell_trace` reconstructs that compound entry from actual
source-loaded VM steps. The VM reports only its final **net encryption delta**
when data and code writes hit the same address. It does not report a separate
intermediate `memory_delta.data` even when the intermediate data value changed.
The verifier therefore authenticates the fetched code word, the exact data
read at C == D, the post-instruction accumulator, and the final encryption
delta before admitting the coupled event. Idempotent data writes remain
counted even when they have no standalone changed-cell delta.

Two independent source-loaded guests cover this previously rejected case
on both the current N15 and frozen historical target profiles:

- C0 `j`, C1 `p`, C2 `i` initialize A and skip the now-overwritten C41.
  C76..C83 then reach C83 `j`, which aligns D with C84 `p`. The real
  C84 operand/source word is 72; `p` writes the same 72 and XLAT2 encrypts
  it. The 14-step guest halts at C85.
- A different branch begins at C92. C121 `j` aligns D with C122 `*`,
  which rotates its own fetched word 105 into 35, then XLAT2 encrypts
  **35**, not 105. The 35-step guest halts at C123; the independent
  VM net delta and physical final word agree exactly.

Forged self-write opcodes, out-of-width words, and non-graphical written
words refuse. A forged ordinary fetch of the reached `*` site produces a
different final code word and omits its data write. These are real guest
instruction effects, not arbitrary source-C arithmetic, conditional branches,
repeatable loops, or a published C23 checksum. Cross-cell inputs/outputs and
source-SSA/phi-state linkage remain open.

Reproduce with:

```sh
.dependencies/rust/1.98.1/bin/cargo.bin test --locked \
  --test compiler_code_cell_trace_guest
```

## Raw Loader Position Fidelity

`verify_source_code_cell_trace` now resolves a requested code-site address
through the raw source loader's exact six ASCII whitespace exclusions, not by
indexing raw presentation bytes. A formatted source with spaces, tabs, LF, CR,
vertical tabs, and form feeds therefore verifies the **same loaded code cell**
as the equivalent compact source. An address beyond the loaded graphical
source remains out of bounds even when its numerical offset falls within the
longer whitespace-bearing presentation stream. This uses raw loader semantics:
it does not skip annotated-source comments or reinterpret a `#` code byte.

An independent real guest C122 self-rotation source is checked twice, once
compact and once with all six whitespace forms interspersed. Current N15 and
historical VM runs both produce the identical authenticated code-site journal,
initial code word, final word and termination. These checks preserve the
existing byte/step ceiling and do not imply source-C linkage.

## Physical Non-Graphical Code-Cell Termination (2026-11-21)

The modern normative VM can terminate on a fetched *non-graphical* code
word. That is different from an invalid loader source byte: an initially
valid graphical code cell may have been overwritten by a real `p`/`*`
before its first fetch. A verifier that assumes every fetched code cell
has a decoded opcode incorrectly rejects that legal final transition.

`CodeCellEvent::FetchNonGraphicalHalt` now records this exact terminal
fetch without invented decode or XLAT2. The phase scheduler requires the
current word to be non-graphical and the event to be last; a still-graphical
word and any effect after the terminal fetch refuse. The frozen historical
profile does not use the same termination rule and explicitly rejects this
event. The normative source-backed tracer obtains the event only from an
actual `NonGraphicalCell` VM termination.

A 43-cell current-N15 graphical source executes C0 `j`, C1 `p`, C2 `i`,
C40 `o` and then attempts C41. C0 positions D at M41; the reached C1
`p` overwrites originally graphical M41 with a non-graphical full-width
word. C2's actual jump operand M42=39 transfers to C40, whose inert
instruction advances to C41. The fifth attempted fetch terminates
without decode, register advancement or encryption. A real VM trace and
the resulting single-site journal agree on the ordered off-site data
write followed by the terminal fetch and exact final M41 word.

The regression was red first (`InvalidEffect`), then passed after the
verifier admitted the actual termination. Negative controls omit the
required write, invent an initial terminal fetch, append an effect after
termination or claim the modern halt rule under the historical profile.
This closes one physical code/data alias verification gap only. It does
not provide a dynamic C23 branch, reusable EOF loop, guest arithmetic,
source-state linkage or publication of the full mutable checksum.

## Complete Source-Code Image Journal (2026-11-21)

`verify_source_code_image_trace` now uses **one** bounded, normative
profile VM execution to inspect the entire loaded source-code region,
rather than replaying the same binary stream separately for each code
site. For every reached instruction, it gathers all in-range fetched,
written and encryption-target cells, deduplicates same-step aliases, and
appends chronological effects through the existing single-cell event
checker. Every touched site must pass `admit_code_cell_schedule` against
its original loader-admitted byte and its independent final VM word;
every **untouched** site must retain that initial source byte. The output
is address-sorted and preserves exact step-budget or termination status.
Raw input whitespace follows the normative six-byte C-locale predicate.
No arbitrary loader-expanded word is claimed to be a source code site.

The tests use a real 81-step N15 future-code mutation (C57 `*` changes
C79 from output to input), with independent single-site and full-VM
comparison; a real 120-cell, 83-step four-read physical guest with seven
C47 input-site fetches, seven unchanged C49 `i` fetches and true off-site
C43 jump-target encryption; original/whitespace-rich byte-for-byte
journal parity; a historical C0/C1 halt with untouched C2/C3 source
suffix; and a real non-graphical C41 terminating fetch after an off-site
C1 `p` write. Oversized budgets, invalid input code and source lengths
refuse. The four-read trace is a budget-limited prefix, not a proved
source-C iteration or arbitrary stream. One replay prevents independent
per-site executions from accidentally combining different guest paths,
but still establishes **physical image consistency only**: no source-SSA
arithmetic, phi-transfer, signed-EOF branch, or complete mutable C23
checksum linkage follows from this local verifier.

To reproduce the focused image checks:

```sh
.dependencies/rust/1.98.1/bin/cargo.bin test \
  --test compiler_code_image_trace_guest
```

## Loader-Expanded Physical Cell Phases (2026-11-22)

The previous per-cell schedule required an original graphical, loader-admitted
source byte. That is correct for code positions inside the source image, but
not for a future instruction or data operand at an address initialized by the
Malbolge loader recurrence. Its initial value can be any full-width guest
word. A source-only schedule therefore cannot authenticate a later off-site
`p`/`*` store, `i`-target XLAT2, or attempted fetch at such an address.

`admit_loaded_code_cell_schedule` now shares the original chronological
phase rules but accepts a checked initial full-width memory word, independent
of any graphical source-byte encoding. The original
`admit_code_cell_schedule` retains its strict loader-valid source-byte gate.
This separation prevents a solver from declaring a non-graphical source byte
valid merely because a future write would replace it. The new
`verify_source_expanded_code_cell_trace` always obtains the **actual**
loader-initialized word from `ProfileMachine::from_source`, replays genuine
execution, reconstructs the site's reached chronological effects and checks
its final word. Missing effects, invalid initial words, forged opcodes,
stale pre-write values and invalid jump-encryption targets refuse.

`tests/compiler_expanded_code_trace_guest.rs` contains two concrete normative
witnesses. First, a three-source-cell `j;(p|*);v` guest uses C0 `j` to address
loader-expanded M41. Both current N15 and historical profiles execute three
instructions, write M41 through a real `p` or `*` and halt. The checked
full-width initial value, exact data write and resulting word agree with the
normative VM. The old graphical-source planner correctly refuses this site.
Second, a six-cell N15 `j;i;o;o;o;o` guest has loader M41=63, M63=36 and
M64=7,174,471. A reached C1 `i` jumps via M41, encrypts unfetched expanded
M63, and C64 then attempts to fetch its still non-graphical word. The new
trace checker verifies both off-site XLAT2 and the genuine terminal fetch;
forcing XLAT2 on the non-graphical M64 refuses.

`verify_source_expanded_code_cells_trace` also verifies a caller-selected,
strictly increasing set of 1..=128 expanded memory positions in **one**
source-loaded VM execution. All initial words are captured before the first
step and every cell's event order and final state is independently checked.
The singleton `verify_source_expanded_code_cell_trace` now delegates to the
same batch authority. Duplicate, descending, source-overlapping, out-of-range
or excessive site sets refuse before execution. Including an untouched site
or ending the guest trace before that site's first effect refuses the entire
batch with its exact offending address. The six-cell indirect `i` guest checks
M63 and M64 together, including raw-source whitespace invariance, and agrees
with both separate singleton witnesses.

A third 15-cell N15 guest, `"(=&_@?>=<;:987C"`, demonstrates actual
inter-site **data-dependent control**, rather than two independent events.
C0 `j` positions D at expanded M41; C1 `p` changes its live value from
7,174,467 to 7,174,480. The source-loaded M42 is 40, so C2 `j` restores
D41; C3 `i` now reads the previously written M41 and encrypts expanded
M7174480, initially 67. A non-graphical fetch from M7174481 ends the
five-step guest trace. The multi-site verifier checks actual physical
write, subsequent dependent branch and target encryption in a *single*
execution; it refuses a false assertion that M42 was data-written. This
witness verifies a concrete guest branch, not a source-C CFG edge.

This is a bounded necessary checker for **requested expanded cells** in
one source-loaded trace of at most 512 steps and 4,096 source bytes. It is
not a planner that proves proposed guest control or C semantics, and it does
not claim the original seven-block mutable C23 checksum has been linked.
The missing compiler stage must still emit and verify the actual arithmetic,
phi writes, EOF edges, state restoration and output under the normative VM.

Reproduce its real-guest witnesses and the unchanged P2 refusal with:

```sh
export TMPDIR="$PWD/.temp"
.dependencies/rust/1.98.1/bin/cargo.bin test \
  --test compiler_expanded_code_trace_guest
.dependencies/python/3.14.7/bin/python3.14 -B -m unittest \
  tests.test_eof_checksum_pipeline -v
```

## One-Pass Source and Expanded Effect Footprint (2026-11-22)

`verify_source_physical_image_trace` now collects the **entire reached
physical effect footprint** of one source-loaded VM prefix, without trusting
an external list of expanded sites. Every source cell is reconciled against
its graphical loader byte, including untouched cells. For addresses outside
the source, the first actual fetch, data-write operand or encryption read
provides the live *pre-effect* word. The verifier then replays all reached
`p`/`*` stores, fetched instructions and off-site `i` encryptions through
`admit_loaded_code_cell_schedule`, checking each final word against the
normative VM. An unchanged data write remains a real physical effect.
Pure data reads do not create an effect-site entry, but are included in the
ordered operand-read journal described below. Source and expanded effects
come from the **same** execution; expanded sites are address-sorted.

The first source-backed witness is the actual `/;j;p;j;p;v` guest from the
byte-exact input store. Four EOF/binary streams each produce two expanded
physical writes, independently matched against the older selected-site
verifier. The second witness, the 15-cell guest with an input-independent
written indirect jump, exposes **all three** physical effects without a
supplied site list: M41 data write, M7174480 `i`-target XLAT2, and the
terminal non-graphical fetch at M7174481. An original source-only guest
has no invented expanded effects. Invalid source/step budgets refuse.
The first regression failed to compile before the implementation existed.

The finite envelope is 4,096 raw source bytes, 512 steps and at most 128
distinct reached expanded sites; overflowing that effect budget refuses
rather than returning an incomplete footprint. This authenticates actual
physical effect chronology for the **observed bounded prefix** only. It
does not prove source-C operation linkage, proposed unreachable paths,
signed EOF normalization, full checksum arithmetic, or reusable loop state.
The original seven-block source C23 checksum remains unlinked.

```sh
export TMPDIR="$PWD/.temp"
.dependencies/rust/1.98.1/bin/cargo.bin test \
  --test compiler_code_image_trace_guest
```

## Ordered Guest Data-Operand Reads (2026-11-22)

The complete physical image additionally returns `data_reads`, an ordered
journal of real `j`, `i`, `p` and `*` data-operand reads. Each entry records
the zero-based VM step, fetched code address, actually decoded opcode,
selected guest D address, exact read word and the most recent **earlier**
physical `p`/`*` store step at that same address, if one exists. The current
instruction's own data write is recorded *after* its operand read, even when
C and D alias. A store is considered reached even when it is idempotent.
The optional predecessor identifies only the last **data store**: it does
not assert that intervening XLAT2 instructions left the word unchanged.

A new source-locked red-then-green regression uses the actual N15
`"(=&_@?>=<;:987C"` indirect-branch guest. It observes C0 `j` reading
M0=40, C1 `p` reading the original expanded M41=7,174,467, C2 `j`
reading M42=40, and C3 `i` reading the *new* M41=7,174,480 with its
`last_data_write_step` bound to C1's real step 1. The other reads have
no prior data-store predecessor. Separate three-step `j;p;v` source tests
execute under both current N15 and historical profiles and agree with
whitespace-padded raw source. A one-step prefix retains only the first
read and no premature data-write site. These are observed physical
read-after-write relationships, **not** C23 typed variable identities,
source-SSA control edges or an executable C checksum loop.
EOF normalization, source branches and mutable checksum linkage remain open.

## Physical Fetch Versions and Last-Effect Provenance (2026-11-23)

The same one-pass `verify_source_physical_image_trace` also records every
actual code fetch in `code_fetches`, alongside its already ordered `data_reads`.
Each entry carries the step, exact physical address/word, last prior `p`/`*`
data-store step and last prior word effect (`DataWrite` or `Encryption`). The
new effect tag distinguishes a direct data-store predecessor from a later
self-encryption or off-site `i`-target XLAT2. The last data-store index is
retained separately: XLAT2 does not erase its history, but it may change the
word that a later fetch or operand read actually sees. The collector records
even idempotent stores/encryptions in temporal order. It takes the executed
instruction's operand and code word from the normative VM, never a proposed
or simulated C state. A code fetch and data read precede their own step's
write; a same-step alias stores first and encrypts afterward. Terminal
non-graphical fetches are retained without inventing a subsequent XLAT2.

The real 81-cell N15 alias guest has C57 `*` writing source C79, which is
later fetched at step 79 with physical word 38 (`/`) and an authenticated
last effect `DataWrite(57)`. A source-valid mutation at C79 instead rotates
into a non-graphical word: its genuine step-79 terminal fetch retains the
same prior data-write identity, with no fictitious post-halt encryption.
The 120-cell source with a genuine repeated read site C47 proves seven
fetched instruction versions, each after its predecessor's XLAT2. Seven
reached C49 `i` fetches, by contrast, remain unchanged because `i` encrypts
its destination, not necessarily its own code word. The expanded indirect
jump's C3 `i` data read separately records C1's earlier physical store.

The complete-prefix bounds remain 512 steps, 4,096 raw source bytes and 128
expanded effect sites. These read/write temporal facts are necessary input
for a source-code layout certificate. They **do not** establish that the
physical data value implements a C32 variable, that guest branch conditions
match source conditions, or that an unvisited CFG edge can be reached. The
unchanged source-C mutable EOF checksum still lacks that physical linkage.


### Off-site XLAT2 before a later physical fetch

A separate three-step, 100-cell source-loaded N15 guest now exercises the
**other order** of code-cell effects. Reached C0 `i` reads M0=98,
encrypts source cell C98 without fetching it, then jumps to C99.
Reached C99 `i` reads M1=97 and transfers to C98. The third real fetch
loads C98's *encrypted* word 81, not its loader byte 64; the fetch journal
links that word to `Encryption(0)` with no preceding data store. The target
executes as an inert `J` and leaves no guest output. If C99 is changed to
an authentic `v`, the same first XLAT2 still occurs, but the VM halts after
two steps without ever fetching C98. The verifier records the code-cell
XLAT2 effect but no invented fetch predecessor or later instruction.

This isolates the missing compiler-relevant ordering (`i` target encrypted
before subsequent fetched code) using two independently actual guest jumps.
It does not assert that an unexecuted C branch or phi transfer exists.
