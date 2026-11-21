# Physical Code/Data Alias Evidence

## Status

Bounded, source-loaded current-N15 guest evidence as of 2026-11-21.
This tests a real guest-memory alias and a physically reached dynamic input
opcode. It does **not** lower source-C arithmetic, link phi edges, synthesize
an EOF loop, or publish the mutable seven-block C23 checksum.

## First Principle

The Malbolge code image is not immutable. A reached `p` or `*` can write a
source code cell as data **before that source cell is ever fetched**. An
address-phase planner that begins every cell's history with its first fetched
instruction silently drops such effects. The eventual opcode comes from the
**current memory word**, not necessarily its initial source byte. Correct
physical linking needs an ordered memory-version history across both code
fetch/encryption and real data writers.

The chronological order on a single affected code cell may be:

1. Loader installs an admitted graphical source byte.
2. Another reached instruction writes the cell as guest data.
3. A later fetch decodes the *written* word at its physical code address.
4. The fetched instruction applies the correct post-step XLAT2 rule.

This is a necessary code/data alias model, not a replacement for the VM's
full control/data/state transition rules. A planner must not claim that a
proposed data write, jump, or subsequent fetch occurs without independent
source-loaded execution evidence.

## Reached Dynamic Input Witness

`tests/compiler_code_data_alias_guest.rs` loads the exact, source-controlled
81-byte graphical guest at
`tests/compiler/fixtures/code-data-alias-dynamic-input.malbolge` (SHA-256
`77a6174889ce0132b632d7256519b669a3d3b4744ac922413582a5906f1a5630`).
Its first 56 instructions are normal no-ops. These reached effects
are confirmed on empty, NUL, `ff`, and `00 ff` input streams:

| Guest event | Exact physical effect |
| --- | --- |
| C56 `j` | Original M56=78; sets next D to 79 |
| C57 `*` | Rotates original M79=114 into M79=38 |
| C58..C78 | Advances without fetching C79 |
| C79 | Fetches **38**, decodes `/`, and attempts one input |
| C80 `v` | Terminates after 81 committed steps |

The loader-admitted **original** M79=114 decodes `<` at C79, so treating
source bytes as immutable would predict output instead of the physically
executed input. The new M79=38 is graphical and decodes `/` at the same
address. The real VM trace captures the C57 data write (before=114,
after=38), C79's fetched word and input event, C79 self-encryption, and
C80 halt. EOF does not consume a byte, the other streams consume exactly
one, and an extra second byte remains unread.

A separate finite checker covers **all 94 address decoder phases** in both
the current-N15 and historical profiles. For each phase, four pre-fetch
full-width write results (`0`, `32`, `127` and the maximum memory word) must
be accepted when their original graphical `o` source word matches. A later
non-graphical fetch must be refused. This is 752 bounded phase/word
combinations, not 752 guest-executed programs.

The short separate 43-cell witness executes C0 `j`, C1 `*` or `p`, and C2
`v`. Both reached data operations modify initially graphical M41 before
it can be fetched, leaving a non-graphical value. This covers the separate
case where an aliasing data write is safe in an already halted path but
would not be safe to fetch or encrypt without further physical repair.

## Missing Compiler Link

The checked per-cell planner in
`src/compiler/malbolge-layout/composition/code_cell_schedule.rs` now admits
ordered `DataWrite { before, after }` effects alongside reached fetches and
`i`-target XLAT2. The values are full guest-width words, and the planner
rejects stale live versions, out-of-range data, illegal subsequent fetches
and XLAT2 of non-graphical words. Its candidate encoder must still rely on
independent VM evidence of the claimed off-site writer, target and result.
Source-C storage, branch edges, phi copies, normalized signed C23 input and
full live state remain separate physical-linking obligations.

## Reproduction

```sh
cargo test --locked --test compiler_code_data_alias_guest
python3.14 -B -m unittest tests.test_eof_checksum_pipeline -v
```

The Python test's first path independently checks C23 `-O0`/`-O2` controls
and the active unlinked-CFG refusal; it does not emit a C23 guest artifact.
EOF and binary guest observations come from real `ProfileMachine` traces,
not host-side source-program simulation.
