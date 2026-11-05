# Normalized C JSON to Typed IR

## Purpose

Decode the exact pinned Clang version-one frontend JSON into a
source-preserving typed-IR void-return or bounded literal-byte-output projection,
then emit independently re-admitted canonical MCTI bytes. This separate
compiler workspace package contains the JSON dependency; the VM's
dependency-free crate remains unchanged.

## Supported slice

For the effect-free void family, the complete normalized artifact must contain
exactly one no-argument external `fn()->void` definition with a compound
body containing only standalone null statements (`;`), single-digit standalone zero expressions (`0;`),
exact casts of zero to void (`(void)0;`), nested compound scopes, and an
optional final `return;` (including inside a nested scope). Thus
`void noop(void) {}`, `void noop(void) {0; return;}`,
`void noop(void) {(void)0; return;}`, and `void noop(void) {{;}}` compile to
the same verified two-cell guest. An absent explicit return uses the original
function body span to attribute its defined implicit return; no invented C return
statement is inserted into the frontend artifact. The bounded semantic preorder
must preserve node IDs, direct-parent ancestry and nonoverlapping source spans
inside each scope. No statement after an explicit return, no nonzero or
compound cast operand, and no effectful or metadata-drifted nested node can be
discarded. Nested depth is capped at 64, with at most 4094 body nodes per
artifact.
Clang metadata, target identity, source digest spelling, semantic preorder,
parent IDs, field grammar and typed-IR provenance are all checked. Unknown or
duplicate fields, extra source statements and all non-void programs reject.

## Witnessed guest C output

A separate **exact** pinned-Clang source shape is also executable:

```c
#include <stdio.h>
void emit(void) { putchar(0); return; }
```

The exact pinned-Clang shape admits one through 33 calls to
`putchar(N);` with optional final `return;`, where every `N` emits the same
low-eight-bit byte. The source leaf must be a nonnegative representable `i32`
value (including `256..2147483647`), from a bounded single-line integer token
(decimal, octal, hexadecimal or C23 binary) or a single C character literal
(including bounded escape spellings). Up to three exact, source-bound pairs of
parentheses may enclose the literal and/or one checked signed unary `+`/`-`
applied to an `i32` literal or a parenthesized `i32` literal. For example,
`putchar(-(191))` and `putchar(+((65)))` preserve the sign's full
source span and the inner operand's checked value. For unsigned `u32`
source tokens, a single checked `u32`-to-`i32` conversion may wrap up to
three pairs of parentheses; unsigned unary expressions are rejected.
A direct output call may also be explicitly cast to void as a standalone
expression statement, for example `(void)putchar(65);`, discarding only the
call's return value. The pinned Clang `to-void` ancestor is checked for exact
parentage, absent effect-bearing metadata, and bounded same-line source spans;
additional discard casts or arbitrary effectful expressions still reject.
Only one sign or conversion is admitted per call. The wrapper's canonical
evaluated signed `i32` must agree with the Clang leaf and unary operator.
Negative arguments emit their low byte with the complete signed source span.
For example, `putchar((65)); putchar(65u);`, `putchar(+65); putchar(-191);`,
`putchar(0x41); putchar(0101);`, `putchar(321); putchar(65);`, and
`putchar('\0');` retain Clang's source spans and evaluated integer values.
The C `putchar` low-byte conversion is applied only after checked `i32`
admission, never by truncating a malformed or overflowing JSON integer.
Ordinary one-line spacing around `putchar (` calls, literal arguments,
parentheses and the optional unary sign is supported. Each separating gap
requires its Clang-reported byte and column distance to agree and admits at
most 16 additional bytes beyond the syntactic delimiter; arbitrary long gaps
and cross-line argument wrappers remain unsupported. The normalized JSON does
not contain the source text: the closed pinned-Clang AST and the public driver's
source SHA-256 check remain the semantic and source-authenticity boundaries.
Each call proves its direct `putchar` reference, one exact literal argument
and function-to-pointer decay;
the complete normalized preorder contains four to nine nodes per call, plus
two structural nodes and optional explicit `return;`, preserving exact source
ancestry and ordered nonoverlapping spans. Lexical compound scopes may contain
these calls and inert statements; each nested scope preserves its own Clang
parent ID, checked source span and original output order. The adapter admits at
most 128 nested scopes with depth at most 64. Up to 128 inert statements
(`;`, `0;`, or `(void)0;`) may occur before, between or after calls at any
admitted depth. Each complete source-bound node is checked without inventing
guest I/O for an inert statement. Nonzero literal expressions, early nested
returns, unexpected metadata, effectful nested bodies and other side effects
still reject. The adapter emits one canonical `u8` constant and
the corresponding number of `ByteOutput` effects.
For zero, the downstream publisher uses `--initial-zero-output --typed-stdin`,
which independently verifies guest stdout of one to 33 NUL bytes. Nonzero
bytes use the separate `--seeded-byte-literal --typed-stdin` backend, where
each byte/count combination must have its own position-sensitive guest-VM
witness. For example, one `putchar(23)`, two `putchar(65)` calls and three
`putchar(146)` calls, and thirty-three `putchar(40)` calls compile and
execute with exact byte output. One `putchar(65)` also has an independently
checked single-byte guest crazy-operation witness. The backend's currently
witnessed subset is enumerated in
`src/compiler/byte-echo-bridge/README.md`; **not** every value or count is
realizable. Integer tokens over 32 source bytes, unrepresentable signed
`i32` values, unsupported composite/unsigned-negation expressions, and more
than 33 calls refuse source admission. An unwitnessed combination fails layout
admission without publishing a `.malbolge` artifact.

An omitted final `return;` uses the original function body span to model
C's defined implicit void return; no synthetic source statement is added.
More than three parentheses, multiple unary operators, multiline
argument spacing, general arithmetic, call-result handling,
arbitrary output streams, interleaved effectful statements, `getchar`, EOF,
I/O errors, general guest libc and C entry ABI remain unsupported.
Mixing distinct **output bytes** generally refuses admission except for
explicitly witnessed two- and three-call sequences. One two-call family starts
with NUL followed by `Z` (90), `P` (80), `T` (84), or `S` (83). The separate
`--zero-then-literal --typed-stdin` backend uses an independently executed
`OutputByte`, exact no-op phase, data relocation, guest crazy operation,
second `OutputByte`, and halt. The four witnesses execute in 5, 7, 11, and
22 guest steps, respectively. Source spans remain distinct, the second SSA
constant is never confused with the first, and unsupported/reversed/extra
outputs reject without publication. Other distinct `i32` literals sharing
the same low byte preserve their own source spans.
The pinned Clang frontend must supply the source-bound integer or character
token, its canonical evaluated `i32` value and a bounded single-line span;
the adapter never decodes C integer or escape syntax or accepts fabricated
byte constants.

`canonical_guest_typed_ir` selects this trace or the existing effect-free void
trace without dropping observable effects. `canonical_void_typed_ir` preserves
its prior no-effect-only admission contract and callers.

`canonical_void_typed_ir` returns no-effect MCTI bytes for
`malbolge_layout --empty-void --typed-stdin` while
`canonical_guest_typed_ir` additionally returns a mode for the supported
bounded literal-byte output trace. This adapter does not invoke Clang, authenticate an
independently supplied C source against its JSON SHA-256, implement a complete
C command line, realize C process-return ABI or replace the independent guest
VM preflight. Its tests run both accepted families through real guest code.

## Executable handoff

`c2malbolge_json` accepts normalized JSON on **stdin**, an explicit trusted
`malbolge_layout` executable, and a fresh `.malbolge` output path. It validates
JSON, produces canonical MCTI, and selects the exact verified
`--empty-void`, `--initial-zero-output`, `--seeded-byte-literal`,
`--zero-then-literal`, `--distinct-literal-pair`, or
`--distinct-literal-triple` mode with `--typed-stdin`.
Optional `--capsule` embeds the current profile identity. The compiler
frontend must have produced the normalized JSON; the pipeline does not infer
semantics from raw C text or trust an unverified layout backend substitute.

```sh
malbolge_c_frontend --guest-include GUEST_INCLUDE \
  --resource-dir RESOURCE_DIR --source-id program.c program.c |
  c2malbolge_json --layout-backend malbolge_layout \
    --output program.malbolge --capsule
```

The pinned Clang 22.1.8 frontend executable and its target headers are required
for this source-driven command. Real native C-to-VM process evidence is now
covered by `tests/test_c2malbolge_native_pipeline.py` on hosts with the native
frontend and Rust guest binaries available. The test accepts explicitly named
frontend/resource paths when repository-pinned provisions are absent. This
does not claim an automated turnkey install or broader C language coverage.
The explicit executable path is a caller-trusted capability, not discovered via
`PATH` implicitly.

Two different nonzero constant `putchar` calls now admit only the independently
witnessed `Y/`, `Y$`, and `Q.` pairs. The Clang JSON adapter preserves exact
source spans and distinct SSA definitions. Other differing pairs refuse;
three-call sequences require their own separately proved guest witnesses.

### Exact three-`putchar` source output traces

Pinned Clang 22.1.8 source evidence now admits three successive constant
`putchar` outputs only for `Z%H`, `Q.O`, `Y-P`, `T"O`, or `T"Q`
(including their equivalent integer literals). Each source call retains its own argument span, canonical
`u8` definition and matching output identity. The selected
`--distinct-literal-triple --typed-stdin` mode is independently checked by
the layout publisher and the normative guest VM. A two-call prefix such as
`Z%` does not have an independent two-byte guest witness and is rejected;
unsupported transitions or any fourth call are also rejected before publish.
The native source-to-guest proof is
`tests/test_c2malbolge_distinct_literal_triplet.py`.

### Four-distinct-byte current-profile witness

The separately selected `T=4>` literal-output mode preserves four distinct
source-bound `u8` constant definitions and four exact SSA byte outputs. Its
independently verified positional target uses eleven no-ops, one data-pointer
relocation and four separate guest `CrazyData`/output pairs before halt. The
normative current-profile VM emits `T=4>` in exactly 21 steps with no input
consumption. Partial prefixes, other four-byte values, stale SSA identities,
foreign profiles and unproved arithmetic remain unsupported; this is not a
general C string-output implementation.

### Five distinct guest-computed bytes (bounded binary witness)

The opt-in `--distinct-literal-quint` mode admits five source-proven byte
constants only for `51 22 1b 37 39` (hex: `Q`, quote, ESC, `7`, `9`).
The eleven-nop relocated target performs five disjoint guest `CrazyData`
writes and executes five actual byte outputs in 23 normative VM steps.
Canonical typed/MCTR identity, all five SSA bindings, profile, input-free
execution, and the raw/capsule publisher are independently rechecked.
Incomplete prefixes, different five-byte outputs, and additional effects
fail without output; this witness is not general C string compilation.

### Six distinct guest-computed bytes (bounded binary witness)

The opt-in `--distinct-literal-six` path admits the exact current-profile
source byte trace `51 1c 4f 1d 50 1b` (hex). Six independent source-bound
`u8` SSA definitions and output uses survive canonical typed/MCTR admission.
A single inert prefix and data-pointer relocation precede six guest
`CrazyData` writes and six byte outputs, all outside the source region.
The normative VM independently emits all six binary bytes in 15 steps with
no consumed input. Both raw and capsule publishers recheck this witness;
unsupported values, partial prefixes, extra output, or stale SSA fail closed.
This does not implement general C string output or the guest C runtime.

### Seven distinct guest-computed bytes (bounded binary witness)

The opt-in `--distinct-literal-seven` path admits only the independently
verified current-profile C output trace `36 3e 35 02 54 1f 18` (hex). Seven
source-bound `u8` SSA definitions survive canonical typed/MCTR admission.
Five inert no-ops and one data-pointer relocation precede seven separate
guest `CrazyData` writes and outputs, with data cells outside the source.
Both raw and capsule publication require normative VM output of these exact
seven bytes in 21 steps, independent of unused input. Incorrect prefixes,
reordered bytes, extra output and altered SSA are rejected without publication.
This remains a finite witness, not general C byte-string lowering.

### Eight distinct guest-computed bytes (bounded mixed arithmetic witness)

The opt-in `--distinct-literal-eight` C path admits exactly eight separate
source `putchar` constants with the independently verified current-profile
binary stdout `53 20 17 3c 36 01 52 06` (hex): `S`, space, ETB, `<`, `6`,
SOH, `R`, ACK. Three no-ops and one data-pointer relocation precede seven
real guest `CrazyData` writes and a final `RotateData` write, each followed by
guest output, then halt. The normative VM proves all eight distinct bytes in
21 steps with disjoint post-source data writes, independent of unused input.
Incomplete prefixes, reordered bytes, duplicate SSA and foreign profiles
reject without publishing an output. This is one finite source witness, not
arbitrary binary C output or general lowering.

### Nine distinct guest-computed bytes (bounded mixed arithmetic witness)

The opt-in `--distinct-literal-nine` C path admits exactly nine separate
source `putchar` constants with proven current-profile binary output
`54 3d 8d d1 c0 b4 bf d2 a2` (hex). One reached no-op and explicit
relocation precede eight real guest `CrazyData` writes and one `RotateData`
write (the third arithmetic step); each data write is followed by output.
The normative VM verifies nine distinct bytes, 21 total steps, nine disjoint
post-source data writes and zero consumed input before publication. Incomplete
prefixes, reordered bytes, altered SSA, foreign profiles and extra writes
reject; this is a finite source witness, not generic byte-string lowering.

### Ten distinct guest-computed bytes (bounded mixed arithmetic witness)

The opt-in `--distinct-literal-ten` C path admits exactly ten separate
source `putchar` constants with proven current-profile binary output
`51 22 fd ce a5 98 ba b6 87 cb` (hex). One reached no-op and explicit
relocation precede nine real guest `CrazyData` writes and one `RotateData`
write (the third arithmetic step); each data write is followed by output.
The normative VM verifies ten distinct bytes, 23 total steps, ten disjoint
post-source data writes and zero consumed input before publication. Incomplete
prefixes, reordered bytes, altered SSA, foreign profiles and extra writes
reject; this is a finite source witness, not generic byte-string lowering.

The eleven-byte C witness is separately admitted as an exact source-bound
`P`, GS, SUB, `6`, ENQ and six binary values. Eleven guest writes
produce 11 distinct bytes in 24 VM steps; the normative VM verifies
raw and capsule outputs without host computation substitution. This
finite trace is not general C byte-stream lowering.

The `--distinct-literal-twelve` C path admits the exact twelve-byte
`51 37 34 38 fb ce 9f 98 b8 b4 83 cd` witness. One reached no-op,
explicit relocation, eleven disjoint `CrazyData` writes and one
`RotateData` write at the fifth arithmetic position emit twelve guest
bytes in 27 VM steps. The normative VM independently verifies both
source-bound outputs and input independence before publication. Other
byte sequences, incomplete prefixes, and forged SSA are not admitted;
this is not general binary-stream lowering.

The `--distinct-literal-thirteen` C path admits only the exact thirteen
source-ordered bytes `42 43 30 16 54 09 bf c6 c8 87 e3 ab a4` (hex).
One reached no-op and a data-pointer relocation precede twelve disjoint
guest `CrazyData` writes and one `RotateData` write (the sixth arithmetic
position), each followed by guest output. The normative current-profile VM
replays the thirteen binary bytes in 29 steps with no consumed input before
raw or capsule publication. Any incomplete, reordered or forged effect trace
rejects; this finite witness does not provide general C byte-stream lowering.


The `--distinct-literal-fourteen` C path admits only the exact fourteen
source-ordered bytes `59 45 2c 48 53 17 4c 4f 3d 40 5b 31 19 34` (hex).
One reached no-op and a data-pointer relocation precede twelve disjoint
guest `CrazyData` writes and two `RotateData` writes (the sixth and thirteenth
arithmetic positions), each followed by guest output. The normative current-profile VM
replays the fourteen binary bytes in 31 steps with no consumed input before
raw or capsule publication. Any incomplete, reordered or forged effect trace
rejects; this finite witness does not provide general C byte-stream lowering.


The `--distinct-literal-fifteen` C path admits only the exact fifteen
source-ordered bytes `51 2e 19 38 3e 89 d2 ad a3 b7 c8 88 08 d5 c6` (hex).
One reached no-op and a data-pointer relocation precede thirteen disjoint
guest `CrazyData` writes and two `RotateData` writes (the sixth and thirteenth
arithmetic positions), each followed by guest output. The normative
current-profile VM replays fifteen binary bytes in 33 steps with no consumed
input before
raw or capsule publication. Any incomplete, reordered or forged effect trace
rejects; this finite witness does not provide general C byte-stream lowering.

The `--distinct-literal-sixteen` C path admits only the exact sixteen
source-ordered bytes `3f 49 36 13 5a 0a ba b3 c3 86 cc aa 01 07 d5 c5` (hex).
One reached no-op and a data-pointer relocation precede thirteen disjoint
guest `CrazyData` writes and three `RotateData` writes (the sixth,
thirteenth and fourteenth arithmetic positions), each followed by guest
output. The normative current-profile VM replays sixteen binary bytes
in 35 steps with no consumed input before raw or capsule publication.
Incomplete, reordered or forged effect traces reject; this finite
witness is not general C byte-stream lowering.

The `--distinct-literal-seventeen` C path admits only the exact seventeen
source-ordered bytes `59 3f 2c 48 50 1b 18 32 15 4d 4b 3b 42 0f 44 30 17` (hex).
One reached no-op and a data-pointer relocation precede fourteen disjoint
guest `CrazyData` writes and three `RotateData` writes (the seventh, ninth
and fourteenth arithmetic positions), each followed by guest output.
The normative current-profile VM replays seventeen binary bytes in
37 steps with no consumed input before raw or capsule publication.
Incomplete, reordered or forged effect traces reject; this finite
witness is not general C byte-stream lowering.

The `--distinct-literal-eighteen` C path admits only the exact eighteen
source-ordered bytes
`54 22 19 3e 38 03 09 dd 87 d1 a5 99 bf 08 c7 c6 c2 91` (hex).
One reached no-op and a data-pointer relocation precede fifteen disjoint
guest `CrazyData` writes and three `RotateData` writes (the seventh, ninth
and fourteenth arithmetic positions), each followed by guest output.
The normative current-profile VM replays eighteen binary bytes in
39 steps with no consumed input before raw or capsule publication.
Incomplete, reordered or forged effect traces reject; this finite
witness is not general C byte-stream lowering.

The `--distinct-literal-nineteen` C path admits only the exact nineteen
source-ordered bytes
`53 21 1a 3c 38 03 17 55 0e 49 2b 10 46 16 40 4c 3a 19 58` (hex).
A first-instruction data-pointer relocation precedes sixteen disjoint
guest `CrazyData` writes and three `RotateData` writes (the seventh, ninth
and fourteenth arithmetic positions), each followed by guest output.
The normative current-profile VM replays nineteen binary bytes in
40 steps with no consumed input before raw or capsule publication.
Incomplete, reordered or forged effect traces reject; this finite
witness is not general C byte-stream lowering.

The `--distinct-literal-twenty` C path admits only the exact twenty
source-ordered bytes
`3e 14 35 12 3f 0a a4 9c ad a3 1a a8 a2 95 ab 9f 98 1d ac ae` (hex).
Twelve reached no-ops shift `j` to position twelve, relocating the data
pointer beyond the 54-cell source. Seventeen guest `CrazyData` writes and
three `RotateData` writes (the seventh, eleventh and eighteenth arithmetic
positions) compute distinct bytes on disjoint guest cells, followed by output.
The normative current-profile VM replays all twenty bytes in 54 steps with
no input consumed before raw or capsule publication. Incomplete, reordered
or forged effects reject; this remains a bounded C lowering witness.

The `--distinct-literal-twenty-one` C mode admits only the exact
twenty-one source bytes
`41 0e 3b 0f 3f 0a 40 8e 26 92 27 96 22 97 8d 15 31 18 35 1a 2f` (hex).
Fifteen no-ops relocate the data pointer at position 15. Eighteen
`CrazyData` and three `RotateData` writes (the eighth, fifteenth and
sixteenth arithmetic positions), plus one reached trailing no-op,
produce twenty-one distinct guest bytes in 60 real VM steps.
The exact C effects are verified without host-side output replacement;
unproved prefixes, reordered literals and forged artifacts reject.

The `--distinct-literal-twenty-two` C path admits exactly the twenty-two
source-ordered bytes `39 16 37 05 41 0c 30 8e 24 9f 1b a0 23 97 15 28
27 29 14 32 1e 1f` (hex). Ten no-ops move the relocating `j` to source
position ten; twenty `CrazyData` and two `RotateData` writes compute the
bytes outside the 57-cell source, with a reached no-op before halt. The real
VM independently verifies all 22 output bytes, zero consumed input and exact
57-step termination before raw or capsule publication. Arbitrary
twenty-two-byte source sequences remain unsupported.

The exact 23-byte guest witness is also admitted as
`--distinct-literal-twenty-three` after pinned C AST effects are checked in
source order; no shorter prefix or reordered literal is admitted as the
23-byte recipe.

The exact source-ordered 24-byte witness is now admitted as
`--distinct-literal-twenty-four`; pinned C AST effects must contain every
literal in order and cannot use an unproven shorter prefix.

The `--distinct-literal-twenty-five` C mode admits exactly 25
source-ordered `putchar` integer literals matching the proven 25-byte
guest witness. Pinned AST effects, source span identity, and complete
sequence are required; shorter prefixes or reordered literals reject.

The exact 26-byte source witness is admitted as
`--distinct-literal-twenty-six` with pinned source-ordered C literal
effects. Shorter prefixes, reordered bytes and unproved expressions reject.

The `--distinct-literal-twenty-seven` mode requires all 27 literal calls in
source order. The pinned Clang AST and source spans must agree with the
independently proved guest output. Exact 25- and 26-byte recipes remain
separately admitted; other prefixes and altered expressions reject.

The `--distinct-literal-twenty-eight` mode requires all 28 ordered
source C `putchar` literals, verified by pinned Clang AST and source spans.
Existing 25-, 26- and 27-byte modes remain separately proven; shorter
unproved prefixes, reordered calls and changed expressions still reject.

The `--distinct-literal-twenty-nine` source mode requires the complete
29-byte independently proven C `putchar` sequence. Pinned Clang AST literal
values and source order are checked before canonical typed-IR projection; no
proper prefix, swapped call or altered expression is admitted.

The `--distinct-literal-thirty` C path requires the complete source-ordered
30-byte `putchar` sequence proven by the independent 97-step guest witness.
Pinned Clang AST constants, source spans and output order must match; partial
sequences, modified expressions and reordered effects fail before typed IR.

The exact 31-byte `--distinct-literal-thirty-one` source mode additionally
admits only the independently VM-witnessed, source-ordered constant `putchar`
trace, with each byte materialized at a separate typed SSA ID. Its incomplete
prefixes and all other 31-byte values remain unsupported; successful sources
are still validated by downstream guest execution before publication.

The `--distinct-literal-thirty-two` C mode admits exactly one independently
proven 32-byte ordered `putchar` trace. Pinned Clang AST, source spans and
separate typed SSA effects must agree before the 97-step guest layout is
constructed; no unproved prefix, swapped effect or arithmetic expression is
accepted. Raw and capsule output remain subject to real-VM verification.

The `--distinct-literal-thirty-three` C mode admits exactly the 33 ordered
`putchar` constants proven by the independent 97-step VM witness. Canonical
source spans and a distinct SSA result for every constant bind the pinned Clang
frontend to typed effects. Incomplete prefixes, changed calls, nonliteral
arithmetic and unrelated 33-byte traces reject before source publication.

The `--distinct-literal-thirty-four` C mode admits only the exact 34-byte
current-profile guest witness; altered order, values or prefixes reject.

The `--distinct-literal-thirty-five` C mode admits only the exact 35-byte
current-profile guest witness; altered order, values or prefixes reject.

The `--distinct-literal-thirty-six` C mode accepts the exact 36-byte
current-profile guest arithmetic witness, rejecting changed values, order,
incomplete source effects and unsupported C before publication.

The `--distinct-literal-thirty-seven` C mode accepts only the exact 37-byte
source-proven guest arithmetic trace; malformed C, values and prefixes reject.

The `--distinct-literal-thirty-eight` C mode recognizes the exact 38-byte
source-proven trace and rejects incomplete or altered literal calls.

The `--distinct-literal-thirty-nine` C mode requires precisely 39 ordered
source-proven byte constants, rejecting partial or altered C traces.

The `--distinct-literal-forty` C mode admits only the exact forty-byte
source order proven by the independent real VM; incomplete, altered and
nonliteral programs fail without publication.

The bounded C frontend now recognizes the exact independently guest-proven
forty-one-byte `putchar` source sequence with fresh SSA byte identities.
Incomplete, reordered, altered and other C effects still fail closed.

The bounded frontend recognizes the precise 42-byte source `putchar`
sequence independently proven in the real guest VM. The 40-byte prefix
retains its distinct witness, but the 41-byte prefix and altered outputs
reject; this does not generalize byte-stream compilation.

### Verified forty-three-byte source bridge

The frontend accepts only the exact independently verified 43-byte
`putchar` literal sequence and rejects its unproved proper prefixes. The
two-byte `Q.` prefix retains its earlier guest witness.

### Verified forty-four-byte source bridge

The frontend admits only the exact independently VM-proven 44-byte
`putchar` literal trace. Proper prefixes, changed constants and further
outputs fail closed; the legacy 43-byte and Q. routes are unchanged.

### Verified forty-five-byte source bridge

The pinned C frontend admits only the exact 45 distinct source-ordered
`putchar` literals witnessed by the normative VM. Other values, incomplete
prefixes, reordered calls, and unsupported expressions fail closed.
