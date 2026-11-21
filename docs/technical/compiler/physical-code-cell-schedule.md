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
of `Fetch(Decoded(opcode) | Inert)` and `JumpTargetEncryption` effects.
`admit_code_cell_schedule` checks an already-proposed source byte instead.
Both return the resulting physical cell word, fetch count and independently
scheduled jump-target encryption count. The first event must fetch a
loader-admitted source opcode; subsequent events must be in execution order.
A reached `v` cannot precede another event. The finite budget is **64
single-cell effects**, and an address outside the selected profile's memory
is refused. No host state is installed into guest memory.

These functions deliberately **do not** guess whether a jump can reach its
claimed destination, whether a data writer aliases code, or whether the
source compiler's control and arithmetic effects match. Those obligations
remain with actual source-loader and normative VM tracing. Consequently a
proposed phase schedule is a necessary condition, not a sufficient
publication certificate. In particular a second `i` whose target is the
same physical instruction cell needs an explicit target-encryption event.

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
unsupported initial event, and physical events after a halt. All 94 position
phases under current and historical profiles permit repeated `i` fetches
without changing the code word; one explicit target-encryption event then
changes the word by exactly XLAT2.

Reproduce the focused source-loaded and C23 regression checks with:

```sh
export TMPDIR="$PWD/.temp"
.dependencies/rust/1.98.1/bin/cargo.bin test \
  --test compiler_code_cell_schedule
.dependencies/python/3.14.7/bin/python3.14 -B -m unittest \
  tests.test_eof_checksum_pipeline -v
```

## Still Missing for P2

This result fixes a **proposal-level code-version gap** only. A complete
physical linker must prove every `i` operand's actual source-memory version,
all data pointer and accumulator live-ins, signed EOF-to-C32 normalization,
branch arm selection, source phi edges, mutable checksum arithmetic and
`putchar` after EOF. A physical backedge with a matching graphical opcode
does **not** establish a reusable operation or the source C checksum.
EOF-dependent termination and byte-stream correctness require separate
independent guest/source semantic verification.
