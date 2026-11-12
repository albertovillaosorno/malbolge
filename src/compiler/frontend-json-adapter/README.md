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

Pure skipped unsigned C unary expressions now authenticate `~`, unary `+`
and unary `-` around arithmetic whose evaluation would be undefined. The
source-bound unary proof uses the same exact span grammar whether the
expression executes or is skipped. In a complete twelve-trip Fibonacci
recurrence, an outer `&&` skips `~(next / (next & 1U))` on even terms,
when its denominator is zero. On odd terms the selected arithmetic remains
strict. The pinned C frontend, typed adapter, layout and normative guest VM
emit twelve independently calculated masked bytes in 47 steps under empty
and binary stdin. Both sign spellings are also tested end to end. Selected
zero division, skipped I/O, signed casts and forged Clang nodes reject.
This is bounded C source replay, not dynamic guest C unary computation.

Complete unsigned Fibonacci C programs may place nested pure unsigned
arithmetic inside an entirely skipped ternary operand. Recursive
authentication covers source-ordered addition, subtraction, multiplication,
division, remainder, shifts and bitwise operators without performing any
skipped operation. A selected path still evaluates all operations strictly
and rejects division by zero. The two tested ternary polarities emit
twelve independently justified bytes on the real VM in 43/41 steps.
Source-side effects and forged normalized nodes remain rejected; this
does not implement dynamic guest C arithmetic or unmasked stream layout.

A complete Fibonacci condition now short-circuits a pure unsigned ternary:
when skipped, both division and remainder branches may have zero divisors,
without triggering undefined evaluation. Both arms are authenticated against
the source tree, while selected undefined arithmetic and hidden I/O reject.
Exact ternary endpoint line/column proof rejects forged normalized nodes.
This remains bounded static C replay, not general guest-side conditionals.

A pure skipped Boolean RHS may itself contain a source-ordered `&&`/`||`
tree. Both children are authenticated without evaluating a division
that C does not execute; the selected path still rejects zero division.
A complete nested logical Fibonacci program emits twelve oracle bytes
through the normative VM (47 steps, two input patterns). The source
proof remains bounded at twelve expression levels, with no guest-side
C branching or general Boolean evaluation.

The source-proven C Boolean evaluator now honors `&&`/`||` evaluation
order for a skipped pure right-hand comparison containing unsigned
division by zero. Complete twelve-iteration Fibonacci programs using
both operators emit twelve independently calculated masked bytes in the
real guest VM (47 steps). Selected zero division, skipped input/output
and forged AST ancestry still refuse. This is bounded source replay;
full runtime C logical branching and arbitrary deeply nested Boolean
expressions remain unsupported.

A source-proven unsigned C ternary may now skip a pure division or remainder
by zero in its unselected operand, including exact parenthesized wrappers.
The selected arm is still fully evaluated, so selected undefined arithmetic
refuses. The twelve-step guarded Fibonacci and dual-arm division/remainder
variants produce the independent masked oracle through the actual guest VM;
this does not admit arbitrary C short-circuit expressions or dynamic guest
branches. Forged operand ancestry and unselected effects still refuse.

Bounded source-state replay now composes a braced `if/else` containing
independent `switch` statements. Both C arms receive complete proof,
but only selected assignments or outputs survive. Two full Fibonacci
variants emit after the conditional or within the selected switch case,
with twelve oracle bytes and 47 real guest steps. Opening brace byte and
column gaps, and closing arm spans, are authenticated. Five unsupported
source mutations and 24 AST forgeries refuse; this is not dynamic guest
branching or arbitrary unmasked byte-stream synthesis.


A bounded whole-C source-state replay also permits a checked unsigned
assignment **between** two real `putchar` effects in a nested switch arm.
Both outputs retain their source order and the second sees the updated local.
Each unselected arm is proved independently and discarded. The complete
`local_interleaved_switch_fibonacci.c` program reaches the normative guest
VM with twelve independently computed recurrence bytes in 47 steps under
both EOF and binary input. Five unsupported C changes and 24 forged
assignment nodes reject before publication; full byte/column endpoint
identity is mandatory. This is finite source-state evaluation, not runtime
Malbolge locals or dynamic control flow.

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

### Paired guest outputs inside a switch-local conditional

A second complete unsigned Fibonacci source wraps each innermost
switch case's two outputs in a braced source-checked `if/else` pair.
The condition's selected compensation must cancel a bit that the
opposite branch would preserve; a wrong conditional decision changes
the guest bytes. Both outputs are captured only after the selected
branch and its alternative pass bounded source replay. All four
switch paths and both condition values occur.

The normative Malbolge VM matches the independent unsigned C oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under EOF and
binary stdin. Three unsupported complete C mutations and 24 forged
Clang conditional nodes refuse without publishing a guest. Third
selected output, dynamic guest conditionals, and arbitrary unmasked
streams remain unsupported.

### Two ordered guest outputs in a nested C switch arm

A complete six-trip unsigned Fibonacci C program now calculates two
consecutive recurrence terms per loop trip, then selects one of four
two-level nested `switch` arms through independent C selectors. Each
selected innermost arm has two different source-bound `putchar` calls.
The adapter captures their complete ordered effect vector while proving
all unselected cases, including fallthrough checks, and publishes the
selected vector only when enclosing switch replay is complete. This
extends the earlier one-output switch proof, not dynamic guest control.

The independent unsigned-C oracle and the normative guest VM agree on
twelve masked bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47
steps under EOF and binary stdin. Six invalid complete C mutations
(including a third call, unselected input, and writes after output) and
48 forged first/second output-call ASTs refuse without a guest artifact.
Three outputs per selected arm, third-level switches and unmasked
Fibonacci guest layout remain unsupported. P0 is still pending.

### Nested source-proven `switch` byte effects

A full twelve-output Fibonacci C program now places the only `putchar`
effect inside each inner case/default of two nested, source-checked
`switch` statements. Each innermost arm first assigns a distinct unsigned
mask (`0`, `32`, `26`, or `58`) and then emits the masked recurrence byte.
The selector values visit all four combinations across twelve bounded
`for` trips. The adapter captures at most one nested effect per selected
path, keeps it out of the outer switch's unselected arm replays, and
publishes only the outermost selected output. A source-checked nested call
is admitted at the existing two-switch depth ceiling. Call closing-byte
and closing-column offsets must agree with the converted argument span;
forged output spans cannot be sent to guest layout.

A separately evaluated unsigned-C oracle and the normative guest VM agree
on `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 guest steps under
EOF and binary stdin. Seven invalid full C sources and 24 forged nested
output-call ASTs reject without publication. The previously admitted
nested-switch state-only program remains a separate regression. A third
switch level, multiple effects along one inner path, dynamic guest
switches, and unmasked Fibonacci guest synthesis are not implemented.
This is bounded compile-time C state replay, not runtime C execution.

### Conditional state updates inside nested switch cases

A full twelve-output Fibonacci C source now places a braced `if/else`
inside every inner `switch` case. Each condition selects an unsigned
mask modification, followed by a checked compound XOR compensation and
one guest `putchar`. The finite source replay checks both paths but commits
only the selected state, including at most one captured output per arm.
It checks the conditional's exact opening `if (` byte/column geometry
and final brace span before permitting outer switch state selection.
The independent C oracle and normative guest VM agree on twelve masked
Fibonacci bytes in 47 steps under empty and binary stdin. Seven bad C
sources and 24 forged conditional ASTs refuse without publication.
A second full C source moves output calls inside the selected branch; its
real guest also matches the same independent oracle in 47 VM steps.
This remains compile-time replay, not dynamic guest C branching; the
unmasked Fibonacci byte stream still lacks a verified guest layout.

### Source-proven two-level C switch dispatch

A complete twelve-output Fibonacci C program places one `switch` within each
case/default arm of an enclosing `switch` under a bounded `for`. Both selectors
vary with source-local recurrence state. The nested selected arm sets a local
mask, with four distinct unsigned mask states (`0`, `32`, `26`, `58`)
that differ in higher bits but preserve the masked byte output. Both switch-
local `break` statements return only from their own switch; a later `putchar`
emits each computed byte. The adapter replays at most
two active switch levels, preserves verified Clang parentage and exact source
spans, and does not let unselected writes escape into the outer case.
The independent unsigned-C oracle and normative guest VM agree on twelve
bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under EOF and
binary input. Eight invalid C sources and 22 forged ASTs refuse publication,
including nested I/O on an unselected arm. Third-level nested switches,
outputs inside nested switch arms, dynamic guest switches and unmasked
Fibonacci byte-stream layout remain outside the admitted subset.

### Unbraced switch as a bounded loop body

A complete twelve-step Fibonacci C program puts a `switch` directly under a
source-proven `for` without adding synthetic braces. Separate complete programs
use that same source-ordered switch as the sole body of a `while` or `do/while`.
Each case writes a computed byte and advances unsigned C recurrence state;
`break` exits only the switch, not the surrounding loop. The adapter
checks Clang's direct parent/child relationship, exact endpoints, and every
selected switch arm before rechecking the surrounding loop condition.
An independent unsigned-C oracle yields the twelve masked bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03`; the normative guest emits them in
47 steps under EOF or binary stdin. Unsupported source mutations and forged
Clang ancestry/endpoints refuse without publishing a guest. No runtime C loop,
general switch nesting or unmasked byte-stream synthesis is claimed.

### Direct unbraced `do` inside a source-proven `for`

An unbraced do body of a six-trip bounded for emits two branch-selected
Fibonacci bytes per outer trip. Direct Clang ancestry, full byte/column
endpoints, the protected induction counter and the post-body condition
are checked without an invented compound scope. The independently
computed twelve-byte oracle matches the real guest VM in 47 steps on
EOF and binary stdin. Four unsupported source mutations and three forged
ASTs refuse. This is finite C source-state replay, not guest runtime loops.

### Direct unbraced `do` inside a source-proven `while`

A complete masked Fibonacci recurrence uses `while (remaining > 0U)` with
one unbraced child `do { ... } while (phase != 0U);`. The inner do emits
branch-selected bytes, toggles phase and decrements the outer bound twice;
the outer condition is then rechecked for six trips. The adapter verifies
Clang's direct ancestry, the do condition's trailing semicolon, and both
byte and column closing endpoints. An unsigned-C oracle agrees with the
normative Malbolge VM on twelve bytes in 47 steps under both EOF and
binary stdin. Six unsupported sources and nine forged ASTs refuse, including
tampered source-end columns. This is finite source-state replay, not guest
runtime C looping or general unmasked byte-stream synthesis.

### Rechecked Boolean `for` guards in complete C programs

A reversed source induction comparison such as `limit > i && b < 20U`
retains its genuine C operand order. The projector proves the exact
right-hand counter, a pure source-local left-hand bound, a semantically
ascending stride and a separately re-evaluated pure guard. A full
mutable-stride Fibonacci C program emits six independent oracle bytes
`02 19 1f 08 17 0f` through the normative guest VM in 97 steps under
EOF/binary stdin. Four invalid C variants and six forged ASTs refuse.
This is compile-time bounded state replay; general guest loop execution
and unmasked Fibonacci layout are not implemented.

A complete Fibonacci source with a mutable unsigned stride, a local bound
of twenty, and `i < limit && a < 9U` initially refused normalized C
admission. The bounded source proof now accepts a left-associated chain of
up to two `&&` or `||` operators whose first operand retains the checked
unsigned induction comparison. Each pure right guard has exact Clang
ancestry, type, token spacing and both byte/column endpoints. Every guard is
re-evaluated after each body and increment, with the changing local state.

The source `i < limit && a < 40U && b < 20U` proves a distinct third
guard: only `b` terminates the loop at six outputs, while the first two
conditions remain true. The normative VM emits the independent
`02 19 1f 08 17 0f` oracle in 97 steps under EOF and binary stdin.
Nine invalid C variants and nine forged AST variants refuse publication.
The five-output `b < 10U` variant still refuses at guest layout; this
frontend repair does not solve general byte-stream synthesis. More guards,
side effects, and dynamic guest loops remain unsupported. A pure OR can
extend past the first induction bound, but any loop that requires more than
twelve iterations still refuses. The finite replay is compile-time C only.

The complete `limit > i || b < 20U` Fibonacci C program starts `limit` at
two and changes its induction stride from one to two, so the original bound
stops being true before the last four iterations. The right Boolean guard
keeps the loop alive, then stops it after six changing C-state iterations.
The independent reference and normative VM both emit `02 19 1f 08 17 0f`
in 97 guest steps under EOF and binary stdin. Five invalid C sources and
seven forged ASTs reject without publishing a guest.

The bound, right subtree, source order and every replay iteration remain
independently checked; this does not provide general guest runtime sequencing
or solve the original twelve-byte unmasked output-layout blocker.

### Rechecked unsigned-local `for` limits in complete C programs

A complete masked twelve-step Fibonacci source first refused a `for` whose
upper bound was stored in an unsigned local instead of an inline literal.
The checked induction projector now evaluates a pure source-backed bound
expression through the normal typed unsigned expression proof and **replays
that same Clang subtree after each body and induction update**, because C
re-evaluates the condition each trip. A second whole C source grows `limit`
from 3 to 6 across the first three iterations; freezing it at entry would
emit only three bytes. The normative guest instead emits the six-byte prefix
`02 19 1f 08 17 0f` in 97 steps, while the unchanged twelve-trip local
bound emits the independent twelve-byte oracle in 47 steps. Both sources
were verified under EOF and binary stdin. Effectful bounds, out-of-range
bounds, unbounded growth, forged references/types/spans and incomplete ASTs
refuse before guest publication. This is compile-time bounded C-state
projection, not dynamic Malbolge control flow or arbitrary guest I/O.

### Re-evaluated unsigned-local `for` increments in complete C

The complete masked Fibonacci source now uses `i += stride`, with a prior
`unsigned stride = 1U` and an in-body write to `stride = 2U` after the
third output. The pinned frontend accepted the whole C program, but the
JSON adapter first refused its nonliteral induction step. The bounded
source-backed projector now checks a pure unsigned increment expression,
remembers its exact Clang subtree and re-evaluates it **after every loop
body**, before updating the protected counter and rechecking its bound.
Only positive strides of at most twelve are supported; assignment-form
`i = i + stride` follows the same rule. An out-of-range or impure stride, forged
source geometry, or an execution beyond twelve iterations refuses without
publishing a guest. The six executed recurrence iterations with a moving
stride produce the independent masked oracle `02 19 1f 08 17 0f` in 97
normative VM steps under EOF and binary stdin. This is finite source-state
replay, not dynamic guest induction or unrestricted C expressions.

### Source-checked middle `default` in a complete C switch

A full twelve-iteration masked Fibonacci source now places `default`
between checked `case` labels, with its own source-verified switch-local
`break`. Unlike a terminal default, this must retain its independent
pre-switch local state while later cases still override dispatch selection.
The checked projector requires at least one prior and one later case,
closed Clang ancestry, exact statement spans and a final switch break.
It rejects fallthrough into or out of the middle default, extra output
or input effects, and unsupported AST changes. The real guest VM emits
independent oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps
under EOF and binary stdin. This is finite source replay, not runtime
C switching or generalized unmasked Fibonacci byte-stream layout.

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

Two nonzero source-distinct `putchar` calls preserve separate source spans
and SSA definitions, even when their observed bytes are equal. A bounded
pair composer searches actual guest arithmetic and independently replays the
emitted source. A two-iteration conditional C loop with different XOR arms
now emits `38 38` from one relocated guest write and two output instructions.
Three loop observations from two source-distinct conditional call sites now
also preserve three separate typed SSA definitions when every emitted byte
agrees. The source-proven three-iteration C recurrence produces `38 38 38`
in the real normative guest VM; an unwitnessed multiplication-derived trace
still refuses.
The layout uses one or two relocated guest writes and three real output
instructions, independently re-admitted by the publisher. This is not
general C runtime state or arbitrary byte emission.
Repeated observations from the *same* C call retain the existing shared-SSA
path. Other unproved pairs refuse; three-call sequences use their own
separately verified guest grammar.

### Exact three-`putchar` source output traces

Pinned Clang 22.1.8 source evidence admits three successive constant
`putchar` outputs with three distinct source-proven byte values, including the
legacy `Z%H`, `Q.O`, `Y-P`, `T"O`, and `T"Q` witnesses. Each source call
retains its argument span, canonical `u8` definition and output identity.
Candidate values are independently admitted by the guest layout backend.
The selected
`--distinct-literal-triple --typed-stdin` mode is independently checked by
the layout publisher and the normative guest VM. A two-call prefix such as
`Z%` has no independent two-byte guest witness and is rejected at layout;
unsupported three-byte traces and unsupported subsequent calls also reject.
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

The opt-in `--distinct-literal-six` bridge retains its original
current-profile `51 1c 4f 1d 50 1b` 15-step guest witness. A finite,
source-independent state-space solver now admits independently validated
nonhistorical six-effect streams with **either** zero or nonzero leading
bytes. The pinned Clang pipeline proves a complete two-trip C `while`
recurrence with branch-selected output triples and intervening local writes.
Its independent source oracle is `35 36 35 00 50 1b`, including an
interior NUL and repeated byte; actual normative VM execution emits that
stream in 19 steps for empty and nonempty input. The older zero-prefix
`00 51 22 1b 37 39` 23-step witness is also preserved.

Every admitted C effect remains bound to distinct source/SSA identities.
The compiler re-admits typed/MCTR and graphical source, validates safe
relocated guest data writes and exact output bytes in the normative VM,
and publishes no artifact if any stage fails. The search is bounded, not a
proof that arbitrary output sequences are synthesizable. C branches and
state are evaluated at compile time, not executed as guest control flow.

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

### Verified forty-six-byte source bridge

The frontend admits only the exact independently VM-proven 46-byte
`putchar` literal trace. Proper prefixes, changed constants and further
outputs fail closed; the legacy 45-byte and Q. routes are unchanged.

### Verified forty-seven-byte source bridge

The Clang JSON adapter admits only the exact separately VM-proven 47-byte
`putchar` sequence, preserving literal SSA provenance and rejecting any
strict proper prefix or altered value. No arbitrary byte stream is admitted.

The exact 48-byte `putchar` literal sequence is admitted only under the
`--distinct-literal-forty-eight` mode, with all 48 constants and source
order checked against the independent 121-step guest witness. No strict
proper prefix or altered constant is promoted to source compilation.

### Source-bound automatic-local byte output

An additional closed Clang JSON shape accepts one automatic `u32` local
initialized by an integer literal, optionally followed by up to eight ordered
assignments of integer literals, then read exactly once by `putchar`. All
values must be in `0..255`. The adapter validates the complete Clang preorder,
source spans, symbol identity and every write before eliminating dead stores:
the live canonical `u8` SSA constant is attributed to the **last** assignment
(or the initializer if there is no assignment). The independently verified
zero/seeded-byte guest publisher still executes the real output instruction.

`tests/compiler/c-frontend/accepted/local_reassigned_output.c` writes `0`,
then `66`, then `65` and emits `0x41` in 31 normative guest VM steps. Tampered
symbols, skipped or reordered writes, aliasing, and other effects reject.

A second bounded source-bound route accepts ordered `= value + N`,
`= value - N`, or `= value ^ N` writes with a matched read of the same
unsigned local, a literal `u32` operand, and every intermediate result in
`0..255`. The expression tree, source ancestry, operation, types, and
read/write identity must agree with pinned Clang before promotion to one
final byte SSA value. The real guest VM emits `0x41` for the tracked
`60 + 8`, XOR `3`, minus `6` C fixture. Multiplication, overflowing or
underflowing byte arithmetic, aliases, branches, loops, and general runtime
state reject. This is bounded source-constant propagation, **not** guest
runtime arithmetic or general mutable storage.

A separate straight-line multi-local route admits two through eight distinct
source-bound automatic `u32` locals initialized from byte constants or
previously defined locals, with checked `+`, `-`, and XOR expressions and
up to 16 ordered definitions/writes. Materialized locals must fit a byte;
source-proven `u32` intermediate additions can temporarily exceed
255 or wrap modulo 2^32 if an enclosing expression reduces them to a byte. Every read is resolved
to the exact declared Clang symbol, with checked ancestry, types, source order, and spans; the final typed `u8` constant
retains its last defining expression's provenance. Exactly one source-backed
`putchar` reads a proven local or evaluates a fully checked argument.
The tracked three-local program computes
`(60 + 8) ^ 3 - 6` and emits `0x41` in 31 normative VM steps. Unknown reads,
new effects, unproven arithmetic, loops and general runtime state
remain unsupported. The adapter never computes these arithmetic operations
inside Malbolge; only its output effect executes in the guest VM.

The multi-local route also accepts a tightly closed, source-constant C
`if ((value & mask) == literal)` with both brace-delimited arms containing
one ordered assignment to a known local. It proves the exact pinned-Clang
comparison, parentheses, `u32` read and bitwise AND, both source-bound arm
assignments, and the chosen successor state. Only one final `putchar` runs
in the guest. In the paired true/false fixtures, `60 + 6` selects XOR `3`
and `60 + 7` selects XOR `2`; both emit `0x41` in 31 normative VM steps,
with distinct selected expression source spans. Unsupported conditions,
missing arms, extra effects, foreign symbols, nested control flow, loops,
and general runtime branching refuse source admission. This is compiler
constant-flow evaluation, not guest execution of the C comparison or branch.


### Source-proven `putchar` expression argument

The bounded multi-local route now also proves a complete Clang
`putchar((int)(result ^ 3U))` argument after an ordered, source-proven
`if/else`. The explicit `i32` conversion contains one parenthesized `u32`
expression; only the existing checked `+`, `-`, XOR and AND tree can be
folded. Every read must refer to a declared automatic local, final stored and
emitted values must fit `0..255`, and call/conversion/parenthesis spans and
parent identities must match the pinned AST. The emitted typed `u8` constant is
attributed to the argument expression, not to a stale prior local assignment.

`local_expression_output.c` emits `0x41` in 31 normative VM steps. A second
source variant selects the opposite branch and emits `0x42` in 69 steps.
The real layout backend rejects bytes without a verified positional witness;
for example the attempted `0x40` variant refused
`Layout(UnsupportedEffectTrace)` rather than publishing a guest program.
Changed AST operators, aliases, source ancestry, extra effects and unsupported
multiplication all reject. This extends bounded compile-time constant-flow
analysis and **does not** implement runtime guest arithmetic, general
`putchar` expressions, loops or mutable guest storage.


### C comma-expression assignment sequencing in a full recurrence

A complete twelve-step masked Fibonacci source now performs its state
transfer through `a = b, b = next;` rather than two expression statements.
The checked projector replays two to four source-ordered unsigned local
assignments within a single C comma expression, using the exact Clang
parent-child preorder, unsigned types, per-write references, nonoverlapping
same-line source spans and a comma-space separator. The left write commits
before evaluating the right write. Parenthesized or effectful operands,
arbitrary comma expressions and general runtime C execution are not
admitted by this bounded proof. The real current-profile guest emits twelve
independently calculated masked Fibonacci bytes in 47 steps under EOF and
binary stdin. Longer nested variants remain separately timeboxed; a
fifth assignment refuses. Five unsupported C variants and five forged ASTs
reject before guest publication; the original unmasked stream still
fails at layout.

### Source-backed comma-separated unsigned declarations

The bounded multi-local C flow also admits an ordinary same-line
`unsigned a = 1U, b = a;` declaration. Pinned Clang represents it as
one declaration statement with two ordered `variable-declaration` children,
not as two statements. Each initializer is proven against the previously
established automatic `u32` locals; no forward or indeterminate read,
side-effectful initializer, duplicate symbol or hidden node is discarded.
The group requires the canonical shared `unsigned ` prefix, exact two-byte
comma/space separation, consistent source byte/column spans, and its
single closing semicolon. The eight-local budget still applies.

Two complete twelve-iteration masked Fibonacci C variants (two initialized
names, or three names with one delayed first assignment) reach the
normative guest VM and emit `02 19 1f 08 17 0f 02 0d 03 10 13 03` in
47 steps under empty and binary stdin. Forged group structure, invalid
reads and hidden source effects reject without publishing an artifact.
This is compile-time source-state projection, not dynamic guest storage
or generalized byte-stream synthesis.

### Fibonacci masked-sum arithmetic boundary

The source-bound `local_masked_sum_output.c` now evaluates
`next = (a + b) & 255U` with exact nested `u32` parentheses and a
**nonwrapping** intermediate sum wider than a byte. It does not truncate
`a + b` before applying the mask: `233 + 144 = 377`, then `377 & 255 = 121`.
All leaf literals and materialized local values are still byte-bounded;
checked `u32` addition/subtraction, source spans, AST operators, declared
symbols and parentheses must agree before a byte-sized assignment commits.
The direct `putchar((int)next)` cast also admits a source-proven explicit
`i32` conversion enclosing the local read. Unproven or excessive cast spans
reject, and wider unmasked results cannot silently become byte locals.

The real guest VM emits `0x41` in 31 steps after the odd branch XORs 56;
a source variant with `232 + 144` selects the even branch and emits `0x42`
in 69 steps after XOR 58. Unsupported operators and forged Clang ancestry
reject before guest publication. All computation and branch selection here
remain compiler-time constant propagation. This does not add runtime C
arithmetic, dynamic state, loops or arbitrary guest byte streams. The
original complete twelve-byte Fibonacci program remains unsupported.


### Bounded output-free `for` evaluation

A closed Clang `for (unsigned i = 0U; i < N; ++i)` with `1 <= N <= 12`
can now be evaluated during compilation, provided its brace-delimited body
contains only proven `u32` local declarations, assignments, and the admitted
`if/else` assignment selection. The private loop counter starts at zero,
advances exactly once per iteration and cannot be assigned inside the body.
The adapter replays the identical checked AST with bounded lexical state,
removing iteration-local declarations at each scope exit and retaining outer
local writes. Unsupported effects, nested loops, dynamic conditions, aliases,
unknown AST nodes and extra output calls refuse before publication.

`local_static_loop_output.c` exercises eight Fibonacci-like updates with a
masked sum, conditional and state transfer, then emits one byte after the
loop. Independent C arithmetic gives `b = 42` and `42 ^ 107 = 65`; the
normative guest emits `0x41` in 31 VM steps. A seven-iteration variant also
reaches independent VM parity, while altered control and output effects
reject. The Malbolge guest executes only the **final output**; this is not
runtime loop execution. The complete Fibonacci program's twelve nonzero outputs
inside the loop still require a verified general byte-stream backend.

### Checked unsigned multiplication in a bounded recurrence

`local_multiplicative_recurrence_output.c` exercises three source-proven
iterations with two unsigned locals, multiplication, masking, an odd/even
conditional assignment, and a final expression-derived `putchar`.
The closed expression walker now admits source-proven `u32` multiplication
with C modulo-2^32 semantics. It retains a product larger than 255 through `& 255U`
and narrows only at a local store or output. The independent recurrence
visits `15, 210, 22`, finishes with `a = 23`, and emits `23 ^ 86 = 65`.
The normative VM outputs `0x41` in 31 steps, including with nonempty input.
Unproven operations and extra effects still reject without a guest.
This is **compile-time evaluation**, not Malbolge multiplication or C runtime
state. The full twelve-byte Fibonacci target still fails at guest layout.

### Checked unsigned remainder in a bounded recurrence

`local_remainder_recurrence_output.c` extends the complete three-iteration C
stateful probe with `next % 17U` in the even branch after a checked masked
product. The source-proven `u32` walker accepts `%` only for a nonzero
divisor. Its independent intermediate stream is `15, 210, 190`; the final
state is `a = 2`, and `2 ^ 67 = 65`. The real guest outputs `0x41` in 31
normative VM steps under both empty and nonempty input. A zero remainder
divisor and unwitnessed effects refuse without publication.
This evaluates C local state at compile time, not at guest runtime. The
original twelve-byte Fibonacci output still has no general layout witness.

### Checked unsigned division in a bounded recurrence

`local_division_recurrence_output.c` compiles a complete three-iteration
unsigned C program with masked multiplication, conditional state writes,
`next / 17U` in the even arm, and one final expression-derived `putchar`.
The closed Clang expression proof now admits `/` through `u32::checked_div`,
refusing a zero divisor and preserving integer truncation toward zero.
The independently calculated products are `15, 210, 170`; the final
state is `a = 11`, so `11 ^ 74 = 65`. The normative Malbolge VM emits
`0x41` in 31 steps with empty or nonempty input. A zero divisor and a
source mutation to unsupported `>>` fail without publishing an artifact.
The prior first-declaration rejection was reproduced before this repair.

Division and C loop/branch state still execute **during compilation** in
this constant-propagation path, not in Malbolge. The full twelve-byte
Fibonacci program still needs generalized guest byte-stream synthesis.

### Checked unsigned shifts in a bounded C recurrence

`local_shift_recurrence_output.c` tests a complete source-proven three-step
recurrence with automatic locals, a masked product, `<< 2U`, a branch with
`>> 3U`, state transfers and an expression-derived `putchar`. The Clang AST
adapter now admits both shifts only for exact unsigned `u32` operators and
checked counts from 0 through 31. Left shifts use C unsigned modulo-2^32
semantics; right shifts are logical. Unknown types, operand ancestry, bad
counts and extra effects still refuse at the source projection. The source
oracle visits `60, 80, 192` and finishes with `25 ^ 88 = 65`.
The golden normalized Clang AST is checked by independent typed-SSA and
mutation regressions. This is compile-time constant propagation, not C shift
instructions or loop execution in the Malbolge guest. The original twelve-byte
Fibonacci program remains blocked at guest layout.

### Checked unsigned bitwise OR in a conditional recurrence

`local_or_recurrence_output.c` tests an entire three-iteration source-backed C
program with two automatic locals, multiplication, `|`, masking, shifts, both
conditional assignment arms, state transfers and a final `putchar`. The pinned
Clang adapter previously rejected the first local declaration. Its closed
`u32` expression proof now admits bitwise OR only on exact typed operands,
checking every source span and symbol before performing integer OR during
compilation. The original recurrence visits `31, 248, 16` and ends with
`3 ^ 66 = 65`; a changed OR mask visits `15, 120, 152` and ends with
`18 ^ 83 = 65`. Both compiled capsules emit actual byte `0x41` in 31
normative VM steps on empty and nonempty input. Logical OR, a widened store
without masking, and a side-effecting read reject before guest publication.

This evaluates C expressions at compile time and emits a proved constant
byte; it does not implement runtime guest OR or arbitrary C state. The
original twelve-byte Fibonacci program is still blocked at guest layout.

### Checked unsigned compound local assignments

The bounded local-state evaluator now admits exact `+=`, `-=`, `^=`,
`&=`, `|=`, `*=`, `/=`, `%=`, `<<=` and `>>=` on automatic unsigned
32-bit locals, including full-width intermediates. It checks the direct
Clang compound-assignment node, active lexical symbol, source ancestry and
single-line token gap (four bytes for two-character and five for
three-character operators, including adjacent spaces). Every operation
uses the prior local value and a completely proven right-hand expression,
with wrapping unsigned arithmetic, checked division/remainder and shift
counts below 32. The bounded `for` induction proof remains separately
restricted. No arbitrary C-side effects or runtime guest local storage
are introduced.

Two complete twelve-iteration masked Fibonacci C programs exercise
`|=`/`&=` and wide `%=`, `<<=`, `>>=`, `*=`, `/=` combined with `+=`.
Both match the independent twelve-byte oracle through the real normative VM
on empty and binary input, in 47 steps each. Division by zero, invalid
shifts, split operator tokens, signed casts and forged normalized AST
parentage/metadata refuse without guest publication. The adapter cannot
independently recover same-width C operator characters from normalized
JSON; the pinned frontend and source-digest boundary remain trusted.
The unmasked original Fibonacci guest stream remains unimplemented.

### Ordinary C `int` constants converted to unsigned locals

The bounded automatic-local evaluator now accepts the exact pinned-Clang
implicit `integral-cast` from a nonnegative `i32` integer literal into `u32`
when the cast and its child share a source span and independently agree on
the canonical integer value. This admits ordinary C spellings such as
`unsigned a = 1;`, `unsigned i = 0;`, `i < 12`, and `next & 255`, alongside
the previously supported explicitly suffixed `1U` and `255U`. Finite `for`
bounds and positive strides remain byte-range and require a source-proven
literal, not an arbitrary folded expression or variable. Signed arithmetic,
negative literals, large signed widths, explicit casts and unrelated
conversion shapes are not silently admitted.

A complete twelve-step masked Fibonacci recurrence initially rejected its
first unsuffixed initializer; after this narrow proof, the same C program
emits the independent twelve-byte oracle from the actual normative guest
in 47 steps on empty and binary stdin. Source negatives and forged cast,
leaf, and loop-bound metadata reject before publication. This remains
compile-time C-state folding; it does not provide arbitrary signed C
expressions, dynamic guest unsigned state or general output synthesis.
The original unmasked Fibonacci stream is still blocked at guest layout.

### Uninitialized automatic unsigned locals with proven later writes

The closed bounded local-flow projection accepts `unsigned next;` followed
by an ordinary source-checked `next = value;` before its first use. It
records an absent initial value, checks the exact Clang name/semicolon span
of the one-line declaration, and requires the active canonical local symbol
on each subsequent write. The local becomes readable only after a selected
plain assignment; `next++`, `next += value`, source reads, and unselected
conditional writes cannot initialize indeterminate C state. For-loop
induction variables remain required to have initial values. The source
hash and pinned Clang frontend remain the authority for characters the
normalized JSON does not expose.

A full twelve-step masked Fibonacci recurrence with this declaration form
emits the independent twelve-byte masked oracle on the actual normative
guest in 47 steps for both direct and selected-branch writes. Invalid C and
forged AST
mutations reject without publication. This does not make guest local state
dynamic or unlock the original unmasked Fibonacci output.

### Source-backed unsigned locals initialized from Boolean predicates

A pure C comparison or logical negation produces `int`, which C implicitly
converts to `unsigned` on local initialization or assignment. The bounded
source-state evaluator now checks an exact `integral-cast` from a complete
`i32` predicate to `u32` with identical source spans. Only a fully proven
unsigned comparison, parenthesized Boolean, or pure `!`/`&&`/`||` predicate
can produce the stored zero or one. An explicit cast, signed arithmetic,
side effect, division by zero, detached child or malformed AST refuses.

Three complete twelve-iteration masked Fibonacci variants store equality,
negation or ordered comparison results in a loop-local `unsigned even`, then
select both real C branches using `if (even)`. Each emits the independent
`02 19 1f 08 17 0f 02 0d 03 10 13 03` oracle on the normative VM with
empty and binary input. Four invalid C variants and seven forged normalized
AST mutations refuse publication. This is bounded source-backed state
projection: the guest does not calculate the predicate at runtime. The
original unmasked twelve-byte output is still unsupported at layout.

### Source-checked nonempty case-to-case fallthrough

A full twelve-trip masked Fibonacci C source now admits one adjacent
nonempty case-to-case fallthrough when the first case performs only
proven unsigned local writes. The next case is checked **twice**, from
the source-backed pre-switch state for direct entry and from the prior
case's final state for fallthrough; both replays must consume the same
complete pinned-Clang subtree and reach the same explicit switch break.
The selected state alone survives. The program's two paths require
*different* incoming local values, so forgetting the carried writes would
change the output. The real normative VM emits the independent twelve-byte
masked Fibonacci oracle in 47 steps under EOF/binary stdin. Five unsupported
source mutations and six normalized-tree forgeries refuse without publication.
A third complete masked Fibonacci recurrence carries a local write from
`case 2U` into a final `default`, which also accepts direct dispatch from
values 1 and 3 with different initial locals. The adapter now separately
replays both default entry states against identical pinned-Clang source nodes
and the same break, retaining only the selected path. The normative guest
executes twelve independently calculated Fibonacci output bytes in 47 steps
under empty and binary stdin. A separate complete source also traverses
`case 0U` to `case 2U` to `default`, proving two consecutive edges and
separate direct entries at the receiving labels. Five invalid source
variants and seven forged ASTs refused before the longer-chain rule.

A second full recurrence proves two consecutive nonempty fallthrough edges
(`case 0U:` to `case 2U:` to `case 1U:`), with separate direct entry into
all three cases. The projector independently replays the exact pinned-Clang
subtree from each candidate entry state and requires identical source-node
boundaries. A further complete twelve-trip C recurrence extends that chain
through a third nonempty edge into `default`, proving the direct default
entry separately from all three carried C local states. Source-ordered
additional cases extend it to the eight-distinct-case limit. The new bound
is on checked case labels, not an arbitrary two-edge chain length: every
carried state is replayed over each remaining real Clang subtree and the
same final switch-local break. The real normative guest emits the independent
masked twelve-byte oracle in 47 steps under both empty and binary stdin.
A ninth distinct case, output before fallthrough, effectful input, an arm
with more than four effects, or forged ancestry/spans/operators still refuses
before guest publication. This proves finite compile-time C-state replay,
not dynamic guest switching or the original unmasked byte stream.

### Source-checked ordered switch-arm effects

An entire four-way twelve-trip masked Fibonacci C recurrence now proves
per-arm dependent local writes: `selected = ...; transferred = selected ^ 0U;`
and one post-switch `putchar((int)transferred)`. Clang parents the first
statement below its case/default label and later statements below the switch
compound. The adapter checks the exact ancestry, source extent, order,
initialized reads and pure unsigned operations: at most four effects per
arm, with at most one terminal pure output and an explicit arm-local break.
Every candidate arm starts from the same pre-switch locals; only the selected
writes and its optional output survive. Unproved side effects, unbounded
fallthrough, extra outputs, output-followed-by-write, and additional effects refuse.
The original unmasked complete Fibonacci remains unsupported at guest layout;
this finite C-state projection does not implement runtime C switching.
The three full-source variants (un-grouped state transfer, grouped case/default
state transfer and an arm-local terminal output) each emit the independently
computed twelve-byte masked Fibonacci oracle in 47 normative guest steps under
empty and binary stdin. Six invalid C and seven forged AST cases refuse.

### Source-checked switch-local assignments

A complete twelve-step masked Fibonacci C source now selects one unsigned
local write through `switch (next & 3U)` and calls `putchar` once **after**
the switch. Each case or final default owns a single checked `=` or `^=`
statement and an explicit switch-local `break`. The projector verifies
all case arms from the same incoming local state, then commits only the
selected arm. This prevents unselected compound writes from changing later
case results. Empty-label case groups and a grouped final default remain
subject to the same complete Clang ancestry and span proof.

Direct assignment to an initially uninitialized `selected`, initialized
compound XOR assignment, and grouped compound assignment each emit the
independent twelve-byte masked oracle on the normative current-profile VM:
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under EOF and
binary stdin. Four unsupported C sources and six forged AST variants
refuse before publication. Switch-local declarations, general
fallthrough, dynamic guest switch execution and the original unmasked Fibonacci layout
remain unsupported.

### Source-checked `switch` without default

A complete twelve-step masked Fibonacci source also admits a C switch
without `default`: every checked `case` has its own source-bound assignment
and switch-local `break`, while unmatched selector values preserve the
initialized pre-switch local and its later output. A matched group of
adjacent empty labels is admitted with the same effect. The closing brace
must immediately follow the last proved break in the bounded Clang shape;
unknown effects and forged spans reject without guest publication.
Both full sources emit the independently computed twelve-byte masked
oracle on the normative VM in 47 steps under empty/binary stdin; three
unsupported source mutations and six forged ASTs reject. This is finite
C-state replay, not runtime guest switching or general C output layout.

### Source-checked `switch` with one case and default

The complete masked twelve-step Fibonacci C source additionally admits
`case 1U: default:` as the final empty-label group, sharing one source-
proved pure output and switch-local break. Pinned Clang nests `default`
under its preceding case, and the proof requires its exact parent, source
extent, ordering and trailing break. Together with `case 0U: case 2U:`,
the full source exercises all four dispatch destinations and emits the
independent twelve-byte oracle in 47 normative guest steps under EOF
and binary stdin. Three valid but unsupported effectful/misordered C
mutations and six forged AST variants refuse without guest publication.
This does not admit general fallthrough or dynamic guest switching; the
original unmasked byte stream remains unsupported at layout.

A complete masked twelve-step Fibonacci C source also shares a single
output arm between consecutive `case 0U: case 2U:` labels. Pinned Clang
nests the label nodes, which now admit a checked common call and switch-local
break without inventing a second effect. All four dispatch values occur;
the actual guest emits the independent twelve-byte oracle in 47 steps under
EOF and binary stdin. Two sources with an effect or break before a second
label and six forged nested Clang trees refuse without publication. The
bound remains eight distinct case labels in total and a final `default`.
This particular label-group proof admits only empty labels; the
separate bounded nonempty case-to-case fallthrough rule is documented above.
Dynamic guest switch execution remains unsupported. Unmasked Fibonacci remains unimplemented.

The source-backed `switch` selector also accepts more than one explicit
case when each selected and unselected arm proves its own direct `putchar`
and switch-local `break`. A red-first complete twelve-step masked Fibonacci
program with `switch (next & 3U)`, cases 0U, 1U, 2U and a final default
now reaches each of the four dispatch arms. The independent masked oracle
is emitted by the normative guest VM in 47 steps under empty/binary stdin;
four unsupported source variants and nine forged middle-case AST variants
refuse before guest publication. The proof is capped at eight unique,
ordered `u32` case labels and exactly one final default; unbounded
fallthrough, multiple effects per arm, case-local declarations, and arbitrary guest
runtime branching remain unsupported. Original unmasked Fibonacci guest
layout still fails closed.

A complete twelve-step masked Fibonacci C source now admits a `switch`
whose source-proven unsigned dispatch has exactly one constant `case` and
one `default`. Each label directly owns one pure `putchar` expression,
followed by an explicit switch-local `break` statement in its common
compound body. Both labels and their output arguments must be proven;
only the selected call is materialized in typed output IR. Switch breaks
do not terminate the surrounding bounded induction. The proof checks
pinned Clang parentage, constant label value, source spans, ordering,
metadata, two break keywords and the absence of trailing body effects.
Fallthrough, extra cases, mutations of the dispatch and effectful case
bodies are unsupported and refuse without guest publication.

Two complete twelve-iteration C programs, with case labels `0U` or `1U`
and opposite `default` parity, emit the same independent masked twelve-byte
oracle on the normative guest VM in 47 steps under empty/binary stdin.
This is a finite compile-time projection, not dynamic guest switch
execution, input-conditioned C state or general C fallthrough support.
The original unmasked twelve-byte Fibonacci output remains unwitnessed.

### Unbraced single-effect C branch arms

The bounded unsigned-local projector now accepts ordinary unbraced
single-statement `putchar` calls or checked unsigned local assignments as
direct `if` or `else` children of the pinned Clang AST. Each arm may instead
remain a compound block. Both arms are independently source-checked before
committing the selected state and output. Direct calls require pure, proven
arguments; direct plain and compound local writes reuse their existing
unsigned binding, initialization, source-span and operator checks. Unbraced
declarations, unknown effects, other calls and forged metadata still refuse.

A complete twelve-step masked Fibonacci C recurrence with both output arms
unbraced first failed at the adapter without a guest artifact. After this
source-checked replay extension it emits the independent twelve-byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 normative guest VM steps
under empty and binary stdin. Two unsupported C sources and six forged
normalized Clang trees refuse publication. A second complete recurrence
uses direct branch writes to an initially uninitialized `unsigned selected`
followed by `putchar((int)selected)`; it emits the same oracle in 47 VM
steps under both inputs. Two negative source and five forged-AST cases for
this write path also refuse publication. This still folds source-proven
state at compilation; unmasked Fibonacci guest layout and dynamic C
control flow remain unsupported.

### Unbraced nested `for` in the source-proven recurrence

The twelve-byte 3-by-4 masked Fibonacci recurrence also admits an outer
`for (unsigned row = 0U; row < 3U; ++row)` whose sole unbraced body is the
inner `for` with its own compound body. The source-checked outer loop may
directly parent exactly one inner `for` ending at the outer statement's end.
Both induction symbols, finite bounds, source spans and nested effects are
replayed as in the braced form; a forged parent, altered tail or write to
an active counter refuses without guest publication. This ordinary C shape
emits the independent twelve-byte oracle in 47 normative VM steps with
empty and binary stdin. Arbitrary unbraced loops, runtime guest induction
and the original unmasked Fibonacci stream remain unsupported.

### Unbraced `for`/`while` with one complete conditional body

The bounded source-backed flow also accepts an ordinary `for` or `while`
whose sole unbraced statement is an `if/else`. The conditional is a direct
Clang child, consumes the exact loop tail, and replays both checked branches
without inventing a compound scope. The selected branch may declare its
own `unsigned next`, emit a byte, and update enclosing recurrence state;
for `while`, a source-proven counter update inside both arms advances the
next predicate check. Unexpected siblings, counter tampering, forged
ancestry and unknown effects refuse before guest publication.

Two red-first complete twelve-iteration masked Fibonacci variants emit the
independent `02 19 1f 08 17 0f 02 0d 03 10 13 03` byte oracle on the
normative VM in 47 steps under empty and binary input. Five invalid source
cases and nine forged AST mutations refuse without artifacts. This is a
finite compile-time C-state projection, not dynamic guest C branches or
loops; the unmasked Fibonacci byte stream still fails layout admission.

### Direct `if/else` or `for` as an unbraced `do/while` body

The bounded C-state projector also admits a single source-proven direct
`if-statement` child of a `do-statement`, followed by its pure trailing
condition. Unlike `for` and `while`, the conditional body ends **before**
the enclosing `do` source span: the adapter checks direct Clang ancestry,
ordered source tails, the predicate and final semicolon without inventing a
compound scope. The body executes before each test, with selected writes and
outputs carried into the next bounded iteration. Additional direct body
effects, unknown side effects and forged AST parent/span/metadata refuse.

A full twelve-step masked Fibonacci C program first refused this ordinary
unbraced source form, then emitted the independently computed byte stream
`02 19 1f 08 17 0f 02 0d 03 10 13 03` on the normative guest VM in
47 steps under empty and binary stdin. Three invalid source variants and
five forged AST variants refuse without artifact publication. This extends
source-backed compile-time replay, not runtime guest control flow or the
still unsupported original unmasked Fibonacci guest layout.

A second full source-C recurrence places a bounded four-trip `for`
directly inside a three-trip `do`, incrementing a checked outer local on
every inner trip. The same direct-parent and trailing-condition proof
also admits this unbraced `for` child, retaining its own protected induction
symbol and all twelve selected output effects. The normative guest VM emits
the independent masked Fibonacci oracle in 47 steps with empty and binary
stdin. Three nonterminating or impure C variants and five forged AST cases
refuse without guest publication. This is bounded compile-time control
projection, not dynamic guest nested loops or the original unmasked layout.

### Function-body lexical scopes with shadowed unsigned locals

The closed multi-local projection also replays an explicit compound block
within the function body, using the same bounded source-parent and span proof
as nested loop blocks. An inner automatic `unsigned b` may shadow an earlier
outer `b` while the enclosing `a` remains writable. Reads and writes must
resolve to the innermost active Clang symbol; declarations inside the block
are dropped at its closing brace, without dropping proven enclosing writes
or guest output effects. Each block is bounded by the existing four-level
nesting and sixteen-effect limits. Unsupported statements, malformed source
geometry, uninitialized inner reads, extra effects and forged symbol links
still refuse; this is compile-time scope evaluation, not guest stack storage.

A complete twelve-iteration masked Fibonacci program with outer `b = 77U`,
inner `b = 1U` and the full recurrence inside that function-body block
initially refused at the JSON adapter without guest publication. After the
source-state proof extension, it emits a real 2,207-byte Malbolge capsule:
empty and binary stdin produce the independent twelve-byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 normative VM steps. Three
invalid-source and six forged-AST cases refuse without an output artifact.
A separate source program declares inner `b = 90U`, closes the block, then
outputs the surviving outer `b = 65U`. The normative guest emits `41` in
31 steps from a 1,295-byte capsule on both input patterns; forging the
post-scope read to the expired inner symbol refuses without publication.
The unmasked original still lacks generalized guest layout; P0 stays open.

### Branch-selected `putchar` effects inside a bounded `for`

The source-proven loop evaluator now accepts one `putchar` in each arm of
an `if ((next & 1U) == 0U)` inside its brace-delimited loop. It validates
both Clang call subtrees and their evaluated arguments on every iteration,
keeps only the selected effect in source execution order, and rejects
unknown calls, extra effects or unchecked arithmetic. The tracked
`local_loop_branch_output.c` retains Fibonacci state and emits zero by
`next ^ next` or `next - next`, according to the branch. Both arm proofs
must succeed even when one arm is not selected.

A twelve-iteration source compiles to one zero SSA and twelve separate
`ByteOutput` instructions, then executes as twelve guest zero bytes in
13 normative VM steps. A seven-iteration variant reaches seven bytes in
eight steps. All C loop state and predicates remain compiler-time constants,
not guest runtime arithmetic or control flow.

When selected loop outputs differ, the projection now retains each source
byte in its own typed `u8` SSA definition and matches that definition to
its exact `ByteOutput` call span. It selects the existing independent guest
trace mode for up to twelve source-proven selected effects; the backend
must still verify the exact ordered values. The full branch-and-loop probe
`local_loop_distinct_output.c` emits `Q.` from separate even/odd outputs
in the normative VM. Changing its source output byte refuses publication.
The original twelve-byte Fibonacci experiment passes this C projection
and structural typed/ternary admission but is rejected by the closed
`--distinct-literal-twelve` guest layout as
`Layout(UnsupportedEffectTrace)`: its exact nonzero sequence is not
witnessed. This is neither a general stream backend nor runtime C state.

### Source-checked `while` inside a complete `for` recurrence

`local_nested_for_while_fibonacci.c` calculates each next Fibonacci value
using a two-trip source-local `while` inside a twelve-trip `for`. Its outer
branch observes the inner loop's writes before emitting a masked byte. A
second complete C variant breaks out of the inner `while` after its second
trip, leaving the outer `for` to emit its remaining bytes. The separate
source-C oracle and real normative VM agree on all twelve output bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps with empty and
binary stdin. Unbounded loops, unproved effects, induction mutations and
forged AST ancestry still refuse. These are finite compile-time source-state
projections, not dynamic guest loops.

### Three source-proven active `while/do` bodies

`local_three_level_while_do_fibonacci.c` uses two nested bounded
`while` loops and one mandatory-first `do/while` within a twelve-trip
`for` to compute and mask a complete unsigned Fibonacci recurrence.
The source-normalized adapter now proves three simultaneous while/do
bodies while preserving scope, loop exits, condition rechecks and the
outer induction symbol. The actual emitted Malbolge program outputs
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 VM steps. Unbounded
loops and fourth-level nesting remain unsupported; this does not
implement dynamic guest loops or general byte-stream synthesis.

### Source-proven mixed nested `while` and `do/while`

`local_nested_while_do_fibonacci.c` computes each next unsigned C
Fibonacci value with a two-trip `do/while` inside a two-trip `while`,
all inside a protected bounded `for`. Source-backed replay now tracks
both active `while` and `do` depths, refusing a combined fourth level.
The reverse `do/while`-then-`while`, two nested `do/while` bodies,
inner `break`, inner `continue`, and outer `break` also retain C control
flow and lexical lifetimes. All six complete C variants produce the
independent masked twelve-byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 real guest VM steps
under empty and binary stdin. Seven invalid source variants and eleven
forged Clang ASTs reject without guest publication, including effectful
predicates, fabricated ancestry and an unproved third nesting level at the time.
This is a finite source-state proof, not Malbolge runtime loop execution
or general unmasked output layout.

### Source-checked bounded `while` inside another `while`

`local_nested_while_while_fibonacci.c` nests a two-trip `while` for the
inner `pass` local inside a two-trip `while` for the outer `phase` local,
all inside a twelve-trip `for`. Every inner condition is re-evaluated against
its own source-checked local, and `pass` is newly declared each outer trip.
The normalized frontend previously refused the second `while`. The closed
replay now tracks at most three active while/do bodies, retaining nearest-loop
`break`/`continue`, lexical local lifetimes, and the protected `for` counter.
The complete compiled source emits the independent twelve-byte masked
Fibonacci oracle in 47 real VM steps on EOF and binary stdin. Fourth-level
`while/do` nesting, unbounded loops, input effects and forged Clang
ancestry remain unsupported. This is static source-state proof, not
guest runtime C execution or general unmasked byte-stream layout.

### Source-checked `do/while` inside a complete `for` recurrence

`local_nested_for_do_while_fibonacci.c` computes each next Fibonacci value
using a mandatory-first-trip, two-trip `do/while` nested in a bounded `for`.
The inner body updates unsigned locals and its trailing pure condition is
checked after each trip. Complete source variants use an inner `continue`
that still checks the trailing predicate, or an inner `break` that terminates
only the `do/while`, not the enclosing `for`. All three compiled guests
emit independent masked Fibonacci oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 normative VM steps under
EOF and binary stdin. Source mutations and forged AST ancestry refuse
without publication, including an inconsistent closing brace byte/column.
A separately proven two-level mixed `while/do` family is now admitted;
three active levels remain disallowed. Loops are finite compile-time
source-state replay, not guest runtime control.
The original unmasked twelve-byte stream still lacks a guest layout.

### Source-proven pure logical predicates

The bounded automatic-local/`for` constant-flow projection now admits
source-checked `&&` and `||` trees over previously admitted unsigned masked
comparisons. Each logical node has an exact `i32` type and two ordered,
independently proven operand subtrees; nested parentheses preserve Clang
ancestry and byte spans. Only effect-free, fully evaluable operands are
admitted. The compiler evaluates both sides even when C would short-circuit,
so unsupported or effectful skipped expressions reject instead of being
silently discarded. Selected loop branch arms are folded at compile time;
the actual guest executes only the verified output byte. This is not runtime
C logical short-circuit execution or unrestricted C control flow.

### Complete C recurrence with defined unsigned wraparound

`local_wrapping_recurrence_stream.c` proves a complete four-iteration loop
whose source-defined unsigned intermediates overflow 32 bits before explicit
byte masks. The closed `u32` evaluator now uses modulo-2^32 addition,
subtraction and multiplication, after the existing full Clang AST proof;
source-bound local stores and `putchar` arguments must still fit a byte.
An independent arithmetic oracle yields output `35 c0 09 e3`, which the
normative Malbolge VM emits from the complete pinned compilation on both empty
and nonempty input. Side-effecting, signed and undefined source mutations
refuse without guest publication. This does not lower runtime C arithmetic,
and the original twelve-byte Fibonacci stream remains layout-blocked.

### Direct unbraced loop exits in source-proven conditional arms

One source-checked `break` or `continue` can now be a direct unbraced
`if` arm within a bounded C loop, with a separately proven `else` body.
The selected keyword terminates the current lexical loop or advances to
its C `for` increment; the other arm is still independently proven for
well-defined source effects. The proof retains exact Clang parentage,
keyword width, byte span and absence of extra control metadata. It does
not discard any unproved statement after a selected exit.

Two complete nested Fibonacci C programs exercise the semantics rather
than a trailing no-op exit. A three-row, five-column `for` nest continues
on column zero and emits on the remaining four columns per row; a separate
six-column nest breaks at column four, skipping its unreachable final
column. Both preserve the full twelve-output independent masked Fibonacci
oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03`. Both capsules execute
in 47 normative VM steps under empty and binary stdin. Source mutations
with induction-counter side effects or unreachable suffixes and forged
Clang control nodes refuse without a published artifact.
This is bounded compile-time C control projection, not guest runtime
`break`, `continue`, generalized C loops or arbitrary guest byte synthesis.
The original unmasked twelve-byte Fibonacci layout remains unsupported.

### Source-backed comma expressions in unbraced conditional arms

An ordinary unbraced C `if` or `else` arm may now consist of one comma
expression containing two to four bounded unsigned local assignments. The
adapter reuses the left-to-right source-backed proof for body statements,
replaying each write before the next expression reads its local value.
Both Clang child trees and their enclosing `if` ancestry, full source spans,
operator types and same-line comma separators are checked, including the
unselected arm; only the selected state and its later output survive. Calls,
read-only operands, a fifth write and unproved C side effects reject.

`local_unbraced_comma_branch_fibonacci.c` exercises both unbraced arms on
all twelve iterations of a full masked Fibonacci recurrence. The real
normative guest emits independently derived output
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under empty and
binary stdin. Eight unsupported source variants and seven forged ASTs
fail closed without publication. This remains compile-time projection,
not guest runtime C sequencing; unmasked Fibonacci guest layout remains
unsupported.

### Dependent function-body comma initialization

The checked C comma statement is also available directly in the function
body. One complete source-ordered expression such as `a = 1U, b = a;`
updates the first local before the second expression evaluates the read.
Exact Clang ancestry, unsigned write metadata, same-line comma punctuation
and both full source endpoints (byte, line and column) must agree with the
first and last child. The additional endpoint check prevents a normalized
AST from claiming a different end column while keeping the original byte.

The tracked complete `local_function_comma_fibonacci.c` initializes a and b
from zero, then runs the twelve-step masked recurrence. The normative guest
emits the same independent twelve-byte oracle in 47 steps on empty and
binary stdin. Five unsupported C variations and six forged AST trees
reject without artifact publication. This is not general runtime guest
expression sequencing or unmasked byte-stream layout.

### Unbraced `while` directly owning `for`

A bounded `while` can own one directly parented unbraced `for`
as its entire body. The projector checks Clang ancestry, the exact
statement endpoint and inner counter scope, then re-evaluates the
outer predicate after the complete inner loop. The tracked full C
`local_unbraced_for_while_fibonacci.c` changes its outer bound in
each inner iteration while computing a branching Fibonacci stream.
The independent twelve-byte oracle matches the actual guest VM
under empty/binary stdin in 47 steps. Six invalid C sources and eight
forged ASTs reject without guest publication. This is bounded static
C replay, not dynamic guest loops or unmasked output synthesis.

### Unbraced C `while` nested directly in a bounded `for` (2026-11-11)

The full `local_unbraced_while_for_fibonacci.c` recurrence uses a direct
`while (phase < i)` body in a six-trip source-proven `for`, without braces
around the enclosing body. The inner condition observes the advancing outer
counter and produces two branch-selected masked outputs on each outer trip.
Clang admitted this complete C source, but the JSON adapter initially refused
the unbraced child. It now verifies the full direct child ancestry and source
endpoints, protects induction against inner writes and preserves inner-loop
`break` and `continue` semantics. All three complete C variants match the
independent twelve-byte Fibonacci oracle in 47 actual Malbolge VM steps on
both empty and binary input. Six unsupported source variants and eight forged
ASTs reject without guest artifacts. Runtime C loops and the original
unmasked Fibonacci output layout remain unsupported.

### Mixed unsigned-scalar logical conditions in bounded C

A source-proven C logical `&&` or `||` may now combine one pure `u32`
expression with one checked `i32` Boolean expression, in either operand
order. The finite evaluator proves both operands, preserves C truth values,
and retains the original source span and normalized Clang ancestry. Two
`u32` operands remain unsupported: their equal-width comparison topology
cannot safely distinguish a forged `==` from `&&` in normalized JSON.
Neither mutation nor I/O in either operand is admitted.

The complete tracked twelve-trip Fibonacci source
`local_unsigned_scalar_logic_fibonacci.c` combines a nonzero unsigned
bit expression with nested Boolean comparisons. Pinned Clang and the
actual normative guest VM agree on twelve masked bytes in 47 VM steps.
Its C branch and recurrence still execute at compile time, not as dynamic
guest control flow. The original unmasked Fibonacci layout is not solved.

### Source-proven scalar induction guards in bounded C for loops

A complete descending unsigned C recurrence now uses
`for (unsigned i = 12U; i; --i)` rather than an explicit comparison.
Pinned Clang admits the entire program; the JSON adapter previously
refused it. The bounded source-flow proof now accepts a direct
lvalue-to-rvalue read of the exact protected induction counter, its
complete source span, and canonical semicolon separators. The bound
is zero and the step must descend safely without unsigned wraparound;
unsupported or effectful scalar guards are not discarded.

The full `local_scalar_guard_fibonacci.c` C source emits twelve masked
Fibonacci bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 normative
guest VM steps under EOF and binary stdin. Pinned Clang normalization
also covers postfix, compound and assignment decrements; full guest
parity for those alternate spellings is not established. Four
unsupported C mutations and eight forged normalized AST nodes refuse. This is
finite source-state replay, not guest runtime loop control or an unmasked
Fibonacci layout.
