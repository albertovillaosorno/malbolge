# Source-Loaded Input-Indexed Code Transfer

## Status and acceptance boundary

Bounded N15 source-backed evidence, 2026-11-21. The source is **not** a
compiled C23 program. In particular, the original mutable EOF checksum still
refuses guest publication: signed C32 `getchar`, checksum arithmetic, phi
copies, its complete branch structure and the EOF loop are not linked.

This experiment combines three already necessary physical mechanisms in one
actual normative VM execution: an exact input-dependent data write, dynamic
pointer relocation using that overwritten state, and a reached `i` jump
into an instruction cell overwritten by the same input. The last step is an
**executed input-selected opcode**, not a predicted decoder or a host-chosen
control path.

## Frozen source and effects

- Graphical source: `DCBA@?>=<;:98hx/v-210/poJ%H`, 27 cells.
- SHA-256: `1e424eeaee058da88ea048133447c3c0e31b0f423a8586a24bc92ff559f48d98`.
- Target: the current `malbolge-2026` N15 profile, 14,348,907 words.
- Construction: change only C24 in the existing exact-byte reentry source
  from `v` to the graphical `J`, which decodes as `i` at C24.
- Step bound: 26 requested normative transitions, with no host guest-state
  injection, preloading of input-derived memory or host-provided output.

The loader seeds M121 and M73 to 7,174,453, the all-one 15-trit word.
The C13 `/` reads a raw input word, C15 `p` writes M121, and C17 `p`
physically stores the **exact raw input** in M73. At C22, `j` reads the
virgin M78=72 and sends D back to M73. At C23, a second reached `j`
reads **the newly written** M73 and makes D equal to `raw + 1` (mod N15).

At C24, the real `i` reads M[D]. For the two witness inputs below that
word is 72, so it encrypts target M72, then fetches **C73** on the next
step. C73 is the same cell written by the earlier C17 `p`:

| Input | C24 data read | C73 decoded | C73 guest effect |
| --- | --- | --- | --- |
| `3d` (61) | M62=72 | `j` | M63=7,174,489 relocates D to 7,174,490 |
| `53` (83) | M84=72 | `p` | M85 changes 7,174,453 to 7,174,373 |

Both paths execute 26 real steps, consume one byte, leave any further input
unread and emit no output. For `3d`, A stays 61; for `53`, the reached
`p` updates A to 7,174,373. Source-loaded instruction decoding and actual
memory read/write trace records distinguish both paths. A code-pointer
branch alone would not prove a C source branch, but here the fetched
instruction and resulting guest state really differ with the input.

## Negative controls and limitations

`tests/compiler_input_indexed_jump_guest.rs` checks original source identity,
code/data aliasing, both distinct opcode/effect paths, EOF and NUL refusal,
and byte `0x23` (35) decoding a no-effect opcode.
Changing the reached C17 `p` to a graphical `o` leaves M73 at its virgin
non-graphical 7,174,453; the mutated guest still jumps to C73, but **cannot
fetch an executable input-selected instruction there**. This isolates the
necessity of the guest data write, not merely its effect on the accumulator.

This exact small physical grammar has no total byte/EOF dispatch. On zero
and true EOF, the C24 jump cannot encrypt its reached target. Other inputs
can terminate at a non-graphical fetched cell or take different, unverified
paths. Two witnessed code options and a branch on raw byte identities do
**not** constitute arbitrary-byte C parity, a valid signed EOF guard or
complete mutable-C control flow. No artifact for the source C checksum was
published.

An independent 15-trit scalar loader recurrence, including the two reached
`p` data writes, also closes the **230 high-byte cases `26..=255`** without
running a host implementation of the source C program. It proves that the
C24 jump can only reach C37 or C73 if it is graphically encryptable:

| High-byte classification | Number of values |
| --- | ---: |
| C24 target is non-graphical, so the jump refuses | 114 |
| C24 selects C37; virgin M37 is non-graphical | 39 |
| C24 selects C73, but raw input is non-graphical code | 45 |
| C73 executes an inert instruction | 29 |
| C73 executes actual `j`, `p`, or `i` | 1 each (3 total) |

Thus **no high-byte case** in this fixed source reaches a guest `/`, `<`,
`v` or `*` at that first dispatched step. This is a finite proof about the
fixed 27-cell grammar only, not a VM-executed 230-stream test or a general
impossibility of conditional input output. Bytes below 26 and true EOF
have separate source-code encryption histories and are not included in
that scalar closure. Real VM controls cover representative positive and
negative paths instead of treating the recurrence as guest execution.
Specifically, byte 27 makes the normative VM fetch non-graphical M37,
whereas byte 29 fetches the non-graphical value written to M73. Each
real guest run terminates on its 26th requested step after one byte read;
subsequent input remains unread. Neither is a source-C guard.

## Reproduction and next real compiler gate

```sh
cargo test --locked --test compiler_input_indexed_jump_guest
python3.14 -B -m unittest tests.test_eof_checksum_pipeline -v
```

A production linker needs to make this input-sensitive code-cell alias safe
for **every** permitted source-C path, prove actual signed C32 input frame
writes, preserve guest A/D and memory versions between blocks, realize
source arithmetic/phi transfers and close a valid EOF-controlled cycle.
This bounded control proof is a possible ingredient, not a substitute for
compiling the unchanged seven-block checksum and matching the five native
C23 `-O0`/`-O2` binary-oracle cases in the normative guest VM.
