# Parametric guest byte-stream emission

## Status

Partial. One original complete Fibonacci C program now reaches the guest VM;
generalized source-C and arbitrary byte-stream support are not implemented.

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

### Verified retry of complete output proposals (2026-11-14)

The straight-line guest search previously stopped at the first state with
all requested outputs, before checking whether its positional encoding could
pass independent layout admission. If that proposal failed, the rest of the
same source geometry was discarded even though subsequent source cells and
different accumulator paths might yield a valid guest.

The completion callback now checks each proposal before search success, and
continues after rejection with at most four completion checks per geometry.
A focused two-entrypoint regression verifies a rejected first completion,
accepted later completion, and the hard all-rejected budget. The unchanged
alternate no-op terminal guest still passes real VM replay in both
entrypoints. This is bounded search coverage, not a completeness proof or
implementation of guest-side C runtime arithmetic and branching. The
pinned C frontend executable is unavailable locally.

### Completed source-revisit progress after bounded pruning (2026-11-14)

A dense source-revisit frontier formerly discarded states whose output count
already equaled the requested byte count. The search tests a complete trace at
each source position, but an unsuccessful early positional encoding does not
prove a valid halt cannot follow additional no-op source cells. Dropping the
completed state after that unsuccessful attempt prevented all later retries.

The beam now retains completed output counts along with incomplete progress,
under the same 16,384-state limit and full-accumulator keys. A red-first
28,672-candidate regression proves both completed high-word diversity and
two-layer reconstruction linkage in both bridge entrypoints. The independent
twelve-byte original Fibonacci guest still executes on the normative profile
VM with empty and binary input. The pinned Clang 22 frontend executable is
absent locally, so the complete source-C pipeline remains unverified.
This is a bounded proposal-search correction, not generalized dynamic C
arithmetic/control, arbitrary guest streams, or P0 acceptance.

### Retained-only source-revisit reconstruction history (2026-11-14)

The bounded source-revisit search formerly allocated permanent predecessor
records for every speculative successor, even when a 16,384-state beam
discarded thousands of them at each source cell. The successor map now
temporarily stores complete links and appends only retained paths to history;
the full accumulator keys, progress-balanced beam, exact sparse behavior,
independent positional verification, and normative VM admission are unchanged.

A two-layer dense regression constructs 24,576 initial candidates and proves
the first layer retains exactly 16,384 links, with all second-layer parents
pointing into that retained layer. The original twelve-output Fibonacci guest
and its canonical typed trace still reproduce
`02 59 5f 08 57 4f 22 6d 03 90 b3 23` on the normative VM with no input
consumption. The pinned LLVM 22 source-C frontend is absent on this host,
so these runs do not establish end-to-end source-C compilation. Guest runtime
C state, arbitrary byte-stream synthesis, and P0 acceptance remain open.

### Source-revisit progress quotas and twelve-byte typed trace (2026-11-14)

A source-revisit beam with six populated output counts had been spending
all capacity beyond per-byte extremes on its most advanced counts. A new
red-first dense regression identifies an intermediate full accumulator
word at an earlier count with a genuine crazy-operation continuation.
The search now apportions its bounded capacity across active counts before
redistributing unused slots toward advanced paths. Exact sparse search,
full-word keys and independent layout/VM acceptance remain unchanged.

The original complete twelve-byte unsigned Fibonacci output has an
existing **test-only** real guest witness via the source-revisit search;
its original `HEAD` implementation and the balanced version both pass
the normative VM replay. The typed canonical publisher can also admit
that full byte stream, so its obsolete negative expectation is updated.
This does not prove the pinned C source compilation: the native frontend
was missing locally, and the three original C-pipeline tests skipped.
Dynamic runtime C operations, general synthesis and P0 remain open.

### Wider finite C steps and protected-counter arithmetic (2026-11-13)

A complete C source with a named `position` counter, two-digit
`position += 12` induction, real binary `getchar`, nested conditional,
`continue` and trailing fresh read originally refused at normalized
lowering. Exact 1–99 decimal source/Clang-backed stride geometry now
admits the three-trip loop and a reverse `position -= 12` loop. Both
execute genuine binary guest I/O, emitting four copies of the initial
byte and a fresh byte in eight normative VM steps. Assigned strides,
zero-trip and boundary forms reach isolated layout admission; skipped
`!=` endpoints, divergent steps and forged source/AST fail closed.

A separate complete C program first refused its protected-counter
`position / 12 == 1` predicate. Bounded signed `i32` induction
arithmetic now proves source- and Clang-authenticated `+`, `-`, `*`,
`/`, and `%` with a positive denominator for division/remainder and
checked overflow for all operators. The program's second-trip `break`
changes its guest effect trace: it emits three real copies of the
initial input and a fresh second byte in seven VM steps, not the five
bytes/eight steps of the unbroken loop. Multiplication selects the
same guest-visible exit; other operations reach frontend admission.
Same-width source comparator and number forgeries (including direct
counter comparisons), altered operators/AST ancestry, zero divisors
and reachable overflow refuse before guest publication. These proofs
replay bounded source-local C induction only; guest runtime arithmetic,
branching, storage, EOF, and generalized streams remain unsupported.

### Source-authenticated named C induction counters (2026-11-13)

A complete C program with a live `getchar` local, a step-by-two finite
`for` loop, a nested input-dependent branch, induction-selected `continue`,
and trailing fresh I/O first failed in the JSON adapter when the counter was
spelled `index` instead of `i`. The induction proof now binds an ASCII C
identifier of 1–32 bytes to the pinned Clang declaration reference and exact
source tokens in the declaration, condition, increment and all proven body
predicates. It derives expression geometry from the identifier width rather
than assuming one-byte counter names. Longer names and absent original source
for non-`i` names remain unsupported and fail closed.

The unchanged complete program emits four copies of its actual first guest
input byte followed by the next input byte in eight normative VM steps,
across binary boundaries and seeded inputs. A descending `position -= 2`
program, and a direct `index == 2` conditional, also emit exact independent
byte oracles. Nine further name/step/predicate shapes reach layout admission
under an intentionally rejecting backend stub. Forged source token prefixes,
header bindings, Clang declaration names and step operators refuse without
publishing a guest artifact. All induction values remain bounded C
compile-time replay, not guest runtime C control, arithmetic, storage or EOF.
The unmasked twelve-output Fibonacci layout and P0 remain pending.

### Proven single-digit non-unit induction with live guest bytes (2026-11-13)

A whole source-C program with an initial guest input, counted `for` loop,
induction-dependent `continue`, nested integer guard, and trailing fresh
read first refused `for (int i = 0; i != 6; i += 2)` at normalized
lowering. The frontend projector now accepts source- and Clang-authenticated
positive single-digit strides (1–9) for compound `i += N`/`i -= N` and
assignment `i = i + N`/`i = i - N` with exact original spelling. The
signed `i32` comparator and initializer/bound leaves remain checked.

Ordered `<`, `<=`, `>` and `>=` use source-time stepped trip counts;
`!=` additionally requires the bound to be *exactly reachable*. All
branches require the step direction to match the comparison, at most
sixteen trips, a bounded initializer, and no change to guest effect
ordering. Skipped or overshot inequalities never become a guessed finite
trace. The adapter refuses zero/two-digit strides, divergent directions,
more than sixteen trips, and forged Clang stride values or ancestry.

The original ascending and a descending complete C program now emit four
actual copies of the first binary input byte plus one fresh second input
through the normative Malbolge VM. The ordered and zero-trip forms reach
layout admission under an isolated rejecting stub. This proves finite
*compile-time* induction over source-authenticated C, not guest runtime
C arithmetic, storage, EOF, arbitrary strides or dynamic C control.
The unmasked twelve-output Fibonacci layout and P0 remain pending.

### Source-authenticated finite inequality loops (2026-11-13)

A complete source-C program with an initial `getchar` local, counted loop,
remainder-selected `continue`, a nested signed-unary guard, and trailing
fresh input first refused `for (int i = 0; i != 3; ++i)` at normalized
lowering. The static induction proof now admits source-spelled `!=` for
canonical unit steps in either direction, but only if the exact bound is
reachable within sixteen trips or initially equal (zero trips). The original
C comparator, decimal initializer/bound, and prefix/postfix/compound/assigned
unit-step spellings are checked against source bytes as well as pinned Clang
parent/span/type/operator ancestry. Opposite-direction and oversized loops,
and same-width Clang comparator, literal and step forgeries, refuse.

The original complete program emits four copies of its actual first byte
and a second fresh input in eight normative Malbolge VM steps on boundary
and seeded binary streams. A descending branch/`continue` loop emits three
fresh bytes in seven steps; zero-trip execution still emits its two trailing
bytes in five steps. Seven further increment forms reach frontend layout
admission without spending guest-search budgets. This is source-proven static
induction, not general runtime C control, arithmetic, storage, EOF or failed
output; the P0 remains pending.

### Signed unary C arithmetic in source-proven live-byte guards (2026-11-13)

A full counted C source program with local state, remainder-selected
`continue`, a nested conditional, and two actual input bytes first rejected
`((~current) ^ current) == -1` at normalized lowering. The source- and
pinned-Clang-authenticated finite proof now composes unary `+`, checked
signed `-`, and bitwise `~` with exact `i32` results across all 256 possible
successful guest bytes. Clang's constant annotation for a literal `-1` is
accepted only when it matches every independently proven value; that
annotation never predicts the guest input or authorizes a side effect.

The original C program emits four copies of its actual first input and a
fresh second byte in eight steps of the normative Malbolge VM across
binary boundaries, strata and deterministic seeded streams. Pure negative
arithmetic forms and a byte-dependent equivalent-output guard also pass
real guest execution. Signed-negation overflow, implementation-defined
negative right shifts, effectful operands, unequal arms and forged Clang
parent/operator/type/span/constant evidence refuse without an artifact.
No guest runtime integer arithmetic, unequal dynamic branching, storage,
EOF or failed output is implemented; the P0 remains pending.

### Checked arithmetic for pure live-byte C guards (2026-11-13)

A complete three-trip source-C program with local state, induction,
remainder-selected `continue`, a nested conditional, and two real guest reads
first refused `((current * 3 + 1) % 3) == 1` at normalized lowering. The
source-/pinned-Clang-authenticated 256-value `i32` proof now composes pure
binary `+`, `-`, `*`, `/`, `%`, `<<`, `>>` and general comparisons in addition
to Boolean/bitwise operators. Checked signed overflow, division by zero,
negative or out-of-range shifts, and nonrepresentable signed left shifts
reject; there is no wrapping or guessed guest input. All operands require
exact original-source spelling, Clang parent IDs, spans and integer types.

The original C program now executes in the normative guest VM with four
copies of its first actual input followed by a new input, in eight guest
steps. A guest-dependent modulus guard with independently equivalent
output-only arms also preserves genuine binary I/O. Bounded boundary,
stratified and seeded oracle streams, additional arithmetic admission
shapes, effectful/unequal branches, undefined arithmetic and forged AST
all have regression coverage. Arithmetic is proven only to decide whether
C branch effects are invariant over successful byte reads: guest-side
arithmetic, dynamic unequal-arm branching, EOF, storage and failed output
remain unsupported. The P0 contract is still pending.

### Exact non-Boolean integer predicate values (2026-11-13)

A complete counted C stream with a live binary input, local state,
remainder-selected `continue`, nested conditional, and a trailing read
first refused `((current & 2) ^ (current & 2)) == 0`. The source- and
pinned-Clang-authenticated predicate proof previously stored only a
256-bit truth set with an exact-Boolean flag. That could not distinguish
different nonzero integer mask values, so XOR/AND had to refuse.

The proof now carries 256 exact `i32` values: direct resident-byte
identities, pure literal/masked/comparison leaves, grouping, negation,
zero comparisons, logical and bitwise operators, and pure conditional
expressions retain C's integer semantics. A predicate arm may be
selected only when all 256 values agree on zero/nonzero; otherwise
both complete output-only effect traces must independently agree.
This still cannot guess runtime input, erase guest reads or writes,
or implement general dynamic guest C branching.

Two full one-trip counted C programs exercise XOR cancellation
and disjoint-mask `&` false selection. A third executes a
byte-dependent non-Boolean XOR guard with equal output effects.
All three run under the normative guest VM with binary boundary
inputs and output `current, current, next` in six instructions.
Three further total guards pass the source-authentication stage
without repeating equivalent guest layout synthesis. Forged Clang
ancestors, operators, spans and type, effectful operands, unsupported
integer expressions and unequal arms fail without publication.
EOF, failed I/O, guest-side arithmetic/storage and general runtime
branching remain unsupported. The original three-trip source has not
yet completed layout, so P0 remains pending.

### Integer bitwise OR truth over successful guest bytes (2026-11-13)

A complete source-C stream with a local guest input, counted induction,
remainder-selected `continue`, a byte-dependent `if`, and two real guest
reads initially refused `(current & 2) | (current & 4)` at normalized
lowering. C integer bitwise OR is zero exactly when both operands are zero,
regardless of their nonzero bit patterns. The bounded source-/pinned-Clang
proof now composes each pure operand's finite successful-byte truth set
under `|`, without falsely treating either integer mask as an exact 0/1
Boolean. This older truth-only implementation has been superseded by the
exact-integer value proof above, including XOR and AND. Dynamic branches
can still be erased only when proven total or both complete source-proven
output traces are identical. Three original bitmask, zero-test and
logical-OR variants each match 15 independent binary streams in the
normative VM, with five output bytes and eight steps per run. Hidden
effects, unequal arms and forged Clang ancestry still refuse without
publishing an artifact. This does
not add guest arithmetic, guest-dependent control flow, EOF, or failed I/O.


### Bitwise Boolean partitions over live bytes (2026-11-13)

A complete source-C stream with local state, a counted loop, a remainder
branch, `continue`, nested `if` and two real binary reads initially refused
`((current & 1) != 0) ^ ((current & 2) != 0)` at normalized lowering.
The bounded predicate proof now distinguishes an exact C result of `0` or
`1` from a merely truthy integer. It authenticates all operands against
original source bytes and pinned Clang ancestry, then composes `^`, `&`,
and `|` as bitwise truth sets only when both operands are proven Boolean.
A nested equality/inequality with literal zero can convert a source-proven
mask into a Boolean, without treating `current & 2` as `0` or `1`.

The original compound program reaches real guest execution and matches an
independent binary-stream oracle in eight VM steps across boundary inputs.
The proof cannot predict the guest byte or implement a runtime branch:
dependent guards are erased only when both full source-proven output traces
are equivalent. General arithmetic and guest control flow, EOF, and failed
I/O remain unsupported; P0 stays pending.

### Byte-dependent ternary statement guards (2026-11-13)

An original C program with binary `getchar`, three-trip induction, a static
remainder/`continue` branch, nested `if` and trailing output first refused
`(current & 1) ? (current >= 0) : (current <= 255)` during normalized
lowering. The source-/Clang-authenticated adapter now composes a pure
conditional expression's three truth sets over **all** successful bytes,
including both branches that C would skip for a particular runtime byte.
The selector chooses one arm's truth independently at each byte; only a
complete/empty result or equivalent nonempty output-only statement effects
can eliminate the guard without predicting the actual guest byte. Source-
checked canonical nonnegative `i32` literal arms, including zero, compose
with the same proof.

Whole C programs with true, false, nested and dependent guards execute on
the normative guest VM with independent binary-input oracles and explicit
step counts. Inactive effects, live input in a predicate, unequal effects,
forged Clang ancestry/spans/operators/literals and changed source reject
without publication. The 256-value proof excludes EOF and failed I/O and
does not implement runtime guest branching, arbitrary state or arithmetic.


### Grouping, negation, and direct-byte Boolean partitions (2026-11-13)

A full C program with live binary input, counted induction, `continue`, and
trailing I/O initially refused an input-dependent `!(current & 1)` guard
although both arms independently write the same byte. The bounded adapter
now recursively authenticates parentheses and unary logical negation in a
256-value truth set. Both source spellings and pinned Clang parentage must
match exactly; `!` complements the bitmap and parentheses preserve it.

A second red-first program refused `current || !current`. A proven pure
resident byte now contributes the truth set for all nonzero successful
bytes, while its source-checked zero test contributes the singleton zero
set. `&&` and `||` compose these without computing the runtime byte. Both
arms are authenticated, including short-circuited operands. Non-total
guards only pass if both arms have identical nonempty output-only effects.

Six source C streams execute in the normative Malbolge VM: 17 independent
binary streams for the negated dependent guard, four for grouped true/false
partitions, and nine for direct-byte tautologies and contradictions. Their
expected output is an independent function of the binary inputs, with no
extra reads and exactly six or eight VM steps. Effectful guards, unequal
arms and forged source/AST refuse without an artifact. This is a proof of
successful-byte static effects, not guest-dependent runtime branching,
EOF, failed output, general arithmetic or storage. P0 remains pending.

### Source-proven equivalent effects across dependent C arms (2026-11-13)

A complete original C program with a live input local, induction, branch,
`continue` and trailing I/O initially refused `if (current & 1)` even
though both arms independently output the identical resident guest byte.
The bounded adapter now proves a pure guard against original source and
pinned Clang, including all short-circuited operands. If its Boolean truth
set varies across `[0, 255]`, both authenticated arms must have the same
nonempty output-only effect trace, with no read, assignment or loop exit
in either arm. Different C spellings of byte-preserving expressions may
therefore eliminate the branch, without predicting a guest byte or host
simulation of the branch.

The original C program executes in the normative VM with five outputs and
eight steps for five binary boundaries, 16 seeded pairs and 16 stratified
first bytes. A two-output-per-arm C variant emits four bytes in seven steps
across both guard polarities; zero-trip behavior emits two bytes in five
steps. Unequal/effectful arms, impure guards, AST parent/operator/literal
and span mutations, changed original source and absent witness refuse
without publication. This establishes only successful-byte output trace
equivalence, not general guest-dependent C branching, storage, arithmetic,
EOF or failed output. P0 remains pending.

### Boolean-complete guest-byte partitions (2026-11-13)

A complete C program with input, three-trip induction, static `continue`,
nested `if` and trailing byte I/O first refused a pure dynamic partition:
`if (current == 0 || current != 0)`. A bounded source-/Clang-authenticated
proof now enumerates the 256 successful input bytes into four `u64` words.
It composes exact comparison and bit-mask truth sets with set intersection
for `&&` and union for `||`. Only an empty or complete final truth set can
select a whole statement arm. A dependent leaf is therefore admissible if
its logical combination is byte-total. The proof authenticates all leaves,
including inactive short-circuit operands, and does not evaluate real guest
input or introduce runtime branching. Non-total/effectful forms reject.
Two full counted programs pass 17 binary input pairs each in the
normative Malbolge VM, producing five bytes in eight steps for both
true and false partitions. Three more guards reach layout admission;
six dependent/effectful guards and five source/Clang forgeries refuse.

Successful `getchar()` bytes exclude EOF; general guest-dependent branches,
storage, arithmetic and failed I/O remain outside the supported slice.

### Pure compound successful-byte predicates select C arms

An original C program with an input local, three-trip induction loop,
remainder branch, `continue`, nested C `if` and trailing real guest I/O
first refused `if (current >= 0 && current <= 255)` at the normalized
adapter. The bounded proof now authenticates the original C bytes,
pinned Clang `i32` logical `&&`/`||` parents, operand trees and spans.
Each leaf must have one truth value across successful bytes `[0, 255]`;
the combined result is independent of the actual runtime input. Both
operands must be pure, including those skipped by C short-circuiting.

Three two-operand and two mixed-precedence complete streams execute in
the normative VM with four genuine copies of the first input followed
by the second, in eight guest steps. Boundary and seeded binary cases
match an independent byte oracle. A separate false compound `if`
without `else` skips an input effect and emits two copies of the first
byte followed by the second in six steps. Eight inconclusive/effectful
guards and six source/Clang integrity cases refuse without an artifact.
Dynamic C branching, EOF, failed writes, general storage and arithmetic
remain unsupported.

### Total successful-byte predicates select a whole C statement arm

An original full C stream combines a live `getchar()` local, a three-trip
induction loop, a static remainder branch and `continue`, a nested C `if`
and trailing binary input/output. The adapter initially refused the live
`if (current < 256)` comparison. It now proves one pure, pinned-Clang
comparison against exact original C text, selects an arm only if its truth
value agrees at zero and across all positive successful bytes `[1, 255]`,
and authenticates both complete C arms before emitting the selected effects.
It never evaluates the actual byte on the host or invents guest branching.

The normative VM reads two real bytes and emits five: four copies of the
first and one fresh second byte, in eight guest steps across four boundaries
and twelve seeded binary pairs. A reversed always-false threshold also
matches. Nine byte-dependent/side-effectful guards, changed Clang nodes,
forged source SHA and an absent original C witness refuse without an artifact.
No arbitrary guest-dependent `if`, EOF, failed output, arithmetic or memory
is implemented; this P0 remains pending.

### Total wide-integer range tests over a live input byte (2026-11-13)

A complete C program combining a live binary input, a four-trip induction
loop, selected `continue`, source-local state and nested arithmetic first
failed normalized projection on `current < 256 ? ((current ^ 0) & 255) : 0`.
The new interval proof authenticates a nonnegative signed C decimal literal
and each pinned Clang node against the original C source. Comparisons are
selected when all positive successful bytes in `[1, 255]` agree; at
zero both arms yield zero. An incompatible mask is proven false when
no low byte bits can overlap. Both arms are source-proven separately,
and the inactive one must be a literal zero.
No guest input value is fabricated or host-evaluated.

The actual Malbolge VM emits the first input byte five times and the
second once, in nine steps over four boundaries and sixteen deterministic
seeded pairs. A false-guard program and a zero-trip program also pass
two-input parity. A second whole-C zero-exception comparison,
`current >= 1 ? ((current ^ 0) & 255) : 0`, now emits its first
byte four times then the second in eight real VM steps across fifteen
binary pairs. Fourteen other threshold/mask forms reach layout;
inconclusive comparisons, forged literals, changed source, effects and
out-of-range signed literals refuse. Dynamic C branching, arithmetic,
storage, EOF and failed I/O remain P0 gaps.


### Proven successful-byte range conditions (2026-11-13)

The original complete source-C four-trip induction/continue program first
failed at normalized lowering on a pure range conditional with unequal arms:
`current <= 255 ? ((current ^ 0) & 255) : 0`. The repair authenticates the
original C bytes and every normalized Clang expression, including the guard,
selected pure byte identity, inactive zero literal and complete ternary span.
For successful `getchar()` byte values only, comparisons with the two exact
range endpoints and `& 0` have invariant truth values. Reusing the genuine
guest SSA byte is sound without host input evaluation or a fabricated branch.

The source now emits five copies of its first input byte and then the second,
from two genuine guest reads and six writes, in nine normative VM steps on
four boundary and sixteen seeded binary pairs, plus 32 stratified
successful first-byte values. Two alternative polarity and
zero-trip programs also match the VM. Negative examples, every affected
Clang line-six node parent/span, forged literal fields, SHA-updated changed
source and missing source fail closed. This proof does not support EOF,
failed output, dependent control, nonidentity arithmetic or arbitrary storage;
the general P0 obligation remains pending.

### Equivalent pure conditional arms over a live guest byte (2026-11-13)

An original source-C program with a live binary `getchar()` result, three-trip
induction, a selected `continue` branch and trailing guest input initially
refused `putchar(current > 127 ? (current + 0) : (current & 255))` at
normalized lowering. The adapter now authenticates pure comparisons (`<`,
`<=`, `>`, `>=`, `==`, `!=`) and a bitmask test (`&`) of a successful byte
against a decimal constant in `[0, 255]`, including exact pinned Clang
parentage, i32 types, source coordinates, operands and literal values.
The branches must each independently prove a pure identity of that same
resident byte; thus either runtime outcome produces the same byte, without
host evaluation or invented guest control flow. Existing zero guards also
support two identity arms.

The original complete C source emits four copies of its first binary byte
and the second in eight normative VM steps across four comparison boundaries
and sixteen seeded pairs. A parity-mask variant and a zero-trip variant
also execute in the real VM. Nine further guard/identity forms pass the
source admission gate; unequal or effectful arms, input/output guards,
unsupported operations, forged Clang nodes, changed original C and absent
source fail closed without guest artifacts. This is not general C branching,
arithmetic, storage, EOF or failed output; P0 remains pending.

### Zero-dependent C conditional byte identities (2026-11-13)

An original complete C stream with a live binary `getchar()` byte, three-trip
induction, a remainder-selected `continue` branch and a trailing guest input
first refused `current ? (current + 0) : 0` at normalized lowering. The
repaired proof authenticates the full source-C spelling and every pinned
Clang child, parent, span, type, operator and literal. Its only admitted
runtime-dependent predicates are a pure, successful resident byte, that
byte's zero equality or inequality, and its logical negation. The two
branches are restricted to source-proven pure byte identities and literal
zero in the matching order. Since either arm selects the identical runtime
byte, typed IR reuses the existing guest SSA identity without host-time
prediction, another input or invented guest control flow.

The original stream emits five correct bytes from two real inputs in eight
normative VM steps, verified on two binary boundaries and sixteen seeded
streams. Three reversed/zero-comparison guards, nested arithmetic composition,
zero-trip behavior, invalid expressions, altered source and forged normalized
Clang evidence have independent tests. General guest-dependent branches,
nonidentity arithmetic, memory, EOF and failed I/O remain outside this
bounded proof; P0 remains pending.

### Effectful identities compose genuine guest I/O (2026-11-13)

An original C program combined a source-local binary input, a three-trip
induction loop, a remainder-selected `continue`, and the effectful expression
`putchar((putchar(getchar()) + 0) ^ 0)`. Pinned Clang accepted the entire
program; normalized lowering initially refused it because the prior
identity proof could only begin from a resident C local. The repaired
recursive proof accepts an exact source/Clang-authenticated `getchar()` or
nested successful `putchar` return at the leaf, retaining all real guest
read/write effects in order. Only the ten exact identity operators compose
on top; neither guest data nor C arithmetic is evaluated on the host.

The original program now writes three copies of its first binary byte and
two of its second in eight actual normative VM steps. Two boundary and
twelve seeded binary streams match an independent oracle. Direct input
identities, two-deep nested output returns, a zero-trip loop, unsupported
nonidentities, hidden effects, forged Clang ancestry, changed SHA-adjusted
source and missing source have dedicated regressions. This does not establish
guest-dependent branching, arbitrary guest C arithmetic, storage, EOF or
failed output; the generalized P0 remains pending.


### Composed C integer identities of a live guest byte (2026-11-13)

An original C stream combining a `getchar()` local, counted induction,
remainder-selected `continue`, subsequent input and nested arithmetic first
failed normalized lowering at `putchar((current + 0) ^ 0)`. The adapter now
proves recursive compositions of the ten exact existing byte identities.
Only a source-authenticated left operand containing the same live local,
matching literal right operands, exact Clang ancestry/types/spans and an
unmodified C witness can reuse the guest SSA byte. Identity subexpressions
may be parenthesized and remain bounded in depth and total source length.
No runtime arithmetic is evaluated by the compiler.

The original C program now compiles through actual layout and emits four
copies of its first binary input plus its second in eight normative VM steps.
Two boundary and twelve seeded streams match an independent oracle. Three
additional compositions spanning masks, modulo, arithmetic and bit shifts
also compile and match the VM. Zero-trip, nonidentity, hidden-effect,
forged-AST, changed-source and missing-source cases fail safely. This is
byte-preserving expression composition, not guest-dependent control,
general arithmetic, memory, EOF handling or output failure. P0 remains open.

### Exact integer identities preserve successful runtime bytes (2026-11-13)

A full C source with a live `getchar()` local, counted induction/remainder
branch, `continue`, and binary guest I/O first rejected `putchar(current &
255)` at normalized lowering. A separate guest-dependent parity/bitwise
branch experiment also rejected; dynamic guest control is still unsupported.

The bounded source-and-Clang proof now admits `putchar(NAME OP CONSTANT)`
for ten exact integer identities on successful guest bytes in `[0, 255]`:
`& 255`, `% 256`, `| 0`, `^ 0`, `+ 0`, `- 0`, `* 1`, `/ 1`, `<< 0`, and
`>> 0`. Every literal, operator, local reference, C source byte, Clang
parent, type and span is checked. No host evaluation or fresh guest input
is substituted for the real byte, and other arithmetic fails closed.

The original complete loop now produces four copies of its first binary input
and one of its second in eight normative VM steps, matching zero/255 and
12 deterministic seeded streams. Four additional full C/VM variants for
modulo, XOR, multiplication and right shift match independent boundary
oracles. The pinned frontend and adapter admit all ten operator shapes; the
admission-only test deliberately fails the layout stage, so it does not claim
VM evidence for those other shapes. Twelve nonidentity/unsupported expressions,
changed Clang parent/span evidence, absent source and SHA-adjusted source
spoofs refuse without a guest artifact. General C arithmetic, memory,
EOF, output failure and guest-dependent branches remain P0 blockers.

### Successful output return can rebind an already-live byte (2026-11-13)

A complete C source with a live input local, a counted induction loop,
remainder-selected branch, `continue`, and nested output expressions first
failed at normalized lowering on
`putchar((current = putchar(current), current));`. Its fresh-input-free
assignment is now source-proven against the pinned Clang call, declaration,
operator, parent and span ancestry and exact original C bytes. Each successful
`putchar` writes the currently resident guest byte, while the assignment
retains that value under the authenticated C local without a new guest input.
One to sixteen nested output calls and a final comma assignment are supported.

The normative VM matches an independent binary oracle for the full three-trip
program: two actual guest reads, seven output bytes, ten steps. A two-deep
return writes nine bytes in twelve steps. A fresh `getchar()` assignment
followed by an output-return reassignment inside the comma expression yields
four reads, seven outputs, twelve steps; a zero-trip loop emits only its
post-loop I/O. Invalid C, stale local reads after an unrelated input, forged
Clang ancestry and modified SHA-matched source must refuse publication.
This is resident single-byte reuse, not general guest C storage, arithmetic,
EOF, output failure or runtime-dependent control. P0 stays pending.

### A comma output operand can assign the fresh guest byte (2026-11-13)

An original complete C program with a live local, counted induction,
remainder-selected branch, `continue`, and real binary input/output tried
`putchar((current = getchar(), putchar(current = getchar()), current));`.
Pinned Clang admitted the source but normalized lowering originally refused
the program. A bounded proof now authenticates the nested output's assignment,
Clang parent/type/span sequence, the exact original C tokens, and the comma
separator. That nested effect performs one real guest read and output while
rebinding the only resident C byte for later comma operands. The same proof
admits a final nested output operand followed by the closing parenthesis.

The original entire source now emits seven bytes from six binary reads in
fourteen normative guest steps, matching two boundary and twelve seeded
independent streams. Source and normalized-node forgery regressions remain
fail-closed. This does not implement general C expression values, EOF,
failed output, guest-dependent branching, or arbitrary storage; P0 remains
open.


### Rebinding a comma operand from a successful output return (2026-11-13)

An original complete C program with a local, counted remainder branch,
selected continue and real input/output initially failed normalized
lowering on a comma operand assigning the result of
putchar(getchar()) to the live local. The source-/Clang-authenticated
reassignment proof now retains that successful returned guest byte,
accounts for its nested outputs in order and permits a later comma
operand to read the rebound name. The final comma operand may itself
be the assignment when followed by the proven closing parenthesis.
No previously clobbered C alias is reconstructed.

Actual normative guest VM execution agrees with independent binary
oracles for two boundary and twelve seeded six-input streams: six reads,
seven writes and fourteen steps. A nested two-output-return form produces
six reads, nine writes and sixteen steps; a final-operand assignment
preserves the same seven-write oracle. A zero-trip loop executes only
two reads and two writes in five steps. Unsupported C expressions,
forged pinned Clang parents/spans and SHA-adjusted original C operators
or names refuse without guest publication. This remains successful
single-byte replay, not general runtime C storage, arithmetic, EOF,
output failure or dependent control flow.


### A comma assignment can feed subsequent guest effects (2026-11-13)

A complete original C program declares a live input local, enters a three-trip
induction-remainder branch with `continue`, and uses a comma-valued `putchar`
argument to assign a fresh input before reading the rebound name multiple
times. The pinned Clang frontend accepted the original source, but normalized
lowering refused it before guest emission. The comma-tree proof now counts only
actual comma operators, admits a source-checked five-node assignment operand,
and carries the assigned byte through later pure reads or nested successful
`putchar(current)` calls. A new read without a proven assignment invalidates
the C binding; original-C identifiers must match their Clang references.

The normative guest matches two boundary and sixteen seeded binary streams at
four real reads, five outputs and ten VM steps for repeated pure references.
An effectful middle `putchar(current)` matches two boundary and twelve seeded
streams at four reads, seven writes and twelve VM steps. A zero-trip variant
leaves the original byte live. Five regression methods cover independent guest
oracles, stale/unsupported expressions, mutated Clang ancestry, missing source,
and SHA-adjusted original-C expression and identifier spoofs. Guest-dependent
conditions, arithmetic, general C storage, EOF and output failure still block
P0 completion; this is successful-byte residence only.

### Comma-output argument can rebind and reread one C local (2026-11-13)

A complete C program with a live input local, three-trip induction loop,
remainder-selected `continue`, and final guest input tried
`putchar((current = getchar(), current));`. Pinned Clang accepted the entire
program, but the normalized JSON-to-typed stage initially refused it.
The source-authenticated proof now reuses the existing five-node C input
assignment proof inside the exact twelve-node comma/output ancestry. It
verifies C token spelling and Clang spans, then reads one actual guest byte,
rebinds only the assigned local, and outputs the freshly assigned value.

The normative guest VM matches two boundary and sixteen seeded independent
binary oracles with five reads, eight writes and fourteen steps. Selected
and skipped branches preserve the right C byte, while a zero-trip loop
skips all effects. A stale top-level local may be rebound after an unrelated
read; old aliases remain inaccessible. Unsupported expressions, forged
Clang ancestry, absent original source and SHA-adjusted source changes
refuse. This is bounded successful-byte identity, not general C memory,
EOF, I/O failure, arithmetic or runtime-dependent branch execution.

### Loop-local effects rebind an outer C local (2026-11-13)

A complete original C source declares a live local, then reassigns it in
each iteration of a two-trip induction loop with a comma expression:
`current = (putchar(getchar()), getchar());`. A remainder-selected
`continue` branch consumes that newly bound byte. The pinned Clang
frontend accepted the full program, while normalized lowering initially
refused the outer declaration because discarded reads lacked direct
reassignment targets.

The source- and Clang-authenticated finite-loop proof now follows each
ordered input/output effect. A discarded fresh input may temporarily
invalidate the outer byte, but output of that C local is admitted only
after a proven assignment restores its identity. This rule also handles
a selected inner branch; skipped branches preserve their prior byte.
The normative guest VM matches 18 binary-input oracle streams at six
reads, five writes and twelve steps. Selected/skipped rebinding and
zero-trip proofs match four reads/four writes/nine steps and two
reads/one write/four steps. Stale intervening reads, unsupported
operands, changed Clang ancestry and source spoofing refuse. This does
not implement general C storage, EOF or runtime guest-dependent control.

### Ordered C comma-valued assignment into a proven local (2026-11-13)

A complete source-C byte stream assigned a parenthesized comma expression
to an existing C local in a selected if branch before a counted loop with
a remainder-selected continue. The pinned Clang frontend accepted the
whole program, but normalized lowering initially refused the assignment.
A bounded proof now authenticates assignment/destination/comma ancestry,
every nested byte-effect call, complete same-line extents and exact
SHA-checked original C token spelling. Earlier reads and writes execute in
order in the guest; the final successful byte alone rebinds the destination.

The normative guest VM matches an independent oracle on boundary and twelve
seeded binary streams: four actual inputs, six outputs and eleven steps.
A skipped branch preserves its original local with two reads and four writes
in seven steps. A stale top-level destination with three comma operands
matches six reads, four writes and eleven steps. Unsupported arithmetic,
stale C value operands, forged AST ancestry, absent source and SHA-adjusted
spoofed C source all refuse without publication. A later bounded,
source-proven loop-local reassignment proof is documented above. EOF,
failed putchar, general C storage and guest-dependent conditions remain
P0 blockers.


### Ordered source-C comma initializers (2026-11-13)

A complete C program used `int seen = (putchar(getchar()), getchar());`
then a three-trip `for` loop with an induction remainder branch and `continue`,
followed by another real guest read/write. Pinned Clang accepted it, but the
JSON adapter initially rejected the first declaration. A new bounded source
proof admits two to sixteen comma operands with fresh `getchar()` effects,
each optionally wrapped in nested successful `putchar()` calls.

It checks pinned Clang call/binary/parenthesis ancestry, source coordinates and
the SHA-verified original C bytes. Guest instructions execute all reads and
writes in C order and bind only the final input/return to the new local.

The original program now emits five independently predicted bytes from three
actual binary inputs in nine normative VM steps over boundary and sixteen
seeded streams. A selected branch and counted loop emit seven bytes from eight
reads in sixteen steps; the skipped branch emits six bytes from six reads in
thirteen steps. Scopes cannot export local bindings, and noncanonical C,
forged normalized nodes, missing source and SHA-adjusted spoofing refuse.
General C comma operands, arbitrary storage, EOF, output failure and dynamic
C conditions remain unsupported; P0 stays pending.

### Successful output-call returns initialize source-C locals (2026-11-13)

The pinned Clang frontend accepts a complete branch/continue C loop whose
first declaration is int current = putchar(getchar()), but normalized
lowering previously refused the declaration. The new bounded source proof
checks the exact original C declaration, local binding, every nested
successful output call, its Clang parent/cast/reference/span and one real
getchar. Each putchar forwards the same guest byte, and the newly bound C
local can be reused or reassigned without inventing a host value.

This is also admitted for block-local declarations in statically selected
branches and bounded counted loops; declarations do not export bindings
outside their lexical block. The original four-trip program emits seven
copies of the first binary input and two copies of a subsequent input,
with 12 normative VM steps. EOF, output failure, guest-dependent control,
general storage and arithmetic remain unsupported.

### Output returns on both sides of a local assignment (2026-11-13)

The original complete C source with
`putchar(putchar(current = putchar(getchar())));` in selected arms of
a three-trip remainder-branch/`continue` loop initially failed at
normalized JSON lowering. The repaired proof authenticates all pinned
Clang call, cast, reference, parent and same-line spans for both
output-call chains, plus the exact SHA-checked source spelling and
existing local destination. The single guest input is written once
per actual successful `putchar` in innermost-to-outermost C order;
only the authenticated local can read the returned byte afterward.
Between two and sixteen output calls can straddle the assignment.

The actual normative Malbolge VM emits eleven oracle bytes for four
binary inputs in sixteen steps on zero/255 boundaries and sixteen
seeded streams. A top-level mix of one- and two-call chains on each
side emits nine bytes from four inputs in fourteen steps, and the
zero-trip loop skips the nested effects. Six tests cover whole-C
guest parity, source/AST refusal, stale aliases and zero trips;
sixteen altered Clang fields, ten shifted spans and a SHA-adjusted
operator spoof are rejected without publication. This is successful
byte identity, not EOF, failed `putchar`, general C storage,
arithmetic or runtime-dependent control. P0 remains pending.

### Nested successful output returns rebind one C local (2026-11-13)

A complete original C program uses a three-trip remainder-selected loop
with `current = putchar(putchar(getchar()));`, followed by a read of
`current` and `continue`. Pinned Clang accepts it, but the earlier
normalized adapter refused the output-return assignment. The source-checked
projector now proves each nested `putchar` call, function-pointer cast,
reference, parent ID and byte span against the SHA-checked original C.
The single real guest input is output innermost-first and rebound only to
the authenticated C destination. The exact grammar supports 1–16 nested
successful output calls, not general C call-result storage.

The original entire C stream reads four binary bytes and writes nine
independently predicted bytes in fourteen normative VM steps on two
boundary and twelve seeded streams. A three-deep top-level assignment
to a stale local writes five bytes from four inputs in ten steps; a
zero-trip proof skips all loop effects. Six focused regression methods
cover guest parity, six invalid C programs, sixteen forged Clang
fields, eight shifted spans, missing source evidence and a SHA-adjusted
C operator spoof. Older aliases remain stale after the fresh input.
Failed output, EOF, dynamic C control, arithmetic and arbitrary guest
memory remain P0 blockers.


### Successful output-call return assigned to a C local (2026-11-13)

A complete original C program first reads a runtime byte and writes it,
then runs a three-trip induction-remainder branch/continue loop whose
selected arms assign `current = putchar(getchar());` and output the rebound
`current`. The pinned frontend accepted the program, but the normalized
projector initially rejected the new assignment. A new eight-node proof
authenticates the enclosing C assignment, destination identity, nested
`putchar(getchar())` call, all Clang spans and the exact SHA-checked C
spelling. Its guest effects are an actual input and actual output, and
the successful output return rebinds only the proven C name. No host
substitution, old-value recovery or general C call-result computation
is involved.

The normative VM matches an independently computed seven-byte output
from four runtime reads in twelve steps under boundary and twelve seeded
binary streams. A stale top-level destination rebinds after a new input;
a zero-trip loop proves but skips the assignment. Seven focused methods
cover six unlowered expressions, eighteen forged AST/span mutations,
missing and SHA-adjusted source witnesses, and old-alias rejection.
Guest EOF, failed output, arbitrary C storage, arithmetic and
guest-dependent control remain unsupported, so P0 stays pending.

### Nested assignment-valued source-C byte output (2026-11-13)

A complete original C stream used
`putchar(putchar(current = getchar()));` inside a
remainder-selected `continue` arm of a counted loop, followed by reads of
the rebound C name. The pinned Clang frontend accepted the program but
the normalized adapter refused it before guest emission. The bounded
projector now source-authenticates every enclosing `putchar` call, its
parentage, function-pointer cast, span, and final assignment/read subtree,
including the exact SHA-checked original C expression and semicolon.
The one real guest input is written by each nested successful call in
inner-to-outer order, and only the proven destination becomes resident;
previous C aliases stay invalid after a new read.

The complete branch/loop program produces nine independent-oracle bytes
from four genuine guest reads in fourteen normative VM steps, under
boundary and seeded binary input. A top-level nested assignment and a
three-deep selected branch with a zero-trip loop each emit six bytes
from three reads in ten guest steps. Seven focused regression methods
cover these cases, five unsupported C expressions, fifteen altered
Clang nodes/spans, absent source proof, SHA-adjusted C operator spoofing,
and a stale alias. Dynamic C arithmetic, mutable storage, EOF and
guest-dependent control flow still have no general lowering; P0 remains
open.

### Assignment-valued output retains C byte identity (2026-11-13)

A complete original C program used `putchar(current = getchar())` in a
source-selected `continue` branch of a counted loop, then read `current` in
later trips and after loop exit. Pinned Clang parsed the whole C program, but
the normalized adapter initially refused the first declaration. The bounded
byte projector now authenticates all eight nested Clang expression nodes and
the exact `putchar(NAME = getchar());` token sequence from SHA-checked C
source. Each call consumes one real guest input, outputs that byte, and
rebinds only the proven C destination; older aliases cannot be resurrected.

The original selected-loop program emits six independent-oracle bytes from
four binary guest inputs in eleven normative VM steps. A second complete C
program with scoped assignments, static branch selection, a three-trip
counted loop and source-selected `continue` consumes ten guest inputs and
emits eleven independent-oracle bytes in 22 steps. The separate selected
branch, zero-trip loop and boundary/seeded streams also reach VM parity.
Unlowered arithmetic, stale aliases, ten AST mutations, forged source
operators and missing source witnesses are refused without publication.
Ordinary short scoped output calls remain admissible when the optional
eight-node assignment proof does not fit the remaining Clang nodes.
Borrowed-loop inputs are permitted only when every fresh read explicitly
rebinds that same authenticated outer C local. This is accumulator-resident
source-C identity, not dynamic C storage or general assignment expressions.

### Source-proven outer C byte across counted output loops (2026-11-13)

A complete C stream reads a runtime byte, copies it into a block-local
alias in a selected branch, and emits it through a four-trip induction
loop with alternating selected `continue` paths. Pinned Clang accepted
the full program, but the normalized adapter refused the loop's outer
C binding. The adapter now reuses the resident guest byte through
input-free, fully authenticated finite loops and nested counted loops;
it also accepts a previously proven equivalent top-level C alias.
The original C output loop runs in the normative VM under boundary and
seeded binary input: two guest reads, eight writes, eleven steps.
Zero-trip, nested and equivalent-alias variants emit four, six and five
bytes respectively with no synthesized reads.

The fallback requires the SHA-checked original source, validates the
spelling of every loop-local C and external identifier reference, and
prohibits any selected guest input while borrowing an outer binding.
An input-producing loop uses the existing independent replay path and
invalidates old aliases. Missing source, a same-length forged C source
with a different live local, stale reads and unsupported arithmetic
refuse without an output artifact. This is source-time bounded replay,
not general guest control, arithmetic, storage or EOF. P0 stays open.


### Multiple original-C scoped reads in one branch or loop (2026-11-13)

A complete C stream placed three distinct `getchar()`-initialized locals in
one statically selected `if` arm, interleaved a source-proven alias and outputs,
then ran a three-trip induction-selected `continue` loop. Pinned Clang accepted
it, but the normalized adapter previously refused the second scoped read.
The branch proof now accepts successive independently source-authenticated
scoped declarations, overwriting only the resident guest accumulator value;
stale C locals are not restored. Every scoped read, including the first local
in a counted loop without an outer binding, must match the SHA-checked
original-C spelling, not merely Clang-shaped JSON.

The full selected C stream consumes nine binary guest reads and emits nine
independently predicted bytes in nineteen normative VM steps. Its skipped-arm
variant keeps the original local live and emits six bytes from five reads in
twelve steps. A separate whole C loop with two new scoped reads per trip
consumes seven bytes, emits four independently predicted bytes, and halts in
twelve steps. Each program matches both boundary and seeded binary oracles;
six malformed or stale C variants, six forged Clang nodes, absent source proof
and forged C initializers refuse. This is still finite source-time control,
not guest-dependent branching, general C storage, arithmetic or EOF.

### Lexically scoped C byte aliases and fresh shadows (2026-11-13)

An original complete C program copied a live `getchar()` value into a
block-local `int scoped = current;` inside a source-selected top-level `if`,
then emitted through both names and ran a three-trip loop with fresh input,
induction-selected output and `continue`. The pinned Clang frontend accepted
it, but the source JSON adapter rejected the entire program because top-level
branches were forbidden from introducing scoped aliases. The bounded branch
proof now admits a source-authenticated identity declaration in either arm
without exporting its C name or synthesizing another guest read. The normative
VM consumes five bytes, emits seven independent oracle bytes and halts after
thirteen steps; the skipped-branch variant emits six in twelve steps.

A second whole C program declared a new `int current = getchar();` inside a
selected `if`, shadowing an outer live local. The branch proof now permits one
fresh, source-witnessed nested input per lexical block, invalidating the
older guest byte rather than assuming C memory can recover it. The normative
VM consumes seven binary bytes and emits six source-predicted bytes in
fourteen steps. The unselected shadow preserves the outer value and emits
five bytes in eleven steps. Boundary and seeded binary streams, unsupported
source expressions, forged Clang ancestry, a forged C constant masquerading
as an input initializer, absent source proof and stale outer-byte reads
all refuse or match as appropriate. This is finite source-C branch replay,
not dynamic guest C scope, mutable storage, arbitrary arithmetic or EOF.
The P0 remains open.

### Selected C branch retains authenticated guest input (2026-11-13)

An original C program initializes and aliases a live guest byte, assigns a
fresh `getchar()` to that same alias inside a compile-time-selected `if`,
then reads the reassigned name **after** the branch and runs a three-trip
counted loop with conditional output, `continue` and final input. The
pinned Clang frontend accepted it; the normalized adapter previously
discarded the updated local identity after the branch. The exact source
and five Clang assignment nodes already proved the new read. A selected
branch now exports that checked C binding to its outer scope; nonassignment
input effects and scoped declarations still erase or cannot export aliases.

The actual Malbolge VM reads seven binary bytes and emits six
independently predicted bytes in fourteen steps on a boundary stream
and a seeded stream. An unselected assignment keeps the original live
name; unsupported C edits, stale aliases, six forged AST mutations and
missing source evidence refuse. Guest-dependent conditions, EOF,
general mutable storage and runtime arithmetic remain unsupported.
The P0 remains open.

### Fresh guest input can overwrite a stale C local (2026-11-13)

An original complete C stream alternated `saved = getchar();` and
`current = getchar();` after both names had been proven, then copied the
current input back into an older local before running a three-trip
induction-selected branch/`continue` loop. The pinned Clang frontend
accepted the C source; the JSON adapter rejected its first attempt to
reassign a stale local. Fresh `getchar()` never needs the prior C value:
the adapter now authenticates the destination against any previously
validated top-level local declaration and proves the exact five-node
Clang assignment plus SHA-checked source bytes. It emits a genuine guest
read, makes that destination the sole live SSA byte, and invalidates all
other guest aliases. No retained stale byte is synthesized.

The complete program consumes eight independent binary bytes and emits
seven source-predicted bytes in sixteen normative VM steps on both boundary
and reproducible seeded input. Negative source variants, forged assignment
nodes, absent source witness, and stale value reads still refuse without
an artifact. This is byte-input rebinding, not general guest memory, EOF
handling, guest arithmetic or dynamic C control; the P0 remains open.

### Source-proven C byte aliases and identity rebinding (2026-11-13)

A whole C stream first failed after `int saved = current;` when it emitted
`putchar(current)`: the normalized projector remembered only the newest
alias to the resident guest byte. It now retains all independently
source-authenticated aliases of the *same* current guest SSA input, so
both original and copied names may be read. A new runtime `getchar()`
invalidates previous equivalents. The fixed source also runs three
induction-selected iterations with a per-trip byte alias, conditional
output, `continue` and a final guest read. The real Malbolge VM reads
five independent binary inputs, emits six independently expected bytes,
and halts in twelve steps across two binary input oracles.

A second original C program copies a newly read byte back into a stale
top-level local with `saved = getchar(); current = saved;`, then emits
through either live name and continues into the same bounded loop. A
four-node Clang assignment proof binds the destination to a previously
validated C declaration and the source to the **currently resident**
byte; exact `DEST = LIVE;` bytes come from the SHA-checked original C.
The copy produces no extra guest operation. The six-read guest emits six
independently predicted bytes and halts in thirteen steps on two binary
streams. Rebound aliases may be copied again while they stay live.

Unproven arithmetic or casting, stale reads or assignments, noncanonical
source spelling, forged normalized type/parent/reference/span fields and
missing source witness refuse without publishing output. The compile-time
loop proof only reuses old aliases for checked output calls, not for
unproved stores. There is still no general guest C storage, dynamic
control, arithmetic or EOF; this does not retire the wider P0.

### Source-witnessed live C local reassignment (2026-11-13)

A complete source-C stream reads `current`, reassigns it with
`current = getchar();`, then runs three induction-selected loop trips
with their own `byte = getchar();` reassignments, `continue` and a final
guest read. Pinned Clang accepted the program, but the normalized compiler
originally rejected its assignment. The repair authenticates the five
Clang assignment/destination/input nodes, their IDs, parentage, types,
declaration identity and source geometry, plus exact `NAME = getchar();`
spelling from the SHA-256-checked original source. Each assignment emits a
fresh guest input and replaces the current SSA byte for later `putchar`
calls; a dead loop body is authenticated without emitting input.

The 1,167-byte guest capsule consumes nine runtime bytes, emits the
independently expected five bytes and halts in fifteen normative VM steps.
Two binary input streams, six rejected source changes and eight forged
Clang-node variants plus a missing source witness verify the narrow slice.
Only an already live accumulator-local `int` can be reassigned; arbitrary
stores, stale locals, arithmetic, guest-dependent control and EOF remain
unsupported. The P0 remains open.

### Source-witnessed live C local copies (2026-11-13)

A complete C program reads `getchar()` into `current`, copies the live
byte through `int snapshot = current;`, emits it, then runs a four-trip
induction-branch loop with fresh input locals, selected `continue` and a
final guest read. The pinned frontend accepted the source but normalized
lowering initially refused the new declaration. The repair authenticates
all four Clang alias nodes, declaration/reference identity, source spans,
and exact `int NAME = LIVE;` spelling from the driver-checked original C
file. A copy rebinds the current guest SSA byte without adding a second
input instruction or substituting a host-provided byte. Chained top-level
copies, per-iteration loop copies, scoped selected-branch copies and
zero-trip dead-body proof use the same bound source witness.

The full guest executes six independent byte reads and six writes in
thirteen normative VM steps. Eight binary VM comparisons, including zero,
128 and 255, match independent byte-stream oracles. Twelve unsupported
sources, eight forged normalized nodes and a missing-source witness refuse
publication. This is accumulator-resident identity copying, not general
mutable C storage, arbitrary expressions, guest-dependent control or EOF.
The P0 remains open.

### Source-witnessed unsigned-byte casts in finite C streams (2026-11-13)

A complete four-trip source-C program reads fresh `getchar()` locals,
branches on authenticated induction remainders, emits
`putchar((unsigned char)current)`, selects `continue` and writes a final
runtime input. The pinned frontend accepted the program, but normalized
loop admission initially rejected the unsigned narrowing. The compiler now
checks both `integral-cast` nodes, all declaration-reference ancestry,
source coordinates and the exact `(unsigned char)` bytes at the cast span.
The driver supplies the original C file to the JSON adapter after SHA-256
identity checks; JSON-only callers cannot assert this cast without a source
witness. Signed narrowing, hidden arithmetic and forged equal-width signed
cast metadata fail closed, without a guest artifact.

Under successful byte input, narrowing to unsigned char and promoting back
to int preserve each 0–255 value; the emitted Malbolge still executes all
five independent input and output effects. Two binary VM oracle streams
(including zero, 128 and 255) match in eleven steps. This is not dynamic C
arithmetic, arbitrary casts, EOF behavior or guest-dependent control.

### Source-authenticated early C return in live guest streams (2026-11-12)

A complete C program reads fresh runtime bytes inside a four-trip `for`,
uses an induction-dependent `if` to emit nested output then `return;`,
and leaves a final input/output statement after the loop. Pinned Clang
accepted the program, but the normalized adapter initially refused its
containing `for`. The repair authenticates the exact six-byte Clang
`return-statement` span, ID, parent and empty metadata. Its selected
control exit propagates across any bounded nested loops to terminate the
function rather than only the innermost iteration.

The original guest reads three independent binary bytes, writes four
oracle bytes and halts in eight normative VM steps. The unselected-return
variant preserves four iterations plus its trailing read; a shadowed
nested-loop variant returns through both loops. Unreachable suffix
statements are still source-authenticated without emitting their effects;
unsupported dead arithmetic, guest-dependent predicates and forged
return nodes refuse publication. Five regression methods exercise
live binary streams, top-level return shapes, six invalid source
variants and nine forged fields.

This is source-time selection over proven finite C state. Dynamic guest
control, general arithmetic and storage, and EOF remain unimplemented.
The P0 remains open.


### Pure C conditional operator in finite guest byte loops (2026-11-12)

A complete C stream uses `for (int i = 12; i >= 8; i--)`, fresh guest
`getchar()` locals, `if (i % 2 == 0 ? i == 12 : i == 11)`, nested output,
selected `continue`, later `break`, and a final runtime read. The pinned
frontend accepted the source but the normalized adapter refused the
containing `for` statement. The finite source predicate evaluator now
authenticates the pinned Clang three-child `conditional-expression`: each
pure condition and both arms must separately prove their exact counter
binding, parent IDs, types, positions, and canonical ` ? ` / ` : ` gaps.
Only the protected induction value is evaluated at compile time; selected
`getchar`/`putchar` remain real guest effects. Nesting is bounded by the
existing expression depth/node limits. This is not a guest-side C ternary.

The original source's six live guest reads produce seven binary-oracle
bytes in fourteen normative VM steps. The regression verifies grouped,
logical and nested ternaries, zero-trip body proof and shadowed counters;
unsupported byte-dependent arms and forged Clang nodes fail closed.
Division predicates remain deliberately unsupported: normalized JSON has
no independent token witness to disambiguate a forged equal-width `/`
from the existing `%` proof. Dynamic guest C control, mutable storage,
EOF and arbitrary byte arithmetic remain P0 gaps.

### Source-proven remainder predicates in finite C loops (2026-11-12)

A complete descending `for (int i = 12; i >= 8; i -= 1)` C program reads
fresh `getchar` bytes, selects a nested output and `continue` using
`i % 2 == 0`, takes a later `break` on `i % 3 == 0`, and performs one
trailing guest read. Pinned Clang accepted the program; the normalized
adapter initially rejected its `for` statement. The corrected source-time
predicate proof authenticates the entire `i % N` subtree: the protected
induction declaration, `i32` lvalue cast, canonical nonzero decimal
literal, operation, parent IDs, types, and source coordinates.

A remainder may select a Boolean arm directly, under `!` or parentheses,
or when compared with a canonical decimal integer using an existing
comparison operator. These expressions can be combined with the already
bounded logical predicate proof. Each admitted source-time branch still
emits real guest input and output, and all unselected Clang descendants
must authenticate. The original source emits a 1,159-byte capsule; its
normative VM consumes six runtime bytes and outputs the independent
`00 00 ff 80 01 01 09` oracle in fourteen steps. Nested shadowed
induction retains the correct lexical declaration, and false-entry loops
validate the unreachable remainder body without guest effects.
Six complete predicate shapes match twelve binary VM oracles, and nested
shadowing plus zero-trip execution match four additional VM oracles.
Eleven unsupported source changes and eleven forged Clang node mutations
refuse guest artifact publication.

This is not guest-side modulo execution or runtime C control. Divisor zero,
noncanonical/signed source literals, guest-dependent operands and
unrecognized arithmetic fail without an artifact. The P0 remains open.


### Two-digit finite induction starts (2026-11-12)

The exact pinned Clang `for (int i = N; ...)` proof now derives the
initializer's source width from a canonical one- or two-digit decimal literal.
All declaration, condition and bound spans advance together; each node remains
independently checked before guest instructions are emitted. The admissible
source-time starts are 0–99 ascending and 1–99 descending, with at most
16 finite trips in either direction, including zero-trip loops.

This capability preserves actual guest input and output, nested counter
shadowing, selected `continue` and `break`, and source-proven direction-matched
unit steps. A complete descending program starting at 12 first failed at
normalized `for` admission, then produced a 1,135-byte capsule whose normative
VM emitted the independent `00 ff 80 80 07` oracle in 11 steps.
Five two-digit loop shapes match ten independent binary guest oracles, and
nested shadowed induction matches two more. Six unsupported C sources and
seven forged Clang node changes refuse publication. Three-digit starts,
signed or noncanonical initializers, non-unit strides, guest-dependent
predicates, general mutable storage and EOF remain outside this slice.


### Nonzero ascending finite C induction (2026-11-12)

The source-authenticated finite `for` proof now accepts ascending starts
from 0 through 9, rather than only zero or one. Descending starts remain
1 through 9. The initial signed comparison determines zero trips and the
exact induction value for every selected trip; only 0–16 iterations may
execute. Pinned Clang integer literals, one-character source geometry and
counter ancestry remain mandatory, so two-digit starts, non-unit steps,
and dynamic input-dependent conditions still refuse guest publication.

A whole ascending stream starting at 2 combines a `getchar()` local,
branch-selected nested output, `continue`, `break` and a trailing runtime
read. Four start/condition/step shapes match eight binary VM oracles;
a shadowed mixed-direction nested stream matches two more. Five source
refusals and five forged initial-node variants reject without artifacts.
The guest executes all selected I/O; C storage, dynamic arithmetic,
runtime branch conditions and EOF remain unsupported.

### Assignment-form unit steps with live guest streams (2026-11-12)

A complete four-trip source-C loop with `int current = getchar();`,
branch-selected nested `putchar` output, `continue`, a later `break`,
and a final live input initially failed at `for-statement` admission
when its step was `i = i + 1`. The adapter now authenticates the entire
pinned Clang assignment subtree, including the protected induction
reference, `i32` read cast, direction-matched `+` / `-`, the exact literal
one, IDs, parentage and source coordinates. Both `i = i + 1` and
`i = i - 1` support source-time forward/reverse finite loops; actual
guest inputs stay runtime values.

Five original program variants (including inclusive bounds and zero trips)
match two independent binary guest VM oracles each. Eight invalid source
steps and nine independently forged AST changes refuse output publication.
This is finite source-time induction proof, not guest-side C arithmetic,
mutable state, dynamic loop conditions or EOF. The P0 remains pending.

### Proven zero-trip C loops with authenticated dead bodies (2026-11-12)

A complete source-C byte stream begins with a false-entry counted loop
containing a fresh `getchar()` local, nested output, a branch and
`continue`; an executed three-trip loop then performs live input,
branch-selected nested output, `continue`, `break` and final I/O.
Pinned Clang accepted the source, but normalized admission refused its
first `for-statement`. Both strict and inclusive increasing conditions
and strict decreasing conditions can now prove zero trips by their actual
signed initial comparison, without inventing a guest read or output.

The body and every nested Clang node are independently authenticated once
even though the execution trace contains no effects from that loop. This
is not a permissive dead-code omission: unrecognized source statements
and forged normalized ancestry still fail before publication. Finite
source-time iteration now admits 0–16 trips; selected zero-trip bodies
cannot substitute host effects for guest execution. Runtime-dependent
C loops, arbitrary guest arithmetic, general storage and EOF behavior
remain outside this proof; P0 remains pending.

### Finite descending C induction with live byte streams (2026-11-12)

A complete descending `for (int i = 4; i >= 1; i--)` program captures
fresh `getchar()` locals, selects nested output and `continue` at `i == 3`
or `i == 2`, breaks at `i == 1`, and emits one final live read. The pinned
frontend accepted its source, but the normalized compiler first refused the
`for-statement`. The source proof now admits `>` and `>=` only with canonical
`--i`, `i--` or `i -= 1`, authenticates the bounded induction ancestry,
and uses the actual decreasing value on every statically proven trip. The
one-digit initial value is limited to 1–9 and loops to 1–16 nonempty trips.
Runtime guest input remains independent of source-time control.

The original program emits seven independently computed output bytes from
six real binary guest reads in fourteen normative VM steps. Seven loop
shapes match fourteen binary guest oracles; a mixed forward/reverse nested
loop matches two seven-byte input/output oracles in fifteen steps.
Thirteen invalid C sources and ten individually forged Clang mutations
refuse target publication. Mutable C state, runtime guest-dependent
control, guest arithmetic and EOF remain unsupported; P0 stays open.

### One-based and inclusive finite C byte loops (2026-11-12)

A complete C byte stream with `for (int i = 1; i <= 4; i++)`, fresh
`getchar()` locals, `i == 2 || i == 3` selecting nested output and
`continue`, an `i == 4` break, and final live input originally refused at
normalized `for-statement` admission. Its source proof now checks a canonical
zero- or one-based initial `int i`, either strict `<` or inclusive `<=`,
the comparison's exact column and byte geometry, a unit-increasing step,
and the correct C induction value on every source-time trip. Only 1–16
nonempty trips are admitted; guest input bytes remain runtime values.

The original emits seven independently expected binary bytes from six
actual guest reads in fourteen normative VM steps. Six loop shapes,
including zero-based `<= 0` and one-based `<= 16`, match twelve binary
VM oracles. Nine unsupported C sources and ten forged normalized changes
fail without artifact publication. Equal-width `!=` is deliberately refused:
without a source-token witness a forged `!=` cannot be distinguished from
`<=` using normalized Clang spans alone. Runtime guest-dependent C control,
arithmetic, EOF, and general mutable guest storage remain outside the
bounded proof; P0 stays pending.

### Canonical increment spellings in bounded C byte streams (2026-11-12)

A full C stream used fresh `getchar()` locals, a source-proven `i &&
!(i == 3)` predicate, nested output, selected `continue`, a later
`break`, and a trailing guest read. Pinned Clang accepted `i++` and
`i += 1` as the counted-loop step, but the JSON adapter initially
refused both complete programs. The source proof now admits those two
canonical increment spellings alongside `++i`. The first two authenticate
exact unary operand spans; the compound step additionally proves the
single direct literal `i32` operand is exactly decimal `1`, with matching
Clang parent, IDs, metadata, and source coordinates. Induction values stay
bounded (1–16 trips) and protected from unverified mutation.

For the four-trip program, the real guest reads six independent binary
bytes, emits seven independent oracle bytes, and halts in fourteen
normative VM steps. Four postfix loop bounds and two compound bounds
have two seeded input comparisons each; a shadowed two-by-three loop
using compound outer and postfix inner steps also matches two nine-byte
binary VM oracles in nineteen steps. Ten postfix and ten compound
forged-node mutations reject, as do five unsupported compound source
steps. No runtime C branch, guest arithmetic, general C storage or EOF
behavior is claimed. The P0 remains pending.

### Source-proven scalar induction truth (2026-11-12)

A complete four-trip C stream selected `if (i && !(i == 3))`, emitted
nested outputs and `continue` on two trips, selected a later `break`, and
read a final guest input. Pinned Clang accepted the source, but the typed
adapter initially refused its `for-statement`. A red-first regression led
to exact proof for `i` as a Boolean scalar: only the current, protected
induction declaration's `i32` lvalue-to-rvalue cast may select a branch.
Both Clang nodes, their binding, metadata, parentage and source coordinates
must match; runtime input locals do not qualify.

The complete source produces seven oracle bytes from six runtime binary
reads and halts in fourteen normative VM steps. Direct `i`, `!i`, and
`i && i < 3` also pass on two binary streams each, for four shapes and
eight guest VM comparisons total. Eight unsupported source mutations and
eight forged Clang nodes refuse without target publication.

This only strengthens finite source-time loop selection. Runtime C control,
general C storage, guest arithmetic and EOF remain unsupported here; the
P0 is not retired.

### Grouped and negated induction predicates (2026-11-12)

A complete C program with a four-trip loop, fresh input locals, a nested
`!(i == 1 || (i >= 3 && i < 4))` branch, selected `continue`, later
`break`, and a final live guest read originally refused its normalized
`for-statement`. A red-first regression reproduced the refusal. The bounded
induction predicate proof now validates `!` and parenthesized children of
source-proven comparisons and logical trees, with exact Clang IDs, parents,
types, metadata, extents, and lexical token positions. Each prefix operand
is independently authenticated before the induction value selects effects.

The original program emits seven independently expected binary bytes after
six real guest reads and halts in fourteen normative VM steps on two input
streams. Four further Boolean shapes, including double negation and grouped
nested comparisons, pass eight seeded binary VM cases. Eight unsupported
source mutations and twelve forged normalized nodes reject publication.

This remains source-time proof over a finite induction counter. No runtime
C control over guest bytes, general storage, arithmetic or EOF is claimed.
The P0 remains open.


### Pure compound predicates over C induction values (2026-11-12)

A complete four-trip C function with a live `getchar()` local originally
failed normalized `for-statement` admission when `if (i >= 1 && i < 3)`
selected two nested outputs and `continue`, followed by a separate
`if (i == 3)` break and a trailing independent guest read. The predicate
proof now recursively checks bounded same-line `&&` / `||` trees whose leaves
are either canonical comparisons against the exact induction declaration or
already-proven pure `i32` constants. Each Clang parent, node ID, type,
reference, child span and token gap is checked; both operands are proven
regardless of the selected short-circuit result. No guest input can be used
to decide C control at compilation time.

The original 1,159-byte capsule consumes six binary guest inputs, emits seven
independent oracle bytes `00 ff 80 80 01 01 09`, and halts after fourteen
normative VM steps. The regression covers two input streams for each of
five conjunction, disjunction, nested-precedence, pure-operand and short
loop shapes, alongside seven source refusals and ten forged-tree refusals.
This is source-time branch replay over finite induction, not dynamic guest
C conditions, general C storage, EOF semantics or guest-side loop execution.
The wider P0 remains pending.

### Iteration-dependent branches in bounded source-C for loops (2026-11-12)

A complete four-trip C program captures fresh input into `current`, selects
`if (i == 1)` to emit twice and `continue`, selects `if (i == 3)` to `break`,
and otherwise outputs the captured byte followed by another runtime read.
An independent final read still executes after the early break. Pinned Clang
accepted the whole source, but the adapter initially refused its outer
`for-statement`. The bounded source proof now validates the exact `i` binding,
checked decimal comparison operand, Clang parentage, reference and extents,
then reevaluates each canonical loop body against its own compile-time
induction value. It preserves lexical body authentication even after a
selected exit and emits the resulting ordered *guest* input/output trace.

The original source compiles to a 1,167-byte capsule, consumes seven
independent binary inputs and emits `00 ff 80 80 01 2a 7f` in 15 normative
Malbolge VM steps. Bounds 1/2/4/5 and shadowed two-level induction loops
have binary VM parity regressions. Six relational operators have a seeded
independent-oracle test, with explicit source/forged-AST rejection coverage.
This is source-time induction selection, not runtime C predicate evaluation,
mutable guest C locals, arbitrary arithmetic or EOF support. P0 remains open.

### Source-proven continue in finite C byte loops (2026-11-12)

A complete three-iteration C loop captures one fresh `getchar()` byte on
any pass, writes it twice, selects a constant `continue` branch, skips a
separately authenticated `else` read and the remaining body read, and
then executes a final read outside the loop. Pinned Clang accepted the
source, but normalized admission refused the outer `for-statement`.

The adapter now authenticates `continue` as an exact eight-byte Clang
statement with the right loop ancestry and no additional metadata.
Every statement after the exit is still independently source-proven;
only the executed prefix is emitted. Unlike `break`, `continue` repeats
the fixed induction and performs a new guest read on each later trip.
A typed loop-exit marker keeps the two source-control meanings distinct.

The original program now compiles to a 1,143-byte capsule. For binary
stdin `00 ff 80 01`, the normative Malbolge VM emits precisely
`00 00 ff ff 80 80 01` and halts after 12 steps. The regression
includes counts 1/3/4, a nested two-by-two loop where `continue` exits
only the inner body, an inactive exit branch, six unsupported sources
and six forged-Clang mutations, each checked for non-publication.
C dynamic conditions, runtime-dependent loops, EOF and general guest
storage remain unsupported. The P0 remains pending.

### Source-verified early break in finite C loops (2026-11-12)

A complete source-C program has a counted `for`, a new `getchar()` local,
nested `putchar` returns, an `if (1) { break; } else` with guest input,
unreachable trailing loop I/O, and a final input/output after the loop.
Pinned Clang admitted the C source but the normalized adapter refused the
outer `for-statement`. The adapter now authenticates the exact five-byte
`break` Clang node (parent, ID, location, metadata) within a bounded loop.
It proves *all* lexical body effects, including inactive branches and
statements after the break, before truncating the executed trace. A selected
break exits the immediately enclosing finite loop after the current pass;
no skipped input is pre-consumed or synthesized by the host.

The original complete C program compiles to a real 1,095-byte capsule. The
normative VM reads two binary bytes, emits the first byte twice followed by
the second byte, and halts in six steps. Dynamic conditions, `continue`,
EOF-dependent behavior and generalized guest storage remain unsupported.
This is bounded source-C loop replay, not runtime guest control. P0 remains
open.

### Source-C counted loops selected by enclosing constant branches (2026-11-12)

A complete source-C program selects a nested two-by-two `for` matrix from
an enclosing `if (1)`, declares a fresh `getchar()` local for each inner
iteration, emits its successful-byte return twice, and reads another guest
byte at each outer boundary and at the end. The inactive `else` contains a
separately authenticated counted loop. The pinned Clang JSON originally
reached normalized source proof but failed at the outer `if-statement`:
its selected typed-IR replay attempted to resolve nested loop-local bytes
through only the enclosing-scope local cache. The corrected replay carries
a latest guest SSA identity inside the selected effect trace and updates
it at every runtime input, without reusing a previous iteration's byte.

The real guest VM consumes seven independent binary bytes, emits eleven
oracle bytes and halts in nineteen steps. The complete suite verifies six
binary VM oracles over one-by-one, two-by-two and skipped-branch loop
shapes. A second source program selects an `else` loop after an outer-local
read: two binary oracles verify four inputs, five outputs and ten steps.
Four source mutations, four forged Clang ancestry changes and a stale
outer-local use fail closed before guest publication. No dynamic C branch,
runtime-dependent induction, general guest storage or EOF is supported.
P0 remains open.

### Nested counted C loops with independent guest input (2026-11-12)

A complete two-level source-C matrix stream combines nested `for` induction,
per-inner-iteration `int current = getchar();`, selected and skipped constant
`if/else` branches, nested successful `putchar` returns and a distinct read
at the end of each outer iteration. Its pinned Clang JSON was initially
rejected at the outer `for-statement` rather than producing a guest artifact.
The extended source proof authenticates both inductions independently against
Clang parent IDs, variable identities, exact source spans and canonical loop
geometry. Each inner counted body is expanded in C execution order before
its containing counted loop; guest `ByteInput` and `ByteOutput` remain real
runtime effects with independent SSA identities for every read.

The original two-by-three program now compiles into a 1,231-byte binary
Malbolge capsule. The normative VM reads eight binary input bytes and emits
fourteen oracle bytes in twenty-three steps, including `00`, `ff` and `80`.
Three loop shapes (1x1, 3x2 and 2x3) match six independently constructed
binary guest-output and exact step oracles. Seven unsupported source shapes
and seven forged Clang node mutations refuse target publication.
Nesting is limited to two lexical counted loops, positive decimal bounds
1–16, and at most sixteen expanded effects inside each compound statement.
The 128-read/256-write total trace caps remain in force. Runtime-dependent
loop conditions, byte arithmetic, EOF and general C storage are not implemented.
P0 remains open.

### Lexically scoped input locals in counted C branches (2026-11-12)

One complete counted C loop now places `int chosen = getchar();` inside
its selected `if (1)` block, uses its successful-byte return through two
nested output calls, then reads and outputs another guest byte. A second
whole loop declares distinct locals in both arms of `if (0) ... else ...`:
the selected `else` emits its own input twice, while inactive-arm input
and outputs have no guest effects. Both compile to actual Malbolge and
match two binary VM oracles each: five reads, seven outputs, thirteen
steps. Source-verified declaration ancestry, exact compound coordinates
and literal-branch selection are required at every depth. Forged local
parent/reference changes and a stale read after a selected input reject.

The allowance propagates only inside the already authenticated counted
loop body, never through arbitrary top-level control or dynamic conditions.
Guest C block storage, input-dependent control and EOF remain unsupported.

### Counted loops with fresh local byte aliases (2026-11-12)

A whole C `for (int i = 0; i < 3; ++i)` program with a source-local
`int current = getchar();`, repeated and nested `putchar(current)` returns
previously refused normalized Clang admission despite its bounded induction.
The loop-body proof now authenticates the five-node declaration as a child of
the loop compound, including original variable identity and byte/line/column
spans. Each unrolled iteration allocates a new guest input SSA value and
repeats the real input instruction; source-local returns only reuse that byte
until a later read invalidates it. Successive distinct locals in a loop body
are permitted only in latest-live order. Source-constant nested `if/else`
arms can select outputs of that same live byte.

Counts 1, 3 and 4 pass six independent binary VM-oracle executions (three
outputs per loop input plus one trailing input/output, `4 * count + 3`
steps). A second complete two-iteration C program with two fresh locals per
iteration, selected nested output returns and skipped reads matches two
binary oracles: five real inputs, nine outputs and fifteen executed steps.
Negative source and forged-Clang ancestry tests reject stale local uses,
mutations and unsupported induction/body effects without guest publication.
This is not runtime C loop control, general storage, dynamic predicates,
arithmetic over guest bytes or EOF behavior. P0 remains open.

### Finite source-C counted loop with actual guest I/O (2026-11-12)

A full C program combining a counted `for (int i = 0; i < 3; ++i)` loop,
increment arithmetic, a literal `if/else` branch, discarded reads and
nested successful `putchar` returns initially failed normalized Clang JSON
admission at its `for-statement`. The adapter now authenticates the complete
pinned-Clang induction subtree, its automatic local identity, exact prefix
increment, positive decimal bound through 16 and all child byte-effect
statements before unrolling the **fixed** loop body to typed guest I/O.
Inputs are never supplied by the host: each iteration executes the actual
normative VM input and output instructions.

The original whole C program consumes ten binary input bytes and emits ten
independently expected bytes in 21 guest steps. Counts one and four agree
with independent oracles, as does a second program with a nested constant
branch followed by another loop-body output (seven bytes in fifteen steps).
Fifteen rejected C shapes and ten forged Clang mutations refuse publication.
Source geometry for multiline nested `if` statements now accounts for
nested indentation and brace-ending statements. General guest loops,
input-dependent branches, mutable locals, EOF and dynamic arithmetic still
refuse; P0 remains pending.

### Source-authenticated pure logical C byte-stream conditions (2026-11-12)

The pinned C frontend accepts a complete source program with a live input
local, `if (!(1 == 2) && (3 > 1))`, selected nested byte outputs, an inactive
input arm, and a trailing read. The JSON adapter initially refused this
source even though its condition is fully pure and constant. Its bounded
recursive proof now admits canonical parentheses, logical negation,
`&&` / `||`, decimal literals and existing relational/equality operators.
The proof checks each normalized Clang ancestor, source coordinate, full
parenthesized extent, and folded `i32` result. Both logical operands are
proved even if one short-circuits. The limit is eight lexical expression
levels or 31 predicate nodes; neither dynamic calls nor hidden effects can
be skipped as constant.

The real Malbolge VM matches `00 ff ff 80` in eight steps for the original
condition and a distinct parenthesized true condition. A false logical
condition reads the branch's two input bytes and emits `80 01` in seven
steps. Focused invalid-source and forged-metadata checks refuse without a
guest artifact. Full matrix runtime validation is resource-limited; this
work does not implement runtime guest C predicates, arithmetic, EOF or
mutable C storage. The P0 remains open.

### Source-proven decimal C comparisons around guest I/O (2026-11-12)

A complete C stream captures a live `getchar` byte, selects a multiline
`if (2 == 2)` branch with local reuse and nested successful `putchar`
returns, authenticates an inactive arm, and reads another guest byte.
The pinned C frontend accepted the source, but the JSON adapter initially
refused its first declaration. Its static predicate proof now covers
`==`, `!=`, `<`, `<=`, `>` and `>=` between two canonical nonnegative
decimal `i32` literals. The operator, operand ancestry and exact source
coordinates, comparison type and Clang folded truth value must all agree.
Branch effects remain source-proven in both arms before the compiler
selects either arm; a later input invalidates the current live local.

The normative VM reads binary `00 ff 80` and emits `00 ff ff 80` in eight
real steps from this complete C program. Focused invalid-source and forged
comparison-node checks reject without guest publication. The comparison
replay matrix is deliberately finite due to profiled VM memory cost; it
does not establish input-dependent C predicates, arithmetic, EOF handling,
mutable guest C storage or dynamic guest control flow. The P0 remains open.

### Canonical decimal C truthiness in constant byte-stream arms (2026-11-12)

A complete C source captured a guest input local, selected a multiline
`if (23)` block containing local reuse and nested `putchar` returns, skipped
its independently checked `else` branch, then selected the `else` of
`if (0)`. The pinned frontend accepted the source but normalized admission
initially refused it, even though the corresponding `if (1)` program worked.
The repaired byte adapter proves canonical, nonnegative decimal `i32`
conditions from `0` through `2147483647`, including literal width,
Clang type/value metadata, branch ancestry, and actual multiline opening,
body, and closing coordinates. Any nonzero literal selects the true arm;
zero selects the false arm. This is compile-time C truthiness only.

The actual 1,111-byte Malbolge guest reads `00 ff 80`, emits
`00 ff ff 80`, and halts after eight VM steps. The boundary tests cover
one-, two-, and ten-digit nonzero predicates, seeded binary stream parity,
unsupported expression spellings, and forged Clang metadata. Arithmetic,
negative or nondecimal predicates, EOF and runtime-dependent control flow
still refuse. The original input-dependent `while` / parity C experiment
was rerun and still refuses normalized admission without a guest artifact.

### Nested constant C conditions and else-if chains (2026-11-12)

A complete source-C function combines a live input local, an unbraced nested
`if (1) if (0) ... else ...`, comma-return output, an inactive nested arm,
and later independent reads. The pinned Clang frontend admitted the source,
but normalized JSON-to-typed-IR projection initially refused it. The source
proof now admits up to four nested literal `if (0)` / `if (1)` levels, including
`else if` chains and nested statements within canonical multiline compound
arms. Every selected and skipped child must match its direct Clang parent,
preorder ID, exact literal, byte extent and line/column coordinates; unknown
or nonliteral branch effects still refuse target publication.

The actual Malbolge guest reads three binary bytes and emits the four-byte
independent oracle in eight normative VM steps for twelve boundary and seeded
streams. A multiline nested-arm source matches three independent three-byte
oracles in seven steps, an inactive nested-arm source reads only the following
byte in three steps, and a selected `else if` source matches four binary
oracles in five steps. Four lexical nesting levels execute while five reject
without an artifact. Six unsupported C sources and seventeen forged Clang
metadata changes fail closed. This remains compile-time literal branch
selection and accumulator-only successful-byte I/O, not runtime guest C
conditions, EOF handling, general storage, arithmetic or loops. P0 stays open.

### Standalone comma effects in constant C arms (2026-11-12)

A complete source-C function uses a multiline `if (1)` block with
standalone comma output and mixed input/output statements, plus a skipped
`else` comma input chain. Pinned Clang accepted the source but the normalized
adapter initially refused. The existing direct comma verifier now accepts
literal-branch parent identity and projects every comma operand in order,
without adding the outer `putchar` write reserved for comma arguments. The
common effect projection reuses live locals until a new guest input replaces
the accumulator, and proves the entire skipped comma arm independently.

The normative VM emits three byte outputs from three guest inputs in seven
steps, matching eight seeded and boundary binary oracles. Forged comma parent,
operation and span metadata and an unsupported skipped-arm output reject
without publishing guest code. Guest-side dynamic C branches, arithmetic,
loops, durable storage and EOF handling are still outside the contract.

### Comma-result evaluation inside constant C branches (2026-11-12)

A complete C program captures a live input local, enters a multiline `if (1)`
arm, writes the return byte of `putchar((putchar(first), first))`, then
executes a distinct `putchar((getchar(), putchar(getchar())))` comma chain.
An inactive `else` arm contains an independently proven two-read comma output.
The pinned Clang frontend accepted the source, but the JSON adapter initially
refused the first declaration. The existing call/comma source proof now accepts
an explicit `if`-arm parent and expands every comma operand into ordered guest
read/write effects, placing the outer output last. Selected new reads still
invalidate an earlier live local. The skipped arm must also authenticate its
entire expression tree and cannot hide unsupported I/O or arithmetic.

The actual Malbolge capsule reads three binary bytes, emits four independent
oracle bytes, and halts in eight VM steps, as demonstrated across ten seeded
and boundary inputs. Ten unsupported C forms and twelve forged Clang AST
variations fail without publishing target artifacts. This is bounded,
compile-time constant-arm selection under successful-byte I/O; runtime input
conditions, EOF, arithmetic, mutable C state, and loops remain unsupported.
The original input-dependent loop/parity/arithmetic C experiment still fails
closed at normalized JSON admission. P0 remains open.

### Canonical multiline constant C arms (2026-11-12)

A complete C source with two multiline `if (1)` / `if (0)` blocks, both
with an `else` arm, initially failed at normalized JSON adapter admission.
The proven source-C projection now authenticates one-call-per-line compound
blocks with canonical indentation, exactly one newline per statement, exact
semicolon and brace byte gaps, and Clang byte/line/column, ancestry, and ID
coordinates. Every statement in both arms is proven, including the skipped
arm. Calls inside a selected arm preserve input and output order; a fresh
read invalidates a previous input-local alias. Existing single-line block
admission is unchanged.

The pinned C-to-Malbolge pipeline emits a real capsule performing three guest
byte inputs and four outputs in eight normative VM steps. Eight independent
boundary and seeded binary streams agree with an explicit C-order oracle.
Multiline blocks of 1, 2 and 16 `getchar()` statements execute at their exact
step counts; a 17th call refuses. Twelve unsupported C variants and 21
forged Clang AST alterations fail without target publication. This is
compile-time constant branch selection, not runtime guest C conditions,
loop arithmetic, EOF handling, failed I/O or general C storage. The original
input-dependent `while` / parity-branch program still rejects safely at the
JSON adapter and the P0 is pending.

### Single-line C compound arms around runtime guest I/O (2026-11-12)

A complete C program first failed normalized frontend admission when two
constant `if/else` branches used braced, ordered calls instead of one
unbraced call per arm. The source-checked byte adapter now admits a bounded
one-line `{ call(); call(); }` grammar with up to sixteen direct `getchar`,
`putchar(getchar())`, nested successful `putchar` returns, and live-local
`putchar` calls. It authenticates every Clang compound ancestor, both branch
arms, call identity, byte/line/column extent, and the exact statement gaps.
Only the selected arm performs guest effects; selected new input invalidates
the preceding accumulator-only local alias. Neither arm can hide an unknown
source effect, including an unreachable arm.

The original compound C witness emits three genuine guest reads and four
independently expected output bytes in eight VM instructions. Runtime C
conditions, multiline blocks, arbitrary expressions, local mutations,
EOF, failed I/O and general guest C loop or branch execution still refuse.
The full Fibonacci-style input-dependent control experiment continues to
reject at the normalized C adapter, without publishing an artifact.

### Constant C if/else arms around live guest bytes (2026-11-12)

A complete source-C function interleaves a live input local with literal
`if (0)` / `if (1)` arms, including skipped input, repeated-local output,
and direct guest I/O. Pinned Clang initially admitted the program, but the
JSON adapter rejected the input declaration. Exact AST parent, source
coordinate, literal and called-function proofs now select a single unbraced
statement and drop every skipped effect. An optional unbraced `else` arm is
also checked before selection; it does not reread stdin or produce output
when it is inactive.

The normative VM matches three selected binary input bytes and three output
bytes in seven instructions for the single-arm case. In a separate whole C
program with three `if/else` statements, ten binary guest input samples match
four oracle outputs in eight VM steps. Nested `putchar` return values,
standalone reads and captured-local returns work in selected arms. Eight
unsupported C forms and 18 condition/else AST forgeries refuse publication.
Runtime-dependent conditions, nonzero/nonone literals, braced arms and
arithmetic remain unimplemented. This is compile-time branch selection,
**not** dynamic guest C branching; the original C input/loop/arithmetic
experiment still cannot lower.

### Pure latest-local comma operands (2026-11-12)

A complete C function captures one byte with `int first = getchar();`,
then evaluates a plain `first` operand on either side of an inner comma in
three different `putchar` calls. Pinned Clang accepted the source with
unused-value warnings, but the JSON adapter originally rejected it at the
first declaration. The bounded projector now verifies both `lvalue-to-rvalue`
and local-reference AST nodes, their original parent and source coordinates,
and the identity of the latest live input. Reading a local for its C value
has no additional guest I/O effect, including when that value is discarded.

The emitted Malbolge source performs one real guest input and five outputs,
matching twelve seeded/boundary one-byte oracles in seven normative VM
instructions. Six invalid C variants and ten forged AST mutations reject
publication. This does not enable stale local reads after newer input,
mutating locals, arbitrary comma arithmetic, EOF or guest runtime C storage.

### Independent input declarations before nested local uses (2026-11-12)

A complete C function captures two successive `getchar` bytes into distinct
`int` locals, but deliberately uses each local **first** as the inner value
of `putchar((putchar(local), putchar(local)))`. A separate standalone comma
statement then combines a direct local output and a nested successful
`putchar` return. The pinned Clang source initially refused at the first
`declaration-statement`, because the projector coupled each local
initialization to a following direct output call.

The source-checked projector now emits a declaration's real guest `ByteInput`
independently of its eventual consumer. The established parent, reference,
source-span and call proofs then reuse the live SSA byte when the first
consumer is a nested or comma expression, with no hidden extra reads. In the
normative Malbolge VM, sixteen seeded/boundary two-byte inputs each produce
twelve independently expected outputs in fifteen instructions. Seven invalid
C source variants and thirteen forged Clang node changes refuse target
publication. Local values remain available only while their exact input is
the current guest accumulator; a newer read invalidates them.

This is successful-byte I/O and bounded source-authenticated straight-line
C, not general C storage, arbitrary expression evaluation, EOF handling,
failed output or dynamic guest control flow. The P0 remains pending.

### Live source-C input locals in comma return expressions (2026-11-12)

A complete C program captures two successive `getchar` bytes in distinct
`int` locals, repeats each byte through ordinary outputs, and then passes
`putchar(local), putchar(local)` as an enclosing `putchar` comma argument.
The existing source-C pipeline initially refused the first declaration.
The repaired Clang ancestry proof now accepts a bounded comma operand made
of one or more nested `putchar` calls around the current live local, with
source coordinates, parent identity, reference and cast metadata checked.
Every write executes in the actual guest VM using the original live SSA byte;
no operand secretly consumes another input. The proof also admits a local
operand before a fresh `getchar`, but refuses a stale local after a newer read.

The compiled guest reads exactly two binary inputs and emits nine independently
expected output bytes in twelve VM steps. Fifteen seeded/boundary streams
match the oracle, as do four additional live-local/mixed-input forms with
exact step counts. Two stale-local source variants and fifteen forged Clang
metadata mutations refuse publication. This remains accumulator-only guest
I/O under successful-read/write assumptions: EOF, runtime C storage,
arithmetic and dynamic C control flow remain unsupported.

## Nested successful-byte returns inside comma effects (2026-11-12)

A complete C function combines a runtime input local, a repeated nested
`putchar` return, a comma expression whose final operand writes twice,
a standalone comma statement with another nested write, and a final nested
call. It originally failed at normalized JSON admission. The shared pinned
Clang nested-call proof now accepts a comma-parent context and returns every
verified output ancestor instead of assuming one write per operand. The
adapter emits all writes in C inner-to-outer order, reusing the latest guest
input value without replaying host input.

Seven guest reads produce nine oracle writes in seventeen normative VM steps.
The bounded grammar accepts up to sixteen nested `putchar` calls per comma
operand, preserving the sixteen-operand comma-chain limit. Each call, cast,
function reference, source coordinate and ancestry must match; unsupported
arithmetic, extra casts, parentheses, EOF and failed output still refuse.

## Comma-result byte propagation in guest output (2026-11-12)

A whole C function with `putchar((getchar(), putchar(getchar())))`
and `putchar((putchar(getchar()), getchar()))` initially failed at
source-JSON projection. The repaired projection reuses the exact source
proof for each comma operand under a parenthesized output argument and
preserves all input and output effects in order. The final operand's
successful C return byte feeds the outer `putchar` without an extra read.

Four guest input bytes yield four independent oracle output bytes in nine
normative VM steps for twelve binary streams. A seventeen-operand argument,
nine unsupported C expressions and sixteen forged AST changes refuse guest
publication. The original two-input comma output remains admitted. This is
a bounded single-line successful-byte grammar: general expression trees,
EOF, failed output, C arithmetic and dynamic guest control remain open.

## Ordered mixed comma effects in guest C (2026-11-12)

A complete C program first failed at the JSON adapter when a standalone
left-associative comma statement mixed `getchar()` and
`putchar(getchar())`, after a local capture and nested output and before
another nested output. The source-checked projection now authenticates
all comma ancestors and each operand's exact Clang call, cast, reference,
source coordinates and lexical bounds. It emits each guest `ByteInput`,
including discarded reads, and each successful `ByteOutput`, including
writes whose return values are discarded.

The complete program reads five runtime bytes and writes the independently
computed five-byte oracle in 11 normative VM steps for 12 seeded/boundary
binary streams. Standalone two-, four- and sixteen-operand chains preserve
alternating reads and outputs with exact step counts; a seventeenth operand,
ten invalid source expressions and 17 forged Clang mutations refuse target
publication. The grammar supports only unparenthesized one-line comma chains
whose operands are direct `getchar()` or `putchar(getchar())`. C EOF,
failed I/O, parenthesized/general comma expression trees, guest-side
arithmetic, loops, branches and durable locals are still unimplemented.

## Standalone comma input sequencing (2026-11-12)

A whole source-C program now composes one automatic input local, nested
`putchar` return-value outputs, a three-call standalone comma chain,
`putchar((getchar(), getchar()))`, and another local-return chain. The
previously rejected comma expression is a real statement with three
successive guest input effects, even though C discards every result. The
pinned Clang preorder proves each left-associative binary comma ancestor,
source byte/line/column span, input call and external function identity.
The selected successful bytes execute inside the normative Malbolge VM:
seven reads produce five oracle output bytes in thirteen steps under twelve
independent binary streams. An input-only three-read chain emits no bytes
and halts in four steps; 2-to-16 comma reads are admitted and 17 refuse.

This remains a bounded, single-line straight-line comma expression with
only direct `getchar` operands. Comma chains containing `putchar`, arithmetic,
casts, parenthesized expressions, or extra effects refuse publication.
C EOF, output failures, guest-side C branch/loop evaluation and persistent
local storage are unimplemented. This fixes a real ordered guest-effect
semantic gap, not arbitrary C comma expressions or general I/O lowering.

### Source-sequenced discarded byte reads (2026-11-12)

A complete C source interleaves automatic `getchar` locals, a standalone
`getchar();` whose return is unused, nested `putchar` return values, and
repeated reads of the most recent local. The pinned Clang normalized source
previously rejected the entire function; the source-checked projector now
preserves the unused `getchar` as a real `ByteInput` effect, invalidates the
old accumulator-local alias, and continues the source-order trace. The guest
reads four bytes but emits only five, in ten normative VM steps. Fourteen
boundary and seeded binary input samples match an independent byte oracle.

A second complete C function passes `(getchar(), getchar())` as the argument
to `putchar`, then outputs a separately captured byte through nested calls.
The left operand must consume a guest input even though its value is
unobserved; the comma result is the right operand's actual byte. Both call
ancestors, the `i32` comma expression, parentheses, binary operator, lexical
bounds and source coordinates are authenticated against Clang. The normative
VM reads four bytes and emits four in nine steps, matching ten independent
binary oracles. A separate input-only C function executes two VM input steps
and one halt step with no output. Unsupported C mutations and forged Clang
metadata reject without target publication.

The admitted grammar is bounded and straight-line, with exact pinned Clang
subtrees. All guest reads must succeed with bytes; EOF remains unimplemented,
as do mutable C storage, nontrivial arithmetic, output failures, branches,
loops and arbitrary comma expressions. No input is synthesized on the host.

### Composed live local and nested call-return guest I/O (2026-11-12)

A complete C source captures two `getchar` results in automatic `int` locals,
passes each value through nested `putchar` return calls, repeats the same
local afterward, and interleaves a directly nested runtime `getchar` call.
Previously, the pinned Clang preorder was admitted but the JSON adapter
refused the first local declaration. The source-checked local projector now
proves each nested call/cast/reference trio, final local lvalue read,
identical live declaration reference, and every exact byte/line/column
endpoint. A new runtime input still invalidates the preceding local.

The actual guest reads three bytes and writes nine in C evaluation order,
without rereading successful input for nested or repeated outputs. A second
complete C program mixes a direct nested call with two nested reads of the
same later local. Binary boundary inputs and twelve seeded binary streams
per program match an independent return-byte oracle and exact normative
VM steps.

A separate sixteen-level local-return chain emits sixteen repeated
bytes in eighteen VM steps for zero and 255 input. Six unsupported source
variants and fifteen forged normalized AST/position changes refuse
publication. This is accumulator-only guest dataflow under successful I/O
assumptions; mutable C locals, EOF, failed output, arithmetic, branches and
general C control flow remain unsupported.

### Nested source-C call return values in a real guest (2026-11-12)

The complete C source `putchar(putchar(getchar()));` previously passed pinned
Clang but failed closed at normalized JSON admission. A source-checked
projector now authenticates up to sixteen nested `putchar` calls, their
function-to-pointer conversions, one innermost `getchar`, exact ancestor IDs
and all byte/line/column source endpoints. Under explicitly successful byte
input and output, each inner `putchar` returns its written byte. The guest
executes one input followed by the nested number of outputs, in C evaluation
order, using the existing latest-read accumulator-only backend.

Four full C programs (including three-level, sixteen-level and mixed
statement nesting) reach the normative VM. Two independent binary inputs
per program match the source-derived return-byte oracle and exact guest
step counts. Eight unsupported C mutations and sixteen adversarial normalized
AST/source-span mutations reject without target publication. The result does
not claim C EOF, output failure, general C function returns, mutable storage
or guest-side control flow; the P0 generalization is still incomplete.

### Dynamic source-C byte echo under successful input (2026-11-12)

The next complete source-C experiment uses three runtime `getchar`
results: one automatic `int` is output twice, a direct call is output
once, and a second automatic `int` is output twice. The pinned Clang
frontend admitted it, but the existing ten-node adjacent-local projector
initially refused the later output, before guest publication. The repaired
source proof authenticates each repeated five-node output, ties it to the
same local declaration and emits multiple guest outputs without rereading
stdin. The compiler selects the independently verified latest-successful-
read layout mode instead of weakening the strict echo mode.

The normative guest VM emits the independent five-byte oracle for both
`00 ff 80` and `41 0a fe` input, taking exactly nine VM steps. Eight
unsupported stale/effectful or over-limit C programs and thirteen forged
later-output AST/span changes reject without guest artifacts. This is
genuine guest
runtime value retention only in the accumulator; it is not mutable C
storage, general I/O flow, EOF semantics or guest C branching. The P0
remains open.

An additional complete source-C experiment now captures each successful
`getchar()` result in an automatic `int` local before passing that local
to `putchar`. The pinned frontend previously refused the first declaration.
The repaired Clang projection checks the ten-node declaration, initializer,
value-read and call ancestry and ties the exact local declaration reference
to the output argument. Adjacent direct calls can be mixed with local-forward
pairs, up to 128 total live reads. Every pair becomes a distinct runtime
`ByteInput`/`ByteOutput` SSA effect; the automatic local is only elided
after proof that no intervening use or mutation is present.

Two complete sources (a three-read mixed call/local trace and sixteen
distinct automatic locals) now produce real guest VM byte parity under
binary input. Eight unsupported source mutations and twenty-five forged
normalized AST node/span variants refuse before target publication. This is
source-local identity forwarding, not guest storage, input arithmetic,
reordering, C EOF behavior or runtime C control flow. The P0 remains open.

A demanding four-iteration C program with `getchar`, EOF checks,
stateful parity and conditional input transformations first exposed the
source-JSON projection gap: its first local declaration still refuses.
An independently useful narrower experiment now authenticates straight-line
C `putchar(getchar());` source calls. The pinned Clang preorder lowers
one to 128 adjacent read/write pairs into distinct typed SSA byte inputs
and outputs. Unlike bounded compiler-time Fibonacci replay, each output
here depends on a byte actually supplied to the running Malbolge guest.

The real C-to-guest pipeline produces normative guest code for 1, 3 and
16 successive pairs. A seeded test exercises every binary input byte
from 0 through 255 plus deterministic nontrivial binary streams; guest
stdout matches each submitted byte exactly. Separate mutated C sources
and forged Clang AST metadata reject before publishing artifacts. The
existing adjacent-echo layout checks its own guest VM witness.

This is a conditional **successful-byte** effect equivalence only; C EOF
returns -1 while the Malbolge VM has a different EOF accumulator word.
C `getchar` EOF, I/O failures, input computation, dynamic state, C loops,
control flow and the independent guest ABI remain unsupported. The P0
work item stays open, and source-C general byte-stream emission still
requires full semantics rather than a host-side output projection.

### Complete original unmasked Fibonacci guest (2026-11-12)

The pinned, complete twelve-trip `conditional_fibonacci.c` source now passes
Clang admission, bounded source-state replay, ternary lowering, layout
publication and normative Malbolge execution. An independent unsigned
recurrence calculates `02 59 5f 08 57 4f 22 6d 03 90 b3 23`; the emitted
guest produces all twelve bytes under both EOF and binary stdin, without
consuming input. The Python integration test compiles the original source,
checks guest artifact publication and independently executes the VM.

The extended search starts with a proved guest-written graphical source word,
revisits it after a real `j`, then uses a second real `j` to reposition D
behind executing code. A bounded state search tracks full accumulator words,
output prefixes, fixed memory operands and admissible graphical operands.
The independent positional layout checker and CLI publisher then validate
all code, D and write positions, the required first repeated rotation, guest
termination and two complete normative VM replays. This witness has more
than one repeated write address; the old exactly-one-repeat requirement was
valid only for the three/four-byte prefix grammar.

This is a finite, source-revisited output synthesis for one admitted complete
C trace, not general guest execution of C loops, conditionals or arithmetic.
The C control/state is still replayed at compile time. General source-C
lowering, arbitrary output streams and a seeded verification matrix remain
open under P0. The dated sections below document earlier bounded stages;
their then-current unmasked-layout refusals were superseded by this proof.

### Revisited guest source continues to a fourth byte (2026-11-12)

The original unsigned C Fibonacci source emits `02 59 5f 08` in four
iterations. Its three-byte prefix already needs a real rotated source word
revisited after a guest `j`; pristine graphical operands cannot reproduce
that prefix under the existing narrow grammar. A new bounded proposal extends
that guest-evolved prefix using checked data-pointer strides and a fourth
rotation of a fresh graphical source cell. The focused Rust test proves the
full four-byte guest output under EOF and binary stdin, with exactly one
repeated write, source-behind-code safety, and independent normative VM replay.
This does not generalize to the original twelve-byte Fibonacci trace or
establish guest-side C control flow. The complete pinned C-to-guest regression
remains a separate publication check.

### A `while` body directly contains a second `while` (2026-11-12)

The original full twelve-trip unmasked Fibonacci C source still refuses at
`Layout(UnsupportedEffectTrace)`. A separate complete masked recurrence then
exposed a normalized-C gap: an outer `while` with an unbraced inner `while`
body was rejected after pinned Clang admission. Both loops mutate separate
unsigned counters; the inner loop selects a real parity branch and writes
its mask before output. A bounded source proof now checks the outer predicate,
exact nested parentage, next-line indentation and identical body endpoint.
It replays both loops without introducing guest-side C state or control.

The independent unsigned recurrence and normative guest VM agree on all
12 bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03`, 47 steps, under EOF
and binary stdin. An independently calculated two-trip inner-loop variant
with idempotent mask writes reaches the same real guest output. Seven
negative complete C variants and nine forged AST
nodes refuse before publication. Unmasked guest synthesis and dynamic
C control remain unsupported; P0 stays pending.

### A selected `do` break skips a lexical output (2026-11-12)

A complete twelve-trip unsigned Fibonacci C program now executes an inner
`do` loop per recurrence term. The selected odd branch emits its masked
byte, then executes `break` before a following lexical `putchar`; even
terms instead execute that very same following output. The post-test
predicate contains division by zero only in its odd arm, which the selected
break must not evaluate. Pinned Clang accepted this complete source, but the
normalized adapter initially refused its first local declaration.

The bounded source replay now accepts one source-authenticated unreachable
`putchar` following a selected loop-local `break`, just as it already does
for `continue`. The skipped statement has no published guest effect; when
control reaches it normally, the same statement executes and emits its
byte. This proof does not introduce runtime guest branching or arbitrary
unreachable C statements. Unknown calls, extra dead siblings, and
unsupported selected arithmetic remain explicit refusals. The independently
computed unsigned recurrence produces twelve masked bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` under the normative guest VM
in 47 steps. The original unmasked Fibonacci layout and dynamic guest C
control remain unimplemented, so P0 is still open.

### A selected conditional `continue` skips the following C output (2026-11-11)

A complete twelve-trip unsigned Fibonacci C loop emits in its odd branch
before `continue`; its next lexical statement is the even-branch `putchar`.
Pinned Clang accepts the whole source, but the normalized C replay previously
rejected the first declaration because the selected exit left an unproven
sibling output in the enclosing compound loop body.

The bounded replay now authenticates exactly one source-backed `putchar` after
selected `continue` without applying that unreachable output effect. The
non-continued iteration still executes that same lexical output normally.
Additional siblings, unknown calls, writes, and selected undefined arithmetic
remain unsupported. Both branch polarities produce the independently computed
12-byte masked recurrence in the normative VM with empty and binary input,
47 guest steps each. Forged normalized output metadata and unsupported C
mutations must refuse without publishing a guest.

This proves ordered source-state selection, not dynamic C branch/loop lowering.
The original unmasked Fibonacci stream still refuses at guest layout, so P0
remains pending.

### Directly parented conditional `while` arms (2026-11-11)

A complete twelve-trip unsigned Fibonacci C program now selects one of two
unbraced `while` statements from `if/else`. The chosen loop iterates once
or twice, changing an unsigned mask before the next `putchar` call. Both
branches execute in the complete source, and each loop has a distinct
state-changing body; this is not a constant folded `if` with empty arms.
Pinned Clang admitted the source, while the JSON adapter initially refused
the first function-body declaration because the branch arm was a loop.

The bounded replay now independently verifies each loop against its own
source-checked Clang parentage and canonical multiline indentation, then
keeps only the selected local writes. Separate source negatives reject
nonterminating steps, hidden `getchar`, and protected counter writes.
The independent unsigned recurrence oracle and normative Malbolge VM agree
on `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps with EOF
and binary stdin for both the original and the inverted dispatch variant.
Seven invalid complete C sources and fifteen forged Clang nodes refuse
without publishing a guest, including an initially accepted end-column
forgery repaired by exact branch-to-arm endpoint checks.
This is compile-time C state replay, not general guest-side branching or
loops. The original unmasked Fibonacci output is still unsupported, and
P0 remains pending.


### `do` / `while` break skips a pure undefined predicate (2026-11-11)

A full twelve-iteration unsigned Fibonacci C program branches inside a
`do` body. Odd recurrence terms select `break` before testing a post-test
ternary; its unselected condition contains `1U / 0U`, which must not be
evaluated by C. Even terms do not break and evaluate the safe zero arm.
The pinned Clang frontend admitted the program, but the normalized adapter
previously evaluated the skipped condition and refused the source.

The bounded replay now authenticates a skipped pure `do` condition without
evaluating it after selected `break` or `return`; normal exit and selected
`continue` still use strict evaluation. The independent unsigned recurrence
and normative Malbolge VM agree on twelve masked bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under EOF and
binary input. Seven unsupported C variants and eleven forged ASTs refuse
publication, including a byte/column endpoint forgery closed by the shared
binary-expression span proof. A valid unconditional-break variant also
reaches the normative guest VM. This remains bounded source replay, not
guest-side dynamic C control; unmasked Fibonacci layout remains unsupported.

### An unbraced inner `while` as a C `do` body (2026-11-11)

A complete unsigned Fibonacci C program places a directly parented,
unbraced `while` inside an outer post-test `do`. Every inner trip advances
the recurrence and writes a selected output byte; a source-proven conditional
`break` exits only the inner `while`. Its changed state and completed-trip
counter drive the outer `do` predicate. Pinned Clang accepted the source, but
the normalized JSON adapter initially refused the first declaration.

The bounded replay now admits that exact two-line `do` / `while` ancestry
with checked byte, line and column placement, and requires the nested
braced `while` endpoint to match its enclosing Clang span. A forged
comparison operator exposed an existing source-authenticity gap; same-line
unsigned comparisons now check both operator width and byte/column gaps.
All fifteen forged AST variants and six unsupported C mutations refuse
before guest publication.

Two complete variants use two outputs across six outer trips or four
outputs across three trips. Both agree with the independent unsigned-C
oracle and actual Malbolge VM on twelve masked bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps, under EOF
and binary stdin. This is bounded source-state replay, not guest-side C
loop execution or an unmasked Fibonacci layout; P0 remains open.

### Nested switch continuation with case-local recurrence writes (2026-11-11)

A full twelve-iteration Fibonacci C source selects two switch levels and
emits from the innermost case before updating both recurrence locals.
The even inner case continues the enclosing `for`, while the odd case
breaks both switches. Pinned Clang admitted the complete source, but
normalized source replay initially refused its first declaration.
The bounded projector now isolates an inner selected `continue` from all
alternate outer switch arms, then carries its checked state and output
through the outer dispatch. The only allowed unreachable outer suffix is
a source-checked switch-local `break`; hidden writes and I/O still refuse.

The independent unsigned-C oracle and normative VM agree on twelve
masked bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under
EOF and binary stdin. A second full program continues from each inner
default instead. Negative source mutations and forged Clang continuations
and outer breaks refuse publication. Three nested switches, general
guest-side C control and unmasked Fibonacci remain unsupported; P0 is open.

### `continue` from a C switch into its enclosing loop (2026-11-11)

A full twelve-iteration unsigned Fibonacci source moves recurrence updates
before a `switch` whose even case emits a byte and continues the enclosing
`for` loop, while its default arm emits and breaks the switch. Pinned Clang
accepted the complete program, but the source-state adapter initially refused
its declaration. The bounded replay now authenticates direct switch-local
`continue` with its exact Clang keyword span and retains the exit only for
the selected arm, after checking the other cases. The inverse variant
continues from the default arm. Both reach real Malbolge VM execution with
twelve independent masked-oracle bytes in 47 steps under empty/binary input.
Unsupported C mutations and forged normalized continuations reject publication.
Nested-switch continues, guest dynamic C branching and the original unmasked
Fibonacci guest layout remain unimplemented; P0 stays pending.

### Skipped pure unsigned unary arithmetic (2026-11-11)

A complete twelve-trip unsigned C Fibonacci recurrence evaluates a
short-circuit `&&` before a bitwise unary `~` applied to division. On the
first even term the division would be undefined if executed, so the
normalized frontend previously rejected the entire program. The
source-proof path now authenticates skipped `~`, unary `+`, and unary `-`
using the exact selected-unary source grammar without evaluating their
operands. The pinned C frontend and normative Malbolge VM produce the
independent masked recurrence `02 19 1f 08 17 0f 02 0d 03 10 13 03`
in 47 steps under EOF and binary stdin. Six invalid C variants and ten
forged normalized nodes reject without a published guest. The bounded
expression-depth limit, general guest-side C execution and original
unmasked Fibonacci layout remain unresolved; P0 stays pending.

### Nested pure arithmetic in an unexecuted C operand (2026-11-11)

A complete twelve-iteration unsigned Fibonacci C program puts additions,
subtractions, divisions and remainders inside both arms of a ternary
protected by an outer C short-circuit guard. Even terms skip the
entire ternary; evaluating either nested division or remainder would
divide by zero. The pinned C frontend admitted the source, but the
normalized adapter originally refused the whole program.

Bounded source replay now authenticates recursively every child of a
skipped pure unsigned arithmetic expression, including multiple undefined
operations, without materializing an arithmetic result. Selected
operands continue through strict checked evaluation. The two full C
variants choose opposite ternary branches on odd terms. The normative
Malbolge VM and separate unsigned-C recurrence oracle agree on twelve
bytes with EOF and binary stdin (43 and 41 steps, respectively). Six
unsupported source mutations and forged normalized operators/metadata
refuse before artifact publication. This is finite source projection,
not guest-side C control flow or arbitrary byte-stream synthesis; the
original unmasked Fibonacci layout is still unsupported.

### Skipped ternary inside a logical guard (2026-11-11)

A complete twelve-trip unsigned Fibonacci C program uses a source-proven
`&&` guard whose skipped right operand is a `?:` selecting unsigned
division or remainder. When the term is even, both would divide by zero,
so neither may be evaluated; odd terms execute the selected arm. A red-first
normalized-frontend refusal was repaired by authenticating both pure ternary
arms without evaluating a skipped one. The selected path still refuses
undefined arithmetic and unsupported effects. A forged Clang column on the
ternary previously reached expensive guest layout; exact start/end byte,
line and column agreement now fails closed.

The real VM emits an independently calculated twelve-byte recurrence for
the alternating division/remainder source. The original unmasked Fibonacci
byte stream still refuses at guest layout; dynamic C control and arbitrary
byte-stream emission are not implemented. The P0 remains open.


### Short-circuit C logical guards (2026-11-11)

A complete twelve-trip unsigned Fibonacci C program guards division with
`&&`; the pinned Clang frontend accepts it but the normalized adapter
initially rejected it because the RHS divided by zero on even terms.
The bounded source replay now checks the entire skipped pure Boolean RHS
without evaluating its division, preserving C evaluation order. The same
full program with `||` and opposite branch selection also compiles. Both
variants match the independent unsigned-C oracle on the real normative
VM: `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps, with
EOF and binary stdin. Selected zero division, hidden input/output, and
forged source nodes still reject before guest publication.

This is finite source proof with bounded expression depth, not general
guest-side short-circuit branching. Complex nested arithmetic can still
exceed the expression-depth bound; unmasked Fibonacci and arbitrary C
control flow remain unimplemented.

### Non-evaluated C ternary arithmetic (2026-11-11)

The complete twelve-iteration masked unsigned Fibonacci program now guards
`/` using a source-proven C conditional expression. An even term causes
its unselected numerator/denominator subtree to include division by zero;
the old eager JSON evaluator rejected the first declaration even though C
would not evaluate that operand. The bounded replay now authenticates the
skipped pure `u32` division/remainder and its parentheses without demanding
an arithmetic result, while selected operands still use checked evaluation.
Only the exact pure subtree with a zero divisor gains this exception.

A second whole-C variant has division in one alternative and remainder in
the other: each becomes undefined if evaluated on the opposite selection.
Both valid selections occur over twelve iterations. The separate unsigned-C
oracle and normative Malbolge VM agree on the twelve masked bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps, under EOF and
binary input. Selected zero division, unselected side effects/input, and
four forged Clang arithmetic nodes reject without guest publication.
The original unmasked Fibonacci still rejects at
`Layout(UnsupportedEffectTrace)`; dynamic guest branching and general C
short-circuit evaluation remain unimplemented. P0 stays pending.

### Conditional C switch arms (2026-11-11)

A complete twelve-trip unsigned Fibonacci C program places a bounded
`switch` inside both braced `if/else` arms. The pinned Clang frontend
admitted the complete source but the adapter initially refused this
control-flow composition. The selected switch now carries its checked
local writes or `putchar` effects out of the conditional without leaking
effects from the unselected arm. A second complete program moves its
only output into the selected switch case.

The independent unsigned C oracle and normative guest VM both emit
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps. Five invalid C
mutations and 24 forged ASTs refuse publication. The source proof now
checks full arm end spans and exact opening byte/column gaps, rejecting
previously accepted forged brace coordinates. Dynamic guest control and
the original unmasked Fibonacci output remain unsupported; P0 stays open.


### Scalar induction truth guards in complete C (2026-11-11)

The full source-backed unsigned recurrence now uses a descending C loop
with `for (unsigned i = 12U; i; --i)` rather than an explicit comparison.
Pinned Clang admitted the complete program, but normalized local replay
originally rejected its first declaration. The compiler now accepts only
the exact protected unsigned induction variable as a pure scalar guard,
with checked Clang source spans, canonical separator geometry, a virtual
zero bound, and source-proven descending steps. Its finite proof refuses
overflowing or nondecreasing increments, unrelated local reads, and
effectful conditions.

An independently computed unsigned-C oracle matches the real normative
guest VM on twelve masked Fibonacci bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps with empty or binary
stdin. Pinned Clang also normalizes postfix, compound and assignment
decrement spellings. The complete guest parity evidence is limited to
the prefix spelling; four unsupported C changes and eight forged AST
variants reject without publication. This does not implement dynamic guest C
loops or the original unmasked Fibonacci layout. P0 remains pending.

### Ordered C state writes between selected switch outputs (2026-11-11)

The complete `local_interleaved_switch_fibonacci.c` program performs six
bounded recurrence trips. Two levels of `switch` select four distinct arms;
each chosen arm emits one source-proven `putchar`, changes the unsigned local
`y` using `y ^= 1U`, then emits a second `putchar` from the changed value.
That second expression cancels the local bit change, so ignoring the write
would alter the emitted byte. The pinned Clang frontend accepted the whole
source, but the JSON adapter initially refused the first declaration and
published no guest because it forbade a local write after an output.

The bounded switch replay now admits precisely checked unsigned assignments
between ordered selected outputs, while retaining the two-output ceiling,
source ancestry, case-local `break` and separation of unselected effects.
Whole-assignment Clang spans must equal their left and right endpoint spans
in both byte and column coordinates; independently forged assignment columns
were previously accepted by the narrower geometry check. The independently
computed unsigned-C oracle and normative Malbolge VM match all twelve bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under EOF and binary
stdin. Five unsupported source mutations and 24 forged assignment ASTs
refuse guest publication. General C runtime control, arbitrary guest state
and the original unmasked Fibonacci byte stream remain unsupported.

### Paired effects in switch-local C conditionals (2026-11-11)

The complete `local_conditional_dual_nested_switch_fibonacci.c`
source places two real guest `putchar` calls in each selected branch
of four conditional statements nested within two-level switch arms.
Each C branch computes different compensation; incorrect selection
changes observable bytes. The pinned frontend, bounded JSON state
replay, typed lowering and verified guest layout admit the source.
The independent unsigned recurrence oracle and normative Malbolge VM
match twelve masked bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03`
in 47 steps, both with EOF and binary stdin. Three complete-C
unproved-effect mutations and 24 forged Clang `if` nodes fail closed,
without guest publication. Guest dynamic switching and unmasked
Fibonacci layout remain unresolved under the P0.

### Two source-ordered outputs per nested switch arm (2026-11-11)

The complete `local_dual_nested_switch_fibonacci.c` C program runs
six source-proven bounded `for` trips. Each computes two consecutive
unsigned Fibonacci terms and selects one of four two-level switch
paths. Each innermost case emits both checked masked terms from two
separate `putchar` calls, with all four selector pairs reached.

The pinned Clang frontend admitted this program, but the JSON adapter
initially refused the second call in each case. A bounded two-output
vector now survives nested switch replay; unselected calls never
escape, outputs cannot be followed by other state writes, and an
effectful fallthrough or third output refuses. The independent C oracle
and normative Malbolge VM match the ordered twelve-byte stream
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 VM steps under EOF and
binary stdin. Six complete-C negative mutations and 48 forged Clang
output-call nodes reject without publication.

This is finite source-state replay, not general dynamic C switching or
an arbitrary byte-stream synthesizer. The original unmasked Fibonacci
trace still lacks a proved guest layout; the P0 remains open.

### Conditional C state inside nested switch cases (2026-11-11)

A complete twelve-trip unsigned Fibonacci C program now uses four inner
`switch` cases, each with a source-ordered `if/else` selecting a different
low-order mask before a compound XOR compensation and a real `putchar`.
The selected branch changes a low bit, so ignoring that decision would
change output even though the proved compensation restores the original
masked Fibonacci stream. Pinned Clang admitted the whole C source; before
the repair, the JSON adapter refused the first local declaration.

The bounded adapter now replays both conditional branches against the same
source state, captures at most one selected output per switch arm and
restores state before proving each unselected case. For switch-local
conditionals it also checks the exact opening `if (` byte/column spacing,
the closing branch span and forbids selected function/loop exits.
An independent unsigned-C oracle and the normative guest VM agree on all
twelve bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps with
EOF or binary input. Seven unsupported C variants and 24 forged conditional
ASTs refuse without publishing a guest. A second complete C source
moves all twelve outputs inside the selected conditional branches; the
normative VM independently confirms the same twelve bytes and 47 steps.
This adds finite C control replay, not guest-side dynamic branching. The original unmasked Fibonacci byte
stream still fails layout synthesis, and the P0 remains pending.

### Nested source-proven switch output effects (2026-11-11)

The original two-level switch Fibonacci source now has a second complete
C variant where each inner case/default both sets the local mask and
emits its own `putchar`; there is no output after the enclosing switch.
Pinned Clang accepts the whole source, but the pre-repair JSON projector
refused nested guest output effects. The bounded projector now captures
the inner switch's one selected output before replaying the outer switch's
other case/default paths, preventing unselected effects from leaking.
All four selector combinations occur. Source-bound Clang call spans must
also match closing byte and column geometry; an initially admitted forged
column exposed that separate validation gap.

The independently computed unsigned-C oracle matches the real Malbolge
VM on twelve bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps
under EOF and binary input. Seven unsupported C mutations and 24 forged
output-call AST variants refuse guest publication. A third active switch,
multiple I/O effects along a nested path, unbounded runtime C switching
and the unmasked twelve-byte Fibonacci byte stream remain unsupported.
The P0 is not complete; this is bounded source-state replay.

### Nested `switch` state selection within a bounded C loop (2026-11-11)

A full unsigned-local Fibonacci C recurrence nests one `switch` in each
selected arm of an enclosing `switch` inside twelve bounded `for` trips. A
nested switch chooses one of four distinct unsigned masks (`0`, `32`,
`26`, `58`); the two switch-local `break` statements do not exit the for.
Pinned Clang admitted the program, but the normalized C adapter first
rejected nested source-state selection. The finite projector now checks at most two active switch levels,
source-ordered and span-checked Clang children, and carries the selected inner
branch's local state into the outer switch without leaking another case.

A separate unsigned-C oracle covers all four selector combinations. The
normative Malbolge VM emits the twelve masked bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps on both EOF and binary
stdin. Eight C mutations and 22 independently forged Clang ASTs refuse
before guest publication, including output effects on selected or unselected
inner switch arms. The bounded projection excludes three nested switches,
nested byte I/O, unbounded guest switches and the original unmasked Fibonacci
layout. The general P0 output-stream milestone remains open.

### Unbraced C `do…while` directly inside `for` (2026-11-11)

The full Fibonacci recurrence also uses
`for (unsigned i = 0U; i < 6U; ++i) do { ... } while (phase != 0U);`.
Each protected for trip executes two mandatory-first inner iterations,
updates the recurrence, emits two branch-selected bytes and resets phase.
Pinned Clang accepts the direct do child, which the adapter previously
rejected for lack of a synthetic compound body. Source-backed replay now
checks the direct do ancestry, full byte/column endpoint, protected outer
counter and the do's post-body condition.

The independent unsigned-C oracle and normative guest VM both emit the
same twelve masked Fibonacci bytes as the nested-while variant in 47
steps, under EOF and binary stdin. Four invalid C programs and three
forged ASTs reject without publishing a guest. Dynamic guest loops and
general unmasked output layouts are not supported; P0 remains open.

### Unbraced C `while` directly inside `for` (2026-11-11)

The complete `local_unbraced_while_for_fibonacci.c` source uses a six-trip
`for (unsigned i = 2U; i <= 12U; i += 2U)` whose entire unbraced body is
`while (phase < i) { ... }`. The inner loop increments `phase` toward the
changing outer induction limit, computes Fibonacci state, branches on the
next term, and emits two masked bytes per outer iteration. The pinned C
frontend accepted the full source; the JSON adapter initially refused the
direct `while` child before any guest artifact was published.

Finite replay now authenticates direct Clang ancestry and matching full
endpoints for outer `for` and inner `while`, retains the protected induction
symbol, rechecks the inner condition after every C state update and respects
nearest-loop `break`/`continue` exits. The complete natural-exit, explicit
inner-break and inner-continue programs each match the independent unsigned-C
oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in exactly 47 normative
VM steps with EOF and binary stdin. Six unsupported source mutations and
eight forged normalized ASTs reject without guest publication.

This is source-proven bounded compile-time C replay, not guest runtime loop
execution. Unmasked twelve-byte Fibonacci output still fails the verified
layout search as `Layout(UnsupportedEffectTrace)`; general P0 remains open.

### Unbraced C `do…while` directly inside `while` (2026-11-11)

The complete Fibonacci source `local_unbraced_do_while_fibonacci.c` uses
`while (remaining > 0U) do { ... } while (phase != 0U);` without braces
around the outer body. The inner do toggles `phase`, changes both recurrence
locals, decrements `remaining` twice, and emits branch-selected masked bytes.
The outer predicate is re-evaluated against those updated locals after each
inner do, for six outer trips and twelve output effects. Pinned Clang
accepts the source; the JSON adapter initially refused the direct do child.

The repaired source replay checks exact Clang ancestry and full source-span
endpoints, including both byte and column geometry. It does not synthesize
a hidden compound scope or move do's mandatory first iteration. A separate
unsigned-C oracle and the normative Malbolge VM agree on twelve bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps, both under EOF and
binary stdin. Six invalid C variants and nine forged AST variants refuse
publication. Two forged closing columns exposed a byte-only endpoint check;
that check now rejects both independently tampered columns.

This is bounded compile-time C-state replay, not guest runtime C loops.
The original unmasked twelve-byte Fibonacci layout remains unsupported;
P0 stays open.

### Unbraced C `for` directly inside `while` (2026-11-11)

A complete twelve-output Fibonacci C program now uses an unbraced
`while (remaining > 0U) for (unsigned j = 0U; j < 2U; ++j) { ... }`.
Each inner trip updates recurrence locals and the outer `remaining`
variable, so the outer condition depends on updated state. Pinned
Clang accepted the source, but the adapter initially rejected the
nested `for` before guest publication. The source-backed replay now
checks direct Clang ancestry and the full statement endpoint, retains
inner counter scope and re-evaluates the outer condition after `for`.

An independent unsigned-C oracle and the actual normative Malbolge VM
agree on twelve masked bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03`
in 47 steps under EOF and binary stdin. Six invalid C sources and
eight forged Clang ASTs reject with no published guest. This is bounded
compile-time C-state replay, not dynamic guest loops. The original
unmasked twelve-byte layout remains unsupported.

### Three source-proven mixed C while/do levels (2026-11-11)

The complete twelve-output C source
`local_three_level_while_do_fibonacci.c` nests a two-trip
`do/while` inside a two-trip `while` inside another two-trip `while`,
with an enclosing bounded `for`. The pinned Clang frontend accepted the
source, but the JSON adapter initially refused the third active while/do
body. Finite source-state replay now permits three total active while/do
levels while retaining the existing twelve-trip cap, checked source
ancestry, lexical local lifetimes and protected for induction.

A real encoded Malbolge guest emits the independent masked unsigned-C
Fibonacci bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps.
The original unmasked twelve-byte layout remains unavailable, as do
dynamic guest loops and general runtime C state.

### Mixed two-level C `while`/`do` nesting (2026-11-11)

A complete twelve-output Fibonacci C source
`local_nested_while_do_fibonacci.c` places a two-trip `do/while` inside
an outer two-trip `while`, itself inside a bounded `for`. Pinned Clang
accepted it, but the JSON adapter originally refused the inner `do`
before guest publication. The repaired finite projector tracks active
`while` and `do` depths separately, enforcing a combined two-level cap.
It replays each inner predicate against updated locals, drops local
`pass` declarations on scope exit, and preserves the enclosing `for`
counter and nearest-loop `break`/`continue` targets.

Six complete source variants prove inner `break`, inner `continue`, outer
`break`, and all three loop nestings: `while/do`, `do/while`, and `do/do`.
The independent unsigned-C oracle and actual Malbolge VM agree on twelve
bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 guest steps on EOF
and binary stdin in each case. Seven invalid C sources and eleven forged
Clang trees fail without publishing guest code. Three active `while/do`
levels, unbounded loops, effectful predicates, forged ancestry and writes
to protected induction remain unsupported. These are compile-time C-state
proofs, not dynamic guest loops; unmasked Fibonacci output remains blocked
by byte-stream layout.

### Two source-checked nested C `while` loops (2026-11-11)

The complete twelve-iteration Fibonacci C source
`local_nested_while_while_fibonacci.c` adds a two-trip inner `while` to an
existing two-trip `while` inside a bounded `for`. Pinned Clang admits the
source, while the pre-repair normalized JSON adapter refused the second
loop. The bounded projector now uses active `while` depth rather than a
single Boolean, proving both predicates with source-checked Clang ancestry
and rechecking all local writes. It preserves lexical `pass` lifetimes,
nearest-loop exits and the protected outer induction symbol.

The source-derived unsigned-C oracle emits
`02 19 1f 08 17 0f 02 0d 03 10 13 03`; the real Malbolge VM matches
under EOF and binary stdin in 47 steps. Third-level `while/do` nesting,
effectful conditions, unbounded loops and fabricated Clang node ancestry
remain rejected before guest publication. This is bounded compile-time
source-state replay, not dynamic guest looping.
The original unmasked twelve-byte Fibonacci layout remains P0 work.

### Bounded C `do/while` nested in a stateful `for` (2026-11-11)

A complete twelve-iteration Fibonacci C source now computes its next
unsigned term in a two-trip, mandatory-first `do/while` directly inside
an enclosing bounded `for`. The pinned Clang frontend accepted the full
program, but the JSON adapter originally rejected the inner loop before
guest publication. The bounded source-state replay now admits this inner
form while preserving the protected outer induction counter, source order,
lexical local lifetimes and the do-loop's post-body predicate.

Independent source variants select `continue` during the first inner trip
and `break` on the second trip. The first still evaluates the trailing
condition; the second exits only the inner loop. All three complete
compiled C programs emit `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47
real normative VM steps under EOF and binary stdin, matching a separately
computed unsigned-C oracle. Five unsupported C variants and eight forged
Clang trees refuse before publication; a regression additionally requires
the closing brace's same-line byte and column offsets to agree.

This is finite compile-time source-state projection, not dynamic guest
C control flow. A separately proven two-level mixed while/do family is
now admitted; three active while/do bodies remain refused.
The original unmasked twelve-byte Fibonacci stream still fails layout;
general synthesis and runtime C state remain P0 work.

### Bounded C `while` nested in a stateful `for` (2026-11-11)

A complete twelve-iteration Fibonacci C source now computes each recurrence
term in a two-trip `while` nested directly in its enclosing `for`. The first
inner trip assigns the sum of the current unsigned locals; the second masks
it to a defined byte before a source-checked outer branch selects guest
`putchar` output. Pinned Clang accepted the entire program, but the JSON
adapter originally rejected the inner `while` before publishing a guest.

The finite replay now admits one source-proven `while` inside a bounded `for`,
with no third-level active `while/do` body. Inner
`break` exits only the inner loop: a second complete C variant proves an
explicit break on trip two does not cut short the enclosing twelve-trip
`for`. The proof re-evaluates the inner condition and source-local effects
on each trip and retains the already enforced limits on loop depth, source
spans and induction mutations. An independently computed unsigned-C oracle
and the normative guest VM both emit twelve bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under EOF and binary
stdin for both C variants. Five invalid sources and eight forged Clang ASTs
refuse publication, including a hidden input effect, induction mutation and
wrong inner-loop ancestry. This remains bounded compile-time C replay, not
runtime guest loop control. The original unmasked Fibonacci guest layout
remains blocked and P0 stays open.

### Source-local disjunctive `for` guard (2026-11-11)

A complete Fibonacci C recurrence uses `limit > i || b < 20U` with a
mutable unsigned stride and checked local state. Pinned Clang accepted the
whole program, but the normalized JSON adapter initially rejected the
source because it admitted only `&&` guards following an induction bound.

The repaired bounded proof preserves a first induction comparison and up
to two source-ordered `&&`/`||` pure right operands, recomputing the entire
Boolean condition after each iteration and increment. OR may keep the loop
alive after its first comparison becomes false; an unbounded true guard
still fails at the twelve-trip ceiling without publishing a guest.

An independent C oracle proves six trips: `i` reaches 10, `a` reaches 13,
and `b` reaches 21, while the initial bound of 2 is crossed after the
second output. The normative guest VM emits the exact six bytes
`02 19 1f 08 17 0f` in 97 steps under EOF and binary stdin. Five invalid
C source variants and seven forged Clang AST variants refuse publication.
This is bounded compile-time C-state replay, not dynamic guest C loops or
unmasked twelve-byte stream synthesis. P0 remains open.

### Source-order-independent `for` induction (2026-11-11)

The complete Fibonacci C recurrence now uses the equivalent source condition
`limit > i && b < 20U` with a changing unsigned `stride` and source-local
state. The pinned Clang frontend accepted this program but the normalized
adapter initially refused because its checked induction variable had to be
on the left. The repaired proof authenticates the original Clang operand
order, counter identity, pure right- or left-hand bound, token spacing,
source positions, and comparison direction. It re-evaluates the bound and
Boolean guard after each body and increment, without confusing `>` with
descending counter motion.

The independent C oracle stops after six iterations at `b == 21`, with
`i == 10`; the actual normative VM emits `02 19 1f 08 17 0f` in 97 steps
under EOF and binary stdin. Four invalid source programs and six forged ASTs
refuse guest publication. The original unmasked twelve-byte Fibonacci
program still refuses at guest layout. This repair is bounded compile-time
C-state replay, not dynamic guest C loops or general byte synthesis.

### Rechecked chained `for` conditions (2026-11-11)

A complete C Fibonacci program now combines source-local bound and stride,
changing recurrence locals, a branch, guest `putchar` effects and a
left-associated three-way `for` condition:
`i < limit && a < 40U && b < 20U`. Pinned Clang accepted this source,
but the normalized adapter originally rejected the nested conjunction.
A bounded proof now retains the induction condition at the left and checks
up to two additional pure `&&` guards, in source order, against the exact
Clang ancestry, type, token spacing and byte/column endpoints. Every guard
is re-evaluated against live C locals after the body and induction update.

The independent C oracle proves that `b < 20U` alone ends the loop at six
iterations, while the other two predicates are still true. The actual
normative VM emits `02 19 1f 08 17 0f` in 97 steps under EOF and binary
stdin. Nine unsupported C sources and nine forged AST variations refuse
without guest publication, including a newly exposed end-column forgery.
The five-output version stops at the separate guest-layout stage, and the
original twelve-output unmasked Fibonacci program remains unsynthesized.
This is bounded compile-time C-state replay, not dynamic guest execution
of general C control flow; P0 remains open.

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

### Rechecked source-local Boolean `for` guard (2026-11-11)

The complete source `local_guarded_for_fibonacci.c` was attempted with
`i < limit && a < 9U`, a local bound of twenty, a mutable stride, and
Fibonacci locals updated every trip. Pinned Clang accepted the source, but
the closed JSON adapter initially rejected its additional `&&` guard.
The bounded induction proof now admits one exact source-ordered pure right
condition after the original checked unsigned counter bound. The right
condition is independently checked for type, ancestry, span, operator and
canonical token separation, and is re-evaluated against the updated source
locals after each executed body and induction step. A logical OR cannot
replace the left induction proof. A changed or effectful guard is refused.

Six actual trips produce independent source oracle `02 19 1f 08 17 0f`,
with the stride changing from one to two and the Fibonacci guard stopping
before the twenty-step bound. The normative guest VM emits exactly those
six bytes in 97 steps under EOF and binary stdin. Source mutations and
forged AST variants refuse without artifact publication. This remains
compile-time bounded C-state replay, not runtime guest loop control or a
solution to the original unmasked Fibonacci output layout blocker.

### Re-evaluated source-local `for` increment (2026-11-11)

The full masked Fibonacci program now selects a source-local unsigned
stride and changes it from 1 to 2 after its third output. Pinned Clang
accepted the complete C, but the closed JSON adapter originally rejected
its `i += stride` induction without a guest artifact. The bounded proof
now retains the exact pure typed increment subtree, re-evaluates it after
each selected loop body, and only then updates the protected counter and
rechecks the condition. The equivalent `i = i + stride` spelling shares
this source-backed replay. Each actual stride must be between 1 and 12;
unknown effects, unproved AST shapes and an execution beyond twelve trips
refuse without publication. In a loop bounded by 10, the changing stride
produces six iterations instead of the ten that a frozen increment would
produce. The actual Malbolge VM emitted the independently computed six
masked bytes `02 19 1f 08 17 0f` in 97 steps under EOF and binary stdin.
This finite C-state replay does not implement runtime guest `for` loops;
the original unmasked twelve-byte program still refuses at guest layout.

### Re-evaluated source-local `for` bound (2026-11-11)

The first complete masked Fibonacci C source used `unsigned limit = 12U;`
and `for (unsigned i = 0U; i < limit; ++i)`. It initially refused at
normalized JSON admission, without publishing guest code, because the
closed induction projector required a literal bound. The repaired proof
accepts a pure unsigned expression bound, preserving the exact pinned-Clang
comparison, source token geometry and bound subtree. It re-evaluates that
subtree after every body and induction update, so writes to source-local
bounds change the next condition as required by C. Unprovable effects,
overwide bounds, and executions exceeding twelve trips still fail closed.

The full source emits an independently calculated twelve-byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 real normative VM steps.
A second full C source starts `limit` at 3 and increments it for the first
three trips; the independent six-byte oracle `02 19 1f 08 17 0f` reaches
the actual Malbolge VM in 97 steps. Both accept EOF and binary stdin.
Five unsupported C variants and six forged AST mutations refuse without
a guest artifact. The original unmasked output stream is still blocked
by the layout backend and dynamic guest loops remain unsupported.

### Dependent comma initialization in a function body (2026-11-10)

The complete masked Fibonacci source now initializes two zeroed locals with
`a = 1U, b = a;` directly inside the function body, before its twelve-trip
loop. It is one source-ordered comma statement with dependent state, not two
independent assignments. The pinned Clang frontend accepted the complete C
source while the normalized JSON adapter originally refused the function
statement without publication. The same bounded comma projector now applies
to function-body writes; a child must match its source parent and the comma
node's begin and end locations must match the first and last complete child
spans, including columns. This closes a forged-AST end-column drift found
by the new negative tests.

The real normative guest emits the independent masked twelve-byte Fibonacci
oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under empty and
binary stdin. Five invalid C variants and six forged AST variants reject
without publishing a guest artifact. The entire proof remains bounded
compile-time source-state replay; the original unmasked output stream still
fails at layout, not at C source admission.

### Unbraced conditional arms with ordered C comma writes (2026-11-10)

The complete twelve-step masked Fibonacci C source now uses two unbraced
`if`/`else` arms, each containing `selected ^= N, a = b;` as one comma
expression. The unselected arm must still be completely source-proven; the
selected arm must apply the first local write before the second, and its
updated recurrence state must survive to the next `for` iteration. Pinned
Clang accepted the whole C source while the JSON adapter initially refused
its direct conditional arm, without publishing a guest. The adapter now
reuses the existing bounded left-to-right local-write proof for unbraced
conditional expressions as well as for braced loop effects. It checks
exact Clang parents, full source spans, symbol identity, unsigned types and
the canonical same-line separator. At most four writes are admitted in a
single comma tree; calls, reads used as statements and unproved operators
still refuse.

The real normative Malbolge VM emitted the independently computed twelve
bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` in exactly 47 guest steps
under EOF and binary stdin. Eight invalid C variants and seven forged
Clang AST variants refuse without guest publication. This remains bounded
compile-time replay, not guest runtime sequencing or a solution to the
original unmasked Fibonacci layout failure. Generalized P0 remains open.

### Sequenced unsigned local writes in C comma expressions (2026-11-10)

The full twelve-iteration masked Fibonacci C source now uses
`a = b, b = next;` to update the recurrence in one C expression statement.
Pinned Clang accepts it, but the JSON adapter originally refused before
publishing guest code. A closed projector now replays each assignment in
C's required left-to-right order, checking the complete Clang subtree,
unsigned types, local symbols, source spans, and the exact same-line comma
separator. Nested comma groups are bounded to at most four assignments;
call effects, read-only operands and unproved shapes remain unsupported.
The entire C program reaches the independently derived masked twelve-byte
oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 normative guest steps
under empty and binary stdin. Nested three- and four-write replay remains
a separate timeboxed validation; five writes are outside the bounded proof.
Five invalid sources and five forged ASTs refuse without publication.
This is finite source-state replay, not dynamic guest sequencing or a
solution to the unmasked Fibonacci layout blocker.

### Bounded long switch fallthrough chain (2026-11-10)

The complete twelve-step masked Fibonacci C source now carries unsigned
locals through `case 0U`, `case 2U`, `case 1U` and a final `default`.
The original source failed at JSON admission without a guest artifact:
its three consecutive source-ordered fallthrough edges exceeded the previous
two-edge proof. An exact pinned-Clang replay now maintains the independent
entry state for each preceding case, checks every consumed node and break
against the direct-entry path, and caps replay at eight distinct case labels.
A source expansion exercises eight cases followed by default, including paths
with eight consecutive edges. The normative Malbolge VM emits the independent
12-byte oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in exactly 47 steps
under both empty and binary stdin, with no host output substitution.
A ninth case, output-before-fallthrough, effectful input, and forged later
case ancestry/spans/operators refuse without publishing guest code. The
original unmasked twelve-byte output still fails at guest layout, and
runtime guest C switching remains unsupported; generalized P0 is open.

### Source-ordered middle `default` C switch (2026-11-10)

The complete twelve-trip masked Fibonacci program
`tests/compiler/c-frontend/accepted/local_mid_switch_default_fibonacci.c`
places `default` between `case 0U` and later `case 2U`/`case 1U`. All four
selector values occur. An independent source-level recurrence computes the
same oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` as the existing masked
program, but each arm now writes a shared local before the sole post-switch
output. The pinned Clang frontend accepts it; the JSON adapter initially
refused the complete program without publishing a guest.

The closed source-flow projector now admits one direct-child middle default,
provided it follows an earlier case, has a checked unsigned write or pure
output, ends at a source-checked switch-local `break`, and is followed by
at least one ordinary `case`. Later cases must also prove the exact final
break and compound closure. No effectful fallthrough into or out of this
middle default is admitted. Every arm replays from independent pre-switch
local state, and the chosen case takes precedence over default regardless
of the labels' textual order. The real normative VM emits the twelve-byte
oracle in 47 steps under EOF and binary stdin. Six invalid C mutations and
eight forged Clang nodes refuse without publishing a guest artifact.
This remains bounded source-state projection: unmasked Fibonacci still
refuses at guest layout, and runtime guest C switching is not implemented.

### Source-proven switch fallthrough into default (2026-11-10)

The complete masked Fibonacci source
`tests/compiler/c-frontend/accepted/local_default_fallthrough_fibonacci.c`
was first rejected by the JSON adapter. Its `case 2U` modifies a `carry`
local and falls into a final `default` body; dispatch values 1 and 3 enter
that same body directly. The two entry classes require different values of
`carry`, and all four dispatch values occur in the twelve-step program.

The closed projector now permits a non-output case effect to reach a final,
source-ordered direct-child `default`. It independently replays the entire
default subtree from pre-switch locals and from every pending carried state,
checking exact Clang source-node extent, ancestry, effect order and the same
switch-local break. This still admits no more than two consecutive fallthrough
edges; effects before fallthrough, effectful input, extra body effects and
forged normalized trees refuse without publishing a guest.

The actual normative Malbolge VM emits the independently calculated masked
Fibonacci oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps with
empty and binary stdin. The separate complete source
`tests/compiler/c-frontend/accepted/local_chained_default_fibonacci.c`
also traverses two consecutive nonempty edges, `case 0U` to `case 2U` to
`default`, and reaches the same guest parity with separate direct dispatch
into both receiving labels. Five unsupported C mutations, seven forged
Clang trees, and an additional valid-C third-edge variant reject without
publication. The original unmasked twelve-output Fibonacci still refuses at
`Layout(UnsupportedEffectTrace)`; source-state replay is not dynamic guest
C switching or generalized byte-stream synthesis. P0 remains open.

### Two consecutive source-proven switch fallthrough edges (2026-11-10)

A complete twelve-iteration masked Fibonacci recurrence was first retried
alongside the unchanged unmasked source. The latter still refused at
`Layout(UnsupportedEffectTrace)` with no guest artifact. The new C source,
`tests/compiler/c-frontend/accepted/local_chained_switch_fibonacci.c`,
then refused at normalized JSON admission. Its switch uses three explicit
case labels in source order `0U`, `2U`, `1U`; direct entry into each case
must read different local state from entry via the previous label. The
case-zero path traverses **two consecutive nonempty fallthrough edges**,
whereas case two traverses one and case one none. Case three takes default.

The repaired closed projector replays each label subtree from pre-switch
locals for direct entry and separately from every pending carried path.
All replays must consume the same complete Clang nodes, end at the same
source position and agree on the switch-local `break` or next label.
Only the selected path's local state survives. At most two consecutive
edges are admitted, with no preceding output, no fallthrough to default,
and no relaxation of the four-effects-per-arm proof. The complete C loop
reaches independent masked oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03`
from real guest Malbolge in 47 steps under empty and binary stdin. Five
invalid C mutations and eight forged Clang trees refuse without an
artifact. This is finite compile-time source-state replay, not runtime
guest C switching, generalized byte layout, or acceptance of the original
unmasked Fibonacci target. The generalized P0 remains pending.

### Source-checked nonempty `switch` fallthrough (2026-11-10)

A complete twelve-iteration masked Fibonacci C source now uses real C
fallthrough from `case 0U:` into the next distinct `case 2U:` while
`case 2U:` also receives direct dispatch. Before repair, pinned Clang
accepted the complete source but JSON admission refused it without guest
publication. Clang parents each label's first `^=` expression directly
to that label, and later statements and `break` to the switch compound.
The projector checks exact label/source order, two complete entry paths,
source-backed local reads, at most four effects per receiving arm, and one
following break. It independently replays the receiving case from both
pre-switch state (direct entry) and the immediately preceding case's final
local state (fallthrough), requiring both traversals to consume the same
complete normalized subtree. Only the selected path's state is retained.

The source initializes `selected` with an extra `7` for dispatch value 2,
then uses a real `carry` write at dispatch 0 to cancel that factor before
falling into the same receiving code. The two entry states are deliberately
different: losing the carried state would change observed output. All four
dispatch values appear. The independently derived twelve-byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` matches the actual normative
Malbolge VM in 47 steps under EOF and binary stdin. Five unsupported
source mutations and six forged normalized AST variants refuse with no
guest artifact. Chained fallthrough, fallthrough to `default`, output
before another label, effectful input, unbounded body effects, dynamic
guest switching and the original unmasked guest layout are unsupported.
This is bounded source-state C selection, not a general runtime branch.

### C switch without default in the complete recurrence (2026-11-10)

The original unmasked twelve-iteration Fibonacci source still refuses at
`Layout(UnsupportedEffectTrace)` without a guest artifact. A separate entire
masked recurrence then attempted ordinary C `switch (next & 3U)` with
`case 0U` and `case 2U` but **no `default`**. It initialized `selected`
before the switch, assigned the even output in its matched arms and emitted
the post-switch local. All four selector values occur in twelve iterations;
1 and 3 must retain the incoming fallback local instead of selecting an
invented default. The pinned Clang frontend accepted the source, but the
JSON adapter initially refused it without publication.

The bounded projector now checks each source-ordered case arm and break,
requires the final break directly before the closing switch brace, and
restores the pre-switch state on an unmatched dispatch. Separate cases and
adjacent grouped `case 0U: case 2U:` both use this no-default behavior.
The complete source emits the independent masked twelve-byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` on the normative VM in 47 steps,
under empty and binary stdin. Three unsupported source variants and six
forged Clang trees refuse without publication. This is only finite
compile-time C-state projection: dynamic guest switching and the original
unmasked stream remain unsupported; P0 stays open.

### Ordered switch-arm C local transfers (2026-11-10)

The unmasked twelve-trip Fibonacci program was reattempted in full and still
fails at the independent guest layout with `Layout(UnsupportedEffectTrace)`;
no guest is published. A second complete four-way masked recurrence then
used two dependent local writes in every ordinary C `case`/`default` arm:
`selected = ...; transferred = selected ^ 0U; break;` followed by one
post-switch `putchar((int)transferred)`. Pinned Clang accepts the C but
originally the JSON adapter refused the switch's extra direct child.

Clang parents only the first statement to its case/default label; later
statements are siblings under the enclosing switch compound. The checked
projector now admits up to three extra ordered, source-bound unsigned writes
or one terminal pure output after that first effect, all before the required
switch-local break. Every arm is checked from the same pre-switch locals;
only the selected arm's final state and at most one output survive. Extra
calls, writes after output, uninitialized reads, fallthrough, effectful input,
more than four arm effects and forged ancestry/spans remain unsupported.
All three full-source variants (separate arms with shared output, grouped
case/default arms and a terminal arm-local `putchar`) emit the independent
masked oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in exactly 47
normative VM steps under empty and binary stdin. Six unsupported C source
mutations and seven forged Clang ASTs fail without a guest artifact.
This extends finite source-level C-state replay, not runtime guest switching.

### Switch-selected C local state in a complete recurrence (2026-11-10)

The complete masked Fibonacci source first refused when a four-way C switch
assigned an uninitialized local `unsigned selected` in each arm and performed
a single `putchar((int)selected)` afterward. Pinned Clang accepted the source,
but the JSON adapter refused at the loop's first declaration and did not
publish a guest. Each source-checked arm now proves exactly one unsigned
assignment or pure output, followed by its own switch-local `break`.
The projector snapshots the same incoming local state before every arm,
verifies even unselected operations, and commits only the chosen arm's writes
or output. This is required for compound `^=` arms that read initialized
state; sequentially replaying the arms would change the selected result.

Three complete source variants exercise direct initialization, compound XOR
state updates, and nested grouped `case`/`default` assignments. All four
switch dispatch values occur in the independent twelve-step Fibonacci
oracle. Each normative guest execution emits
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 VM steps with empty and
binary stdin. Four effectful/fallthrough source mutations and six forged
Clang trees refuse without publication. The bound remains one effect per
arm, at most eight distinct labels and one final default. This is bounded
compile-time C state replay, not runtime switching or general source C.
The original unmasked Fibonacci guest layout is still unsupported, so the
P0 remains pending.

### Bounded C switch selection in a complete recurrence (2026-11-10)

A full twelve-step masked Fibonacci source first refused at the normalized
JSON adapter after replacing its `if/else` output with ordinary C
`switch (next & 1U)`, `case 0U`, `default`, and explicit `break` statements.
The pinned Clang tree places each case's one `putchar` directly under its
label while parenting both `break` statements to the switch's compound
body. A source-bound proof now checks this exact shape, both pure output
arguments, the constant label, dispatch expression, ancestry, complete
spans, fallthrough barriers and source order before choosing one effect.
The switch-local `break` does not exit the surrounding bounded C loop.

The full C program emits the independently computed masked oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 normative guest steps
under empty and binary input. A second whole-program variant exchanges
which parity reaches the explicit case versus `default`; it emits the
same oracle. Three valid-but-unsupported C mutations (fallthrough,
effectful dispatch and an additional case) and eight forged normalized AST
variants reject without a guest artifact. This proves finite compile-time
C control selection, **not** runtime guest switch or input-dependent C
state. The original unmasked Fibonacci output remains unsupported at
layout, so P0 stays pending.

### Shared C case/default output in full Fibonacci (2026-11-10)

The entire twelve-step masked recurrence was rerun with two C switch label
groups: `case 0U: case 2U:` sharing one output and `case 1U: default:`
sharing the other. Pinned Clang nests `default` below its preceding
case label; before the repair, the JSON adapter rejected the valid whole
C source and published no guest. The closed projector now checks this
final nested default's direct parent, complete shared extent, source
order, effect-free label body, single pure output and switch-local break.
The default must remain the last label. An earlier effect, earlier break,
trailing case, or forged normalized tree still refuses. No general
fallthrough or runtime guest switch is implied.

All four switch destinations occur in the independent twelve-trip oracle.
The normative VM emits `02 19 1f 08 17 0f 02 0d 03 10 13 03` in
47 steps under empty and binary stdin. Three unsupported C mutations and
six forged Clang AST variants refuse without publication. The original
unmasked stream still fails at guest layout; P0 remains open.

### Grouped C switch labels in the complete recurrence (2026-11-10)

The full twelve-step masked Fibonacci source was retried with ordinary
`case 0U: case 2U:` labels sharing one pure `putchar` and a single
switch-local `break`. Pinned Clang nests the second case beneath the first;
the former direct-call-only projection refused the whole program without
publishing a guest. The source-state projector now recognizes this exact
consecutive empty-label nesting, checks both labels and the shared final
call against one source extent, and selects the group when either label
matches. The eight-unique-label ceiling still applies across all groups.
An intervening effect or break is not an empty-label group and still
refuses; neither runtime switch nor general fallthrough is implemented.

All four dispatch values occur in the independent twelve-trip C oracle.
The actual normative guest emits `02 19 1f 08 17 0f 02 0d 03 10 13 03`
in 47 steps under EOF and binary stdin. Two valid but unsupported
fallthrough sources and six forged Clang case-group trees refuse with no
guest artifact. Original unmasked Fibonacci and dynamic guest branching
remain P0 work.

### Multiway C switch selection in the full recurrence (2026-11-10)

A separate complete twelve-step masked Fibonacci C source replaced the
`if/else` output with `switch (next & 3U)` containing three explicit
`case` labels (0U, 1U and 2U), a final `default`, and one pure
`putchar` and switch-local `break` per arm. Its first pinned Clang-to-
JSON-to-guest attempt refused at the adapter with `Unsupported` and no
artifact. The source-state projector now checks up to eight distinct,
source-ordered unsigned case labels, each direct Clang output child and
separate break, followed by exactly one final default. It rejects duplicate
labels, fallthrough, hidden effects, forged case ancestry/value/geometry,
missing or misplaced breaks and an out-of-order default.

The full four-way program reaches all four arms over its twelve Fibonacci
iterations. Its independently calculated output is
`02 19 1f 08 17 0f 02 0d 03 10 13 03`; the normative current-profile
VM emits these exact bytes in 47 steps under empty and binary stdin.
Four unsupported C variants and nine forged middle-case Clang trees
refuse without publication. This widens only finite source-state switch
selection, not runtime guest branching or arbitrary output-stream layout;
the original unmasked Fibonacci program remains blocked at guest layout.

### Unbraced C branch effects in complete recurrences (2026-11-10)

The full twelve-step masked Fibonacci program was retried after replacing
both braced `if`/`else` output arms with ordinary single-statement `putchar`
arms. Pinned Clang accepted the whole C source, but the JSON adapter first
refused its local-flow projection without publishing a guest. Its normalized
AST directly parents each `call-expression` to the `if-statement`, rather
than inserting implicit compound blocks.

The bounded branch replay now accepts either a source-checked compound arm,
one direct pure-argument `putchar` call, or one checked unsigned local write
per arm. The selected state and output effects are committed only after both
alternatives are proved against the same incoming state. Source order, direct
parentage, complete spans, local bindings, pure expressions, nesting and
effect limits remain checked; unsupported effects and forged AST ancestry or
fields refuse without publishing a guest.

The original masked recurrence with unbraced output calls emits the independent
oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 normative guest VM
steps under empty and binary stdin. Two invalid source variants and six forged
Clang trees reject before guest publication. A second whole-source variant
replaces both branch calls with direct assignments to an initially
uninitialized `unsigned selected` and emits it with `putchar` after the
`if`/`else`. It also produces the same independent twelve-byte oracle in 47
normative guest VM steps with both inputs. Two uninitialized/incorrect-write
source variants and five forged AST bindings or operations reject without
guest publication. This is finite source-C state projection, not runtime
guest branches or locals. The original unmasked Fibonacci output remains
unsupported at layout; P0 is still pending.

### Lexical function-body blocks and C shadowing (2026-11-10)

A complete twelve-step masked Fibonacci recurrence was retried with an
additional function-body scope: an initialized outer `unsigned b = 77U`
is shadowed by an inner `unsigned b = 1U`, and the inner block contains the
entire bounded loop, branch and source-selected byte outputs. Pinned Clang
accepted the C source but the JSON adapter first rejected the block at the
initial declaration; no guest program was published.

The finite local-flow projector now reuses its source-checked lexical block
replay at function-body depth. It preserves enclosing writes and accumulated
output effects, resolves active same-name locals by their exact Clang symbol,
and drops only the inner declarations at the closing scope. Depth, ordered
source spans, parentage, automatic unsigned local types and effect limits
remain bounded. The complete real guest capsule is 2,207 bytes, executes
in 47 normative VM steps and emits the independent twelve-byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` under empty and binary stdin.
Invalid inner initialization, unknown effects and forged source/scope/symbol
metadata refuse with no guest artifact. A separate complete C source
proves the post-block binding: an inner `b = 90U` expires before the final
`putchar((int)b)` reads outer `b = 65U`. The normative VM emits `41` in
31 steps from a 1,295-byte capsule under both inputs; forging that final
read to the expired inner symbol refuses before publication. This extends
compile-time C-state proof, not guest runtime local storage or the original
unmasked Fibonacci layout. P0 remains open.

### Source-ordered unsigned declarator lists (2026-11-10)

A complete twelve-iteration masked Fibonacci program was retried after
combining its first two locals as `unsigned a = 1U, b = a;`. Pinned Clang
accepted the source, but the JSON adapter rejected its first
`declaration-statement` before guest publication. A red-first regression
now passes: the closed local-state proof consumes consecutive Clang
`variable-declaration` children in source order, carrying each proven
initializer into the next declarator. Bare declarators remain unreadable
until a selected later plain assignment proves their values.

A second complete source also proves a three-declarator group,
`unsigned a = 1U, b = a, later;`, followed by `later = b;` before the
loop. Its first use of `later` is a source-checked write, not a fabricated
zero initializer.

The bounded proof admits only automatic `u32` declarators, up to the
existing eight-local limit. For multi-declarations it checks the shared
`unsigned ` prefix, exact comma-and-space source offsets, source span and
column agreement, canonical symbols, a single final semicolon, and no
hidden initializer effects. In the full pipeline, the normative guest VM
emits the independently calculated twelve-byte masked oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under empty and
binary stdin for both two- and three-declarator whole-source variants.
Three invalid C variants and eight forged normalized AST variants reject
without publishing a guest artifact. This does not add
runtime guest locals, arbitrary C declarations, or original unmasked
Fibonacci layout; P0 stays open.

### Ordinary `int` literals in full unsigned C recurrence (2026-11-10)

The full twelve-step masked Fibonacci C program was attempted with the
conventional unsuffixed integer constants `unsigned a = 1;`,
`for (unsigned i = 0; i < 12; ++i)`, `& 255`, and the ordinary literals in
both output branches. Pinned Clang accepted this complete source, but the
JSON adapter first rejected its initial unsigned declaration and published
no guest. Clang's source-normalized tree represents these constants as
`i32` integer leaves wrapped in implicit `integral-cast` nodes carrying
their evaluated unsigned result.

The closed local-flow proof now accepts the bounded **nonnegative** `i32`
leaf only when its value agrees exactly with the enclosing `u32` cast,
its source span is identical and neither node carries hidden metadata.
The same proof retains byte limits for finite `for` bounds and strides,
while all other local arithmetic remains checked `u32`. The complete
program emits `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps from
the actual current-profile Malbolge VM with both empty and nonempty binary
stdin, exactly matching an independently evaluated unsigned-C recurrence.
Six unsupported C-source variants and eight forged Clang-node mutations
refuse without publishing guest code. Explicit casts, negative signed
constants and signed arithmetic remain outside this proven topology.

This repairs an everyday C-source conversion boundary; it does **not**
execute dynamic C locals in Malbolge. The original unmasked twelve-byte
Fibonacci source still requires generalized guest layout and arithmetic;
P0 remains pending.

### Source-proven unsigned locals assigned after declaration (2026-11-10)

The original unmasked twelve-step Fibonacci C program was rerun and still
refused at `Layout(UnsupportedEffectTrace)`, without publishing a guest.
An independent complete masked Fibonacci C variant declared `unsigned next;`
inside its bounded loop and subsequently assigned `(a + b) & 255U` before
the conditional `putchar` arms. The adapter previously refused this ordinary
C declaration at the first local, before any target artifact was written.

A local now carries `None` until a source-backed plain assignment proves
its first value. The uninitialized declaration requires exact pinned-Clang
name and semicolon geometry, automatic `u32` storage and no initializer
children. A local read, compound assignment or prefix/postfix step before
its first selected write rejects. Branches prove both arms on shadow state
and commit only the selected state; an unselected write does not initialize
a variable. The bounded `for` induction still requires its initialized
counter. Normalized JSON cannot recover the literal token contents;
source authenticity rests on the pinned frontend and source digest.

Both direct and selected-branch assignment variants compiled into 2,207-byte
Malbolge capsules. The normative guest emitted the independently computed
oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps per replay.
Negative uninitialized-use sources and forged AST metadata reject without
guest publication. This remains compile-time state folding rather than
runtime guest C variables; the unmasked P0 byte stream remains unsupported.

### Unsigned unary signs over full C locals (2026-11-10)

The complete twelve-step masked Fibonacci recurrence was retried with a
full-width intermediate `unsigned wide = -(a + b);` and a subsequent
`unsigned next = (+(0U - wide)) & 255U;`. The typed adapter first refused
both ordinary C unary signs, even though subtraction and unsigned wraparound
were already proven for binary expressions. The closed local-state projector
now admits unary `-` as wrapping 32-bit negation and unary `+` as identity,
only for adjacent parenthesized expression operands. The previously supported
`~next` complement remains accepted, but changing its normalized operator
to a sign without matching operand topology now refuses before guest layout.

The pinned frontend and typed/backend compiler emit a 2,207-byte current-profile
Malbolge capsule. Both empty and binary stdin replays of the normative VM
produce the independent masked Fibonacci oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps each. Five invalid source
variants cover unparenthesized or spaced signs, hidden state mutation,
undefined division, and a signed cast; six AST mutations cover operator,
type, parent, unrecognized metadata and operand topology. All refuse before
guest publication. Normalized AST metadata is still a bounded proof input,
not a complete raw-source token attestation. Dynamic C state and the original
unmasked twelve-byte output remain unsupported at guest layout; P0 stays open.

### Full unsigned C locals across the complete recurrence (2026-11-10)

Replaying the entire twelve-output masked Fibonacci C program with
`unsigned wide = a + b + 65536U; unsigned next = wide % 256U;` first
refused at the typed JSON adapter and published no guest: its bounded
constant-flow projector still narrowed **every automatic `unsigned` local**
to a byte, although the previous change already supported full unsigned
expression intermediates. Local declarations, references, ordinary and
compound assignments, and standalone `++`/`--` now retain the complete
source-checked `u32` value (including C unsigned wraparound). The separate
bounded `for` induction proof still requires byte-range counters, and
a direct `putchar((int)local)` still requires an exactly representable
byte; the original simple one-local projector is not broadened.

The full twelve-iteration C recurrence with an intervening wide local now
reaches a real current-profile Malbolge capsule. On empty stdin the normative
VM emits `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps, matching
the independent unsigned-C recurrence oracle. Full-program regression
variants also exercise a compound wide local write, wrapping at 2^32, and
standalone wide-local increment under empty and binary stdin. Invalid C
width, undefined remainder, out-of-byte guest output, and forged Clang
literal metadata are explicitly rejected without guest publication.

This remains **closed compile-time C-state evaluation**: neither C local
state nor its arithmetic executes dynamically inside the guest. The
original unmasked Fibonacci byte stream `02 59 5f ...` still fails at
layout; a bounded forward-jump scratch search cannot synthesize its early
`5f` under its current operand/geometry limits. No general byte-stream
synthesis or dynamic C control-flow capability is claimed; P0 stays open.

### Full unsigned-C intermediates in a bounded recurrence (2026-11-10)

A complete twelve-step masked Fibonacci C program was rerun with a normal
`% 256U` recurrence instead of the previous `& 255U` mask, and again with
`((a + b) + 65536U) % 256U`. Both whole programs initially refused at the
typed adapter before publishing a guest because its source-backed local
projector accepted only `0..255` integer leaves. The shared Clang-literal
proof now retains the entire normalized `u32` value for closed expression
arithmetic, including unsigned C wraparound, while the original simpler
byte-only projector and (at the time of this experiment) every local
store/output required a byte.

A third whole-source variant using
`((a + b) + 4294967295U + 1U) % 256U` also proves C `u32` wraparound
and reaches the same real guest output. All three complete programs emit
the independent twelve-byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` on the actual normative guest
VM under empty and nonempty binary stdin, in 47 steps per execution.
Malformed Clang literal metadata, out-of-range intermediate types,
undefined division, and attempts to store a non-byte still reject without
guest publication. This improves genuine C expression coverage, not dynamic
guest arithmetic. The original unmasked Fibonacci layout remains unsupported
and P0 is still pending.

### Source-proven `else if` chains in full C control flow (2026-11-09)

The complete twelve-iteration masked Fibonacci C recurrence was retried with
three source-level output arms, using an ordinary `else if` condition between
the original even and odd cases. The pinned Clang frontend represented the
second condition as an `if-statement` directly parented to the first; the
typed adapter initially refused the program at its first declaration and
published no guest artifact.

The closed C-state projector now proves a nested `else if` as a source-ordered
Clang child of its enclosing `if`, with bounded conditional depth and exact
parent and end-span agreement. Each arm is replayed against the same incoming
local state; only the selected branch commits its writes, exit and byte
effects. Unselected arms and conditions must still be pure and defined.

All three output arms are selected by the complete recurrence. The resulting
Malbolge guest emits the independent twelve-byte masked Fibonacci oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` under both empty and nonempty
binary stdin. Four negative whole-C cases (undefined arithmetic in a third
arm or provably skipped `else if`, an unbraced arm, and excess chain depth)
and four forged normalized-AST cases refuse without guest publication. The
compiler still folds finite local state at compile time, not in the guest;
the unchanged unmasked Fibonacci output remains unsupported at guest layout.

### Assignment-form `for` induction in a complete C program (2026-11-09)

The twelve-output five-bit masked Fibonacci recurrence was first retried with
`for (...; i < 12U; i = i + 1U)`. The pinned frontend normalized the ordinary
C assignment into an `=` node with a nested unsigned `+` read, but the typed
adapter refused it at the first local declaration without guest publication.
The bounded projector now checks the entire source-backed step tree: exact
assignment and arithmetic tokens, both matching induction references, the
Clang lvalue-to-rvalue cast, typed positive literal stride, and guard direction.
A second complete recurrence uses `i = 24U; i > 0U; i = i - 2U`. Both forms
are limited to at most twelve proven trips and preserve the existing checked
byte-range state updates; they do not introduce guest-side loop execution.

Both complete C sources compiled through the pinned compiler and emitted the
independent twelve-byte oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03`
from the actual normative guest VM, each under empty and nonempty binary
stdin (163.855 seconds for the combined replay). Eight source negatives
(including zero/large stride, wrong direction or source symbol, different
operator, nested expression, unproved spacing and an extra effect) and eight
forged AST negatives all refused without guest output publication. The
original unmasked Fibonacci guest layout remains unsupported; compile-time
state replay is still bounded and does not satisfy the general P0 objective.

### Standalone unsigned local steps in bounded C loops (2026-11-09)

The whole twelve-output masked Fibonacci C program was retried with a
`while` loop and a standalone `++i;` replacing its earlier `for` induction.
The pinned Clang frontend accepted the source, but the typed adapter refused
at the first local declaration, without guest publication. The repaired
bounded projector now admits discarded source-contiguous `++i;`, `i++;`,
`--i;` and `i--;` writes to the active automatic unsigned local. It proves
Clang ancestry, exact identifier width, prefix/postfix two-character token
position, no extra metadata, and a byte-representable result before each
store. The protected `for` induction variable cannot be mutated this way.

All four complete ascending or descending `while` variants compiled to
actual Malbolge. The normative VM emitted the independent twelve-byte
Fibonacci oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` under empty and
nonempty stdin. A source underflow, separated prefix token, forged AST
parent, operator, target, extent or metadata refused without guest
publication. The JSON-only proof cannot authenticate equal-width source
spellings or `++` versus `--` independently of the pinned frontend and the
driver's source digest. This remains compile-time C-state replay with a
12-trip ceiling, not dynamic guest `while` execution; the original unmasked
Fibonacci output still lacks a general layout witness.

### Conditional branch-local lexical scopes (2026-11-09)

The complete twelve-iteration masked Fibonacci C program was retried with a
source-declared `unsigned selected` inside each conditional branch, and with
an additional nested lexical brace around the even branch's temporary. The
pinned Clang frontend accepted the whole C source, but the typed JSON adapter
initially refused its first declaration statement without publishing guest
output. The repaired source-backed projector now proves declarations in both
branches, source order, nested brace ancestry and all expression effects. It
drops branch-local names at the end of each arm while retaining enclosing
Fibonacci writes and only selected guest outputs. The same local name in the
disjoint branches is permitted only after the first arm's scope closes.

The actual `malbolge-2026` VM emitted the twelve-byte independent oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` with both empty and nonempty stdin;
an initial variant took 47 guest steps. A zero-trip variant emits only a later
`0x41`, and a division by zero in its skipped nested conditional, excessive
brace nesting, forged branch parentage and extraneous metadata all refuse
without a guest artifact. The accepted projection is finite C-state folding;
this does not implement runtime guest C scopes, branching or arithmetic. The
original unmasked stream remains blocked at layout.

### Bounded C `for` exit statements (2026-11-09)

The full twelve-iteration masked Fibonacci C source was retried with an
explicit `if (i == 6U) { break; }` after the recurrence transfer. The pinned
Clang frontend accepted the whole source but the typed adapter initially
refused the first declaration and published no guest output. A bounded
source-backed exit proof now admits `break` and `continue` only within a
canonical `for` loop, checks Clang parentage, metadata and exact keyword span,
and keeps the selected exit separate from the unselected conditional arm.
`break` terminates replay without advancing the induction counter; `continue`
advances the counter through the original checked step. An exit must be the
last effect within its lexical block, or the whole source refuses rather than
silently discarding an unchecked dead suffix. Arbitrary post-exit C
statements remain unsupported.

For a break selected after iteration 6, the independent C oracle is the first
seven bytes `02 19 1f 08 17 0f 02`; a `continue` at the same iteration
preserves all twelve masked Fibonacci bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03`.
The focused whole-source test checks both artifacts under empty and nonempty
VM stdin, rejects unreachable effects after the selected exit, and exercises
forged break ancestry, keyword identity and metadata. This is closed bounded
C-state replay with actual Malbolge byte output, not runtime C branching or
loop control; the original unmasked guest-layout blocker remains.

### Bounded C `while` loop exits (2026-11-09)

A complete five-bit masked Fibonacci C recurrence was retried with a
source-declared unsigned counter, a pure `while` comparison and an `if`
selecting `break` or `continue` after the counter update. The pinned Clang
frontend accepted the whole source, but the typed adapter originally refused
its first declaration without publishing guest code. The closed projector
now binds exit keywords to the active `while` body as well as the existing
bounded `for` body. A selected `break` preserves earlier byte effects and
ends replay before rechecking the guard; a selected `continue` rechecks the
original source-proven guard. An exit may not hide later effects in its
lexical block, and malformed keyword parentage or metadata still refuses.

A 13-bound `while` with a selected break after its twelfth iteration emits
the independently calculated twelve masked Fibonacci bytes through the
normative guest VM under empty and nonempty stdin. Separately, a three-bound
`while` exits after its second iteration and the guest emits the
independently verified `Q.` pair, proving a genuine early break rather than
just a final iteration limit. A bound-12 `while` with selected `continue`
emits all
twelve oracle bytes. A zero-trip while proves a selected break in shadow state,
discards speculative effects and emits only a later source-derived `A`; an
undefined divisor within that skipped body is rejected. Exact Clang keyword,
parent and metadata mutations also refuse without publication. This remains
bounded compile-time C-state replay, not runtime guest C control flow. The
original unmasked stream and arbitrary seven-byte layout remain unsupported.

### Selected `do…while` exits in a full C recurrence (2026-11-09)

A complete twelve-output masked Fibonacci C program with a body-first
`do { ... } while (i < 13U);` and source-selected `break` initially
refused at the JSON-to-typed adapter, publishing no guest artifact. The
finite projector now allows selected `break` and `continue` in the
source-proven `do` body. As in C, an executed `break` terminates after
preserving preceding body outputs, while `continue` reaches the trailing
predicate. The remaining condition subtree is still required to be pure
and source-proven even when the executed break skips its value; unsupported
or undefined unexecuted conditions fail closed rather than being assumed
safe. Source-checked lexical bounds, iteration-local lifetimes and the
12-trip ceiling are retained.

Both complete variants emit the independent twelve-byte masked Fibonacci
oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` on the actual normative
Malbolge VM with empty and nonempty stdin. A three-bound `do` with break
after its second iteration emits only `Q.` instead of a third byte,
proving genuine early exit even while its trailing predicate would remain
true. Post-exit statements and forged Clang keyword, parent or metadata
refuse without publication. This is bounded compile-time C selection, not
runtime guest C control flow; the original unmasked twelve-byte stream
and generalized guest layout remain unsupported.

### Checked compound C assignments in a full recurrence (2026-11-09)

The entire twelve-iteration masked Fibonacci source was rerun with its
`b = next;` state transfer replaced by each of `b ^= b ^ next;`,
`b += next - b;`, and `b -= b - next;`. The pinned Clang frontend accepted
these complete C programs; before the fix, the typed adapter rejected the
first declaration because it could not prove the later compound assignment.
The bounded projector now proves the old local value, the complete pure
right-hand expression, the canonical two-character operator geometry, and
the unsigned `u32` operation before updating one active local. The result
was initially byte-bounded; `+=`, `-=`, and `^=` were the first admitted
compound local writes. Loop induction retains its separate strict contract.

All three full variants emitted the independent twelve masked Fibonacci
bytes through the normative guest VM under empty and nonempty stdin in a
260.944-second complete replay. Unrecognized compound operators, undefined
arithmetic, incompatible-width destination symbols, forged ancestry or
metadata, and broken source span geometry refuse without publishing a guest
artifact. The JSON-only adapter does not independently recover the original
operator characters or distinguish forged same-width identifier spellings;
source authenticity remains part of the pinned frontend trust boundary.
This is finite C-state folding, not guest runtime state or general C
compound-assignment support. The original unmasked
Fibonacci stream still refuses at guest layout.

### Full-width unsigned compound local writes (2026-11-10)

Two more complete twelve-iteration, branch-selecting masked Fibonacci C
sources were attempted before changing the typed adapter. Both initially
failed at the first unlowered declaration, without guest publication. The
first replaces the recurrence transfer with `b |= next; b &= next;`;
unsigned bitwise OR then AND must write `next`, not leave the prior value.
The second uses `unsigned wide = next + 65536U;`, then `wide %= 256U;`,
`wide <<= 1U;`, `wide >>= 1U;`, `b *= 0U;`, `b += wide;`, and `b /= 1U;`.
This exercises actual wide-state narrowing, both shift widths, zeroing and
restoration of C recurrence state. Independently computed scalar oracles
confirm twelve expected masked Fibonacci bytes.

The closed local-flow proof now admits ordinary unsigned `&=`, `|=`,
`*=`, `/=`, `%=`, `<<=` and `>>=` along with the earlier `+=`, `-=` and
`^=`. Each reads its prior local value and evaluates a source-proven pure
right-hand expression under exact unsigned 32-bit semantics. A contiguous
same-line token gap must match the two- or three-character operator; zero
division/remainder and shift counts above 31 refuse. C loop induction and
unsupported effects remain outside this wider local-store contract.

Both complete programs compile to real 2,207-byte modern Malbolge capsules.
The normative VM emits `02 19 1f 08 17 0f 02 0d 03 10 13 03` after
47 steps under both empty and binary stdin. Seven invalid source variants
and six forged AST variants reject without publication, including undefined
arithmetic, broken operator geometry, inconsistent parentage and extra
metadata. Normalized JSON does not authenticate same-width operator spelling
independently of the pinned frontend and driver's source-digest proof.
The original unmasked twelve-byte Fibonacci C stream still fails at layout;
this is bounded compile-time unsigned-C evaluation, not dynamic guest C state
or generalized arbitrary guest output. P0 remains open.

### Stored unsigned Boolean predicates in a full recurrence (2026-11-10)

A new complete twelve-iteration Fibonacci C experiment replaces the direct
`if ((next & 1U) == 0U)` branch with an automatic `unsigned even` initialized
by the same comparison and `if (even)`. The first pinned compiler attempt
refused at the JSON-to-typed adapter, without emitting a guest. A second and
third variant use `!((next & 1U) != 0U)` and `(next & 1U) < 1U` respectively.
All three retain source-defined loop state, arithmetic, both output arms,
and twelve distinct ordered byte effects.

The closed evaluator now admits the pinned Clang implicit `int` to `unsigned`
conversion only when its `u32` `integral-cast` node has the exact span of a
complete checked `i32` Boolean subtree. Existing pure source-backed
comparisons, logical operators and negation prove a result of zero or one.
Signed casts, side effects, undefined division, calls, and seven separately
forged AST changes reject without publication. In particular a claimed
`i32` result cannot be treated as an arbitrary unsigned value.

All three full programs compile to genuine guest capsules, then emit the
independent masked Fibonacci oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03`
on the normative VM under empty and binary input. The full positive
regression took 223 seconds on the local host. This is *compile-time* C
predicate evaluation and verified guest output, not live guest Boolean
state. The unmasked original `02 59 5f ...` stream still lacks a layout
witness; P0 remains pending.

### Source-proven lexical shadowing in a complete recurrence (2026-11-09)

A full twelve-iteration masked Fibonacci C source introduced a nested loop
block declaring a new `unsigned b`, while its enclosing recurrence already
had a distinct `b`. The inner `b` supplies selected `putchar` arguments,
but the next recurrence transfer must read and update the enclosing `b`.
The pinned Clang stage accepted the complete C program, but the bounded
typed adapter initially refused at its first declaration statement without
publishing guest output. The projector now admits distinct same-name locals
only across source-proven lexical scopes, selecting the innermost visible
symbol for both reads and writes. Same-scope aliases remain unsupported.

Two complete C variants independently reach the normative `malbolge-2026`
VM: the shadowed local is initialized to its output value directly, or is
initialized differently and then explicitly reassigned before output.
Both emit the twelve oracle bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03`
under empty and nonempty stdin, while the enclosing recurrence state stays
unchanged by the shadowed writes. Forging a Clang inner read or assignment
target to refer to the still-active outer symbol now refuses, as do forged
declaration parentage, metadata and invalid source arithmetic; no failed
case publishes a guest artifact. These are finite source-proven C state
projections, not dynamic C lexical environments or runtime C variable
storage in the guest. Original unmasked Fibonacci still lacks a guest
layout witness.

### Conditional void return in bounded whole-program C (2026-11-09)

A complete twelve-output masked Fibonacci program with a `for` bound of
thirteen and a source-selected `return;` after iteration twelve initially
refused at the typed adapter, with no guest artifact. The closed projector now
proves an exact six-character Clang void-return statement and propagates a
selected function exit through bounded loop replay, distinct from an inner
`break`. Both conditional arms remain source-checked, and an unselected
return is discarded along with its speculative state. A selected return is
accepted only when no subsequent statement or unproved effect remains, even
outside the enclosing loop; malformed return parentage, keyword, metadata and
source extent refuse without publishing an artifact.

The full C source reaches the actual normative guest VM and emits the twelve
independently computed bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` on both
empty and nonempty stdin. The thirteenth would have been executed without the
source-selected return. A second complete C recurrence emits the independent
`Q.` pair on an early selected `for`, `while` or `do…while` return, as well as
when the `for` return arm is never selected. All four forms are checked through
the actual VM on both stdin modes. These are checked, finite C-state
projections, not runtime guest stack unwinding or general C function-call
support. The original unmasked Fibonacci output remains blocked by guest
layout.

### Source-expression metamorphic parity (2026-11-09)

The complete 12-iteration five-bit masked Fibonacci C program has a bounded
metamorphic matrix that inserts either `0x20` or `0x40` XOR into **both**
conditional output arguments before the `& 31U` truncation. The independently
checked C identity `(value ^ high_bit) & 31U == value & 31U` holds for each
selected high bit, including input boundary values. Both entire changed C
sources pass pinned Clang, the closed JSON adapter, typed lowering, and layout.
The actual `malbolge-2026` VM emits the same `02 19 1f 08 17 0f 02 0d 03 10
13 03` twelve-byte stream with empty and nonempty stdin; a tested witness
executes 47 guest steps. `tests/test_compound_c_pipeline.py` owns the
replayable two-seed acceptance test. This exercises new source expression
ancestry and constant propagation without adding any emit-N fixture.

The unmodified, unmasked Fibonacci C source still refuses with
`Layout(UnsupportedEffectTrace)`. A bounded follow-up experiment could not
produce its first `02 59 5f` three-byte prefix by increasing graphical
source-scratch depth from five to twelve operations, nor by combining verified
two-output source-scratch prefixes with a relocation to loader-expanded data.
These were proposal-search failures, not a semantic impossibility proof; no
unverified guest proposal was admitted or retained. The stop condition for the
new metamorphic matrix is two independent high-bit seeds, both stdin modes,
exact whole-stream parity and explicit recognition that runtime C state and
the unmasked byte-stream target remain unsupported.

### Postfix `for` induction in a complete C recurrence (2026-11-09)

The full 12-iteration five-bit masked Fibonacci C program was retried with
`i++` instead of `++i` in its `for` step. The pinned frontend accepted the
source, but the strict local-state projection initially refused its first
`declaration-statement`, without publishing a guest. The adapter now admits
the source-proven **postfix** unary increment alongside the established
prefix form, only where the expression result is unused as a `for` induction
step. The Clang operator, counter symbol, exact parentage and two-character
postfix source extent must agree; decrement, compound assignment and forged
increment metadata fail closed. The independent twelve-byte C oracle is
`02 19 1f 08 17 0f 02 0d 03 10 13 03`. The actual current-profile guest
reproduces it in 47 VM steps. Both stdin modes and negative-source/AST
mutations are replayed in `tests/test_compound_c_pipeline.py`.

This is a new complete-source loop syntax admitted by compile-time static
state projection, not a guest runtime increment or general C loop execution.
The original unmasked Fibonacci stream remains unsupported at layout.

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
condition or selected checked break within twelve body executions; neither
nested loops nor unbounded, impure, undefined or unsupported effects are
admitted.

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

### Fifth live data relocation across twelve real output effects

The complete, unchanged twelve-iteration Fibonacci C program was retried
before this change and still refused at its positional guest-layout boundary.
The typed C effects remain admitted; no guest artifact was published. The
four-relocation writer had a separate, concrete ceiling: its proposal guard
rejected a source-independent guest with five actual `j` relocations even
though the independent layout checker could admit that guest.

A 30-cell, positionally encoded source with five relocations, twelve distinct
`p` writes, twelve real `<` instructions and a final halt emits
`41 47 5a 25 25 4d 32 18 5a 25 25 4d` in the normative current-profile VM.
The five relocations read untouched operands, and all twelve write addresses
are disjoint and outside code. The red-first test verified that the source
executed and its layout was independently admissible while the bounded
proposal rejected the same guest. Extending the existing relocation-count
parameter to five recovers its exact source. Empty and nonempty stdin replays,
output order, write footprints and forged-output rejection pass.

The general short-stream bridge now tries this additional paired-write search
for streams of 10 to 12 bytes only, after its established smaller-region
proposals. For this output stream the production bridge can independently
admit a different 30-cell guest, which is equally valid because the compiler
contract is observable byte parity, not exact source-byte identity. This
adds one bounded relocation capability; it does not establish shortest-code
optimality, arbitrary output synthesis, guest-side C state, or a witness for
the original Fibonacci C stream. P0 remains open.

### Source-scratch arithmetic after a forward code jump

The complete twelve-iteration conditional Fibonacci C program was retried
first and still refused guest publication at layout. A two-iteration variant
of the same original source independently requires bytes `02 59`, but the
previous guest grammar could not realize that pair. A forward `i` jump can
leave graphical no-op source cells behind the code pointer; the actual VM
may use those cells for `p` and `*` data writes without changing future code.
The prior layout checker refused every in-source arithmetic write.

The layout checker now permits only writes strictly behind the active code
pointer, updates its shadow memory with exact arithmetic results, and still
rejects current or future code overwrites. A bounded source-scratch proposal
explores these skipped loader bytes without host-produced output. The final
publisher independently decodes the forward jump, proves no pending code
write and distinct data writes, re-admits the full source, and executes two
normative VM replays with different stdin. The real pinned C pipeline now
emits a capsule executing 85 guest steps and returning `02 59` on both inputs.
A source-backed positive regression, red-first layout tests, mutated source
rejection and the independent VM oracle cover this new semantic boundary.

This is **not** runtime C loop or arithmetic lowering: the frontend still
projects closed C state at compile time. The full twelve-byte Fibonacci
stream remains unwitnessed by the bounded layout grammar, and P0 stays open.

### Forward-jump scratch streams beyond two effects

The bounded source-scratch search now tracks the jump-encrypted skipped cell
as an exact prospective operand, rather than assuming its original no-op
byte. The guest may rotate or apply crazy arithmetic to that cell after the
forward jump, since it remains behind the code pointer. A targeted layout
regression checks the post-jump encryption value, actual source mutation and
normative VM byte output on two input streams.

The source-scratch proposal also reaches three guest output effects for
`02 59 1b`. The three-distinct-output bridge can propose this geometry and
the file publisher independently decodes its forward jump, re-admits exact
source-cell writes and replays the normative VM. A complete three-iteration C
recurrence with unsigned locals, branch selection and nested arithmetic emits
the same bytes through the pinned pipeline and guest VM. The C control flow
and arithmetic still project at compile time; no guest C integer runtime or
arbitrary output-stream synthesis is claimed. The original twelve-byte
Fibonacci target remains unsupported at layout.

### Loader-valid variable source scratch for twelve-effect C streams

The unchanged twelve-output Fibonacci target still fails closed at layout:
`02 59 5f 08 57 4f 22 6d 03 90 b3 23` has no admitted guest within
these bounds. Its early `5f` effect is a concrete blocker for the previous
fixed-no-op source-scratch geometry. The compiler now supports a distinct,
source-proven complete twelve-iteration C recurrence whose two conditional
arms mask the selected Fibonacci values to five bits. The independent C
oracle is `02 19 1f 08 17 0f 02 0d 03 10 13 03`.

The first attempt at that complete C program reached typed IR but refused
at the guest layout boundary. The repaired layout admits explicit graphical
`SkippedDataByte` words **only inside a proven forward-jump gap**, and only
when the exact decoder phase yields an instruction the normative loader
accepts. The code pointer never executes those cells; the data pointer
reads them as distinct real operands. A finite source-scratch search tracks
both the exact accumulator and its advancing data phase, allowing up to
five arithmetic/no-op steps between output effects. Each candidate is
re-admitted positionally and rerun under two normative VM input streams.

The independent publisher reconstructs the jump and every skipped source
byte from the staged artifact; it does not trust the search proposal or
interpret skipped data as executed opcodes. It proves all source writes are
strictly behind code and distinct, rejects overwritten pending code, and
checks both exact guest byte order and input independence. The full pinned
C pipeline now emits an actual capsule that terminates after 49 VM steps
with all twelve masked bytes under empty and nonempty stdin. Mutating its
source to introduce undefined division is refused before guest publication;
loader-invalid and reachable-as-data placements are negative regressions.

This is bounded output arithmetic in Malbolge after **compile-time**
source-checked C state/branch/loop projection. It does not implement C
runtime loops, arbitrary guest memory, or the original unmasked twelve-byte
Fibonacci stream. The general P0 output-language goal remains open.

The bounded scratch state search now stores predecessor indices instead of
copying full opcode/operand paths for every alternative. Skipped code cells
may also decode as the profile's input instruction or as a jump: the loader
accepts those graphical bytes, but the actual jump skips them, so the guest
reads them **only as data**. The proposal precomputes all eight
loader-valid source bytes at each decoder phase. An independent layout/VM
regression places the otherwise executable input and jump byte at skipped
address one, proves its arithmetic data write lies strictly behind code,
and confirms it consumes no stdin under two inputs. The exact-address layout
checker and normative VM still own acceptance, not the search.

A second source-derived twelve-iteration conditional Fibonacci program
preserves six bits instead of five in each output arm (`& 63U`), with
independent unsigned-C oracle `02 19 1f 08 17 0f 22 2d 03 10 33 23`.
The pinned C frontend, canonical byte bridge and graphical publisher emit a
real VM guest reproducing those twelve bytes on empty and nonempty stdin;
a source mutation introducing division by zero is rejected without an
artifact. This is a semantic-width matrix case, not proof of arbitrary
six-bit streams or of the unchanged unmasked `02 59 5f ...` program.

### Source-proven compound induction in a full C recurrence

A complete twelve-iteration masked Fibonacci C program with the conventional
`for (...; i < 12U; i += 1U)` induction failed at the normalized JSON-to-typed
boundary. The pinned Clang emitted a typed `compound-assignment-expression`
for the loop's step, whereas the bounded source proof admitted only prefix
and postfix `++`. The original attempt correctly returned `Unsupported`
without publishing a guest artifact.

The bounded loop projector now also proves an unsigned induction variable
advanced by exactly the `+=` operator and a single `u32` literal `1`, with
canonical counter identity, complete right-hand side, source ordering and
checked span coverage. The complete pinned C source now produces a real
guest capsule with twelve verified output bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03`, matching the independent oracle
under empty and nonempty stdin. Source mutations to a two-step increment,
subtraction, and the wrong induction symbol reject without publication; six
forged operator, literal, symbol and span metadata cases also refuse.

Compound assignments in the loop body, variable-derived steps, other
operators and steps other than one remain unsupported. The compiler still
folds the closed C recurrence at compile time, not in guest-side C control
flow. The unchanged unmasked twelve-byte Fibonacci target remains unsupported
at guest layout; the P0 generalized guest-output language goal stays open.

### Bounded non-unit induction with a source-derived trip count

A complete masked Fibonacci C program was first attempted with
`for (unsigned i = 1U; i < 12U; i += 2U)`. The typed frontend rejected
its nonzero start and two-step induction before guest publication. Its
six-byte output required a distinct, expensive guest layout search, so the
whole-program acceptance was instead retained at twelve iterations by
changing the checked loop bound to `25U`.

The bounded loop projector now proves a source-typed unsigned initial value,
positive literal `+=` stride up to twelve, and the exact counter progression
until the `<` test becomes false. The limit is on actual iterations, rather
than the numeric bound. It retains exact source order, canonical counter
identity, typed operands and checked spans. Zero-trip bodies are still proved
without publishing their speculative effects. A zero step, subtraction,
wrong increment symbol, step beyond twelve and thirteen-trip loop are rejected
without a guest artifact.

The independently calculated twelve-iteration C recurrence with `i = 1U`,
`i < 25U`, `i += 2U` emits
`02 19 1f 08 17 0f 02 0d 03 10 13 03`. The real pinned compiler and
normative Malbolge VM reproduce that entire stream with both empty and
nonempty stdin. This broadens compile-time closed-loop evaluation, not
runtime C arithmetic or guest control flow. The unmasked original Fibonacci
stream still has no admitted guest layout; general P0 completion remains open.

### Inclusive unsigned induction in the complete C recurrence

The twelve-output masked Fibonacci C experiment was first retried with
`for (unsigned i = 0U; i <= 11U; ++i)` and a descending
`for (unsigned i = 12U; i >= 1U; --i)`. Both were accepted by the pinned
Clang frontend but rejected by the normalized JSON-to-typed adapter before
publishing guest code. Strict `<` and `>` were the only proven `for` bounds.

The bounded projector now admits `<=` and `>=` against an unsigned literal
bound, with canonical one-space comparison-token geometry independently
checked against Clang source spans. This rejects shortening an inclusive
operator in forged AST metadata while retaining the existing closed-source
provenance and exact counter identity checks. It supports ascending and
descending unary or bounded compound steps, checks each update against
unsigned underflow or the adapter's byte-range ceiling, and refuses any
thirteenth body iteration. Even zero-trip loops must have an admissible
body, and their speculative effects are discarded.

The complete ascending, descending and two-step inclusive C recurrence
variants have the same independent twelve-byte oracle as the strict source:
`02 19 1f 08 17 0f 02 0d 03 10 13 03`. Tests under
`tests/test_compound_c_pipeline.py` compile each entire variant to guest
Malbolge, compare normative VM stdout with empty and nonempty stdin, and
check source and AST mutation refusals. This is compile-time C state folding,
not runtime guest C induction. The original unmasked Fibonacci output is
still outside the bounded layout publisher, so the P0 remains open.

### Source-proven descending bounded induction

The full masked twelve-iteration Fibonacci C source was retried with
`for (unsigned i = 12U; i > 0U; --i)` after the bounded increasing-loop
projector rejected it at the first declaration. The adapter now checks a
strict typed `>` comparison and permits prefix/postfix `--` or literal `-=`
steps on the same unsigned induction symbol. It replays the actual counter
values with checked subtraction, rejects wraparound, and enforces a maximum
of twelve executed iterations rather than a numeric start limit. A zero-trip
body is still fully source-admitted on shadow state without retaining output.

The entire `--i` C recurrence reaches the normative Malbolge VM and emits
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 guest steps, agreeing with an
independently calculated unsigned-C oracle. `tests/test_compound_c_pipeline.py`
checks prefix/postfix decrement and a 24-to-zero two-step countdown against
both empty and nonempty stdin, plus unsafe step, wraparound, loop-bound,
source-symbol and forged Clang-AST mutations. These are **compile-time**
closed-state loops; guest runtime C induction and the unmodified twelve-byte
Fibonacci output remain unsupported.

### Bounded not-equal induction with exact-endpoint guest parity

The complete twelve-iteration masked Fibonacci C program was retried with
`for (unsigned i = 0U; i != 12U; ++i)` rather than a relational bound.
Pinned Clang accepted the whole C function, but the typed adapter rejected
its declaration before any guest publication. A red-first end-to-end test
confirmed the same refusal for descending `i != 0U; --i` and the positive
stride `i != 25U; i += 2U` from one.

The source-bounded projector now accepts `!=` with checked two-character
comparison-token spacing, source-tied induction symbol, discarded prefix,
postfix or bounded compound step, and an exact reachable endpoint. The step
operator determines direction; crossing the bound, `u8` underflow or overflow,
zero stride, wrong symbol, and more than twelve trips all refuse. Zero-trip
bodies are still proved on shadow state without publishing skipped output.
This is a finite **compile-time** projection of known C state, not a guest
implementation of dynamic comparison or induction.

`tests/test_compound_c_pipeline.py` verifies ascending, descending, and
stride-two whole-program variants against the independent twelve-byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` using the actual Malbolge guest VM,
with both empty and nonempty stdin. An ascending witness takes 47 VM steps.
A separate zero-trip `!=` full C program preserves a later three-step
`do-while` recurrence and emits only `0x41` on both guest inputs. Negative
C source and forged AST tests refuse without a guest artifact. The original
unmasked Fibonacci stream still has no admitted general guest layout; P0
remains pending on its generalized byte-stream and runtime-control goals.

### Two-level source-proven bounded induction

The complete twelve-output masked Fibonacci C program was first retried with
three outer `row` iterations and four inner `col` iterations. The pinned Clang
frontend accepted the nested `for` statements, but the JSON-to-typed adapter
refused the first declaration because the previous closed-flow projector
allowed only one active induction counter and no nested `for` body. No guest
artifact was published in that red-first experiment.

The bounded projector now permits exactly two lexical `for` levels, each with
its own source-proven unsigned induction, bound, step and symbol. It protects
**all** active counters from body assignments, preserves outer local state
across the inner loop, drops inner lexical declarations at each iteration,
and rechecks source/AST identity during every replay. Both loops retain the
existing checked 12-iteration ceiling; a third nested `for` refuses.

The complete 3-by-4 C recurrence now produces the independently calculated
`02 19 1f 08 17 0f 02 0d 03 10 13 03` through the actual normative VM on
empty and supplied input. An inner zero-trip variant validates the skipped
body on shadow state, discards its output effects and then emits only `0x41`
from a later C call in the real guest. Mutations that assign either active
counter, corrupt the skipped body, forge a Clang parent/step/symbol or add
a third loop nesting level refuse without publication. These are closed
compile-time C loops; the guest does not implement dynamic C induction,
and the unmodified unmasked Fibonacci stream still lacks a guest layout.
The generalized P0 remains open.

A further whole-C experiment removed the outer braces from the same 3-by-4
recurrence, so the outer `for` directly parents the inner `for`. Clang
accepted that ordinary source but the adapter first refused without a guest.
The bounded replay now accepts this **one** unbraced nested `for` body when
its parent, source span and exact final-child end are proven. It does not
invent a compound scope, admit arbitrary unbraced loop bodies, or relax the
two-level induction limit. The unchanged twelve-byte oracle reaches the real
guest VM in 47 steps under empty and binary stdin. A forbidden write to the
outer counter and three forged AST parent/tail mutations refuse without
publishing a guest. The unmasked Fibonacci layout remains unsupported.

### Direct unbraced conditionals as bounded loop bodies (2026-11-10)

Two full twelve-step masked Fibonacci C programs moved all state transfers,
branch-local `unsigned next` declarations and `putchar` outputs into the
selected arms of an `if/else` directly under a `for` or `while`. Both valid
programs were first rejected at the JSON adapter, before guest publication.
The `while` source increments its loop guard in either arm and rechecks the
predicate against updated state for each of the twelve iterations.

The bounded replay now accepts **one** source-checked direct `if` as the
entire unbraced body of either loop. The pinned Clang parent must be the
actual loop statement, and the conditional's source tail must end exactly
where the loop ends. Both branches are proven against the same incoming
state; only the selected branch's local writes and output are committed.
No brace scope is synthesized and no second direct sibling is admitted.
This extends the existing bounded compile-time state proof, not Malbolge
runtime branches, C storage or dynamic induction.

Both complete programs emit the independently derived masked Fibonacci bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` from the normative guest VM in
47 steps under empty and binary input. Five invalid C-source cases (a
condition side effect, a forbidden induction-counter write and unproved
`switch` effects) and nine forged AST ancestry, metadata and tail cases
fail without publishing guest code. The original twelve-output unmasked
Fibonacci C still lacks generalized guest layout; P0 remains pending.

### Unbraced `do/while` with conditional and nested `for` (2026-11-10)

The full twelve-step masked Fibonacci C recurrence was retried with an
ordinary `do` whose sole unbraced body is an `if/else`. Both branches declare
an iteration-local `unsigned next`, emit the selected byte, transfer the
recurrence state and increment the enclosing `i`. The trailing
`while (i < 12U);` is tested after every body execution. Pinned Clang
accepted the complete C program but the JSON adapter originally refused
its first local declaration, publishing no guest artifact.

The bounded replay now checks a single direct `if-statement` child of the
`do-statement`, with no invented compound scope. The next direct Clang
sibling must be its pure condition, after the complete conditional span;
its source tail must leave exactly the final semicolon. Source-parent,
span, metadata, local writes, branch effects and the twelve-trip bound
remain checked. As in braced `do/while`, the predicate is evaluated against
state updated by the selected branch, after the mandatory first body trip.

The real normative guest VM emits the independently derived byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under both empty and
binary stdin. Three invalid source variants (nonterminating induction,
side-effecting predicate and an unproved nested loop) and five forged AST
cases refuse without publishing guest artifacts. This remains finite
compile-time C-state replay; the original unmasked Fibonacci stream and
dynamic guest C loop execution still lack proof. P0 remains pending.

The same source proof now admits one direct bounded `for` as the entire
unbraced `do` body. A separate complete C Fibonacci program uses three
outer `do` trips, each executing four inner `for` trips. The inner loop's
source-checked `++outer` advances the trailing pure `outer < 12U` guard,
while each inner trip performs the real conditional output and recurrence
state transfer. Pinned Clang parents the inner `for` directly to `do`;
the parser does not synthesize any missing braces. The complete program
initially refused at the JSON adapter; after the repair, it emits the same
independent twelve-byte masked Fibonacci oracle from the normative guest
VM in 47 steps under empty and binary stdin. Three nonterminating or
impure C-source variants and five forged AST mutations reject before
publication. This proves finite source-C replay, not general nested guest
induction or unmasked byte-stream layout. P0 remains pending.

### Source-proven lexical scopes in loop bodies

A complete twelve-output masked Fibonacci C recurrence was first attempted
with an explicit compound scope inside its `for` body. The scope declares an
iteration-local `transfer` from `next`, then updates the enclosing `a` and
`b`. The pinned Clang frontend admitted the C program, but the typed adapter
refused the compound source node without publishing a guest artifact.

The bounded loop-body projector now walks up to four nested lexical compound
scopes with exact Clang parent and span evidence. It retains writes to
outer locals and selected `putchar` effects, drops each scope-local declaration
upon exit and reapplies that proof on every loop replay. The existing loop
iteration, statement, local-count and source-identity bounds still apply;
a fifth nested compound refuses. Skipped-loop shadow traversal also proves
every nested source expression before discarding speculative state and output.

The complete 12-effect C program has an independently calculated masked
Fibonacci oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03`.
`tests/test_compound_c_pipeline.py` exercises actual guest VM parity,
zero-trip preservation of a following `0x41` output, undefined division
inside skipped scopes, forged Clang parent/metadata and excessive nesting.
The original unmasked Fibonacci trace still lacks a general guest layout.
This is compile-time C state propagation, not runtime guest C block storage.
P0 therefore remains open.

### Selected unbraced `break` and `continue` in complete C recurrences

Two complete masked Fibonacci C programs extend the selected-control probe.
The first has three outer `for` trips and five inner trips per row, using
`if (col == 0U) continue; else { ... }`. The second admits six inner
counter values, but `if (col == 4U) break; else { ... }` stops each row
after four recurrence outputs. Both are ordinary, pinned-Clang C sources
with twelve stateful conditional `putchar` effects and the independent
expected byte sequence `02 19 1f 08 17 0f 02 0d 03 10 13 03`.

The original complete sources refused at the JSON adapter. The repaired
bounded projector allows source-proven unbraced `break`/`continue` as one
conditional arm, using its existing exact keyword/Clang-span proof. An
unselected control arm is replayed only on shadow state; the selected arm
carries the exit to the nearest `for`, which consumes `break` or advances
the induction step for `continue`. Other branch-local variables, state
transfers and effects remain source-checked. Both real guest capsules
emitted the independent twelve-byte oracle in 47 normative VM steps under
empty and binary stdin. Four invalid source variants and ten forged AST
keyword, parent, span and metadata cases refused artifact publication.
This does not add dynamic guest C control flow or the original
unmasked byte-stream witness; P0 remains open.

### Unbraced unsigned while updates before conditional output

A pinned-Clang complete twelve-trip Fibonacci source uses an unbraced
`while (parity < (next & 3U)) ++parity;` to calculate an unsigned
local that selects a following putchar branch. The bounded source
projector now admits a directly parented unary while body and replays
its checked writes and condition before each selected output.

The normalized Clang oracle and adapter regression verify twelve
independently source-proven typed output effects, yielding
`02 19 1f 08 17 0f 02 0d 03 10 13 03`, with malformed
statement ancestry, foreign references and kinds refused. The
complete guest compilation still reaches the unsolved literal-stream
layout synthesis without publishing an artifact in its search budget.
This is source-level static replay, not dynamically lowered guest
loop execution; the original unmasked Fibonacci blocker remains.

### Bounded negative reachability after expanded scratch relocation

The complete unmasked C recurrence still requires `02 59 5f` at its
start. After the previously VM-proven `02 59` source-scratch prefix, a
guest `*` write and two live `j` relocations yield a concrete 15-trit
accumulator and a pointer into loader-expanded memory. The bounded scalar
regression now searches up to twelve no-op/crazy/rotate/relocation steps
for the next byte, allowing zero to two further data relocations. For
each candidate length, four final source opcodes before halt independently
change the loader's two-cell recurrence seed. Exact accumulator words
and data-pointer locations remain distinct search states.

No explored fresh-expanded-word state produces `0x5f`. The graph allows
more paths than the admissible linker, but it assumes each arithmetic
operand retains its original loader word; guest-written operand revisits,
modified graphical scratch, and other source tail geometries are outside
this negative result. The existing `02 59 b9 b6` witness still proves two
real expanded-memory arithmetic effects in the normative VM with empty
and binary input. No source compiler capability is claimed, and the P0
remains unresolved.

### Exhaustive fresh graphical scratch reachability

The original full unmasked Fibonacci C source still needs the byte prefix
`02 59 5f`; the compiler continues to refuse at guest layout. A new finite
state-space experiment removes the twelve-instruction limit for a specific
single-forward-code-jump geometry. It starts with the phase-zero jump, varies
every subsequently read graphical scratch operand over all eight
loader-valid positional bytes, and retains the **full 15-trit accumulator**
and number of correctly emitted output effects at each data-pointer position.

`o`, `p`, `*`, `<`, and **any number** of strictly forward `j` data-pointer
relocations are included. Since D always increases, each operand is fresh and
the graph is acyclic; dynamic programming exhausts all 96,732 reachable
state/phase combinations for `02 59 5f` in this geometry. None emits the
third byte. As a positive control, `02 59 5d` is reachable, and a separately
admitted 109-cell source executes it in eleven normative VM instructions under
two binary-input conditions. The result is **not** an impossibility claim for
Malbolge or the full C program: backward/rewritten operand revisits, other
initial jump phases, additional code jumps and loader-expanded memory are not
part of this graph. General guest arithmetic and runtime C control remain P0
work, not a completed compiler capability.

### Mixed unsigned scalar and Boolean C conditions

A new complete twelve-iteration Fibonacci source combines a pure unsigned
bit expression with a nested `&&`/`||` condition. The normalized pinned
Clang AST previously refused the mixed `u32`/`i32` logical operands. Bounded
source-state replay now proves each operand, retains the original checked
Clang ancestry and C truth semantics, and admits the mixed shape in either
order. Two unsigned logical operands remain intentionally unsupported: an
untrusted normalized AST can otherwise forge a same-width `==` operator into
`&&` without distinguishable operand types.

The complete C compiler emits a real 47-step guest whose twelve binary
outputs are exactly `02 19 1f 08 17 0f 02 0d 03 10 13 03`, matching an
independent unsigned recurrence under both empty and nonempty VM input.
This capability extends compile-time C replay, not dynamic Malbolge guest
state. The original unmasked Fibonacci stream and P0 remain pending.

### Source-proven nested short-circuit subtrees (2026-11-11)

A complete twelve-iteration unsigned Fibonacci C program now nests a
Boolean `||` expression under an outer `&&`. The outer guard is false
on even recurrence terms, so the entire nested expression is skipped
including a division whose divisor would be zero. On odd terms, the
inner `||` selectively evaluates a defined division or skips it. The
pinned Clang frontend accepted the full C source, while bounded
source replay originally rejected it before producing a guest artifact.

The projector now authenticates both pure children of a wholly skipped
logical subtree without evaluating undefined C arithmetic. It retains
complete AST ancestry, checked operator metadata, source-ordered spans
and the existing ban on ambiguous two-unsigned logical children. A
limited expression-depth increase to twelve admits this composition;
unknown effects, selected zero division and malformed Clang trees still
refuse. This is **compile-time source replay**, not dynamic guest
short-circuit execution or arbitrary C expressions.

The independently calculated twelve-byte masked recurrence
`02 19 1f 08 17 0f 02 0d 03 10 13 03` matches the actual normative
Malbolge guest in 47 instructions with EOF and binary stdin. The
original unmasked Fibonacci output still has no generalized layout
witness, and the P0 remains open.

### Evolved source-scratch third byte (2026-11-12)

The original unmasked Fibonacci C source initially refused after three loop
iterations (`02 59 5f`) even though a hand-constructed source-independent
VM witness could produce the prefix. A bounded, byte-parameterized proposal
now reuses the genuine two-output source-scratch guest, rotates an untouched
skipped source word, relocates D back to it with a real `j`, and rotates the
modified word a second time. Fresh graphical operands supply the final
arithmetic and third output; neither byte is host-injected into guest stdout.

The independent publisher admits exactly one relocation after two outputs
and one repeated source write only when the relocated D revisits the earlier
written cell. Positional decode, source shadow, all write addresses and two
normative VM replays remain mandatory. The pinned three-trip complete C
program emits `02 59 5f` with EOF and binary stdin, while selected undefined
C arithmetic rejects and the original twelve-trip program still refuses
without publication. This search costs roughly two minutes through the full
pipeline; dynamic guest C control, longer full-width streams and faster
reusable block synthesis remain open.

### Mixed-byte dense source-revisit search (2026-11-14)

A red-first bounded search regression combined six output-progress counts
with every possible low accumulator byte and 65 distinct high-word
representatives. Prior per-progress quotas retained each class's minimum
and maximum full words but discarded its middle candidate `8195`.
With the same guest operand zero, a real `p` step maps the words
`3`, `8195`, and `16387` to distinct low bytes `50`, `93`,
and `223`. Therefore equality of a pending output byte does not justify
discarding this full-word continuation.

The bounded source-revisit beam now keeps an existing word nearest the
midpoint of each active progress/low-byte range in addition to its
extremes. Even the maximum nine progress counts and 256 byte groups use
at most 6,912 protected representatives, below the existing 16,384
state cap; unused capacity remains shared among progress counts. All
candidate sources still require independent positional/layout admission
and normative VM replay. The red-first regression, twelve-byte real
Fibonacci guest and canonical typed publisher pass; the pinned frontend
was unavailable, so no original full source-C pipeline parity or
generalized P0 acceptance is established.
