# Source-valid two-input guest fold and encrypted halt

## Status and owning contract

Bounded P2 constructive evidence, 2026-11-24, for the open
`parametric-guest-byte-stream-emission` task. The acceptance program remains
`tests/compiler/c-frontend/accepted/mutable_eof_checksum.c`. This experiment
is **not** a translation of that program and does not link any source-C CFG.

The executable regression is
`tests/compiler_c23_saved_input_fold_reentry.rs`. It constructs exactly
135 graphical source cells and admits all 135 against the canonical
position-sensitive source decoder before constructing the normative N15 VM.
Neither guest memory nor stdout is seeded with host-computed input results.

## Physical data path and control route

The guest executes both real reads and a genuine feedback computation:

1. C10 `/` receives the first raw N15 input word; C11 `<` emits its low byte.
   C29 `j` and C30 `p` write `crazy(121, first)` into guest M106.
2. C37 initially executes a positional `o`. Its own code encryption leaves
   value **105** in M37, to be re-read *as data* on the later pointer route.
3. C58/C59 restore the D pointer to its earlier checkpoint. C82 `/` receives
   the second raw N15 input word. The actual four-jump chain C83..C86 reads
   M99=94, M95=97, M98=36 and encrypted M37=105, selecting D=105.
4. C87 `p` reads the previously written M106 and writes
   `crazy(crazy(121, first), second)` back into M106 and the accumulator.
   C88 `<` emits the computed low byte. Equal-valued writes have no VM
   memory delta but still execute `p`, read the saved word, and update A.
5. C89..C93 execute five real `j` instructions, reading M108=103,
   M104=123, M124=126, M127=100 and M101=110. C94 `i` reads the
   unexecuted source-valid M111=81 and enters C82. The earlier `/` actually
   encrypted source byte 35 at C82 to 93, which decodes as `v` on reentry.
   The genuine halt occurs at **96 guest steps** with two output bytes.

All designated pointer-data positions are legal graphical source cells and
are not illicitly injected into the loaded VM. In particular M37 is a
physically encrypted instruction cell, not a virgin or host-written constant.
The source is not specialized to either input, and the guest reads at most
two attempted bytes before its one valid halt.

## Finite independent evidence

- Nine traced input streams include empty, single NUL, single high byte,
  double NUL, mixed high/low, and trailing input. Every trace checks the
  physical code and D-pointer route, both I/O actions, two data writes,
  actual late `p` read, final output and encrypted-code terminal.
- 257 first-input classes (0..255 and true raw N15 EOF) with the second at
  EOF, and 257 second-input classes with the first fixed at byte 5, replay
  a fresh source-loaded VM. Every case checks a **96-step HaltInstruction**,
  input consumption, both output bytes and final M106.
- Independent fifteen-trit scalar crazy arithmetic predicts each first
  saved word and the subsequent fold; the oracle is not the VM crazy helper
  and does not substitute for a physical trace or a Clang C oracle.
- Five source-valid mutations remove the first save, first pointer route,
  second fold, indirect terminal, or terminal operand. A mutation must not
  retain the joint real input, folded state, output and halt witness.
- Three full positive VM executions with one changed input at a time prove
  that the second output and saved fold can differ as either input changes.

The word operation here is **Malbolge crazy**, not C integer `+` or `^`.
N15 raw EOF is neither converted to signed C23 `-1` nor compared as a C
predicate. The physical reentry is a terminal jump, not a repeatable
checksum loop backedge. No source SSA phi/cast/provenance or guest C
return has been authenticated by this fixture. These remain necessary
work for the original seven-block mutable EOF checksum gate.
