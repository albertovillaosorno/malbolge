# Source-Loadable Indirect Guest Continuation

## Status (2026-11-24)

Bounded physical pre-link capability, **not** C23 source compilation.
The unchanged seven-block mutable EOF checksum still refuses guest target
lowering, and P2 remains open.

## Source-identified physical output effect addresses (2026-11-24)

The opt-in **verify_source_return_branch_io_effect_anchored** composes the
existing exact source-known branch/I/O verifier with independently replayed
source operation/effect anchors. Each reached normative VM output must decode
as an actual output instruction at the proposed **canonical source output
effect address**; matching stdout bytes without such an anchor cannot pass.
The output-site receipt is additionally replayed in the **same source branch
CFG walk**, with the actual physical transfer's full-I/O cut. Its source and
physical traces must agree on all reads, I/O events, output, consumed bytes
and termination. This avoids claiming that independently plausible source
output and source branch paths establish one executable source-C program.

The 132-cell source-authenticated C23 first-read classifier still passes its
narrower real guest pointer and source branch checks on EOF/NUL/high-byte
classes. All five pinned EOF, one-byte and multiple-byte streams now
independently refuse the strict effect-address option: the real C57/C128
class-marker outputs have **no placed C23 checksum output effect anchor**.
The source checker reports **UnexpectedGuestOutput** before pretending those
markers came from the checksum's source putchar. This is a negative physical
witness and a necessary verifier boundary, not a positive full-output linker;
the original seven-block checksum remains unlinked and unpublished.

## Source branch and complete I/O must agree on one path (2026-11-24)

The stricter opt-in `verify_source_return_branch_io_ordered` first replays
both source input and guest-written pointer, verifies complete source return,
source-known branch arm, and exact physical read-before-transfer ordering.
It then checks **the same bounded source CFG walk** against the actual
normative guest output bytes and ordered input/output events. The exact
physical transfer step also fixes a **cut in the full I/O timeline**: the
source conditional must occur after the same number of total input *and*
output events. Checking only the number of earlier reads could mistakenly
accept a guest `i` that executes before a required source output, or after
an extra early output, when the final bytes happen to agree. The existing
C114 classifier executes after exactly one I/O event (the first C53 read).
Synthetic source-only controls independently prove a legal conditional after
one read **and one prior output**, rejecting cuts before that output even
with identical final bytes. This still does not prove source operations ran
in the guest. An independent branch-matching source path and a different
output-matching source path are not interchangeable. If output-site
identities were authenticated in the source prefix receipt, the joint walk
also requires those same identities.
The source branch binding also requires **both** claimed arm landing
addresses to belong to the guest probe's admitted physical landing set,
even though any one finite execution can verify only its selected arm. A
real C45 successful-byte branch with an admitted set omitting C126 now
refuses a two-arm source binding; the narrower single-landing physical
pointer witness still passes. The older direction/chronology methods remain
usable for deliberately partial physical control experiments without
claiming source output parity.

A source-only positive for the original C23 checksum admits true first
EOF with one final zero byte, as well as successful NUL, odd and high-byte
reads followed by EOF and their known checksum output. Swapped arms, a
premature output, wrong output value and wrong source output ordinal refuse.
These are **synthetic source-walk controls**, not real checksum guest runs.
On the actual 132-cell guest, empty input and one byte followed by EOF
still pass the earlier reached C114 `i` branch/chronology gate, but the
joint gate rejects its `0x1e`/`0x9a` class markers: those bytes are not
the source checksum and the physical guest's output chronology does not
implement the C23 output after EOF. Streams with two successful bytes
continue to fail the earlier complete-return gate because the C loop
requires another read. No complete C23 checksum artifact is published.

This is a necessary **joint finite source control/I/O check**, not proof
that the guest calculated the source predicate, C32 arithmetic, signed
SSA locals or backedge/phi updates. The physical prefix must separately
bind output effect code cells and operand provenance before publication.

## Physical input/branch execution chronology (2026-11-24)

A stricter opt-in `verify_source_return_branch_ordered` builds on the
source-known direction and complete-return gate. It counts **actual input
trace indices before the reached indirect-transfer step**, requiring exactly
the source guard's declared `after_inputs` reads. The input address is not
its execution timestamp: on successful-byte runs the second C23 `getchar`
has code cell **C101** but executes at normative VM step **171**. The
first input executes at step 53; reached C114 `i` executes at step **114**,
so the first source guard is genuinely between the two reads. An arbitrary
hypothetical read at step 101 would instead be counted before C114 and
invalidate the same source-guard timing claim.

Actual EOF, NUL-then-EOF and high-byte-255-then-EOF guests pass this
chronology and branch-direction gate. The original checksum with two
successful bytes still fails the independent full source-return check.
This is **necessary guest input/control order**, not a guest C23 comparison,
C32 storage, executable source backedge, correct output or full checksum.

## One source-known EOF guard bound to a physical guest arm (2026-11-24)

`verify_source_return_branch_bound` now adds a conservative **source/guest
arm parity** requirement to the previously joined source input/return and
physical indirect-pointer proof. It rederives the canonical C23 predicate
from source-known operations in the **same bounded CFG walk** and requires
an exact nominated `(function, block, after_inputs)` conditional. The real
indirect destination must match the source condition's true or false arm.
Any complete matching-input source return path with a missing, unknown,
repeated or incompatible nominated branch fails closed; search exhaustion
is an error, not evidence of a match.

For the unchanged seven-block mutable checksum, the first C23 `getchar`
in block 0 feeds the source `current != EOF` guard in **block 1** after
one input observation. The two source-conditioned guest destinations are
C45 for a successful byte and C126 for true EOF. This authenticates the
actual N15 guest C53 `/` -> C82 `p` write to M143 -> C114 `i`, including
EOF, NUL and high-byte 255 followed by EOF. All 256 byte classes and EOF
pass the *source-known* branch-direction check; physical positive tests
replay those three representative guest inputs. Swapped arm mappings,
wrong guard block, wrong read occurrence, source-unknown conditions and
guest halts before the C23 source's required next read refuse. The
previous 257-class physical pointer census remains a separate test.

This is **one finite source-known branch direction**, not general C
branch computation in Malbolge. It still does not show a guest-produced
C32 signed frame value, physical comparison arithmetic, all source CFG
edges, live backedges/phi copies or checksum output. The guest emits
class markers and the full C23 checksum remains unlinked and unpublished.

## Source-typed input to physical indirect pointer (2026-11-24)

`SourceWrittenIndirectGuestVerifier::verify_source_bound` now joins two
**independently replayed** normative VM obligations for an *identical* N15
source and finite stdin: the existing source-typed input/CFG-prefix checker
and the guest-written pointer/indirect-control checker. The caller supplies
specific canonical `(function, block, ordinal)` input operation identities,
not guest code addresses or an already accepted source proof. The checker
rederives each reached input transition index and physical code position
from the source-verified observations, then requires **exact equality** with
the guest pointer's complete `/` ancestry. It returns both trace receipts
only if VM halt steps, input consumption and output also agree. Duplicate,
missing or unreachable source identities and alternate physical source
images refuse.

The frozen *original seven-block C23 checksum* typed IR provides the source
input identities for this necessary-condition test: the first `getchar` at
block 0/ordinal 1 is reached as C53 `/` and supplies an actual C82 `p`
write to M143, used by reached C114 `i`. A later source `getchar` in block
5/ordinal 2 can execute at C101 without feeding that earlier pointer. The
real empty, NUL and high-byte/trailing-input executions preserve the
C45/C126 physical destinations and 119/175-step halts. Wrong source
operation identity, duplicate or empty selections, wrong input anchor,
wrong arm and source-image mismatch refuse. Regression:
`tests/compiler/source_input_cfg_order.rs`.

This **does not** establish that the C23 `current != EOF` condition selects
the guest arm, nor that a signed input is converted and written into the
source frame, that checksum arithmetic executes, or that a source backedge
or phi transfer occurs. The guest still emits class markers, not the source
checksum. A genuine complete source-C23 artifact still cannot be published.

The stricter `verify_source_return_bound` option also checks a **complete
source CFG input/return path**, rather than accepting any genuine guest input
prefix. With the same original checksum and M143 pointer, empty input and a
NUL byte followed by EOF satisfy this extra *source input-order* obligation.
On input `00 00` or `ff 00 2c`, the physical guest reads two bytes and
halts before the C23 loop's mandatory next read. The strict checker refuses
this incomplete source path with `UnreachedSourceInput`. Its initial
pointer proof still succeeds; a pointer ancestor alone cannot turn an
incomplete C loop into a published target.
Even the strict gate does not check physical arithmetic, signed frame words,
source branch parity, phi transfers, emitted checksum or loop backedge.

## Input-site-bound guest pointer provenance (2026-11-24)

The physical guest-written indirect verifier no longer reduces every input
origin to one Boolean taint. Its opaque proof now retains the exact **trace
indices** of genuine input transitions that can feed the final pointer word.
A bounded `p` combines its accumulator and data-operand origins, `*` uses
its data-operand origins, and a later `/` replaces the accumulator origin
with that specific read (including a reached EOF). Guest stores replace
rather than append stale memory origins. The earlier requirement that the
pointer's latest physical version comes from a real `p`/`*` still holds;
post-store self-encryption of that pointer invalidates the candidate.

`SourceWrittenIndirectGuestVerifier::verify_from_input_site` now requires
that the named, reached input instruction be the **only** physical input
site in the pointer's ancestry. Its general counterpart
`verify_from_input_sites` accepts an explicit nonempty, duplicate-free set
and requires exact equality with every observed contributing input site.
The proof retains individual transitions even when a code site is revisited
across loop iterations. The verified classifier with a second read refuses
both missing C63 and extraneous C53 site claims; empty or duplicate origin
sets also refuse. No source-C linker can borrow an unrelated successful VM
input path. This remains **possible physical dataflow**, not proof that every
bit of each read affects a branch or that a C23 predicate is equivalent.

The optional `verify_from_input_transitions` gate additionally checks the
**exact set of `(trace_index, code_address)` pairs** against actual reached
`/` transitions in the final pointer's ancestry. It rejects duplicates,
out-of-budget indices, missing or surplus transitions, and mismatched
addresses even when a claimed address is a genuine but unrelated input
instruction. Unlike the site-set gate, the transition-set gate will not
silently merge multiple guest reads at the same code position. The current
first-/second-input controls prove positive first C53 and second C63
occurrences, their EOF cases, and false-index/address refusals. No test yet
proves a *repeated physical input site* in a linked guest loop; this gate
supports that eventual matching contract without asserting it exists.

The fixed 132-cell first-input classifier's 257 byte/EOF runs now require
origin C53. The existing two-read classifier's 256 second-byte classes,
truncated EOF and trailing-input controls require origin C63 instead; the
first read at C53 does *not* contribute to its final M143 pointer. Both
physical branches still execute reached C114 `i`, select C45/C126, emit
the checked guest outputs and halt in 175/119 steps. Claiming C53 as the
second-read pointer's origin or claiming an unreached C101 `/` now refuses
with `MissingRequiredInputProvenance`. Tested in
`tests/compiler_indirect_source_suffix.rs`. This is not source-C signed EOF
conversion, an unbounded loop or whole-checksum publication.

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
  `v` or `i`. An `i` is terminal, not a proved return or halt; there is no
  interior branch or arbitrary loop synthesis.
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

## Fourth cumulative fold reaches its own fifth output (2026-11-24)

A revised source-admitted **135-cell** guest now emits the actual low byte
of the fourth-input update to **the same cumulative M106**. The unchanged
C128 `/`, C129/C130 `j`, C131 `o` and C132 `p` sequence reads the fourth
raw N15 input and combines it with the previous three-input M106 state.
C133 is now `<`, emitting the new accumulator, and C134 is a true `v`
halt. The five bytes for input `03 04 05 06` are `03 31 05 3a 53`;
M106 becomes **7,174,483** and the VM halts in **113** steps.

The first direct attempt, retaining protected C134 `i`, did emit `53` but
failed at `InvalidEncryptionTarget`: C127 `*` had already rotated M108=103
to 4,783,003, which the terminal `i` read as an unusable code target.
Simply changing C134 to its source-valid `v` encoding, **41**, redirected
the earlier C58 `j` through M42=58 rather than the original M134=58,
losing the later input effects. A two-cell, source-valid repair changes
C60/C61 from `o` to `j`: the reached C60 reads the **encrypted C59=104**
and relocates D to M105; C61 reads the original M105=57 and continues
with D=58. C82's second input is then reached with D=78 rather than 98,
but C83 reads previously encrypted M79=94, rejoins the original chain at
C84 with D=95, and retains the same M106 fold. The source is re-admitted
after **all** three changes, not trusted solely on the suffix planner's
initial protected-word admission.

A separate fifteen-trit digit-table oracle now checks the fifth output:
`crazy(crazy(crazy(crazy(121, a), b), crazy(57, c)), d) % 256`.
The normative N15 VM checks all 257 fourth-byte/true-EOF classes, each
of the other three 256-byte marginals (768 cases), six empty/truncated/
extra-input controls, and 128 cross-input streams from a frozen
`0x4f07ba23` LCG seed. Every case consumes at most four real inputs,
retains the exact M106 word, emits its five expected bytes and ends at
the same real C134 `v` within a **130-step** per-run ceiling. A physical
trace authenticates both early redirects, the later encrypted pointer,
the cumulative write and fifth output. Seven source-valid opcode/operand
mutations fail to preserve the entire five-output, state and 113-step
witness. Tests: `tests/compiler_indirect_source_suffix.rs`.

This closes the **specific fourth-input observable cumulative-fold gap**
without claiming a generic source-C linker. Raw profile EOF is not a
signed C23 `getchar()` EOF check; the fold is ternary `crazy`, not C23
checksum XOR/add. No source-language conditional, loop, phi transfer or
published seven-block C23 checksum follows from these finite tests.
P2 remains open.

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

This proves a bounded **physical continuation and cumulative output**
inside a source-loaded guest, not source-C input-loop lowering. `crazy` of
four raw N15 input words is not C23 unsigned XOR/add or signed `getchar()`
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

## Source-rederived physical suffix verification (2026-11-24)

`verify_source_loaded_indirect_suffix_guest` provides a **separate finite
execution gate** for candidate leaves. Unlike the preparatory source placer,
it first reconstructs the exact graphical candidate from the original
pre-patch source, the requested landing, the pointer-cell address, the
protected-cell set and every suffix opcode. A changed protected word,
forged candidate source byte, stale pointer or different target cannot
borrow the original placement witness.

For each explicit guest input (up to 4,096 bytes) it starts a fresh normative
current-profile N15 VM and observes at most 4,096 steps. A successful proof
requires a complete physical `v` halt, exactly one reached nominated `i`
with a real `M[D]` read of the promised **source-loadable pointer word**,
its actual successor `C` equal to the reserved landing address, and each
suffix opcode fetched in order at exactly the expected code cell. Fetching
any suffix cell before that `i`, missing the leaf, or revisiting a suffix
cell after completion refuses. When the leaf ends with an `i`, the verifier
also checks its real successor transition; the remaining guest must halt
under the same bounded VM run, including any earlier encrypted-code reentry.
The proof exposes the actual transfer step, complete VM step count,
consumed input count, output bytes, terminal-indirect return address and
**every bounded normative transition**. An opaque proof with private
fields exposes read-only accessors for the verified state and sequence.
Each immutable observation records registers, reads, writes, encryption,
committed I/O and the reached code word. A prospective linker may compare
these per-input physical facts with separate source-SSA obligations; their
presence in a trace does not establish a C operation by itself.
It **does not** transform or compute source C output, recognize a runtime
C `while`, certify all stdin streams, or publish an executable artifact.

The focused production-verifier tests demonstrate the genuine 107-step
three-input fold leaf with binary stdin/EOF, an alternate graphical pointer
at C111=117 landing at C118, and the 123-step terminal `i` return that
reaches a previously encrypted C82 `v`. The verifier rejects source-only
or candidate-only mutation, a nominated `i` site that never executes,
a source-valid M110 pointer that is never read because the real C94 `i`
reads M111 instead, a guest run truncated before its actual halt, an
oversize stdin and an unsupported profile. Separate existing VM and
exhaustive-scalar tests remain authoritative for all byte/EOF
classes. In particular, this new gate is
**physical guest-control evidence**, not linkage of the seven-block
source-C mutable EOF checksum; P2 remains open.


### Source-rederived terminal halt with cumulative fourth-input output

The strongest existing 113-step four-input cumulative guest previously
patched C60/C61 and terminal C134 *after* planning the indirect suffix.
That admitted a valid graphical VM source, but the planner's input was
not the exact source that actually ran. In particular, the preparatory
suffix still ended with `i` while the real final code at C134 was `v`.
The physical verifier correctly cannot rederive that inconsistent pair.

The corrected construction moves the C60/C61 `j` reroute, M110=117 and
C134 `v` into the **original source before planning**. The suffix now
explicitly ends in `<v`. The protected final C134 word is preserved
byte-for-byte, so the entire 135-cell candidate is exactly reproducible
by the production source planner. A dedicated regression passes the real
source, plan, protected words and suffix to the new normative verifier.
It checks five frozen binary, high-byte, empty, EOF and extra-input
streams within 130 steps each, including the distinct trit oracle for
the actual fourth cumulative `crazy` result. The returned trace pins
C94's M111=116 pointer read; C60/C61 encrypted-code reentry; the C129
M110=117 and C130 encrypted M118=104 data transfers; C132's real M106
read and computed write; C133's calculated fifth output; and terminal
C134 `v`. Three source-graphical altered-code candidates cannot borrow
the original proof. This verifies finite *physical effect provenance*,
not signed C23 EOF, a source-C mutable loop, or publication of the
unchanged seven-block checksum.

## Source-loaded, guest-written indirect branch witness (2026-11-24)

The suffix planner's pointer is a protected graphical source word. That
contract cannot prove the other P2 control case: a reached `p` produces a
**full-width, input-dependent pointer in loader-expanded memory**, and a
subsequent `i` reads that live word to select a physical code destination.
The new `verify_source_written_indirect_guest` entry point validates this
second case without assuming that a candidate target was reached. It checks:

- One canonical, strictly source-admitted N15 program and a bounded normative
  VM run ending with a real `v`; no simulated C output or synthetic guest
  transitions are used.
- Exactly one reached nominated `i`, its actual data-pointer position, the
  memory word read and the resulting code pointer, against an explicit set
  of at most eight admitted physical successor addresses.
- A prior reached `p` or `*` at the pointer address, with a conservative
  input-taint path through real `/`, accumulator updates and prior guest
  memory writes. A source-only constant pointer or an input-independent
  overwrite cannot count as this computed-pointer witness.
- The exact input stream, output, consumed byte count, latest pointer-writing
  transition, indirect transition and all normative physical steps. The
  proof fields are private with immutable accessors.

The VM's data-write delta is intentionally *changed-value only*. It omits
idempotent `p` stores. This verifier reconstructs the reached `p`/`*` write
from the decoded opcode, live data pointer and actual data read, even when
the resulting value equals the previous word. Without this distinction the
true-EOF branch would falsely fail `MissingGuestPointerWrite`.
The version audit also refuses to attribute an earlier guest pointer store
to a cell later modified by off-site XLAT2 encryption. Its earlier data
provenance cannot authenticate that subsequent code-cell version.

A reusable `SourceWrittenIndirectGuestVerifier` loads each graphical source
and its 15-trit memory image once. Each finite input uses a **fresh copy**
of the pristine VM; failed/earlier streams never donate state to later runs.
Bounds are 4,096 source cells, 4,096 input bytes and 4,096 guest steps per
run. Oversized requests refuse before cloning the source memory.

The complete 132-cell N15 byte/EOF guest from
`build_signed_eof_branch_source` is a physical positive control. Real C53
`/` consumes one signed guest input; reached C82 `p` writes M143=44 for
all 256 successful byte classes or M143=125 on true EOF. C114 `i` then
reads that *written* word and transfers to C45 or C126. The successful-byte
path halts at C104 in 175 steps and emits byte 154; EOF halts at C129 in
119 steps and emits byte 30. Two extra nonempty streams preserve the
first-input selection and leave trailing input unread. Each test checks
source, pointer, all events and exact full-width branch state. Negative
controls reject an unrelated M142 pointer, absent `i`, incorrect arm,
incomplete guest run, other target profile, empty destinations, oversize
input, zero steps and an authentic but **never guest-written** source
pointer. The entire 257-class sweep replays the normative VM and produces
opaque per-input physical evidence, not an inferred branch from source
position alone.

This new gate is **not** a C23 EOF conversion: the two marker outputs are
fixed class values, and input-taint tracking establishes only necessary
physical dependence, not agreement with a typed C comparison. The seven-block
mutable C23 checksum is still **unlinked and unpublished**. The next linker
must bind the source SSA condition, signed EOF, selected control arm,
mutable checksum frame, source phi transfers and loop backedge to physical
effects and independently checked C23 output. The bounded N15 classifier
alone satisfies none of those whole-program obligations.
