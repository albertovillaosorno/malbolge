# Source-valid one-revisit guest halt and two-input state

## Status and authority

Bounded P2 implementation research, 2026-11-24. The owning acceptance task is
`docs/todo/open/compiler/parametric-guest-byte-stream-emission.mdc`.
The original complete C23 mutable EOF checksum remains the phase gate. This
record does **not** substitute a finite guest fixture for its executable CFG.

`tests/compiler_c23_eof_code_gate.rs` constructs the exact source, checks the
normative 15-trit profile loader, replays real VM instructions and compares a
separate scalar crazy-word oracle. No host-generated output is attributed to
the guest.

## Why the previous EOF control path did not halt

The existing two-saved-input source can rewrite C49 from its second physical
input: its 256 successful bytes make C49 non-graphical, while raw EOF leaves
C49 graphical. The EOF-only path reaches C57 output, then C60 becomes
non-graphical. Neither side has a valid `v` termination. A distinct source
placement is needed to demonstrate that a **real**, source-loaded indirect
backedge can end on an earlier encrypted halt.

## Constructive 101-cell control proof

The first candidate is an exact 101-byte graphical program. Every unspecified
source cell is encoded as `o` at its own position. Fixed code cells are
C59=`j`, C82=`/`, C83=`<`, C84=`j`, C85=`i`; source data cells M94=81 and
M100=93 are themselves legal positional source opcodes (`v` and `<`).

The first traversal executes a genuine N15 input at C82 and output at C83.
C59 first reads its literal source value 75 and sets D=75. C84 subsequently
reads virgin M100=93, selects D=93, and C85 reads virgin M94=81. Its indirect
transfer enters **C82**, whose original instruction byte 35 was actually
encrypted to 93 by the earlier `/`. At position 82, byte 93 decodes as `v`.
The second C82 visit halts, without another input or output. All 256 input
bytes and true raw EOF terminate via a real `HaltInstruction` at step 87;
no non-graphical-cell termination is accepted.

This is a finite reentry, not an EOF-dependent conditional or an unbounded
loop. It demonstrates a control mechanism needed by a later guest linker.

## Constructive 135-cell two-input state proof

The second candidate extends the source to 135 graphical bytes and preserves
C59/C82..C85 and M94/M100. It adds C10=`/`, C11=`<`, C29=`j`, C30=`p`,
C58=`j`, M106=121 and M134=58. Both explicit data cells also decode as legal
source instructions at their respective source positions.

The first read at C10 outputs at C11. C29 reads its own source value 105,
positioning D so C30 reads untouched M106=121. The real C30 `p` writes
`crazy(121, raw_first)` to M106. This encoding is injective for the 256
successful bytes **and** the distinct N15 EOF word. No source byte is
precomputed from stdin. A second independent `/` at C82 overwrites A with
`raw_second`, and C83 outputs its raw low byte; M106 still retains the first
attempt. C58 reads untouched M134=58 to reset D to C59's source value 75,
restoring the tested C59/C84/C85 branch to encrypted C82. The guest halts at
step 87 after both inputs, both outputs and the first state store.

The two 257-class marginal sweeps fix the other input and verify real guest
output, step-87 halt and M106 state. The first-input sweep also requires 257
unique M106 words and direct agreement with a separately coded 15-trit scalar
crazy oracle. Ten full trace fixtures include empty, one-byte, NUL, high
byte, mixed and trailing-input streams. Fourteen individual source-valid
no-op mutations target each required input/output, write, pointer operand
and transfer; none preserves the combined output/input/store/halt witness.

## Frozen finite evidence boundary

- Profile: repository current N15, 14,348,907-word guest memory; code lengths
  exactly 101 and 135 cells, with explicit positions above.
- Guest budget: at most 90 steps per positive run (87 observed). Two physical
  input attempts maximum, up to two observable output bytes. Separate
  negative mutations have a 100-step budget.
- Inputs: 257 classes per marginal, 10 traced two-input examples, six traced
  one-input examples, and 14 named source-cell mutations; no randomized
  expansion and no unbounded search.
- Success: strict graphical source admission, actual N15 machine steps,
  correct read/write/output provenance, and `HaltInstruction`, never
  `NonGraphicalCell`, at step 87.
- Original C23 gate: `tests.test_eof_checksum_pipeline` was rerun; its three
  checks pass **because the seven-block program correctly refuses unlinked
  publication**. This is not positive checksum compilation evidence.

The first guest output at true EOF is the *raw N15 sentinel modulo 256*, not
C23's unsigned-byte representation of signed `-1`. Neither candidate executes
C23 arithmetic, an EOF predicate, phi transfers, a source-C branch, or the
mutable checksum. The source-cell store is an authentic input-dependent guest
side effect, but its value is not read back for source-C computation. Physical
backedge construction is therefore one necessary capability, not P2 exit.
