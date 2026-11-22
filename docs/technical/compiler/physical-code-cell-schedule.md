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
