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
state, chosen branch, and actual `putchar` call effect. The independent
arithmetic oracle is `38 38 38`. Before the repair, the frontend merged
all observations into one SSA constant; the finite single-constant
backend refused the trace.
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

### Source-proven modulo-2^32 arithmetic in a four-byte C stream

The complete four-iteration source program
`local_wrapping_recurrence_stream.c` exposed another real semantic gap:
`unsigned` subtraction, multiplication, and addition were incorrectly
restricted to nonoverflowing intermediate values. The first pinned Clang
compilation refused the declaration and published no guest. C defines these
operations modulo 2^32 for the pinned `wasm32` unsigned-int target, even when
an intermediate is much larger than a byte. The multi-local expression
checker now proves the original `u32` operand tree, typed operator, Clang
ancestry and source order before applying `wrapping_sub`, `wrapping_mul` or
`wrapping_add`. It still narrows only on source-proven masks/stores and
refuses unsupported conversions, effects and undefined operations.

Each iteration reconstructs a Fibonacci state update using
`((0U - (a + b)) * 255U) & 255U`, then restores the same byte through
`((~next + 1U) + (next * 2U)) & 255U`. The unsigned subtraction wraps for
all four iterations; the product and final addition also exceed 2^32 - 1
before modulo reduction. A separately calculated 32-bit modular arithmetic
oracle yields the state sequence `2, 3, 5, 8` and source-selected output
`35 c0 09 e3`. The full pinned C/JSON/typed/ternary/layout pipeline produces
a real Malbolge capsule whose normative VM emits exactly those four bytes on
both empty and nonempty stdin. Division-by-zero, source increments, and a
signed complement mutation refuse without an artifact.

This is **compile-time** folding of a bounded, fully known C recurrence. It
does not implement runtime C integers or dynamic guest loops, and it does not
solve the original `02 59 5f 08` prefix or the twelve-byte Fibonacci layout.
The generalized byte-stream P0 remains pending.

### Source-proven unsigned zero/nonzero predicates

A complete three-iteration C recurrence with automatic unsigned state,
checked multiplication, left/right shifts, an `if/else` and final output
initially refused at the first declaration for `if ((next & 8U))`. The
pinned Clang AST reports an unsigned scalar expression as the condition,
not an `i32` comparison. The bounded constant-flow proof now consumes a
complete `u32` expression and selects the arm when its evaluated value is
nonzero, following C scalar truth semantics. The existing expression walker
checks Clang ancestry, exact types and spans, and pure defined arithmetic;
side effects and unsupported casts cannot be discarded.

For `next = ((a * b) << 2U) & 255U`, starting from `a=3`, `b=5`,
the independent recurrence visits `60`, `160`, `128`. Masked truth selects
then/else/else, producing final `a=127` and `127 ^ 62 = 65` (`0x41`).
The complete pinned C-to-Malbolge pipeline emitted this byte in 31 real
normative VM steps. The source test also covers direct unsigned-local
truthiness; mutated C side effects, zero division, signed casts and forged
Clang operator/type/ancestry/metadata must refuse without publication.

This is bounded **compile-time** condition selection over already known
unsigned values; it adds neither guest runtime branching nor a general
byte-stream layout. The original twelve-byte Fibonacci P0 remains open.

### Bounded source-backed `while` control flow

A complete C recurrence with automatic unsigned local state, multiplication,
shifts, a conditional with both arms, and a mutable loop counter was first
attempted through the pinned compiler and refused at its first declaration.
The closed JSON adapter now accepts a source-proven `while (condition) { ... }`
when the condition and every executed body effect are completely evaluable
from current local constants. Unlike the earlier fixed-bound `for` proof,
the `while` condition is re-evaluated **after each body execution** against
updated local state. The full canonical Clang subtree, exact source spans,
node ancestry, pure condition and body effects are checked on each replay.
Iteration-local declarations are discarded at the end of each execution.

The evaluator requires at least one executed iteration and an observed false
condition after at most twelve iterations. Zero-trip loops are conservatively
unsupported because the skipped body would not be proved. Infinite loops,
side-effecting or undefined conditions, nested loops and unrecognized effects
fail without publication. Loop evaluation is compile-time only; it does not
claim general C control flow or mutable Malbolge guest state.

`local_while_recurrence_output.c` visits the independent unsigned values
`60, 160, 128`, takes true/false/false branches and derives the final byte
`127 ^ 62 = 65`. The generated current-profile Malbolge capsule emits
`0x41` in 31 normative VM steps. A separate two-iteration `while`-converted
Fibonacci branch program emits two independently derived bytes `Q.` in eight
actual guest steps. The real VM, not the host C program, produces both output
traces. The original twelve-byte Fibonacci P0 still requires generalized
guest byte-stream layout and remains open.

### Bounded source-backed `do…while` control flow

A complete C recurrence with automatic unsigned state, multiplication,
shifts, a two-arm branch, and a mutable counter exposed another missing
control-flow boundary: `do { ... } while (condition);`. The pinned Clang
frontend already emits `do-statement` with the compound body **before** the
trailing condition; the JSON adapter initially refused the first local and
published no guest artifact. The closed evaluator now consumes that exact
node order and checks the whole loop body before the condition on each pass.
It replays both from the same Clang subtree, re-evaluates pure checked
predicates against updated state, and drops iteration-local declarations
before evaluating the trailing predicate. It requires a source-proven false
condition within twelve body executions; neither nested loops nor unbounded,
impure, undefined or unsupported effects are admitted.

The independent three-iteration trace reaches `60, 160, 128`, takes the
true/false/false branches and produces `127 ^ 62 = 65` (`0x41`). A distinct
source variant starts with `i = 3U` so the test is already false **before**
the first body; C still executes one body and yields `(60 >> 3) ^ 1 = 6`,
then `6 ^ 71 = 65`. A two-iteration converted Fibonacci conditional stream
retains two real guest outputs `Q.`. Tests check actual normative VM stdout
against independent C arithmetic for empty and nonempty guest input.
Unsupported sources and malformed or unsupported AST structures must refuse
without a guest artifact. As elsewhere in the bounded frontend, normalized
Clang input is trusted evidence; its digest is not an independent proof that
an adversarially rewritten but still valid AST operator matches original C.

This is compile-time replay of a proven finite C program, not dynamic guest
control flow. The original twelve-byte Fibonacci P0 remains blocked by
generalized byte-stream layout.

### Source-proven `if` without `else` in bounded C recurrences

A complete three-iteration unsigned C recurrence with a `do…while` loop,
checked multiplication and shifting, mutable state and a conditional update
without an `else` first failed at the JSON adapter and published no guest.
The closed conditional proof formerly required two braced arms. It now admits
an exact source-backed single braced assignment only when that arm ends at
the `if` statement's own end and there are no unconsumed child nodes within
its span. It proves the assignment even when the condition is false, then
retains the prior local state for a skipped arm. A true condition commits the
source-proven assignment. Existing two-arm selection is unchanged.

The independent source oracle visits masked products `60, 160, 0`, takes the
first assignment and skips the remaining two, then derives `6 ^ 71 = 65`.
A second source variant checks an always-false mask and preserves `a = 3`,
so its final `3 ^ 66` also yields `0x41`. Both variants are checked against
actual output from the normative Malbolge VM on empty and nonempty input.
Extra assignments or outputs inside the sole arm, unbraced statements,
undefined division, out-of-budget loops and forged AST nodes are rejected
without publication.

This is bounded compile-time selection of C state, not guest runtime branching
or a general byte-stream emitter. The original twelve-byte Fibonacci layout
remains unsupported and P0 is still pending.

### Source-proven zero-trip `while` with discarded effects

A complete C program combining a `while` that is false at entry, a guarded
state update and `putchar` in that skipped body, and a subsequent three-step
`do…while` recurrence initially refused at the first local declaration. The
bounded evaluator now still proves the entire skipped body against shadow
local state, checks its branch and putchar AST, then discards all speculative
state and output effects. An executed `while` still reuses its previously
proven body and requires a source-proven false exit within twelve iterations.
The admitted zero-trip subset is deliberately conservative: undefined or
unsupported expressions in a skipped body still refuse compilation, even
though C would not evaluate those expressions at runtime.

The independent C oracle verifies that the first loop executes zero times;
the following three iterations visit `60, 160, 128` and derive `127 ^ 62 =
65`. A source variant swaps the unreachable branch selector so both shadow
branch outcomes are exercised. Both complete programs emit only `0x41` in the
normative Malbolge guest VM on empty and nonempty input, with no output from
the skipped `putchar`. Impure guards, unsupported skipped effects, undefined
expressions and tampered loop/body/guard/output AST reject without artifacts.
This proves a finite source-constant C control-flow slice, not runtime guest
state or a general guest byte-stream layout. The original twelve-byte
Fibonacci P0 remains open.

### Source-proven zero-trip `for` with discarded effects

A complete C recurrence also exposed the separate zero-iteration gate for
`for (unsigned j = 0U; j < 0U; ++j)`. Previously the bounded evaluator
required a positive literal bound and refused before the independently
computed final output. The source-backed proof now permits literal zero
provided the entire body can be checked against shadow local state. Every
speculative write and `putchar` effect is discarded, the loop-local counter
leaves scope, and subsequent real C statements see the unchanged outer state.
The existing positive-bound replay and twelve-iteration cap are preserved.

The full input program skips a guarded state update and putchar, then executes
three iterations of a source-proven `do…while` recurrence. The independent
oracle visits `60, 160, 128` and emits `127 ^ 62 = 65`; the current-profile
normative Malbolge VM emits only `0x41` for empty and nonempty input. Skipped
unsupported increments, undefined division, nested loops, foreign counters
and forged Clang AST nodes refuse without guest publication. As with the
zero-trip `while`, even unreachable unsupported C is conservatively refused.
This is compile-time bounded state projection, not dynamic guest C control
flow or a generalized byte-stream emitter; the original twelve-byte
Fibonacci target remains pending.

### Ordered multi-assignment C conditional arms

A complete three-iteration `do…while` C recurrence now exercises a branch that
updates two unsigned locals per arm before the next loop trip. The pinned
adapter previously refused the program's first declaration because its
source-constant conditional proof accepted only one assignment in each braced
arm. The repaired bounded proof consumes every ordered assignment from both
Clang-backed arms, checks its parent, span, symbol and unsigned expression,
then retains only the chosen state. An `if` without `else` keeps the original
state when skipped. A branch cannot hide an extra output, declaration, nested
statement or unsupported side effect, even in an unselected arm.

The independent C oracle for the two-arm program visits `60, 208, 192` with
branch choices true/false/false, finishes at `a = 191`, and derives output
`191 ^ 254 = 65`. The first complete pinned source probe emitted the real
normative guest byte `0x41` in 31 steps. The regression also covers the
false-first, single-arm taken and single-arm skipped state traces against
actual guest execution on empty and nonempty stdin; source and forged-AST
mutations reject without publishing guest artifacts. This finite projection
still executes C branching at compile time, not in the guest. General runtime
state and the original twelve-byte nonzero Fibonacci layout remain open.

### Source-proven mixed branch assignments and guest output effects

A complete two-trip C `while` recurrence now mutates a different automatic
unsigned local in each `if` arm, then calls `putchar` with a value derived
from the loop state. The previous adapter refused at the first declaration:
it could prove either branch-local assignments or branch-local output, but
not their source-ordered combination. The unified bounded arm walker now
proves every assignment and call in both brace-delimited arms against the
same incoming state. It snapshots the then-arm state and output effects,
restores the incoming state for the else-arm proof, and commits only the
selected state and selected guest outputs. Calls remain independently
source-checked, and an unselected arm cannot hide other effects.

The independent C oracle starts with `a = b = 1` and visits `next = 2, 3`.
The first arm updates `a` to 2 and emits `2 ^ 83 = 81` (`Q`); the second
updates `b` to 4 and emits `3 ^ 45 = 46` (`.`). The real pinned C-to-Malbolge
compiler and normative guest VM emit `51 2e` (`Q.`) on empty and nonempty
stdin; a one-trip variant and a two-trip `if` without `else` each emit
only `51`, proving that skipped calls do not leak. Source mutations involving
increments, division by zero, unsupported calls and nested branches, plus
forged Clang node ancestry, refuse without publishing guest artifacts. The
prior output-only conditional proof is subsumed by the same closed arm
traversal, not replaced by unchecked host output. C state and branching
remain compiler-time projections. General Malbolge byte-stream synthesis
and the original twelve-byte Fibonacci P0 acceptance remain pending.


### Source-proven nested conditional guest effects

A complete two-trip unsigned C `while` recurrence with `if` statements
inside both outer conditional arms initially refused at the JSON adapter.
A bounded arm walker now recursively proves nested, braced `if` statements
up to three levels, including both selected and unselected inner arms.
Every inner predicate, write and `putchar` must belong to the exact source-
backed Clang tree; an unselected branch is checked but cannot leak its
state or output. Branch-local effects replay in source order.

The independent oracle starts at `a = b = 1`: the first trip sets `a = 2`
and emits `2 ^ 83 = 81` (`Q`); the second sets `b = 4` and emits
`3 ^ 45 = 46` (`.`). The full pinned C compiler emits actual Malbolge
whose normative VM produces `51 2e` in eight steps, including an empty
input witness. Regressions cover both guest input cases, skipped outer
`else`, inner `if` without `else`, unsupported source effects and forged
nested AST ancestry. Previously negative tests for valid nested branches
were revised to test genuinely unsupported unbraced forms instead.

This remains compiler-time bounded C replay, not dynamic guest branching.
The original twelve-byte Fibonacci layout remains unsupported and P0 is
still pending.

### Bounded zero-prefixed six-byte guest stream

A complete C source with three automatic `unsigned` locals and a two-trip
`while` loop emits three `putchar` effects in each selected `if` arm. The
first arm writes new local values after its three outputs; the second arm
observes those values and emits three more. The independent C oracle is
`00 51 22 1b 37 39` (NUL, `Q`, quote, ESC, `7`, `9`). The old six-effect
pipeline first refused a non-fixed trace at the typed adapter even though
the standalone guest encoder could execute the corresponding positional
Malbolge program.

The six-effect typed projection now reuses the checked generic source-distinct
SSA proof used for shorter streams, without relaxing type, symbol or output
order checks. The previously fixed six-byte bridge retains its exact 15-step
witness, while zero-first candidates use the bounded state-space proposal
solver. Both paths independently re-admit the layout and execute the
normative profile VM on unused empty and nonempty input. The complete C
program produces exactly six bytes in 23 guest steps, with five real
relocated data writes and no input consumption. A source mutation adding a
selected branch output rejects without artifact publication; forged SSA uses
and nonzero unwitnessed prefixes also reject. The six-byte sequence is not
generated by a host stdout callback.

This proves only closed compile-time local-state and branch replay followed by
six physical guest outputs. It does not lower general runtime C control flow
or arbitrary byte streams, and the original nonzero twelve-byte Fibonacci
P0 acceptance target remains unsupported by the bounded layout grammar.

### Nonzero-leading, source-proven six-effect stream

The existing six-effect search rejected any nonhistorical stream beginning
with a nonzero byte, even when its positional guest arithmetic grammar could
reconstruct the exact target. A red-first standalone VM experiment used a
source-independent six-write guest to derive `35 36 35 00 50 1b` (ASCII
`535`, NUL, `P`, ESC). The bridge first rejected its complete source-distinct
SSA projection; removing only the zero-first restriction permitted the
bounded state-space solver to reproduce the guest sequence. Its output and
real out-of-source data writes are independently decoded and VM-verified.

A second full pinned C experiment uses a two-trip `while` loop, branching and
state transfers between three automatic unsigned locals. It emits the first
three source-backed values `53, 54, 53`, updates them to `0, 80, 27`, and
emits the latter three on the next branch. The source-derived reference is
therefore exactly `35 36 35 00 50 1b`, without a host output substitute.
The final publisher no longer demands a leading zero or literal fixture
identity: it still independently reopens the admitted graphical source and
checks normative VM termination, complete bytes and no input consumption on
empty and nonempty input. The result is an actual 19-step Malbolge guest.
An extra selected C output effect is rejected without publication.

This is a new output-identity boundary (nonzero first byte, repeated byte and
interior NUL), not a new byte-count milestone. Compilation still folds C
control flow into checked constants; the guest executes physical arithmetic
and output, not general C storage, branching or loops. The full twelve-byte
Fibonacci acceptance target still fails at the layout witness boundary and
P0 remains pending.

### Source-independent twelve-byte positional search

A complete twelve-call C output experiment demonstrated that its typed
SSA values were valid, but the bridge and publisher accepted only the
historical twelve-byte fixture. A direct attempt to use the larger
state-space solver for the original Fibonacci trace exceeded a 75-second
bound without a guest witness. Search exhaustion is not impossibility.

The new finite twelve-effect search examines at most 94 relocation phases
with one real `p` or `*` arithmetic write immediately before each output.
It prunes partial paths as soon as their accumulator byte differs from
the source-proven expectation. The cached loader tail proposes candidates
only; the existing independent layout admission checks disjoint writes
outside source, and the normative VM checks exact output, termination and
no consumed input on both empty and nonempty stdin before publication.

An independently encoded guest using eleven `p` writes and one `*` write
at output six emits `51 37 34 38 50 8b cf b9 b2 ba ce 9d` in 27 steps.
The pinned Clang C-to-Malbolge pipeline emits that same binary stream
from twelve source-backed `putchar` calls. An extra output effect refuses
without an artifact; the historical 27-step twelve-byte guest remains
unchanged. The original twelve-byte Fibonacci trace remains unsupported
by this bounded search, and P0 is still open. This is a compiler-time
constant byte stream, not dynamic guest execution of C state or branches.

### Interleaved repeated-output guest layout

A nonfixture twelve-effect literal C program initially passed Clang-backed
source admission but refused at `Layout(UnsupportedEffectTrace)`. The stream
`3e 09 0d 0d 28 2e 13 3d 0a 2e 0a 3d` requires a repeated guest output
without another arithmetic write, plus mixed `p` and `*` instructions. A
source-independent 34-instruction seed was independently decoded and run in
the normative VM, then reconstructed by a bounded accumulator-state beam.
The beam preserves one deterministic representative per progress/low-byte
class; this is a proposal heuristic, not a proof of high-word equivalence.
A short (at most 36-cell, at most 12-prefix) search now supplements the
straight-write twelve-byte grammar; every proposal must pass full positional
admission, disjoint-write checks and VM replays before publication.

The complete C-to-Malbolge pipeline emits that exact binary stream in 34
real guest steps under empty and nonempty stdin. An extra selected C output
refuses without an artifact. The original Fibonacci stream
`02 59 5f 08 57 4f 22 6d 03 90 b3 23` still lacks a guest witness,
and neither dynamic C state nor general byte-stream synthesis is implemented.

### Exact capacity pruning for bounded guest search

The interleaved twelve-byte search originally spent significant time on
geometries that could not possibly emit their requested byte effects. Every
source-backed output needs one physical guest `<` instruction, and every
change from the prior accumulator low byte (initially zero) needs at least
one real `p` or `*` instruction. Repeated bytes can share an accumulator
value. These are **necessary** instruction-count bounds, not full synthesis
or a replacement for verification.

For longer traces (at least eight effects), the search now rejects an
impossible source length, relocation prefix, or partial accumulator state
when its remaining body has too few cells for the
unemitted output effects **plus** their unavoidable byte transitions.
Initial zero outputs before relocation count toward the prefix rather than
body; a final output suffix is handled separately. The current terminal
output proposal pads completed body effects only with no-ops, so two final
unequal bytes cannot use that shape. The valid 34-cell interleaved guest has
an eight-cell prefix and precisely 23 body cells for twelve outputs and
eleven byte changes. The following prefix would leave only 22 cells and is
provably impossible within this layout grammar. Shorter streams retain
existing deterministic witness-selection order.

The proposal beam still discards high-word alternatives, and its finite
length, prefix and geometry budgets can miss valid guests. Every accepted
candidate is independently positionally decoded, checked for disjoint
source-external writes, and replayed on the normative VM under empty and
nonempty input. The original twelve-byte Fibonacci target remains open;
no guest runtime implementation of general C state or control flow follows
from this pruning.

### Preserving bounded high-word guest continuations

Reattempting the complete twelve-iteration Fibonacci C program after exact
capacity pruning still reached typed source admission but refused at
`Layout(UnsupportedEffectTrace)`. The long-stream search had a separate
false-negative mechanism: it retained only the smallest fifteen-trit
accumulator word for each `(emitted effects, low output byte)` group, although
`p` uses the full word when computing the next accumulator. A red-first
successor regression shows that words 3 and 259 both emit byte 3 but a
subsequent crazy operation with data word zero yields bytes 50 and 53,
respectively. Discarding 259 loses the latter valid continuation.

For traces of at least eight effects, the proposal beam now retains the
smallest and largest **full accumulator words** per output-progress/low-byte
group. It still enforces finite source, state and work budgets. An additional
red-first test showed that the search previously recorded discarded
predecessors as permanent reconstruction steps (46 records for 16 surviving
successors). It now materializes only the retained predecessor steps,
keeping history growth aligned with live search paths. Shorter traces keep
their established deterministic search behavior.

The known twelve-byte interleaved source-independent witness remains
independently decoded and replayed in the normative guest VM; the complete
Clang-to-Malbolge C regression still emits its exact 34-step binary stream
on empty and nonempty input. The original Fibonacci stream still has no
admitted guest layout. Keeping two extreme words does not prove equivalence
of discarded middle states, and neither static C replay nor this heuristic
search implements arbitrary guest runtime arithmetic or control flow.

### One-step byte-reachable high-word retention

A further red-first successor experiment found that retaining only minimum
and maximum full accumulator words still loses a valid continuation. The
three words 3, 259 and 515 all emit byte 3, but with the *next* data word
zero their subsequent `p` outputs are 50, 53 and 38. Only the discarded
middle word 259 can produce the next requested byte 53 in one write.

For streams of at least eight effects, the bounded proposal now retains
both full-word extremes **and** up to two extremes among states whose next
crazy operation reaches the pending byte. It reads the next guest data word
from the actual relocation/loader-tail geometry, rather than using the
current word or a fabricated constant. A changed next word of 2 gives 55
instead of 53 and must not retain the false continuation. At most four
representatives survive per output-progress/low-byte group, and only
surviving predecessors enter the reconstruction history.

The red-first middle-word regression, next-word negative control, and the
independently decoded twelve-byte interleaved guest pass. The full pinned
Fibonacci C source still refuses at the guest-layout boundary with no
artifact. One-step reachability is only a deterministic beam priority;
longer-term alternative word states, runtime C state, and arbitrary stream
synthesis remain unimplemented. All published layouts still require exact
independent decoder, disjoint-write and normative-VM verification.


### Two-step byte-reachable high-word retention

The complete twelve-iteration Fibonacci program was retried after the
one-step search improvement and still refused at the verified guest-layout
boundary without publication. A separate red-first successor regression
exposed another deterministic beam false negative. Accumulator words 3,
259 and 515 all emit byte 3.

With the next loader word 2, the first `p` opportunity cannot emit the
pending byte 53 from word 259: it yields 55. Yet a guest no-op advances
the data pointer to the following loader word 0, where `p(0, 259)` yields
exactly 53. The minimum and maximum full words yield 50 and 38 there,
so the old beam lost the middle word.

For streams of at least eight effects, the proposal now inspects two
actual consecutive loader-tail words after each successor. Alongside
full-word extremes and immediate-byte-reachable extremes, it retains up
to two additional representatives that can match after one no-op then
one crazy write. This delayed match is considered only when at least
three body instructions remain for the no-op, write and output.

A negative control changes the later word to 2, for which 259 no longer
matches 53; the older immediate-word negative control also excludes a
delayed match. At most six representatives survive per progress/low-byte
group, and discarded candidates consume no reconstruction records.

The independent twelve-byte interleaved search and complete pinned C
pipeline continue to produce actual normatively verified Malbolge on
empty and nonempty input, while the original Fibonacci twelve-byte
stream still refuses at layout. This bounded two-step prioritization is
not a complete beam, arbitrary guest byte-stream synthesis, or runtime
C arithmetic and control flow. Every accepted candidate remains subject
to the existing decoder, disjoint-write and normative VM checks.

### Two-consecutive-write byte reachability

The complete twelve-iteration Fibonacci C program remains source/typed
admitted, but its original `02 59 5f 08 57 4f 22 6d 03 90 b3 23` trace
still has no verified guest layout. A red-first search regression exposed
another false-negative beam equivalence: full words 3, 259 and 515 all
emit byte 3, but only the middle word 259 reaches byte 255 after two
successive real crazy writes with loader words 2 and 0. The first write
produces low byte 55; the second produces 255. The extreme words yield
3 and 14, and neither a single write nor a no-op followed by a write
reaches 255 from the middle word.

The bounded long-stream proposal now retains minimum and maximum full
words reaching the pending output byte by this two-write sequence, in
addition to its existing full-word, immediate-write, and delayed-write
representatives. It reads both actual future loader-tail cells, requires
at least three remaining body instructions for the two writes and output,
and caps retained representatives at eight per progress/low-byte group.
Changing the later loader word from 0 to 2 removes the middle match in
an explicit negative control. Discarded proposals still consume no
reconstruction history.

This is a deterministic pruning improvement, not an arbitrary-stream
solver. The independently decoded and VM-replayed twelve-output
interleaved guest remains accepted; the original Fibonacci trace still
fails closed at layout. Longer write sequences and alternative guest
control flow may require a different search grammar. No proposal is
published without positional, write-disjointness, and normative VM proof.

### Bounded multi-step guest-byte continuation

The original complete Fibonacci C program still reaches typed byte effects but
has no accepted guest layout. A red-first successor experiment then exposed a
more general loss in the long-stream accumulator beam: words 3, 259 and 515
share output byte 3, but with subsequent loader words 1, 2, 2 only word 259
can reach byte 54 within three physical `p` instructions. The prior beam kept
only extrema and fixed immediate, delayed and two-write patterns, so it
discarded that valid middle-word continuation.

The proposal search now looks ahead through up to three **actual** future
loader words, considering `p` and no-op at each position. A rotation erases
prior accumulator identity, so it cannot distinguish grouped full words. For
each pending-byte class the beam keeps full-word extrema plus up to two
representatives for each shortest matching lookahead distance. The output
instruction consumes a further cell; insufficient remaining capacity prevents
false retention. This replaces the separate short-pattern selectors without
increasing the maximum eight retained words per progress/low-byte class.

The red-first three-write path, changed-third-word negative control and
instruction-capacity limit now pass. All sixteen focused bridge search tests,
independent twelve-byte interleaved guest reconstruction, and full pinned C
interleaved guest/VM parity pass. The original twelve-byte Fibonacci program
still refuses with `Layout(UnsupportedEffectTrace)` and no guest artifact.
The beam remains a bounded proposal heuristic: a valid fourth-step path or a
non-extremal full word may still be missed. The independent layout decoder and
normative empty/nonempty-input VM replay remain mandatory for every publication.

### Alternate short-stream terminal seeds

A twelve-output source-independent guest exposed a distinct layout false
negative: the short-stream search modeled only a no-op immediately before
halt. The actual loader derives its expanded memory from the final two
source cells, so replacing that no-op with a genuine `p` or `*` changes
all earlier relocated data words. This is not merely a harmless terminal
padding choice. A red-first complete guest trace ending in `p` reproduced
the omission even though the independent positional encoder and normative
VM admitted its 34-instruction source.

The bounded short-stream search now tries no-op and crazy terminal
shapes, retaining the previous no-op-first choice and the same 36-cell,
12-prefix geometry bounds. Every proposed variant remains subject to
independent positional decoding, source-disjoint write checks and empty/
nonempty-input normative VM replay. A changed-tail control checks that
the original byte trace cannot simply borrow the no-op loader seed.

This closes one source-seed false negative, not general byte-stream
synthesis. The complete original Fibonacci source still lacks an admitted
guest layout; no dynamic guest C loop, arithmetic or branching is inferred
from a source-proven static byte projection. P0 remains pending.

### Rotating short-stream terminal seed

A complete 36-instruction guest, including a bounded interleaving of real
crazy/rotation writes and twelve outputs, exposed another loader-tail
false negative. Its initial relocation and output source decode correctly,
and both empty-input and nonempty-input normative VM executions yield
`88 b0 85 b6 8b bc b6 88 b0 88 c8 88`. The final source instruction
before halt is a rotation (`*`), not a no-op or crazy write. Because the
loader derives its expanded data words from those source cells, neither
of the two previously searched terminal seeds reconstructs this stream
within the 36-cell, 12-prefix short-search bound.

The red-first test first confirmed that the complete source passes the
independent positional and VM checks while the short-search entrypoint
returns no layout. Adding the rotation seed admits a verified proposal
under the same geometric bounds and acceptance checks. A changed expected
byte is rejected against the independently reconstructed source. The full
original Fibonacci C program still refuses at guest layout without
publishing an artifact; this is one real guest search capability, not
runtime C control flow or arbitrary byte-stream synthesis.

### Changed-byte output at the final source instruction

Retrying the original twelve-iteration Fibonacci program still reached the
source-proven twelve-byte effects but refused at guest layout, without an
artifact. A separate red-first, source-independent guest exposed a false
negative in the terminal search: the final body instruction can be a real
crazy-data write, immediately followed by an output instruction and halt.
The preceding output and that terminal output need not have equal bytes.
The search had discarded this entire terminal shape for traces of at least
eight effects, and the production 36-cell short search never considered an
output opcode as the final loader-source seed.

A complete 34-instruction guest with twelve real crazy-data writes and twelve
output instructions produces `59 3f 2c 48 50 1b 59 3f 2c 48 50 1b`. Its
independent positional source encoding, disjoint data writes and normative
VM replay were established before the search fix. The direct terminal search
and the bounded production short search now both reconstruct a verified
layout. The search retains its 36-cell and twelve-prefix bounds, preserves
existing seed precedence and never authorizes publication from cached loader
memory or predicted output bytes alone.

This removes a structural false-negative assumption, not the need for a
witness for any particular C output trace. The original Fibonacci output
`02 59 5f 08 57 4f 22 6d 03 90 b3 23` still lacks an admitted layout;
no guest runtime C arithmetic or dynamic branching is established. A separate
C probe with nested conditional expressions and a loop failed at frontend
admission and produced no guest, so it supplies no additional C coverage.

### Terminal data-pointer relocation seed

The original complete twelve-iteration Fibonacci C program was retried and
still refused at verified guest layout without publishing source. A red-first,
source-independent 35-instruction guest then exposed an additional false
negative in the layout/search boundary. Its 12 real crazy-data writes emit
`3f 0a 2b 14 35 00 3f 0a 2b 14 35 00` in the normative VM, followed by
a second `j` immediately before halt. The previous layout validator rejected
all second data-pointer relocations, even this output-neutral final move.
The final `j` also changes the last loader source seed, which the bounded
output-stream search had not considered.

At that stage, the linear checker admitted **only** a second `j` as the
penultimate source instruction. It reconstructed the unwritten expanded
loader operand from the original final source bytes and proved D's exact
profile-width wraparound. At that stage nonterminal second relocations and
all third relocations rejected; source-aliased arithmetic also rejected.
The bridge preview models the terminal move only, and the source search
tries the new
seed after the established earlier choices. Actual positional encoding,
disjoint-write checks and both empty/nonempty-input normative VM executions
remain mandatory for admission. The independent 35-step guest and the bounded
production search now pass their original red-first regression.

This establishes a narrowly safe extra guest loader seed, not general
relocation or arbitrary byte-stream synthesis. The original Fibonacci
`02 59 5f 08 57 4f 22 6d 03 90 b3 23` still lacks a verified layout,
and runtime C arithmetic and dynamic control flow remain out of scope.

### Sparse guest search frontiers remain exact

A red-first search regression exposed an avoidable loss beyond the beam's
three-loader-word lookahead. Three full accumulator words (`3`, `259`,
`515`) all emit byte `3`. Following an output, a future source data-word
sequence `0, 0, 0, 2` lets the middle word reach byte `1` through guest
crazy operations and no-op strides, but only at the fourth future word.
The previous unconditional min/max and short-lookahead pruning discarded
word `259` even though the frontier had only a few states and therefore
needed no heuristic reduction. This was a genuine proposal false negative,
not a verifier rejection or an unsound guest program.

Search now retains every distinct `(emitted output count, exact accumulator)`
state when its candidate frontier fits the existing 16,384-state cap.
Only an over-budget frontier invokes the existing bounded high-word beam.
A separate dense-frontier test proves that the budget and history-record
limits remain active. A changed fourth guest word cannot produce the same
byte from the retained middle state. The underlying crazy operations and
output matching use the canonical profile helpers; no new source encoding
or bypass of positional decoding, data-write disjointness or normative VM
replay is authorized by this proposal change.

The original source-backed twelve-iteration Fibonacci program still reaches
typed and ternary admission but refuses at guest layout without publishing
a source artifact. The 36-cell short-stream geometry remains bounded; this
search correctness fix does not establish an arbitrary byte-stream backend,
runtime guest C arithmetic, state or dynamic control flow. P0 stays open.

### Leading-zero guest outputs before relocation

The complete twelve-iteration Fibonacci C program was rerun and still refused
at verified guest layout without publishing an artifact. An independent
11-instruction guest exposed a separate bounded-search false negative: seven
real zero-byte outputs can occur **before** the single data-pointer relocation,
followed by a crazy write and a final nonzero output immediately before halt.
The canonical source encoding and normative VM agree on all eight output
instructions with no input consumed, but the old search started at `N + 4`
source cells and limited relocation prefixes to `length - (N + 3)`.
Both exclusions are invalid when initial output effects occupy prefix cells.

For streams of at least eight effects, the search now starts at the necessary
instruction lower bound and permits the longest prefix with at least one body
instruction. Existing per-geometry body-capacity checks still subtract
source-encoded zero outputs, and every accepted candidate passes independent
positional decoding, disjoint-write checks and normative empty/nonempty-input
VM replay. The red-first eleven-cell source now reconstructs an independently
admitted guest; a forged final byte still rejects. This broadens one valid
source geometry, not runtime guest C state or unbounded synthesis. The
original Fibonacci stream remains unsupported and P0 stays open.

### Dense beam lookahead across repeated effects

The original twelve-iteration Fibonacci C source was rerun and still reached
layout admission without a verified guest witness or published artifact. A
red-first dense-frontier regression then exposed another general proposal
false negative: distinct full accumulator words can have the same low byte
`3`, so the next output may repeat `3` without changing state. The previous
beam skipped future-word reachability whenever that immediate expected byte
already matched, discarding accumulator `259` before a later changed output.
For the actual next loader word `0`, a subsequent crazy write from `259`
produces byte `53`; changing the word to `2` removes that short continuation.

The over-budget beam now looks for the next **different** pending output
byte, including beyond repeated output effects, before choosing reachable
full-word representatives. A red-first regression checks retention, the real
repeated-output/crazy/output continuation, the changed-loader-word negative,
and the 16,384-state budget. Below that budget the complete exact frontier
remains unchanged. The lookahead remains a bounded search heuristic: candidate
source publication still requires independent positional decoding, disjoint
guest data writes and normative VM replay under two inputs. This fixes one
pruning false negative, not the full Fibonacci layout or runtime C state.

### Wider bounded source geometry for twelve-byte streams

The complete original Fibonacci C program still reaches the guest layout
stage without a verified twelve-byte source and refuses without publication.
A separate source-independent thirty-nine-instruction guest demonstrated an
avoidable 36-cell search boundary: eight initial no-ops, one relocation,
twelve crazy/rotate data writes separated by five no-op data strides, twelve
real output instructions and a final halt. Its VM output is
`b5 4f 42 3d 33 08 50 23 b4 4d 5d 31` under empty and nonempty input.
The original positional source independently passes disjoint-write and
normative-VM verification, while the previous short search returned no guest.

A separate, effort-capped fallback now searches 37 through 39 source cells
with an output instruction immediately before halt, at most eight prefix
cells and a 2,048-step history stop threshold per geometry. It tries longer
sources and prefixes first to reach a viable witness without traversing
all earlier high-cost geometries. The established 36-cell search retains its
original order and 700,000-step cap; the wider path never overrides its
witnesses. The 39-cell guest is reconstructed and independently re-admitted,
and the pinned C frontend can emit these same twelve source-proven bytes as a
real guest capsule. A forged expected output fails the original guest proof
and an extra thirteenth source output refuses without artifact publication.

This is a finite additional verified source geometry, not arbitrary stream
synthesis, guest runtime arithmetic or completed P0 acceptance. The exact
Fibonacci stream `02 59 5f 08 57 4f 22 6d 03 90 b3 23` remains unsupported.

### Wider source layout with an arithmetic loader tail

The original twelve-iteration Fibonacci C source still reaches layout and
refuses to publish an unwitnessed guest. A source-independent 39-instruction
Malbolge program exposed a separate missed layout: an eight-cell prefix,
relocation, twelve crazy/rotate writes and their outputs, four interleaved
no-op strides, and a **final crazy write before halt**. The final write
changes the loader expansion seed without adding a thirteenth output. Its
normative guest bytes under empty and nonempty input are
`a1 11 2c 0b 28 10 2d 0a a1 ff a3 ff`. The previous 36-cell search and
the 37-to-39-cell **output-terminal-only** fallback both missed that guest.

The wider fallback now considers the crazy-terminal source seed after its
established output-terminal priority, retaining the 37-to-39-cell geometry,
eight-prefix limit and 2,048-history-step cap per geometry. A red-first
source-independent regression proves the source's positional encoding, exact
VM output and disjoint guest data writes; the recovered guest is again
independently decoded and replayed before admission. A forged first output
byte fails verification. This does not establish an arbitrary output stream,
source-level C loop support, guest runtime state or the original Fibonacci
acceptance; P0 remains open.

### Longer rotated loader tail admits a verified twelve-byte stream

An attempted full twelve-iteration Fibonacci C compilation still reaches the
bounded guest layout search and refuses without an artifact. The same search
had a concrete additional false negative: a 39-instruction relocated program
with twelve separate guest outputs, twelve interleaved crazy/rotate writes,
four data-pointer no-op strides and a final output-neutral **rotation** before
halt. The exact normative guest output is
`b1 8a b7 88 b1 8a b4 88 b0 88 b3 82`, with no consumed input. The
existing 36-cell search and the wider output/crazy-tail fallbacks could not
reconstruct it, even though independent positional encoding and normative VM
execution under empty and nonempty inputs proved the complete program.

A red-first test now exercises the missed trace. The 37-to-39-cell fallback
searches the distinct rotated loader seed after its established output and
crazy priorities, with the same eight-prefix and 2,048-history-step caps per
geometry. The recovered source is independently re-decoded and replayed, its
thirteen disjoint writes remain outside the source, and a forged expected
first byte is rejected. The added fallback has observable search cost, so it
is restricted to twelve-effect searches only. This is not a general source C
runtime or a witness for the original Fibonacci outputs; P0 stays open.

- A red-first 39-instruction relocated guest with twelve arithmetic-derived
  outputs and a final output-neutral no-op exposed a missing long-tail loader
  seed. Its normative VM output is `a3 10 30 10 2a 11 2c 11 a2 01 a6 fc`.
  The public 37-to-39-cell fallback previously searched output, crazy and
  rotate terminals but not no-op, and rejected this independently proven
  stream. Adding the no-op seed after the existing priorities recovers the
  full guest with unchanged eight-prefix and 2,048-history caps. Independent
  positional admission, both-input VM replay, forged-output refusal and a
  pinned C-to-Malbolge source with twelve ordered `putchar` effects pass.
  The original conditional Fibonacci C source still fails closed at layout;
  this is bounded guest synthesis, not general runtime C state or P0 closure.

### Live second relocation as a new guest layout capability

A full retry of the twelve-iteration Fibonacci C source still fails safely at
its original unsupported guest output stream; no capsule is published. A
source-independent 13-step real Malbolge program instead exposed a different
layout limitation: after `j`, a second `j` can read a fresh expanded-loader
word, relocate D again, execute a real crazy-data write and emit a byte
before halt. The old linear validator refused this valid sequence solely
because the second `j` was not penultimate. A separate 15-step guest proves
that a live second `j` between two arithmetic/output pairs changes the
actual D path and emits `36 08`, without consuming supplied input. The
unrelocated comparison happens to emit the same two bytes; the proven
semantic difference is the guest's data address, not its output value.

The corrected layout checker permits **at most two** relocations, derives
the fresh operand from the original graphical source's loader-tail recurrence,
refuses operands already written by the guest, and checks source-disjoint
writes and exact profile-memory D-pointer wraparound after either move.
The raw independently encoded guests now match every admitted code,
encryption, D and data-write position during traced normative execution.
A replaced second-j opcode and a third relocation still reject. This
advances address-sensitive guest layout, not the byte-stream proposal search:
the C-to-guest publisher does not yet synthesize this nonterminal shape,
and the original Fibonacci output oracle remains unsupported. P0 stays open.

### Source-bounded repeated relocation with loader checkpoints

The unchanged full twelve-iteration Fibonacci C program remains a guest-layout
refusal, not an emitted guest program. A separate red-first, source-independent
18-step Malbolge experiment instead executes three live `j` operations,
interleaved with crazy/rotate writes and three actual guest byte outputs. The
previous layout checker rejected the graphical program solely because it
permitted no more than two relocations. Both historical and current normative
VMs execute the raw independently reconstructed source; the repaired layout
encoder now emits those identical graphical bytes and matches every traced
code, data-pointer, encryption and write address. A second triple-`j` guest
reads a later operand thousands or millions of words past source and changes
D again; its independent VM trace agrees under both profiles.

The linear admission proof now checks each relocation independently: a later
`j` must read an exact source-shadow or untouched expanded-loader word, and
all following arithmetic
writes must remain disjoint from graphical source, with exact D wraparound.
Sparse 1024-word recurrence checkpoints amortize distant, repeated and
backward operand queries without storing full VM memory. A forged `j` opcode
still rejects at independent source re-admission. This removes an artificial
relocation *count* ceiling, not the proof limits on modified operands,
post-relocation jumps, source aliasing, runtime input-dependent state, or
full source-C synthesis. The P0 acceptance oracle remains unsupported.

### Constant-time untouched loader-tail relocation proof

The original source-backed twelve-iteration Fibonacci C program still needs
a guest layout. A follow-up experiment on repeated live `j` relocation
found that the loader's crazy recurrence has a six-word period starting
with the first expanded memory word. Each of its nine possible pairs of
ternary digits has period dividing six from that point; the independent
word-width components preserve the same property for both historical 10-
and current 15-trit memory.

The exact layout admission helper now computes untouched loader operands
with at most six crazy steps, rather than expanding up to distant source-
memory addresses through 1024-word checkpoints. Tests exhaust the nine
single-trit seeds, check both profile VMs at source-adjacent, middle and
final memory positions with two different graphical terminal seeds, and
retain separate three-live-relocation VM trace checks. Source-overlapping
or guest-written operand reads remain disallowed; this changes verification
cost, not accepted guest semantics or production proposal coverage. The
byte-stream generator still proposes only its original first `j`, and P0
remains pending.

### Bounded second-relocation guest proposal

The longer-stream bridge previously reconstructed only an initial guest `j`,
although the independent layout checker could verify additional moves. A
red-first source-independent guest with two arithmetic/output effects and a
second live `j` emits `36 08` in the normative VM. The bounded byte-stream
proposer now explores two relocation regions separated by actual guest
arithmetic and output effects. The second `j` operand comes from the exact
untouched loader tail, never from a guessed destination.

A second, three-effect guest with two outputs before the later `j` also
reconstructs, with real normative VM byte parity and disjoint data writes.
A forged byte oracle rejects. The new proposer examines up to 33 source
prefix positions, at most twelve bytes, and fixed final output/halt cells.
It runs only after previous finite search shapes fail. The original full
Fibonacci program still has no verified guest layout; this is bounded
synthesis of arithmetic/byte effects, not runtime C state or P0 closure.

### Bounded third-relocation proposal through real source C

An independently constructed 18-instruction Malbolge guest, with three live
`j` relocations separated by crazy/rotate writes and output effects, emits
`51 a2 fe` in the normative current-profile VM. The previous output-stream
proposer supported at most a second relocation even though the standalone
layout verifier could already validate the third one. A red-first test
reproduced that gap. A separate five-output guest with later relocation
splits emits `54 08 a7 b1 bc`, proving the new search is not tied to a
one-effect-per-region split.

The bounded third-relocation proposal enumerates 0 through 32 initial
no-operation cells and two interior splits among 3 through 12 output effects.
Each region contains at least one arithmetic write and an actual byte output.
The proposal derives each fresh `j` operand from untouched loader memory;
it refuses reads of source bytes or guest-written addresses, aliases among
arithmetic writes, and unsafe source overlap. The final output/halt cells
fix the loader seed for this finite straight-line grammar. Every proposed
source is independently re-decoded, checked for exact data addresses and
replayed in the normative VM before acceptance.

The real pinned Clang C pipeline now admits a three-iteration Fibonacci-style
unsigned recurrence with local state, arithmetic, a branch and three `putchar`
effects. Its independently computed reference is `51 a2 fe`, matching actual
VM output with empty and supplied input. The distinct-triple publisher has
its own explicit three-`j` grammar and repeats source-disjoint layout and
VM proofs; it does not trust the bridge's proposal. Source mutation to
unsupported division rejects without artifact publication. This remains
**compile-time** evaluation of bounded C state, not Malbolge runtime C
arithmetic or arbitrary guest byte-stream synthesis. The original twelve-
output Fibonacci acceptance oracle remains unwitnessed; P0 stays open.

### Four live relocations and a nonzero-first five-output C recurrence

An independent source-code experiment first exercised the five-iteration
Fibonacci-style unsigned C recurrence with locally maintained state, an
odd/even branch, checked division and multiplication, and five distinct
`putchar` effects. Its independently calculated output is
`35 08 dc 08 a3`. The existing compiler first rejected the nonzero-first
five-output stream at its bounded bridge, then rejected its actual candidate
at the separate file publisher. Neither stage published a guest artifact.

A generalized deterministic proposal now enumerates the positions of up to
three internal `j` splits among three to twelve output effects, rather than
assuming a particular region length. Each relocation reads an exact untouched
loader operand; every arithmetic write is outside the complete code source
and all guest writes are disjoint. All accepted proposals still undergo
independent positional encoding, source re-admission and normative guest VM
replay with empty and nonempty input. A separate four-output guest emits
`38 17 2a 2a` using four live relocations. A five-output guest with a
later split emits `35 08 dc 08 a3` using four relocations and five genuine
write/output pairs. Forged output is rejected. The generalized three-region
search retains the previously verified three-relocation grammars.

The five-effect publisher now also independently decodes its staged source,
checks the exact four-relocation instruction grammar, reads the precise
profile identity and verifies five separate source-disjoint write addresses
before performing its own normative VM replay. The complete pinned C pipeline
now publishes a genuine capsule for the five-iteration recurrence and the VM
emits exactly `35 08 dc 08 a3` under both empty and nonempty input. A C
division-by-zero mutation refuses without producing a guest file. This
still compiles C recurrence arithmetic and control flow **at compile time**,
not inside the guest; full twelve-output Fibonacci and general guest runtime
C state remain unsupported, so P0 remains pending.

### Independent twelve-byte publication admission

The full twelve-iteration Fibonacci C source was rerun after the four-live-`j`
work and still fails closed at guest layout, with no published capsule. A
separate red-first publication regression exposed a different verifier gap:
a real forward-jump guest that skips inert source cells emits twelve zeros
and halts in the normative VM, yet the twelve-byte publisher previously
accepted that output transcript despite the bridge never proposing `i`
control flow. VM byte parity alone was not a proof of the allowed linear
machine-code shape.

The twelve-byte publisher now independently decodes the entire staged
source, requires one opcode per byte effect, re-admits positional code and
current-profile identity with the linear layout checker, and verifies every
arithmetic write address is unique and outside source. It requires the
reconstructed execution to cover the source in exact step order before
replaying the same real VM byte oracle with empty and nonempty input.
The red-first forward-jump guest now refuses, while an independently encoded
12-output relocated arithmetic guest still passes. This tightens source
publication proof, **not** the range of synthesizable byte sequences; the
original Fibonacci reference and general guest runtime C state remain open.

### Two live relocations without paired output effects

The complete twelve-iteration Fibonacci C program was rerun first and still
refuses safely at guest layout. A separate source-independent real Malbolge
program exposes a wider capability gap: it executes two live `j` relocations,
intersperses no-op data strides, and emits repeated and distinct bytes without
one `p`/`*` write for each output. Its twelve-byte VM transcript is
`36 36 01 fe a2 0e 28 fe b1 85 fe b1`. The prior bounded output search
could not reconstruct that transcript.

The finite search now admits a second relocation at an independently checked
source position, derives the new data pointer from the untouched expanded
loader word, and resumes accumulator/output state search on its new data
region. It rejects overlapping or source-bound data regions before proposing
code and caps both the per-geometry search and the number of geometries.
Every proposal still passes canonical positional layout, disjoint guest write
proof, and normative VM execution with empty and nonempty input. A source-
independent test constructs the original machine code without using the
search under test, checks the real VM bytes, recovers a two-relocation guest,
and rejects forged expected output. This advances general guest synthesis,
not runtime C state or the original Fibonacci target; P0 remains open.

### Three live relocations across non-paired guest byte effects

The original twelve-iteration Fibonacci C program was retried before this
change and still refused safely at guest layout. A separate independently
encoded Malbolge program has three live `j` relocations, repeated output
instructions without intervening writes, and no-op data strides. The
normative current-profile VM executes all 31 source instructions, producing
nine output bytes (`41 41 11 30 17 17 2c 18 35`) with supplied input
left unread.

The bounded split-beam proposal now models one or two subsequent live
relocations after the initial source relocation. It derives each `j` operand
from an untouched expanded loader word and conservatively reserves every
data address, including no-ops and relocation reads. A three-region fallback
explores a small, deterministic set of balanced layouts only after the
previous cheaper proposals fail. The source-independent test checks that the
three-relocation proposal is admitted by the separate positional verifier and
VM replay, and that a forged output transcript refuses admission. The same
nine bytes can also be realized by a simpler one-relocation guest: the test
establishes that three live relocations can be **proposed and verified**, not
that they are necessary for those bytes. This is neither general guest
byte-stream synthesis nor guest-runtime C state; P0 remains open.

A further red-first 33-cell guest exercises the same real three-region
semantics but concentrates two additional no-op data strides before the
second relocation. It emits `35 35 86 af 8f 8f b5 83 c4` in the normative
VM; the previous 29/31-cell balanced search missed this transcript. A
bounded 33-cell, one-position-offset split geometry now reconstructs an
independently admitted 33-cell guest with three live relocations, source-
disjoint data writes, VM parity on two input streams, and forged-output
rejection. The original twelve-iteration Fibonacci program was retried
first and still refuses at layout. This is bounded proposal coverage, not
a general layout solver or guest runtime C-state implementation.

### Source-zero outputs before the first relocated data region

A separate source-independent 34-instruction Malbolge program executes an
initial output while the accumulator is still zero, followed by three live
`j` data relocations and nine more byte effects. Its actual current-profile
VM transcript is `00 3e 3e 2e 0a 3d 3d 10 40 19`. The prior three-region
search could synthesize the same bytes by a different guest program, but
**could not recover an initial zero-output instruction**: it forced every
pre-relocation source position to be a no-op. A red-first regression checks
this missing executable layout behavior rather than falsely claiming the
output transcript was altogether unreachable.

The bounded three-region proposer now considers proven leading zero outputs
in the graphical source prefix before falling back to the old no-op path.
It still derives all later `j` operands from untouched loader memory and
only accepts candidates after independent positional/source-disjoint layout
admission and normative VM replay under empty and nonempty input. The test
checks exactly three live relocations, an actual output instruction at the
first source cell, and forged-output refusal. This improves source-layout
coverage but does not implement arbitrary C state or complete the original
twelve-byte Fibonacci guest; P0 remains open.

### Compact two-region sources with a zero-output prefix

An independently encoded 22-instruction guest emits zero before any `j`,
then executes two live data relocations with both repeated and distinct
outputs. The real VM emits `00 53 53 42 39 38` without consuming stdin.
The earlier two-region search missed this complete source: descending
lengths exhausted its 1,500-geometry attempt cap before reaching shorter
valid layouts, and the searched prefixes excluded initial zero outputs.

A compact-source pass now checks lengths through 28 under a separate
600-geometry limit before the unchanged 1,500-geometry descending scan.
Both passes retain the existing per-beam work cap.
Source-proven leading zero effects can occupy prefix instructions, with the
old no-op prefix retained as a fallback. The red-first test requires a
source no longer than the independent guest, its actual first zero-output
instruction, both live relocations, source-disjoint writes, and VM parity
under empty and nonempty input; a forged byte refuses admission, but the
full twelve-output Fibonacci C acceptance remains unimplemented.

### Compact three-region source with repeated outputs

A separately positionally encoded 27-cell guest outputs an initial zero,
then nine total bytes across three live `j` relocations, six arithmetic
writes, and repeated output effects. The normative current-profile VM emits
`00 38 38 82 ce ce c6 7b 8b` without consuming its supplied input. The
old three-region fallback tested 29, 31 and 33 cells for this nine-byte
stream and missed the valid shorter program even though the independent
layout checker admitted its source and disjoint guest data writes.

An additional bounded `3 * N`-cell geometry now places its two subsequent
relocations at independently offset thirds, retaining all previous search
priorities and work caps. The red-first regression requires a recovered
source of at most 27 cells with a real first zero-output instruction,
three live relocations, source-disjoint writes, normative VM parity on two
input streams, and forged-output refusal. This is one additional finite
proposal shape, not shortest-code optimality, general byte-stream synthesis,
or C guest-runtime arithmetic. The original twelve-output Fibonacci source
remains the P0 acceptance target.

### Uneven compact three-region relocation spacing

The independent 28-cell guest places live `j` instructions at positions 8,
14 and 21, with a no-op data stride before the second region's first write.
Its nine real output effects are `00 50 50 3f 36 36 3f 00 12`. It exercises
both repeated and nonadjacent zero bytes, not nine host-emulated writes.
The existing bounded three-region search missed this source-independent,
positionally admitted guest because its fixed lengths skipped 28 cells.

A parameterized `3 * N + 1` compact geometry now allows the second extra
relocation to shift independently by one cell. The red-first test requires
an equally short or shorter three-`j` guest, the same actual initial zero
instruction, source-disjoint writes, normative VM replay with two input
streams left unread, and forged-byte refusal. Existing geometry priorities
and per-search work limits are preserved. This neither proves shortest-code
optimality nor implements general C runtime state: the original twelve-byte
Fibonacci P0 acceptance remains pending.

### Four live data regions with read-only operand revisits

The complete twelve-iteration Fibonacci C source was rerun first. It still
fails closed at guest layout, without publishing an artifact. A separate,
independently encoded 29-instruction guest then demonstrated four live `j`
relocations, nonpaired writes/outputs, repeated byte effects and a genuine
read-only revisit of an earlier data operand. The normative VM emits
`00 42 42 03 b7 b7 ff b9 a9` without consuming supplied input. Its exact
positional source, data writes and VM execution independently pass the
publisher, while the previous split proposer rejected the layout.

The split proposal now admits three additional relocation operands after
the first `j`, with each later `j` still required to read an untouched
loader word. A data address may be revisited by a later no-op or output:
it need not be reserved as another write. The independent layout verifier
continues to exclude overlapping writes and replays the actual VM trace,
so proposal uncertainty cannot authorize publication. A compact bounded
four-region zero-prefixed fallback now explores the `3 * N + 2` source
geometry after existing search priorities. The red-first regression proves
recovery, four real relocations, normative guest replay under two inputs,
and forged-output refusal. This is a finite candidate grammar, not general
stream synthesis, runtime guest C state or completion of the P0 Fibonacci
program.

### Nonzero-first effects in the four-region proposal

A separate independently encoded 29-cell guest retains four live `j`
relocations, repeated output effects and read-only data revisits, but moves
its initial zero output into an existing later data stride. Its actual VM
transcript is `42 42 03 03 b7 b7 ff b9 a9`, not a host-produced output
record. The prior four-region fallback rejected the trace before search
because it required the first byte to be zero, although the unchanged
independent verifier admitted its complete source and write footprint.

The four-region proposer now also explores a no-output prefix for nonzero-first
streams. The first byte still requires a genuine relocated arithmetic write;
no source or data changes are inferred from the host output bytes. Recovered
code must pass independent positional decoding, source-disjoint write proof,
and normative VM replay with empty and nonempty input; forged expected bytes
refuse. This removes a gratuitous output-value gate within one bounded
geometry, **not** a complete generalized layout solver or guest-runtime C
state. The original twelve-byte Fibonacci C acceptance remains pending.

### Uneven four-region source with an early data stride

The original twelve-iteration Fibonacci C program was rerun and still
refuses guest publication at layout. A separately encoded 30-cell guest
inserts a no-op immediately after the first `j`, moving subsequent live
relocations to positions 15, 20 and 23. The actual VM emits nine bytes
`00 41 41 8a c4 c4 8a c6 86` and consumes no stdin. The existing
29-cell four-region proposal missed this independently admitted guest.

A bounded `3 * N + 3` proposal now admits the shifted four-region geometry
after the previously established `3 * N + 2` shape. The red-first
regression independently decodes the source, checks genuine four-`j`
recovery, replays the normative VM under two inputs, and rejects a forged
output. Source-disjoint writes and exact effect order remain independent
publisher obligations. This is a new finite geometry, not a general C
runtime or the full Fibonacci P0 acceptance.

### Four-region output in the final source instruction

The original complete twelve-output Fibonacci C program still refuses at
guest layout without publishing a guest. A separately encoded 30-cell guest
with four live `j` operands moves a repeated output into the penultimate
source cell, immediately before halt. This changes the loader expansion seed
and emits the actual nine-byte VM trace `00 41 8a ce ce 0b bb 09 09`.
The independent publisher admitted its positional source and source-disjoint
write footprint, but the four-region proposer searched only a final no-op.

That proposal now tests the existing no-op terminal first and a real terminal
output second for each bounded four-region geometry. The last output must
match the current guest accumulator; source-tail memory changes are not
guessed from the desired bytes. Red-first recovery, four-relocation decoding,
empty and nonempty input VM parity, and forged-output rejection pass.

This widens one bounded candidate grammar, not general synthesis or runtime C
arithmetic. The original Fibonacci P0 acceptance is still pending.

### Four-region arithmetic terminal seeds

The original complete twelve-output Fibonacci C program still refuses at
layout with no published guest. A source-independent 30-cell guest with
four live relocations instead makes its final instruction before halt a
real `p` or `*` data write. The unchanged nine output instructions emit
`00 38 38 8a b5 b5 b1 88 b0` with the terminal `p`, or
`00 41 41 8a b5 b5 8a c6 8a` with the terminal `*`. Those source cells
also select a different loader-expanded data stream for earlier writes.

Both 30-cell programs were independently admitted by the publisher and the
normative VM. Earlier four-region proposals searched only terminal no-ops
and outputs, so neither source could be recovered.

A shorter 29-cell source-independent guest exposes the same gap in the
original compact relocation geometry. Its terminal `*` changes the loader
seed while the VM emits `00 42 42 03 c6 c6 a5 18 ff`. The independent
publisher admitted the source before the expanded search; recovery failed
without arithmetic terminal candidates in this shorter geometry.

The four-region composer now makes a tightly bounded first pass over both
`3 * N + 2` and `3 * N + 3` split geometries with 64 retained search steps
for each arithmetic terminal. The established no-op/output searches retain
their previous geometry order and 32,768-step budget. Red-first tests pin
all three guest oracles, check four live `j` relocations, replay both input
streams and reject forged outputs. Independent positional and source-disjoint
write admission remains decisive.

This adds bounded source-tail choices, not arbitrary byte-stream synthesis or
runtime C arithmetic and loops. The original Fibonacci P0 acceptance
remains open.
