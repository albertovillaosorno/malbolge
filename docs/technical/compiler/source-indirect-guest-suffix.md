# Source-Loadable Indirect Guest Continuation

## Status (2026-11-24)

Bounded physical pre-link capability, **not** C23 source compilation.
The unchanged seven-block mutable EOF checksum still refuses guest target
lowering, and P2 remains open.

## Exact problem

In the current 15-trit profile, Malbolge `i` reads `M[D]` as its new
code pointer; the step then increments that pointer before fetching the next
instruction. A source-contained pointer word must itself be an ASCII
graphical byte that decodes to a **legal loader instruction at the pointer
cell's own position**. A proposed target address alone cannot prove that
its pointer word survives source admission. Already-executed code, live
pointer data, and future code cells must also remain disjoint from patches.

`plan_source_loaded_indirect_suffix` makes one narrow preparation reusable:

- It accepts an already source-admitted N15 graphical program and one
  source-resident, candidate pointer-cell position.
- It explores a finite code window in increasing landing-address order,
  with a bounded linear suffix of `o`, `/`, `<`, `j`, `p`, `*` and terminal
  `v`. No recursive branch or `i` may occur inside the suffix.
- It requires `landing - 1` to be a printable graphical source byte **and**
  decode to a valid opcode at the exact pointer-cell position. Protected
  source words inside a suffix may be *executed* only if their unchanged
  bytes already decode to the requested instruction; all other overlaps
  refuse. It re-admits the entire patched graphical source.
- It returns only a candidate source, operand word and target address. It
  never asserts that an `i` is reachable, points D to that word, or executes
  an unmodified, unencrypted code leaf. The caller must independently prove
  those conditions in normative VM traces before any target publication.

Bounds: at most **4,096 source cells**, **32 leaf opcodes**, one finite
landing interval, and **94** possible graphical pointer byte values.
The candidate is deterministic; it does not search arbitrary guest state.

## Physical witness after an actual stateful fold

The reproducible existing 135-cell N15 source starts with the original
C10 input and output, writes a first-input-dependent word at M106 via C30
`p`, reads a second word at C82, and folds both genuine input words using
C87 `p` into M106. C88 outputs the fold's low byte. An actual C94 `i`
reads an unmodified, source-resident M111 operand. Previously that operand
was 81 and jumped to the encrypted C82 halt.

The initial proposal to set M111 to 111 (for C112) **failed** source
admission: byte 111 at position 111 decodes to a forbidden opcode. The
finite placer instead picks **M111=116**, which decodes as `*` when loaded
at C111. The already-reached guest `i` at C94 physically reads that word,
encrypts code cell C116 and continues at **C117**. Unreached C117/C118/C119
can independently encode `/`, `<`, `v`, respectively. No intermediate pointer
word, prior code cell or first/second input fold instruction is modified.

The normative VM executes exactly **98 steps**, reads input at C10, C82
and C117, outputs at C11, C88 and C118, and halts at C119. C30 and C87
still write their original guest-computed values, and M106 remains intact
after the third read. A separate fifteen-trit digit-table oracle verifies:

- `first = byte0` or raw N15 EOF;
- `saved = crazy(121, first)`;
- `fold = crazy(saved, byte1_or_EOF)`;
- output is the three low bytes of `first`, `fold`, `byte2_or_EOF`.

The physical test checks nine differing streams, including empty, truncated,
high-bit, NUL, and unread-suffix inputs. Another **257-case** bounded guest
matrix fixes the first two bytes and varies every third byte plus real EOF;
it checks the same 98-step halt, input consumption, output and preserved M106.
A different leaf `<;v` uses the **same placement function** to output the
existing fold without a third read and halts in 97 steps.

Negative controls show that forcing the desired but loader-invalid C112
pointer fails, protected windows and malformed sources refuse, an alternate
source-valid landing is selected when the first is protected, and mutations
to the actual pointer cell or landed input opcode remove the third-read
witness. The guest paths are not inferred from the scalar oracle.

## Stateful third-input continuation (2026-11-24)

A further complete physical experiment extends the **same** already reached
C94 indirect jump with the 12-opcode suffix `/<oooojpp<*v` at C117..C128.
The planner now allows an existing protected source word to serve as a later
code instruction **without modifying the original word**. The original
M124=126 (`p`) and M127=100 (`*`) are preserved, as is M134=58 used in
first-input setup. Both original input reads and the C87 fold still execute.

On entry at C117, the real third `/` loads a byte or N15 EOF. C118 `<`
emits it, then encrypts its **original source byte 75 to word 104**. At
C123, a physical `j` loads that already encrypted M118=104, sets D=105,
and enters the old C124 `p` at M105=57. That reached crazy operation
writes `crazy(57, third)` into M105; C125 `p` uses the *previously stored*
first/second fold M106 to compute
`crazy(crazy(crazy(121, first), second), crazy(57, third))`.
C126 `<` emits this third-input-dependent fold and C128 `v` halts.

The normative N15 VM terminates in **107 steps**, with exactly three real
reads and four outputs. For input `03 04 05`, output is `03 31 05 3a`;
M105 and M106 contain the two actual computed words. Nine independent
empty/truncated/NUL/high-byte/suffix traces and a 257-case third-input/EOF
sweep match a separate fifteen-trit scalar oracle. Another 514-source
matrix varies **each of the first two byte inputs** independently over all
256 byte values with third input fixed at 0x80, then checks empty and
second-read EOF streams. All maintain the exact real 107-step stateful fold.
Mutating the encrypted pointer site C118 or either C123/C125 operation breaks
the witness; the
planner refuses an attempted overwrite of protected C124. The guest trace,
not the scalar formula, proves the reached code, pointer read, memory writes
and halt. See `tests/compiler_indirect_source_suffix.rs`.

The crucial composition mechanism is **code-to-data reuse**: an earlier
reached instruction's post-encryption byte becomes a later relocation
operand. Requiring all source-resident operands to be globally inert would
miss this valid path. Such a source alias is legal only with separately
verified read/write phases and positional guest semantics; the planner
alone does **not** validate these dynamic facts.

## Fourth input stores through previously executed source code (2026-11-24)

A second **17-opcode**, protected-source continuation uses
`/<oooojpp<*/jojpv` at C117..C133. It preserves the original M124=126,
M127=100, M134=58 and all previously executed code bytes. The first
three genuine reads and their M106 fold remain unchanged. C128 now reads
a **fourth** signed N15 input word, and a reached C129 `j` reads source
M110=52 to relocate D to M53; C130 `o` advances to M54. An earlier
executed C54 no-op encrypted its original 108 to 39, so C131 `j` sets
D=40. Previously executed C40 likewise encrypted 122 to 63, and the
reached C132 `p` reads this **actual** M40=63 before writing
`crazy(63, fourth)` back into M40. C133 `v` halts in **112 steps**.

All 256 fourth-input bytes plus true EOF run to the same halt under the
normative N15 VM; the independent trit oracle checks exact M40 contents,
three previously saved input effects, output, and read consumption.
Detailed trace assertions verify both earlier encryptions, each reached
`j` data read, the final reached `p`, and the halt. Independent mutations
of C128, C131 and C132 cannot preserve the same four-input storage
witness. No source byte is initially replaced at M40 or M54; this is
**time-ordered code-to-data reuse**, not an arbitrary storage alias.

The observable output remains the first, two-input fold, third and
three-input fold bytes. The fourth input is **not output or incorporated
into M106**; its effect is a late physical write to M40 after that code
cell has executed. This is a bounded state-lifetime witness, not a
repeatable guest loop, source local, C23 arithmetic, signed EOF dispatch
or executable mutable checksum.

## Fourth-input computed output and encrypted-code return (2026-11-24)

The same 135-cell source can combine the fourth-input code-alias store
**and** a fifth observable output with a valid nonlinear halt. The
18-opcode suffix `/<oooojpp<*/jojp<i` at C117..C134 preserves original
M124=126, M127=100 and M134=58, including a protected C134 that already
source-decodes as `i`. The first three real reads still build the M106
fold; C128 then reads the fourth byte or raw N15 EOF. Reached C129/C131
`j` instructions follow M110=52 and previously encrypted M54=39; reached
C132 `p` combines the actual fourth input with encrypted M40=63 to store
`crazy(63, fourth)` at M40. Crucially, reached C133 `<` now **emits** its
low byte, rather than halting without exposing the computation.

The preserved C134 source word 58 decodes as `i` in its own source
position. After C133, D=42; C134 reads **previously encrypted** M42=58
(original graphical C42=120, reached as a no-op), indirectly returns to
C59 and traverses earlier encrypted code to an authentic C82 `v` at
step **137**. For stdin `03 04 05 06`, normative output is
`03 31 05 3a 4d` and M40=7,174,477. The fifth byte `4d` is the low byte
of this real fourth-input-dependent computation, not a host projection.

One graphical 135-cell source passes a 257-class fourth-input/true-EOF
sweep, 256 cases in **each** of the first three prior-byte marginals,
five empty/truncated/extra-input controls and a physical trace of the
C42 encryption, C128 input, C132 write, C133 output, C134 pointer read,
C59 reentry and C82 halt. Changed C128, C132 and C133 source opcodes
cannot preserve the same output, state and 137-step halt. The source,
stdin and normative VM have independent scalar 15-trit crazy oracles;
the maximum is 150 VM steps per case. Exact tests are in
`tests/compiler_indirect_source_suffix.rs`.

This is a genuine **fourth dynamic input computation reaching observable
output through protected-source indirect reentry**. It does not extend
M106 with the fourth input, implement C23 signed EOF conversion, link a
source-language branch or loop, or compile the seven-block mutable C23
checksum. In particular, an output of the raw N15 EOF image is **not** a
C23 `getchar()` EOF condition. P2 remains open.

## Fourth input folds the existing cumulative guest state (2026-11-24)

A distinct source-admitted 17-opcode suffix `/<oooojpp<*/jjopv` at
C117..C133 makes the fourth raw input update the **same M106 word** that
already holds all three previous input effects. The original protected
M124=126, M127=100 and M134=58 stay unmodified. M110 changes from 52
to the source-loadable value 117; C129 `j` reads that real operand and
points D to 118. The earlier C118 `<` has already encrypted to 104, so
C130 `j` reads the real encrypted M118=104 and points D to 105. C131 `o`
advances D to 106, and C132 `p` physically reads the preceding M106 fold
and writes its crazy combination with the fourth runtime input. The real
C133 `v` halts after **112** normative N15 steps.

For `03 04 05 06`, the first three inputs give M106=58; the reached
fourth crazy write produces **M106=7,174,483**. The independent
fifteen-trit oracle checks
`crazy(crazy(crazy(crazy(121, a), b), crazy(57, c)), d)` for the four
raw byte/EOF words. Exhaustive fourth-input 256-byte and genuine-EOF
classes, all 768 earlier-input one-byte marginal cases, six truncated or
extra-byte controls, exact reached step/data/encryption traces, and five
source-valid negative operand/opcode controls prove this finite guest.
It consumes four real inputs and preserves the four earlier output bytes
`03 31 05 3a`, **without** emitting the fourth fold yet.

Replacing terminal C133 `v` with a source-loadable terminal `i` yields a
second 139-step valid-halt guest: C133 reads protected M107=55, reenters
already encrypted C56, eventually emits an **input-independent** fifth
byte `57` (hex) at C57, and halts on the real encrypted C82 `v`. All
257 fourth-input/EOF classes retain the precise M106 fourth fold even
through this nonlinear return. The fifth byte is caused by a later
rotation of a fixed prior word, **not** the fourth computed M106 value.
Both paths remain physical proof of four-input cumulative ternary state,
not C23 XOR/add, signed `getchar()`/EOF dispatch, a dynamic branch, a
loop or a source-compiled checksum. The full C23 checksum still refuses
target publication; see `tests/compiler_indirect_source_suffix.rs`.

## Terminal indirect return through already encrypted code (2026-11-24)

The source-loaded 135-cell three-input fold now has a *nonlinear* terminal
continuation. The earlier C94 `i` still reaches the admitted 12-opcode
C117..C128 window, and its C123/C124/C125 data path still updates M105 and
M106 from three **real** input reads. Instead of ending in a fresh C128 `v`,
the new candidate ends in a reached C128 `i`. Its D points at M109=66, a
previously protected, graphical source word (`v` at its own code position).
The actual `i` reads that value, transfers C128 -> C67 and traverses prior
**encrypted** instructions before halting on a real C82 `v` at guest step
123. C82 was earlier reached as `/` and encrypted; the later `v` is neither
an inserted source halt nor simulated host control.

For `03 04 05`, the normative N15 VM consumes three input bytes, emits
`03 31 05 3a`, retains the genuine third-input fold in M106, and halts in
123 steps. A separate fifteen-trit crazy oracle agrees with all 257
third-input/EOF classes, 256 first-input variants, 256 second-input
variants, and four empty/truncated EOF vectors. Every case completes at
the same genuine `v` and consumes precisely the supplied bytes. A complete
trace confirms C128's operand read `(M109, 66)`, C67 reentry, the earlier
C82 input instruction, and the eventual C82 halt. Replacing terminal `i`
with `v` terminates at 107 steps; replacing the protected M109 operand
cannot retain the 123-step path. The leaf placer now admits a terminal
`i` only as an **unverified candidate**; a terminal source word is not
itself evidence of safe guest control, nor does the planner certify the
transferred path.

This is a constructive *control-return* contract for one bounded already
executed physical prefix. It is **not** a fourth read, a reusable loop,
a signed C23 EOF conversion, a variable source branch, SSA/phi placement,
or a C23 checksum. The unchanged seven-block checksum still refuses guest
publication. Reproduction:

```sh
.dependencies/rust/1.98.1/bin/cargo.bin test --release --test \
  compiler_indirect_source_suffix
.dependencies/python/3.14.7/bin/python3.14 -B -m unittest \
  tests.test_eof_checksum_pipeline -v
```

### Fixed-pointer reentry census: extra reads are not computation

A separate finite census fixes the source, original three inputs
`03 04 05`, and a fourth byte `06`, and varies only the terminal `i`'s
preloaded M109 operand over all 94 graphical byte values (33..126).
Eight source-valid values survive strict loading. Under a **180-step**
normative N15 budget, six halt on a real `v`, and three execute a fourth
actual `/` after the C128 `i`. This classifies this exact operand grammar,
not all possible guest code layouts or C control programs.

Two fourth-reading valid-halt paths (M109=83 and M109=118) run for 156
and 161 VM steps respectively, reaching the fourth `/` at encrypted C126.
With the first three inputs frozen, a five-stream EOF, `00`, `06`, `ff`
and trailing-input check verifies byte consumption and preservation of
M106. The first path emits only the four earlier bytes; the second adds
a **constant** byte `c5` (197). Neither emitted suffix changes with the
fourth input in this bounded control family. A fourth `getchar` effect
alone is not a computed checksum, even when a valid guest halt follows.
The finite census and real guest checks are in
`tests/compiler_indirect_source_suffix.rs`.

## What is still missing

This is successful **physical continuation placement** of a bounded
source-loaded computation, not source-C input-loop lowering. `crazy` of
three raw N15 input words is not C23 unsigned XOR/add or signed `getchar()`
normalization. The extended suffix is a linear guest data/I/O segment,
not a phi pad, loop backedge, variable-layout branch or final checksum.
Its source-level operation and data dependencies remain unlinked to the
original C program.

The next P2 linker must prove the complete source-locked operation graph:
source SSA frame writes, typed arithmetic, parallel predecessor copies,
signed EOF comparison, conditional code transfer, a live backedge and the
final checksum byte, with the normative VM and the unchanged five native
C23 `-O0`/`-O2` input controls. A successful bounded leaf alone cannot
retire any of those obligations.

## Reproduction

```sh
.dependencies/rust/1.98.1/bin/cargo.bin test --test \
  compiler_indirect_source_suffix
.dependencies/python/3.14.7/bin/python3.14 -B -m unittest \
  tests.test_eof_checksum_pipeline -v
```

The second command tests the intentional original-checksum refusal and
non-publication, **not** an accepted complete compiler target.
