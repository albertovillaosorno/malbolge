# Parametric guest byte-stream emission

## Status

Proposed. Generalized compiler behavior and its proof are not implemented.

## Purpose

**First experiment, then verify.** Try one demanding, complete C program
before increasing output-byte counts or the verification fixture inventory.
Repair the first real compiler gap and rerun the same whole program; only
after success introduce a generated verification matrix and independent
end-to-end oracle. The maximum N is not a product progress metric.

## Scope

The existing corpus is useful regression history and may remain SHA-pinned.
A new example must establish a previously untested semantic boundary.
Increasing the byte count from 48 to 49 without such a boundary is not
an acceptable completion milestone.

The work belongs to the C frontend, typed lowering, layout backend, VM,
and their tests. It does not require a single enormous hand-authored C file
or hundreds of individual documentation pages.

## Current Behavior

### First complex C experiment

The following compact function uses local state, a bounded loop, a branch,
integer arithmetic, and observable guest output. It was intentionally tried
as a single complete program before creating any additional small cases.

```c
#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 12U; ++i) {
        unsigned next = (a + b) & 255U;
        if ((next & 1U) == 0U) {
            putchar((int)next);
        } else {
            putchar((int)(next ^ 0x5AU));
        }
        a = b;
        b = next;
    }
}
```

An independently derived reference returns these twelve bytes:
`02 59 5f 08 57 4f 22 6d 03 90 b3 23`. The pinned compiler attempt on
2026-11-05 failed at `c2malbolge_json` with the diagnostic `Malformed`,
before publication of a guest program. This is a real failed
experiment, not proof that the compiler supports general C.

The first adapter defect was confirmed and fixed in DCO commit
`e5773e312`: the Clang schema already defined `storage_duration`, but the
closed JSON adapter had omitted it. The adapter now admits the specified
`automatic`, `static`, and `thread` values as metadata while still rejecting
unknown fields and values. Its supported effect-free and literal-output
paths reject that extra metadata instead of silently discarding state.

With the same program and updated adapter, the real pinned pipeline now
reports `Unsupported; unlowered C declaration-statement` at the first local
variable, with the C source line and column, and publishes no guest. The
tracked experiment is
`tests/compiler/c-frontend/accepted/conditional_fibonacci.c`, replayed by
`tests/test_compound_c_pipeline.py`; its oracle is independently calculated.
That test requires explicit failure while state semantics are unsupported
and will require actual normative guest-VM parity if compilation succeeds.
This is a repaired **schema/diagnostic** gap, not completed C lowering.

### First source-bound automatic-local output

A separate pinned-Clang source now exercises a real automatic `unsigned`
local initialized to `65U`, then read by `putchar(value)`. The closed JSON
adapter admits the exact single-definition/single-use AST, connects the
source-bound declaration to its read, and promotes this unmodified constant
local to a typed byte SSA value. Its `0..255` admission range preserves the
unsigned-to-signed call conversion and low-byte output for this slice.

The existing byte backend independently checks its selected guest witness.
The compiled capsule emitted `0x41` under the normative profile VM in
31 steps on 2026-11-05. The tracked regression is
`tests/compiler/c-frontend/accepted/local_initialized_output.c`, with native
process/VM acceptance and tampered-node rejection tests. The declaration
and its use must carry the same canonical Clang symbol reference.

This is source-bound constant propagation for one immutable local, **not**
general automatic storage, mutable variable assignment, or guest integer
computation. An out-of-range or nonliteral initializer, additional effect,
branch, loop, or unsupported symbol relationship must reject without
publishing an artifact.

### Ordered literal writes to an automatic local

The pinned Clang experiment `local_reassigned_output.c` initializes one
`unsigned` local with `0U`, then writes `66U` and `65U`, and outputs the local.
Before the repair, the adapter refused the whole source at the first local
statement and published nothing. The repaired adapter admits at most eight
consecutive `=` assignments of source-backed `u32` literals in `0..255`.
It checks their exact AST ancestry, spans, order, and matching symbol before
eliminating the unobservable dead stores. Only the final literal is emitted as
a source-attributed typed byte SSA value, with one real guest output effect.
The actual current-profile VM emits `41` (hex) in 31 steps. Arithmetic
involving the prior local value was unsupported at this stage.

This is bounded dead-store elimination, not a guest implementation of general
mutable storage. Neither runtime arithmetic nor aliases, multiple variables,
conditional execution, or loops are supported by this projection. The original
Fibonacci program still refuses at its first declaration and remains the P0
end-to-end acceptance target.

### Bounded prior-value arithmetic writes

The pinned C fixture `local_arithmetic_output.c` contains one automatic
unsigned local initialized with `60U`. It then computes `value + 8U`,
`value ^ 3U`, and `value - 6U` through three source-bound assignments.
The initial value and three operators are checked against the complete
Clang AST, including exact symbol references, types, node ancestry and
nonoverlapping source spans. The adapter reads the previous proven value
for each operation and admits only results in `0..255`; it rejects
multiplication, unbounded or wrapping intermediate arithmetic, aliases,
foreign reads and extra effects. The live typed SSA constant receives the
last arithmetic expression's source span rather than an invented literal.

The independently verified guest output is `41` (hex), produced by the
existing Malbolge byte-output witness in 31 normative VM steps. The guest
performs **output**, not the arithmetic: this route is source-constant
propagation and dead-store elimination, not a runtime arithmetic backend.
General state, multiple locals, branches and loops still need actual
ternary and layout lowering. The original Fibonacci target remains blocked.

### Cross-local, source-proven constant flow

A new whole-source experiment `local_multi_output.c` declares three separate
`unsigned` locals, initializes `a` and `b` to `60U` and `8U`, initializes
`result` from their sum, then applies XOR `3U` and subtraction `6U` before
`putchar(result)`. The original pinned Clang-to-guest pipeline refused its
first declaration and published no guest artifact. The repaired JSON adapter
proves ordered, symbol-matched reads across distinct locals, exact AST
ancestry and spans, and every intermediate result within `0..255`. It accepts
up to eight distinct automatic unsigned locals, 16 straight-line writes and
bounded expression depth, with one final output call. Undeclared reads,
aliases, unchecked overflow, extra effects, control flow and other calls fail
closed. The live source expression anchors the final typed byte definition.

The actual emitted `.malbolge` capsule outputs `0x41` in 31 normative VM
steps. `tests/test_compound_c_pipeline.py` compares the real guest output
against `(60 + 8) ^ 3 - 6`, and the pinned JSON mutation regression proves
foreign symbols and unsupported effects refuse admission. Arithmetic remains
compile-time constant propagation; the guest performs only the witnessed byte
output. General locals, runtime arithmetic and loops are **not** implemented.
The original Fibonacci target continues to reject at its first declaration.

### Bounded source-proven conditional selection

A new demanding C branch experiment uses three initialized unsigned locals,
computes a cross-local sum, and selects one of two updates under
`if ((result & 1U) == 0U)`. The pinned frontend first rejected this whole
source at its first declaration without publishing any guest program. The
repaired multi-local projection checks the `i32` equality, nested unsigned
AND, all symbol references, exact source ancestry and spans, and one
side-effect-closed assignment in **each** brace-delimited arm. It evaluates
both arm shapes against the same proven incoming constants and retains
only the selected successor state before the final `putchar`.

Two source-backed variants exercise opposite outcomes: `60 + 6` selects
`result ^ 3U`, while `60 + 7` selects `result ^ 2U`. Typed-IR assertions
confirm that the live definition comes from the correct C line in each
variant. Both actual capsules output `41` (hex) in 31 normative VM steps.
Foreign reads, wrong operators, missing or nested arms, extra effects and
malformed metadata reject. At most 16 bounded writes are admitted,
counting both branch arms, and every intermediate arithmetic value must
fit `u8`. This is compile-time constant propagation, not an executable
guest branch or generalized mutable state. The original twelve-output
Fibonacci program still refuses at its first declaration; runtime loops,
variable-dependent output, and guest control flow remain pending.

### Conditional expression-derived output

The tracked pinned Clang source `local_expression_output.c` now selects a
proven branch update across three `unsigned` locals, then outputs the
**expression** `(int)(result ^ 3U)` instead of outputting a bare local. A
closed argument walker checks the explicit conversion, C parentheses, nested
unsigned arithmetic and source-bound local reference; any unconsumed effect
or mismatched Clang ancestry refuses publication. A red-first Rust regression
and mutated-node tests establish that the byte's SSA origin is the actual
call argument rather than an earlier variable write.

Two real native C-to-Malbolge compiler runs select different branch outcomes:
the first produces guest byte `0x41` in 31 VM steps; the second changes the
branch and argument constant and produces `0x42` in 69 VM steps. Independent
C arithmetic gives those values, and `tests/test_compound_c_pipeline.py`
checks actual guest output and rejects multiplication without an artifact.
A distinct `0x40` experiment reached the layout backend but was refused as
`UnsupportedEffectTrace`: the current positional single-byte guest witness
table does not contain that byte. The compiler did not fabricate guest output.
All arithmetic and control flow in the admitted case is still evaluated at
compile time; guest runtime computation, general loops and multi-byte dynamic
output remain unimplemented. The original Fibonacci acceptance is pending.

### Nonbyte unsigned intermediates with source-proven masking

The original Fibonacci loop computes `next = (a + b) & 255U`, which may
have a nonbyte sum even when the stored result is a byte. A pinned Clang
probe with `a = 233U` and `b = 144U` initially refused in the multi-local
adapter because the expression walker did not admit its nested parentheses.
The revised bounded evaluator retains the **checked `u32`** value 377 through
the inner addition, applies `& 255U`, and only then proves the byte 121
assigned to `next`. Source-proven Clang parentheses and an explicit
`putchar((int)next)` cast are now admitted while unknown operations, symbols,
AST mutations and extra effects still refuse. The leaf literals and each
materialized local remain byte-bounded; this is neither arbitrary 32-bit
C lowering nor guest runtime computation.

In a complete loop-free branch probe, the odd condition selects XOR 56,
producing `0x41` in 31 normative VM steps. An independent second C variant
uses `232 + 144`, selects the even condition with XOR 58, and produces
`0x42` in 69 normative VM steps. Both real guest capsules were compared
against independent C arithmetic and a pinned JSON regression verifies the
actual typed source span. The original twelve-byte Fibonacci experiment
still refuses its first declaration: its stateful `for`, repeated output,
and guest control flow remain missing and P0 stays open.

### Closed, statically evaluated C for-loop state

A new pinned Clang experiment
`tests/compiler/c-frontend/accepted/local_static_loop_output.c` reuses
Fibonacci-like unsigned locals in `for (unsigned i = 0U; i < 8U; ++i)`.
Its body declares an iteration-local `next`, computes a masked sum, selects
one of two source-proven assignments with `if/else`, and transfers the state
into `a` and `b`. A single `putchar` after the loop reads the final state.
The original full source was attempted first and still rejects because it
emits *inside* its loop.

The bounded adapter now proves an exact Clang `for-statement` declaration,
`u32` counter read, `i32` less-than comparison against a byte literal,
`++` increment, brace-delimited body and matching symbol/span ancestry.
It accepts only a zero-initialized, private `unsigned` counter with a bound
from 1 through 12. Each iteration replays the **same checked AST** against
proven local values, disposes of loop-body locals on scope exit and advances
the counter. Assignments to the counter, nested loops, effects inside the
loop, unsupported operations, and out-of-budget iteration bounds reject.
The body may contain bounded local declarations, assignments, and the
previously proven closed conditional assignments. All materialized locals
stay byte-sized; wider checked unsigned intermediates require masking.
The result is one constant-SSA byte with a real guest output, **not** a
Malbolge loop or guest runtime arithmetic.

Independent unsigned-C arithmetic yields `a=26`, `b=42` after eight
iterations and `42 ^ 107 = 65`. The real source-to-Malbolge pipeline emits
`0x41` in 31 normative VM steps, with a source variant at seven iterations
also producing `0x41` after independent oracle adjustment. Tests assert
changed counter identities, loop controls, branches and added effects refuse
publication. The complete twelve-byte Fibonacci program remains blocked by
loop-body output and dynamic guest control-flow realization.

The remaining first semantic gap for the original complete program is the
**general runtime** local-variable declaration, initialization, read/write
and provenance needed through typed IR and ternary lowering. The same
program additionally needs arithmetic, bounded loops, conditional branches,
and value-dependent `putchar`; the active
`docs/todo/open/compiler/ternary-machine-lowering.mdc` and
`docs/todo/open/compiler/malbolge-layout-and-encoding-backend.mdc` own the
subsequent executable target and control-flow realization. Re-run the **same**
complete program after each meaningful capability correction; retire this P0
only when its actual guest VM output matches the independent reference.

Do not substitute a host output transcript for guest execution or retreat
to another 49-byte literal-output demonstration to avoid this failure.

### Bounded branch-selected output inside a source-proven loop

The full twelve-iteration, branch-selected-output Fibonacci program was
retried. Before this change it still failed at the first local declaration.
A source-close variant, `local_loop_branch_output.c`, retains the same
three-state updates, masked sum, conditional and `putchar` inside the loop,
but proves zero using `next ^ next` in the even arm and `next - next` in
the odd arm. The pinned Clang AST is consumed completely for both arms on
every iteration; only the selected call is added to the ordered typed
output effects. Its `u32` state and loop counter are still **evaluated by
the compiler**, not by Malbolge.

The selected calls produce twelve verified zero bytes, with four even and
eight odd arms. The canonical typed IR contains one zero-valued SSA
constant and twelve distinct `ByteOutput` effects. The existing
zero-output backend generates a real guest capsule, and the normative VM
emits `00` twelve times in thirteen steps; a seven-iteration variant
emits seven zero bytes in eight steps. Tests refuse an unknown callee,
altered predicate, extra effects and a nonzero stream without publishing
a guest artifact. This is a new observable control-flow effect boundary,
not a fixed literal-count fixture.

The original compound program still requires **arbitrary nonzero output
sequences**: its reference is `02 59 5f 08 57 4f 22 6d 03 90 b3 23`.
The finite witnessed backend cannot yet realize that ordered sequence,
and the adapter explicitly rejects the unverified trace. General guest
state, dynamic loop execution and P0 completion remain pending.

### Source-proven, heterogeneous output from a bounded C loop

The original twelve-iteration Fibonacci C program was retried after the
selected-output loop proof. The next failure was the projection's assumption
that all selected output effects shared one byte. The generalized projection
now materializes a **distinct typed `u8` SSA constant for every selected
nonidentical output**, retaining the actual source expression and call spans
for each iteration. It selects an existing backend mode by the trace length
(up to twelve folded iterations) and leaves every byte value for the
independent typed/ternary/VM verifier to admit or reject. Uniform zero or
nonzero streams still use the existing one-SSA paths.

A complete source-backed two-iteration branch-and-loop experiment,
`local_loop_distinct_output.c`, evaluates the same Fibonacci-like state
transfers. Its even arm emits `2 ^ 83 = 81` (`Q`), and its odd arm emits
`3 ^ 45 = 46` (`.`). This is the independently witnessed guest pair `Q.`:
the real Clang-to-Malbolge capsule runs under the normative VM and emits
those two bytes. The pinned JSON regression checks distinct SSA IDs, exact
C call spans, both branch proofs, and foreign-symbol/operator rejection.
A C mutation changing `83U` to `82U` yields an unwitnessed pair and refuses
at the backend without publishing a guest artifact.

The **original full twelve-byte** C program now passes this bounded C
projection and the structural typed-byte adapter, which checks all twelve
source-backed `u8` definitions and SSA uses without choosing output values.
The canonical ternary bridge then reaches `--distinct-literal-twelve`, whose
independently witnessed guest layout is for a *different* fixed sequence.
It rejects with `Layout(UnsupportedEffectTrace)` and publishes no artifact.
The two-byte adapter similarly retains distinct nonzero SSA and delegates
which pairs are executable to the verified guest layout. An unwitnessed pair
now fails at that boundary, not while decoding the typed source. Neither
change synthesizes arbitrary bytes, adds runtime C state, or completes P0;
verified general guest byte-stream lowering remains the blocker.

### Bounded verified two-byte layout search

The distinct-pair guest bridge no longer chooses only three hard-coded byte
pairs. For the canonical current profile, it enumerates 94 graphical prefix
phases and both `p`/`*` arithmetic choices at each of two output positions.
A disposable loader/accumulator preview discards nonmatches before invoking
independent positional layout admission. Two external guest writes must be
distinct, and empty-input and nonempty-input normative VM runs must agree
with the source-proven bytes. The artifact publisher separately decodes and
admits the actual graphical source against exactly this two-write grammar
before its own VM replay; it does not trust the bridge's preview or a fixed
pair table.

The tracked two-iteration Fibonacci-style conditional C program, changed to
select `2 ^ 0 = 0x02` and `3 ^ 204 = 0xcf`, now produces `02 cf` from a
published capsule executed by the normative guest VM. This is a new binary
pair with mixed `*` and `p`, not an extra emit-N source fixture. The old
`Y/`, `Y$` and `Q.` guests remain exact. Unwitnessed streams still refuse
without a published file. The original twelve-iteration Fibonacci oracle
`02 59 5f 08 57 4f 22 6d 03 90 b3 23` remains unsupported by the
finite twelve-byte layout; P0 and dynamic guest state remain pending.

### Composed two-byte arithmetic from the original C experiment

The original conditional Fibonacci C program was reduced to two iterations
with the odd-arm XOR changed to `54U`, preserving its local state, bounded
loop, masked unsigned addition, conditional and source-proven output effects.
Its independent result is `02 35` in hexadecimal: the first value is 2 and
the second is `3 ^ 54 = 53`. The pinned Clang frontend, typed adapter,
ternary lowering and Malbolge layout now produce a real guest capsule that
the normative VM replays to exactly those bytes. This expands the earlier
two-write pair grammar to one extra arithmetic write, with bounded no-op
strides and three distinct out-of-source guest memory writes.

The candidate preview caches positional graphical encodings instead of
rescanning all printable characters for each candidate. The cache has no
acceptance authority: the layout is independently decoded, checked for
self-modification geometry and replayed on empty and nonempty input before
publication. An expanded negative regression now treats `QZ` as an admitted
VM-replayed pair rather than incorrectly expecting its refusal. Equal
output bytes were historically rejected by the distinct-pair bridge and the
independent publisher; the source-bound repeated-pair extension below now
admits witnessed equal pairs with distinct SSA identities and genuine guest
outputs. This is a bounded guest layout, **not** general runtime arithmetic,
looping or twelve-byte Fibonacci acceptance. P0 remains open.

### Source-proven triple output through bounded mixed guest arithmetic

The full twelve-iteration Fibonacci compiler experiment still fails closed at
its twelve-output layout boundary. Its independently computed first three
bytes, `02 59 5f`, likewise have no witness under the newly expanded bounded
three-output grammar. Neither failure publishes a guest artifact.

The three-output compiler backend now proposes an independently checked
combination of `p` and `*` at each of three output positions, across all 94
canonical graphical prefix phases. A finite additional search admits up to
eight no-op data strides before and between writes within twelve short prefix
phases. Cached graphical decoding and a disposable accumulator model accelerate
only candidate selection. The layout encoder must still prove three distinct
out-of-source data writes; the publisher separately re-decodes and admits the
actual staged guest and replays it under the normative VM with empty and
nonempty input. C source and typed adapters preserve three distinct output
SSA identities and delegate candidate-byte acceptance to this boundary.

Two native C-to-capsule-to-normative-VM probes establish new exact outputs:
`5a 0a de` in eight steps using three guest arithmetic writes and `51 2e 5a`
in 33 steps with nonzero data-pointer strides. Both have source-backed typed
outputs and full guest stdout parity; neither claims runtime C state or
arbitrary bytes. Previously admitted positional triple witnesses remain
byte-identical. This is a partial capability, not P0 completion.

### Checked product in a source-proven C recurrence

A complete three-iteration C recurrence now checks a distinct arithmetic
construct: `unsigned next = (a * b) & 255U`. Starting from `a=3`, `b=5`,
the product and parity-selected assignment update the local state through
`next = 15, 210, 22`; the final `putchar((int)(a ^ 86U))` emits `0x41`.
The original pinned pipeline refused this source at its first declaration.
The repaired bounded constant evaluator admits `*` only for `u32` operands
with `checked_mul` and stores only byte-range results. An unmasked product
outside the byte domain, unsigned overflow, division, unrecognized effects,
and forged AST structure remain rejected rather than being silently folded.

The end-to-end regression replays the **actual** Malbolge guest under the
normative VM with empty and nonempty stdin: `0x41` in 31 steps, equal to an
independently computed C oracle. This admits a new C arithmetic construct,
not multiplication, branches, or loops at guest runtime. The original
Fibonacci program is retried separately and remains rejected at
`Layout(UnsupportedEffectTrace)` for its unwitnessed twelve-byte sequence.
P0 is therefore still open; the earlier guest layout synthesis gap remains.

### Later verification matrix

Only after the complete experiment succeeds, use a deterministic corpus
generator to broaden coverage without manually creating one source and
technical document for every output length.

One versioned matrix specification declares a fixed seed, the C output
program template, target profile, resource limits, and oracle encoding.
The generator uses deterministic byte vectors of lengths 0, 1, 2, 3, 7,
8, 16, 32, 48, 64, 128, and 256, plus budgeted seeded lengths.

The vectors cover ASCII, all 32 low control bytes, zero, 0xff, high-bit
bytes, repeated bytes, and distinct-byte permutations. More than 256
positions necessarily permit repeats even when testing all byte values.

## Invariants

- Generate cases from inputs and a seed, not from separate manual fixtures.
- Translate each generated C program through the real compiler frontend,
  typed lowering, layout backend, and published Malbolge artifact.
- Run the actual guest in the normative VM under an explicit step budget.
  Byte output must come from guest behavior, not a host-generated substitute.
- Compare VM output to an independent byte-oracle before accepting a case.
  Record compiler identity, source hash, output hash, steps, and resources.
- One parameterized test runner must replay the whole retained corpus.
  Existing teaching artifacts keep their own source and SHA identities.
- Reject unsupported input, missing tools, timeouts, output drift, and
  incomplete lowering with typed failures rather than fabricated success.
- Test metamorphic relations such as repeated prefixes, concatenation,
  permutation, and equivalent C syntax only when the compiler promises
  the corresponding source semantics and exact output relation.
- Prevent regression masking: one failing case reports its seed, vector,
  source artifact, first byte mismatch, and reproducible command.
- Enforce an explicit wall time, memory, VM-step, and case-count budget.
  A truncated run is incomplete; it cannot publish a green receipt.
- A case that exposes a missing C feature becomes a compiler feature task
  with a red-first regression, not another arbitrary `emit-N` milestone.
- Use coverage of implemented C semantics, control flow, memory safety,
  input/output, and compiler lowering as progress metrics, not the maximum N.

## Failure Behavior

Do not infer support for general C, arbitrary loops, dynamic input, or
unbounded output from a finite sequence of literal `putchar` programs.
A single mega-source that prints 256 constants is also only one witness;
it does not replace the parameterized semantic and metamorphic matrix.

A compiler can pass every retained fixed example while mishandling a
single input-dependent expression. The matrix must detect such defects,
retain the smallest reproducer, and avoid adding repetitive manual pages.

## Verification

Start by running `python3.14 -B -m unittest` on the existing
`tests.test_versioned_example_corpus` matrix. A new generator and
parameterized contract test shall add deterministic seeded cases without
requiring one new test module for every output length.

The mandatory evidence is exact C-to-Malbolge compilation, independent
VM output and trace, source/guest digests, finite budgets, negative cases,
reproducible seed replay, and no dependence on untrusted host output.

Completion means the generalization is tested across the declared matrix,
not merely that the next individual `emit-N` example works. If input or
control-flow lowering is not supported, report that precise gap and leave
the product claim incomplete rather than extending examples forever.

## References

- `docs/technical/examples/versioned-c-malbolge-corpus.md`
- `docs/todo/open/applications/versioned-c-and-malbolge-example-corpus.mdc`
- `docs/todo/open/compiler/malbolge-layout-and-encoding-backend.mdc`
- `docs/todo/open/compiler/ternary-machine-lowering.mdc`
- `docs/todo/open/compiler/compact-guest-bytecode-strategy.mdc`
- `tests/test_versioned_example_corpus.py`

### Repeated byte values from distinct source-bound loop effects

A three-iteration, conditional Fibonacci-style C program now verifies that
**equal observed byte values need not share a source SSA identity**. The
source-backed recurrence evaluates `(a + b) & 255U` at compile time, selects
`next ^ 58U` or `next ^ 59U`, and produces the independent oracle `38 38 3e`
(`88>`). Before repair the typed bridge refused the full program as
`UnsupportedTypedIr`; the layout publisher also rejected its duplicate bytes.

The repaired three-output bridge retains separate source SSA definitions while
allowing a repeated adjacent output of the *live guest accumulator*. A bounded
positional search proposes two arithmetic data writes and three output
instructions, never copies a host-calculated output stream into the guest.
The independent publisher decodes the complete target from actual source
bytes, validates the repeated-output grammar and distinct out-of-source data
writes, then checks exact termination and output under the normative VM with
empty and nonempty input. The real C-to-guest capsule emits `38 38 3e`.
A mutation that introduces unsupported C multiplication must still refuse
without publishing. The original twelve-byte Fibonacci acceptance target
remains unsupported at layout: C state and branches here are statically
projected, not executed dynamically by the guest.

### Source-distinct C branch effects with equal observed bytes

On 2026-11-06, a two-iteration `for` loop with the same masked Fibonacci
state updates as `local_loop_distinct_output.c` selected opposite conditional
`putchar` arms: `2 ^ 58 = 56` and `3 ^ 59 = 56`. The original C-to-guest
pipeline refused `Layout(UnsupportedEffectTrace)` because the bounded Clang
projection coalesced all same-valued outputs into one SSA constant, then
selected a seeded single-byte layout with no matching witness.

The repaired source-aware frontend retains two independent `u8` SSA values
when the two nonzero equal-valued outputs originate from different C call
spans. Same-call repeated loop effects still use the existing shared-SSA
projection. The exact typed pair lowering preserves both SSA identities;
a bounded positional guest search uses one relocated `p`/`*` write followed
by two genuine `<` output instructions that reuse the unchanged accumulator.
The independent publisher re-decodes the emitted graphical source, verifies
out-of-source guest writes, re-admits the layout, and executes the normative
VM on empty and nonempty input before artifact publication.

Red-first regressions verify the exact selected source spans and distinct SSA
IDs, the one-write/two-output guest trace, actual C-to-VM `38 38` parity,
and refusal of an unsupported multiplication mutation with no guest artifact.
The original twelve-byte Fibonacci program still has no generalized guest
byte-stream witness. Compile-time C loop folding is not a claim of runtime
Malbolge branching or a complete C compiler; P0 remains pending.

### Nonadjacent equal source-derived outputs

A complete three-iteration, index-branching Fibonacci C program now projects
three distinct output effects `5a 25 5a` (`Z%Z`), using masked recurrence
state and a source-backed `next - next` expression. Its first and third
outputs match although the middle output differs. The pinned C frontend,
JSON/typed adapters and bounded triple bridge already synthesized a guest
candidate; the independent publisher refused it solely for nonadjacent
repeated values (`distinct-literal triple has nonadjacent repeats`). The
red-first end-to-end test reproduced this refusal with no published artifact.

The publisher now admits this pattern only through the existing three-write
relocated grammar, with three distinct out-of-source arithmetic data writes,
re-decoded staged instruction bytes, canonical layout admission, and exact
normative VM output under both empty and nonempty input. The complete C
pipeline emits `Z%Z` from actual guest instructions; a multiplication
mutation is rejected before publication. No host output substitution,
dynamic guest C state, general loop execution or arbitrary byte-stream
synthesis is claimed. The original twelve-byte Fibonacci target still fails
closed at layout, so the P0 acceptance remains pending.

### Three identical outputs from source-distinct conditional calls

The three-iteration Fibonacci-like C loop from the nonadjacent-repeat probe
was compiled again with both branch expressions changed to
`(next - next) + 56U`. All three loop iterations still prove the C local
state, chosen branch, and actual `putchar` call effect. The independent arithmetic oracle
is `38 38 38`. Before the repair, the frontend merged all observations into
one SSA constant; the finite single-constant backend refused the trace.
A red-first complete pipeline regression reproduced the missing artifact.

When two or three nonzero equal-valued effects use different C call spans,
the frontend now preserves separate typed `u8` SSA definitions and their
source spans. The three-effect bridge may compute one accumulator through
one or two relocated `p`/`*` data writes, then execute three distinct `<`
output instructions without changing the accumulator. The independent
publisher re-decodes the actual graphical source, proves the bounded
arithmetic/three-output geometry and nonaliasing data writes, then runs the
normative VM with empty and nonempty input. `888` reaches exact real guest
parity; an unsupported multiplication mutation still refuses without a
published capsule. Same-call uniform loop effects retain the shared-SSA
path, not an invented new source identity.

This covers an additional output-identity shape, not arbitrary byte streams,
execution of C loops in the guest, or the full twelve-byte Fibonacci target.
The latter continues to refuse `Layout(UnsupportedEffectTrace)` and this
P0 remains pending.

### Source-proven unsigned remainder in a complete loop

A new red-first whole-source probe, `local_remainder_recurrence_output.c`,
uses two automatic unsigned locals, three stateful `for` iterations, a masked
`u32` product, odd/even conditional assignments, `next % 17U`, and a final
expression-derived `putchar`. It originally refused at the first declaration
because the unsupported remainder prevented the complete constant projection.
No guest artifact was published. The adapter now consumes the exact Clang
`u32` operator and checks nonzero-divisor `checked_rem` before narrowing.
The separately computed recurrence is `15, 210, 190`, finishing at `a = 2`
and output `2 ^ 67 = 65`. The emitted Malbolge produces `0x41` in 31
normative VM steps under empty and nonempty stdin. At the time, division
and zero-divisor mutations did not publish a guest program.

This is finite source-backed compile-time evaluation, **not** Malbolge
remainder arithmetic, dynamic C state or general stream realization. The
original twelve-byte Fibonacci program still fails closed at the independent
guest-layout boundary; the P0 remains pending.

### Source-proven unsigned quotient in a complete recurrence

A three-iteration whole-C program, `local_division_recurrence_output.c`,
combines two automatic `unsigned` locals, a masked product, conditional
assignments, `next / 17U` in the even arm, state transfers and one final
`putchar`. It initially refused at the first declaration because the
full expression walk could not establish `/`; it emitted no guest artifact.
The checked source-bound `u32` evaluator now uses `checked_div` after
validating exact Clang ancestry, operator and operand types. It refuses a
zero divisor rather than folding undefined C behavior.

The independent unsigned oracle visits product values `15, 210, 170`,
finishes with `a = 11`, and derives output `11 ^ 74 = 65`. The complete
pinned Clang-to-typed-to-ternary-to-layout pipeline publishes a real
Malbolge capsule. The normative VM emits exactly `0x41` after 31 steps
under both empty and nonempty input. Source mutations to division by zero
or an unsupported shift refuse without publishing a guest artifact.
This is closed compile-time state projection; guest division, dynamic C
state, and generalized twelve-byte synthesis remain unimplemented. P0 is
still open because the original Fibonacci trace remains unwitnessed.

### Bounded unsigned-shift C recurrence

A complete source-backed three-iteration C experiment now tests masked
multiplication shifted left by two, branch-selected logical right shifts,
state transfers and an expression-derived output. Before the addition,
`c2malbolge_json` refused the first declaration with `Unsupported`; it
published no artifact. The adapter now checks both shift operators against
exact pinned Clang `u32` AST ancestry and operand ranges. Shift counts
outside 0 through 31 reject rather than evaluating undefined C behavior.

The independent C recurrence visits `next = 60, 80, 192`, finishes at
`a = 25`, and expects `25 ^ 88 = 65`. Golden normalized AST tests check the
byte's actual typed SSA definition and refuse altered operators, forged
symbols, operand types, ancestry and shift counts. This bounded constant
projection does not execute C shifts or branches in the guest and cannot
synthesize the original twelve-byte Fibonacci stream. Its P0 remains open.

### Additional guest write for source-proven three-byte Fibonacci loops

A new full three-iteration source experiment uses the original Fibonacci
local-state transfer, bounded loop and conditional output, changing only the
odd-arm XOR constant to `0x3d`. Its independently evaluated byte trace is
`02 3e 38`. The canonical C frontend and typed/ternary bridge admit its
ordered source effects, while the guest executes four separate relocated
`p`/`*` arithmetic writes and three actual output instructions. This
expands the earlier three-write guest grammar by allowing a fourth write
before one of the output sites, without inventing a host output callback.

The proposal filter caches position-encoded source-length-dependent memory
suffixes and checks predicted byte values before asking the independent
layout encoder to admit a candidate. The separate file publisher parses
its exact decoded instruction grammar, requires every guest data write to
be disjoint and out-of-source, and runs the normative VM on empty and
nonempty input. Independent proposal-model comparisons, source-backed
regressions and VM parity are required; cached previews have no authority.
The earlier original three-byte prefix `02 59 5f` still has no admitted
witness in the bounded grammar; the full twelve-byte Fibonacci target and
runtime guest-side C control flow remain pending.

### Source-distinct four-output projection without a guest witness

A complete four-iteration version of the original conditional Fibonacci C
program, using odd-arm XOR `0x3d`, independently computes the ordered bytes
`02 3e 38 08`. The pinned frontend and JSON adapter admit its locals,
loop, branch, arithmetic, and four separately source-anchored `putchar`
effects. The typed stage previously rejected the fourth byte because its
four-output projector required the unrelated hard-coded teaching sequence
`T=4>`, despite the ternary and guest stages being responsible for positional
layout admission.

The three- and four-output typed projections now share an exact ordered
constant/output validator. It preserves every original SSA ID and call span,
requires an eight-bit scalar with a matching output use, and rejects duplicate
IDs, extra effects, foreign types, and malformed instruction order. The same
full C program now reaches `Layout(UnsupportedEffectTrace)` without publishing
an artifact.

The regression uses an independently computed unsigned-C oracle
and will require actual empty/nonempty-input normative guest parity if layout
support is later added. This is an intermediate compiler-boundary repair, not
four-output guest synthesis, dynamic guest C state, or P0 acceptance. The
original twelve-output Fibonacci experiment still lacks a guest witness.

### Four real guest outputs from source-distinct conditional loop effects

The complete four-iteration Fibonacci C probe with odd XOR `0x3d` still
fails closed for `02 3e 38 08`. A separate full four-iteration C experiment
changes the even arm to `putchar((int)(next ^ 26U))` and keeps the odd arm
at `next ^ 61U`. Its independently calculated values of `next` are
`2, 3, 5, 8`, giving four distinct output bytes `18 3e 38 12` (hex).
Before this repair the pinned compiler rejected the complete source at
`Layout(UnsupportedEffectTrace)` and published no guest artifact.

The bridge now searches four independent `p`/`*` arithmetic writes, each
followed by a real guest output instruction, with up to eleven prefix
no-ops and at most eight no-ops before each write. The disposable search
reuses the immutable loader-expanded memory suffix by source length;
it does not authorize a result. The independent publisher re-decodes the
staged source, verifies four distinct out-of-source writes, admits exact
instruction geometry and replays the normative VM with empty and nonempty
input. The complete masked C loop now emits exactly `18 3e 38 12` on both
inputs. A division-by-zero source mutation refuses without publication,
and proposal-preview parity tests compare the cached model with full
source expansion. The historical `T=4>` witness remains admitted.

This realizes a new four-effect semantic boundary, not arbitrary streams.
The original twelve-byte Fibonacci target and dynamic guest-side C state
remain unimplemented. P0 stays open until the original compound C program
(or another accepted complete compound program with comparable runtime
semantics) meets the contract's full guest-parity acceptance criteria.

### Bounded state-space guest output proposals

A complete four-iteration C recurrence with local state, conditional byte
output, multiplication, division and masking now emits `35 c0 09 e3` through
the current-profile normative guest VM. The source is
`tests/compiler/c-frontend/accepted/local_loop_wide_branch_stream.c`.
The independently calculated unsigned-C values are `2, 3, 5, 8` before the
branch-derived output expressions. Both empty input and `ff 00 80` input
produce identical verified guest output. A division-by-zero mutation refuses
before artifact publication.

The first compiler attempt reached the quad publisher and refused its exact
four-write/output-pair grammar. A new deterministic, capped state-space
proposal searches exact 15-trit accumulator states and source-ordered byte
effects with guest `p`, `*`, `<` and no-op instructions. The loader-memory
suffix cache remains advisory: the independent publisher re-decodes every
instruction, requires four outputs and four to 32 disjoint out-of-source
data writes, re-admits the complete linear source and executes the normative
VM twice before publication. A five-write/four-output regression is outside
the older four-write grammar but passes all checks. The historical `T=4>`
source remains admitted.

The original search covered at most 94 source cells, a 30-cell prefix and
explicit state/node limits. A later bounded extension covers up to 104 source
cells, including ten cells after the first 94-phase positional decode cycle.
The `extended_decoder_phase_reconstructs_real_guest` regression starts with a
100-cell relocated guest, recovers its `3e 3f 2c 12` output using actual
15-trit accumulator transitions, and independently re-encodes and replays the
guest twice. A forged expected byte fails verification. The current search
still uses finite per-geometry state/node limits and a 104-cell budget, below
the graphical relocation operand ceiling of 126. This is a source-independent
layout witness; it does not prove that the compiler needs more than 94 cells
to produce that particular output.

Search exhaustion does not establish target-language impossibility. A renewed
real C-to-guest attempt still refuses the unmodified four-output Fibonacci
prefix `02 59 5f 08` at layout without publication, as does the complete
twelve-output program. C state and arithmetic here execute during compilation,
not as runtime guest C operations. P0 remains pending.

### Alternate terminal source geometry

The four-output state-space proposal now also explores code with an extra
no-op immediately before `halt`, moving the fourth real output earlier. That
changes the two graphical words seeding the loader-expanded memory beyond the
source. The proposal cache substitutes the positional no-op cell only when
computing that memory tail; the actual published source is still produced,
independently decoded, checked for out-of-source writes and replayed in the
normative guest VM under empty and nonempty input. The verified four-byte
`5c 3f 11 42` guest is a geometry witness, not evidence of general C state
or unrestricted byte-stream synthesis. The original twelve-output Fibonacci
program and its four-byte prefix still lack guest layouts.

A subsequent experiment now includes two more source terminators: `p; halt`
and `*; halt` after the final byte output. These instructions write one
out-of-source data cell and replace the loader's final pre-halt seed, but
do not emit another output. The bounded search uses each corresponding
positional encoding only in its disposable tail model; the independent
publisher still checks the complete source, every guest data write and
both normative VM input replays. Both terminal variants reconstruct real
four-output guests with five disjoint data writes, and forged expected
output bytes are rejected. After rebuilding the real layout executable,
the original Fibonacci four-byte prefix and full twelve-byte trace still
refuse without publishing an artifact. The additional search shapes are
not a proof of unrestricted byte-stream synthesis or runtime C execution.

### Source-backed unsigned bitwise OR in a complete recurrence

A separate complete three-iteration C experiment uses local state, checked
multiplication, `|`, masking, shifts, both conditional arms and an output
expression. Its pinned Clang projection initially refused the first local
because bitwise OR was not admitted by the bounded `u32` expression walker.
The expression proof now checks the exact source operator and both operands,
then folds unsigned bitwise OR before narrowing to a byte store.

Independent oracles for OR masks `16` and `8` visit `31, 248, 16` and
`15, 120, 152` respectively. Both derive a final output of `0x41`. Each
complete C source produces a real `.malbolge` capsule that emits `0x41` in
31 normative VM steps for both empty and nonempty input. Changing the source
to logical OR, removing its state-width mask or adding a side-effecting
read refuses without an artifact. The new test is
`test_unsigned_or_recurrence_reaches_real_guest` in
`tests/test_compound_c_pipeline.py`.

This is source-proven, bounded constant evaluation, not guest runtime C OR,
loop execution or generalized stream synthesis. The original twelve-byte
Fibonacci program remains rejected at layout, so P0 stays pending.

### Source-backed unsigned relational conditions

A complete three-iteration C program now exercises automatic unsigned locals,
checked multiplication and shifts, a relational `if` inside a `for` loop,
source-derived state transfers and a final `putchar`. The first pinned-Clang
compile refused the initial declaration because the bounded adapter only
admitted `==` in the conditional expression. The revised closed evaluator
preserves the exact unsigned `u32` operands and typed `i32` comparison result,
and selects both source-proven branches with `==`, `!=`, `<`, `<=`,
`>` or `>=`.

The red-first regression derives the branch sequence and final XOR key
independently for all six operators. Every full C source now emits a real
Malbolge capsule that outputs byte `0x41` under the normative VM with empty
and nonempty stdin. The comparison boundary admits only the existing checked
`(unsigned_expression & mask) OP byte_literal` condition shape; unsupported
logical `&&`, a side-effecting increment and a signed cast in that condition
reject without publication. The checked-in source is
`tests/compiler/c-frontend/accepted/local_relational_recurrence_output.c`;
the end-to-end regression is
`test_unsigned_relational_recurrence_reaches_real_guest`.

Comparison, loop state and branch selection still fold during compilation;
the guest executes the independently checked byte output, not runtime C
comparisons. The original 12-byte Fibonacci acceptance still refuses at
unwitnessed guest layout, so the P0 remains open.

### Source-backed pure logical conditions

A complete three-iteration C recurrence now combines checked multiplication,
shifts, two automatic unsigned locals, a loop, a branch selected by C logical
`&&`/`||`, state transfers, and a final output expression. The initial pinned
Clang-to-guest attempt refused the first declaration because the closed
constant-flow projection admitted only one masked unsigned comparison.

The evaluator now consumes a bounded tree of source-ordered `i32` logical
operations over exact source-proven unsigned masked comparisons. It checks
both operands and both assignment arms, including parentheses, canonical
Clang ancestry, types, symbol references, spans and absence of effects.
Both operands are checked before logical selection: this is sound for the
admitted pure, defined subexpressions, but rejects some otherwise-defined
short-circuit C programs whose unexecuted right operand is unsupported.

The source fixture `local_logical_recurrence_output.c` evaluates an AND
condition through three iterations, selecting false, true and false arms.
An OR variant selects false, true and true; a nested AND/OR variant tests
source parenthesization and mixed precedence. An independently calculated
state trace supplies a different final XOR constant to each variant so the
normative Malbolge guest must emit the same byte `0x41` under empty and
nonempty input. Side-effecting increments and calls in a logical operand,
plus unsupported logical-to-bitwise mutations, must refuse before artifact
publication.

No runtime Malbolge Boolean evaluation, general short-circuit effects, dynamic
state or arbitrary byte-stream synthesis is claimed. The original twelve-byte
Fibonacci program still fails closed at guest layout; P0 remains pending.

### Source-backed pure logical negation

A further complete three-iteration C recurrence uses local state, checked
multiplication and shifts, a nested logical predicate inside a loop, both
conditional assignment arms, and an expression-derived final `putchar`. The
first pinned-Clang compiler attempt refused at the first declaration because
the closed Boolean evaluator did not handle the source-proven unary `!` node.
The revised evaluator consumes an `i32` `!` over a fully proven pure predicate,
requires exact Clang parentage and typed expression spans, and reuses the
existing closed unsigned-comparison and `&&`/`||` rules. Both operands of every
logical binary subtree are checked, even if C would short-circuit one.

The tracked source `local_negated_logical_recurrence_output.c` produces the
independently calculated branch trace false/true/true. Double-negation and
nested-negation variants prove other branch traces through the full pinned
pipeline. The resulting actual Malbolge capsules each emit `0x41` in 31
normative VM steps for both empty and nonempty stdin. Source mutations that
introduce an increment, an impure call or bitwise complement fail before
guest publication; separately corrupted unary AST operation, type, parent or
kind metadata are rejected by the canonical adapter. The end-to-end and
adversarial regressions live in `tests/test_compound_c_pipeline.py`.

This is source-backed **compile-time** C constant evaluation, not runtime
Malbolge Boolean execution or short-circuit side effects. The original twelve-
byte Fibonacci stream remains blocked at guest layout, so P0 remains open.

### Computed unsigned operands in source-proven comparisons

A full three-iteration C recurrence now compares **two independently computed
unsigned expressions** within its loop's branch. The condition combines
masked local values on the left with an XOR and addition derived from a second
local on the right. The first pinned C-to-guest run refused the declaration:
the closed Boolean evaluator only admitted one parenthesized masked expression
compared against a byte literal.

The evaluator now proves each complete `u32` comparison operand through the
existing bounded, source-ordered expression walker. It requires exact Clang
parentage and operand spans before computing the `i32` Boolean comparison
result from the two unsigned values. For `>=`, the independent
three-iteration oracle selects true/false/false; for `<`, it selects
false/true/true.

Both complete C variants reach actual Malbolge execution, emitting `0x41`
with empty and nonempty stdin. Side-effecting increments,
a zero-divisor expression, and an unsupported logical-operand mutation refuse
without publication. Forged right-hand AST kind, type and parent also reject.

The checked-in source and regressions are
`local_computed_condition_recurrence_output.c` and
`test_computed_unsigned_comparison_*` in
`tests/test_compound_c_pipeline.py`. This is pure compile-time C folding, not
guest runtime arithmetic, branches or control-flow execution. The original
twelve-byte Fibonacci trace still lacks a positional guest layout witness;
P0 remains pending.

### Source-backed conditional expressions inside unsigned recurrences

A complete three-iteration C recurrence now uses the source-proven
`condition ? then : else` expression to select an unsigned local's next
value inside a loop. The initial pinned Clang-to-guest attempt refused at
the first declaration, because the closed `u32` expression walker did not
admit the `conditional-expression` node. The repaired adapter requires an
exactly typed `u32` result, a fully proven pure `i32` condition, two complete
checked unsigned alternatives and their exact source-ordered Clang spans.
It proves **both** alternatives even though C executes only the selected
one; an unselected side effect or undefined operation is conservatively
rejected, not silently dropped.

The checked-in source `local_conditional_expression_recurrence_output.c`
visits unsigned `next` values `60, 160, 128` and selects the true, false,
false alternatives. The separately computed final state is `a = 127` and
`a ^ 62 = 65`. The complete pinned compiler emits a real current-profile
Malbolge capsule; the normative VM outputs `0x41` under both empty and
nonempty input. Negative source variations with increment side effects,
zero division or unproven conversions refuse without an artifact; forged
conditional node/arm operation, kind, parent or type metadata also reject.
The complete acceptance and mutation regressions live in
`tests/test_compound_c_pipeline.py`.

This is bounded source-constant folding, **not** guest runtime selection,
C control flow or arbitrary byte-stream synthesis. The original twelve-byte
Fibonacci output remains blocked by positional guest layout; P0 is open.

### Verified zero-prefixed guest output before data relocation

A complete four-iteration C recurrence with automatic unsigned state, a
masked Fibonacci update, source-proven `if/else`, pure `?:` expressions, and
four `putchar` effects initially reached the quad layout publisher but
failed at `distinct-literal quad geometry disagrees`. Its independently
computed output is `00 54 b2 3f`; no guest artifact was published.

The bounded state-space proposer now considers one or more real initial-zero
output instructions before the data-pointer relocation. Its source-independent
preview counts those bytes rather than silently omitting them, and still
models all subsequent `p`/`*` writes on loader-expanded guest memory.
The independent quad publisher now re-decodes these prefix effects and
permits an output, no-op, or arithmetic instruction before the final halt.
It still requires exactly four outputs, a single early relocation, at least
one guest arithmetic write, distinct out-of-source data writes, exact
positional source admission, and normative VM replay with both empty and
nonempty input. The maximum prefix, source length, and write count remain
bounded; no unverified byte stream is accepted.

The tracked `local_zero_prefix_conditional_stream.c` program now compiles
through the pinned Clang/JSON/typed/ternary/layout pipeline, and the real
guest emits `00 54 b2 3f` under both input cases. A side-effecting C
comparison mutation fails without publication. The source-independent
seeded-layout regression proves the actual first guest instruction outputs
zero before relocation; a forged preview must not authorize a source.
These are source-constant-folded C values with real guest output, not guest
runtime C arithmetic or general byte-stream synthesis. The original
12-byte Fibonacci acceptance remains unsupported, so P0 remains open.

### Maximum graphical relocation boundary

The bounded state-space quad search now considers source lengths through 126
cells, the maximum relocation operand representable by a graphical ASCII
code cell. In particular, the canonical `j` at source position eight has
encoded byte value 126. A source-independent four-output guest uses that
relocation and 126 source cells, crosses the 94-phase decoder wrap, and
performs real disjoint guest arithmetic writes. The pinned current-profile
VM independently emits `36 14 35 02`; the bounded proposer reconstructs
the program, and independent layout/VM admission accepts the reconstruction
while rejecting a forged final output byte. The verification tests preserve
the full-source length and at least four distinct guest writes.

An additional complete four-iteration C Fibonacci-style loop with unsigned
state, parity selection, nested conditional expressions and four `putchar`
effects was compiled through the pinned Clang/typed/ternary/layout pipeline.
Its independent recurrence oracle was `36 14 35 02`, and its actual capsule
emitted exactly those bytes with empty and nonempty input in 24 VM steps.
That C example chose a *shorter* accepted layout: it proves guest-output
parity, not that the longer search boundary was necessary for that source.
The unmodified original four-byte Fibonacci prefix `02 59 5f 08` still
exhausts the expanded bounded grammar without a verified guest. This
search-space expansion is not generalized byte-stream synthesis, dynamic
C state or runtime control flow; the P0 remains open.

### Source-proven unsigned bitwise complement in a stateful recurrence

A complete three-iteration C recurrence first refused its first declaration
when a conditional expression used `(~next) & 255U` in one branch. The closed
unsigned expression evaluator previously supported binary operators and pure
conditional values, but not unary `~`. It now proves the full Clang-backed
`u32` unary subtree, including operation, type, ancestry, exact operand span
and clean metadata. It computes the complement at the full 32-bit unsigned
width before narrowing with the source-proven mask; a bitwise complement is
not an eight-bit operation until the C expression explicitly makes it one.

The tracked `local_complement_recurrence_output.c` uses checked multiplication,
shifts, automatic state updates, a source-proven loop, both conditional arms,
and one final output. Its independent three-step oracle visits `60, 208, 192`
for `next`, takes true/false/false, ends at `a = 25`, and emits
`25 ^ 88 = 65` (`0x41`). A double-complement source variant checks nested
unary ancestry and unsigned width, visiting `60, 64, 0` and emitting
`1 ^ 64 = 65`.

Both reach actual normative Malbolge guest output under empty and nonempty
input. Side-effecting or undefined operands, signed complement, unsupported
unary minus and forged AST metadata reject without publishing a guest
artifact. Tests cover actual guest stdout and adapter refusal.

This implements **source-backed compile-time** C constant propagation only.
The guest runs the output instructions, not the C multiplication, branching or
bitwise operations. The original twelve-byte Fibonacci output still lacks an
independently verified general layout, so the P0 remains pending.
