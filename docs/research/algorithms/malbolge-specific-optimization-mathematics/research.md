# Malbolge-specific optimization mathematics

## Status

Active

## Research Question

Does `malbolge-specific-optimization-mathematics` provide a reproducible
verified benefit over its declared baseline for the Malbolge compiler or
execution problem without weakening semantic correctness?

## Background

Derive algebraic decompositions, lookup-table factorizations, state reductions,
canonical forms, and lower bounds that reduce synthesis search before brute
force or stochastic optimization begins.

- Status: Active
- Research ID: `malbolge-specific-optimization-mathematics`
- Last reviewed: 2026-08-31

## Prior Work

- `../../../bibliography/publications/superoptimization/egg.md`

## Hypothesis

- H1: the proposed technique improves at least one preregistered objective under
  an equivalent resource budget while all accepted outputs pass the independent
  verifier.
- H0/rejection condition: the technique is unsound, cannot reproduce its result,
  or provides no meaningful advantage over the declared baseline on the admitted
  challenge distribution.

## Method

The executable mirror lives at
`algorithms/malbolge-specific-optimization-mathematics/`. Experiments use
versioned configuration, explicit seeds where stochastic behavior exists, fixed
resource budgets, parametric challenge identities, and the same verifier used
for baselines. Raw regenerable output stays in the mirror's Git-ignored `out/`.

## Evidence

Candidate generation, heuristics, models, and accelerators are untrusted. A
research result can compare quality or cost only after the trusted semantic
verifier accepts the candidate under the declared target profile.

- Derived canonical forms, factorizations, bounds, and algebraic reductions
  state applicability conditions and are benchmarked only after equivalence
  evidence is established.
- Definitions state domains and assumptions precisely; executable code cannot
  claim a mathematical reduction outside those stated preconditions.
- Every correctness-relevant equation or equivalence used by implementation has
  explicit domain assumptions and a traceable executable correspondence check.

## Results

The first verified reduction slice is positive for the existing CPU VM table
implementation.
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
`src/specification/formal-model/math/algorithms/malbolge-specific-optimization-mathematics.tex`
formalizes two hundred eight exact reductions: classic five-trit crazy
factorization,
general profile-width crazy chunking, exact parametric five-trit padding and
uniform chunk factorization, exact checked profile-width projection laws and
output/rotate-
compatible word counts, monotone source admission and exact initial-memory
projection across checked widths, exact decode compatibility and self-
encryption invariance, exact input projection and graphical-fetch mismatch
counts, a finite lockstep certificate theorem, a minimum-certified-width
selector, exact decode sum-class
canonicalization,
classic rotate
lookup, graphical self-encryption orbit canonicalization,
classic rotate-history canonicalization, exact classic rotate minimal-period
partition, exact crazy-target preimage cardinality, constructive mixed-radix
preimage rank/unrank through width 14, exact one-trit Gray traversal of
preimage hypercubes, exact `2^k-1` minimum aggregate trit-edit cost for
bijective complete traversal, exact binary-cube one-trit neighborhood
structure, exact coordinate-permutation quotient into `k+1` Hamming-weight
classes, exact ordered cube-word pair quotient into `C(k+3,3)` joint-count
classes, exact ordered cube-word triple quotient into `C(k+7,7)` joint-count
classes, exact endpoint-unordered triple quotient under `S_3` with dense
rank/unrank, exact ordered cube-word quadruple quotient into `C(k+15,15)`
joint-count classes, exact
endpoint-unordered quadruple quotient under `S_4` with dense rank/unrank, exact
ordered cube-word
quintuple quotient into `C(k+31,31)` joint-count classes, exact endpoint-
unordered quintuple quotient under `S_5`, exact ordered sextuple quotient into
`C(k+63,63)` classes, exact endpoint-unordered sextuple quotient under `S_6`
with a mathematical
mass-fifteen Burnside/Young-stratum extension and stabilizer-type stability
theorem, plus a six-vertex-pair/eleven-Young-stabilizer residual factorization,
trivial-stabilizer distinct-vertex dense rank/unrank, order-two and order-six
Young-stabilizer dense rank/unrank, V4 and S3-times-S2 Young-stabilizer dense
rank/unrank, an exact nested S4 vertex-bundle/K4-edge factorization for the
`(4,1,1)` stratum with complete dense rank/unrank composed across all five
second-layer stabilizers, an exact `(5,1)` nested S5 factorization with dense
trivial, S2, S3, S4, V4, and S3-times-S2 second-layer rank/unrank plus an
exact widened full-S5 edge hard-core count and stabilizer-order spectrum plus
dense rank/unrank for five bounded symmetric strata, scalable disjoint-V4
quotient/exact rank/unrank, scalable single-transposition S3 quotient,
normalizer-free, and exact ranks,
and exact count plus quotient/exact rank/unrank for the double-transposition
V4 type plus ordered-pattern/strict-color trivial-stabilizer rank/unrank,
low-mass D10/full-S5 ranks, and complete eleven-stratum full-S5 rank/unrank,
where the S4 branch has
complete dense spoke rank/unrank across all five stabilizers and their combined
residual interval, an exact nested S2-cubed quotient/fixed-set decomposition,
and dense stabilizer-chain rank/unrank plus dense S3-times-S3 Young-stratum
rank/unrank, an exact S4-first S4-times-S2 descended-swap decomposition, and
dense hard-block-first S4-times-S2 Young-stratum rank/unrank, and an exact
rooted-S5/full-S6 deficit decomposition plus an exact 56-conjugacy-class S6
subgroup-lattice stabilizer spectrum plus dense exact full-S6-stabilizer
rank/unrank plus dense exact point-stabilizer S5 rank/unrank plus a dense
normalizer-free single-transposition S4-quotient rank plus a compact-frontier
dense exact-transposition rank/unrank plus dense exact double-transposition
rank/unrank with S3(3,3)/D10 sparse exclusions plus dense exact S2-times-S2
rank/unrank with S3-times-S2/S3-times-S3 sparse exclusions plus dense exact
triple-transposition rank/unrank with 217 transitive-S3 exclusions plus dense
exact three-pair-V4 rank/unrank with no external exceptions plus dense rooted-S5
trivial-stabilizer rank/unrank plus an exact unique-minimum rooted selector for
full-S6 trivial classes plus an exact pair-trivial K6-edge factor covering over
three quarters of the mass-fourteen free stratum plus dense pair-transposition,
pair-S2-times-S2, pair-double-transposition, pair-three-pair-V4, pair-S3,
pair-triple-transposition, pair-C2-cubed, pair-S3-times-S2, pair-order16-42,
pair-S4-times-S2, pair-D8-42, pair-C2-cubed-42, pair-V4-42, and
pair-S3-times-S3, pair-S4-411, pair-transitive-order48, pair-D8-411,
pair-diagonal-S3-33, pair-D10-51, pair-full-S6-breaking, and
pair-transitive-S3-6 K6-edge/
triple-breaking branches, an exact
S3-extension/S4-exception count decomposition plus an exact S4-extension/point-
S5-exception count decomposition,
dense exact-S4 and exact-S3 rank/unrank, and an exact repeated-six
exact-transposition outer composition for the remaining all-equal stratum,
a generic
checked-arity ordered tuple quotient into
`C(k+2^m-1,2^m-1)` classes for `1<=m<=8`, a dense combinadic rank/unrank over
those classes, a generic endpoint-unordered Burnside quotient under `S_m` for
`1<=m<=8`, exact combined coordinate/endpoint orbit masses, endpoint-minimized
canonical integer keys, exact ordered and endpoint-unordered canonical-search
budget exceedance and inverse coverage laws, a finite candidate-local binary-
verifier call lower bound plus checked tuple substitution and exact all-pair
aggregation, an exact binary-decision-tree information lower bound plus checked
tuple substitution, exact global ordered and endpoint-
unordered checked-arity
transforms, exact global ordered-triple and endpoint-unordered triple quotient
counts with dense global S3 rank/unrank, exact global ordered-quadruple and
endpoint-unordered quadruple
quotient counts, exact ordered-quintuple and endpoint-unordered quintuple
quotient counts with dense global S5 rank/unrank, exact ordered and endpoint-
unordered sextuple quotient counts across all reachable fixed pairs, exact
endpoint-symmetric pair quotient with
`(C(k+3,3)+floor((k+2)^2/4))/2` classes, dense local rank/unrank, and dense
global ragged-domain rank/unrank, plus exact binomial distance
shells/balls, diameter, and shortest-path
lower bounds/counts plus fixed-radius covering lower bounds, perfect
radius-one Hamming covers, the exact checked perfect-partition dimensions, and
the complete nontrivial perfect-radius partition classification, the tight
classic 1,024-preimage global
bound, the exact zero-or-power-of-two preimage spectrum,
the accumulator-specific `2^(10-n2(a))` worst-target bound, and the exact
`2^(10-n2(a))*3^n2(a)` reachable-target count, the exact checked-width fixed-
accumulator target distribution `C(N-m,k)*3^m` over preimage class `2^k`, and
the exact `C(10,k)*2^(10-k)` cardinality of accumulator class `k`, the exact
`7^10`
count of reachable accumulator/target pairs, and the exact
`C(10,k)*2^k*5^(10-k)` count of pairs in preimage class `2^k`, the exact
profile-width `C(N,k)*2^k*5^(N-k)` distribution for `1<=N<=14`, the exact
base-seven canonical rank/unrank over all `7^N` reachable pairs, the exact
reachable-pair mean preimage size `(9/7)^N`, exact second moment `(13/7)^N`
and variance `(13/7)^N-(9/7)^(2N)`, the exact Binomial(N, 2/7) law for
`log2` preimage cardinality with mean `2N/7` and variance `10N/49`, the exact
`9^10-7^10 = 3,204,309,152` unreachable-pair count, its exact `9^N-7^N`
generalization for `1<=N<=14`, and the exact classic threshold
sum for reachable pairs whose full preimage set exceeds a nonnegative
enumeration budget, its exact width-indexed generalization for `1<=N<=14`, and
the exact minimum complete-preimage budget needed to cover any integer target
from 0 through `7^N` reachable pairs across the same checked widths.
The canonical semantic-width model is now parametric. For every `N>=10`, set
`P_N=5*ceil(N/5)`. Zero-padding only the final partial `crazy` chunk adds
exactly `C_N=(3^P_N-3^N)/2` because every added zero/zero trit maps to one.

Therefore `Crazy_P_N(d,a) mod 3^N` equals native `Crazy_N(d,a)` exactly. N15
has `P_N=N` and no padding; N16 starts a fourth five-trit chunk.

With `B=243`, the same result is `ceil(N/5)` invocations of one five-trit table,
weighted by successive powers of B and reduced modulo `3^N`. Exhaustive
final-chunk evidence covers all five residual classes; representative whole-word
fixtures include N15, N16, N20, N31, and N37. The N31 check already exceeds
u32 geometry, demonstrating that backend integer limits are not mathematical
semantic-width limits. This is arithmetic equivalence only and makes no
performance claim.


The product runtime now has a value-level `ChunkedProfileWord` realization of
this construction. Its radix, minimum width, chunk width, chunk cardinality, and
unbounded maximum marker are generated from `malbolge.json`; no second `5` or
`243` authority is maintained in the word contract. N10--N20 compatibility is
checked against the existing `u32` primitives, and independent trit-vector
oracles cover crazy/rotate through N100. Chunked successor performs exact
`3^N` wraparound without materializing that modulus, while small-modulus residue
supports decode modulo 94 and byte output modulo 256 directly from the chunks.

The nine possible ternary recurrence states `(older, previous)` are exhaustively
checked: after the first transition each lies on a cycle of length 2 or 3, so
the complete state repeats after six transitions. `recurrence_cell` therefore
needs only a positive transition count modulo 6, even for an N100 word.

The optional `u32` bridge is value-exact rather than width-based: N21 zero can
narrow to `u32`, while N21 EOF cannot. The representation does not prove
scalable memory addressing. Registers,
pointers, resident wire, and state-applying backends remain `u32`-bounded while
the chunked word is introduced independently as the required value primitive.

This remains a state-equivalence result, not a timing claim.

For checked width pairs `10<=N<M<=14`, radix projection preserves pointer
successor and `crazy`, but `rotate` has an explicit quotient-dependent high
trit. The rotate condition is exactly equality between trit `N` and trit zero,
so different candidate widths can alternate between compatible and incompatible.
Byte output is equal only when the discarded high quotient is zero; wide EOF
projects to narrow EOF while their output bytes still differ. Thus source size
or low addresses alone cannot prove semantic narrowing.

For each checked `N<M`, byte output agrees with width-N projection for exactly
`3^N` of the `3^M` wide words: precisely those with zero discarded quotient.
These sets are nested as N decreases, unlike rotate compatibility. This is an
output-primitive classification only, not a whole-program narrowing proof.

Checked source admission is monotone in width because lexical and decode rules
are unchanged while memory capacity grows from `3^N` to `3^M`. After a source
is admitted at both widths, every cell in the complete narrow initial memory is
exactly the wide initial-memory cell projected modulo `3^N`; the recurrence
proof is induction through the already proved `crazy` projection law.

For graphical execution, decode compatibility is stricter than pointer
projection: because `XLAT1` is injective and `3^N` is coprime to 94, the wide
and narrow decodes agree exactly when the wide code pointer already lies below
`3^N`. Self-encryption itself is width-invariant on the shared graphical byte
domain, but the certificate must still prove that both states select the same
graphical encryption target.

Input assignment projects exactly for every byte and for EOF, although a later
output of the projected EOF remains width-sensitive. Fetch classification has a
precise asymmetric failure set: for width pair `N<M`, exactly
`94*(3^(M-N)-1)` wide words are non-graphical while projecting to a graphical
narrow word. Reachable instances of that set must be excluded by a narrowing
certificate because they change immediate termination behavior.

At width 14, requiring rotate compatibility for any selected candidate-width
set `S` leaves exactly `3^(14-|S|)` words. One candidate therefore admits one
third of the word domain; requiring all widths 10 through 13 leaves exactly
59,049 words, or one eighty-first of the domain. This is a primitive
compatibility classification only, not a program-width certificate.

A finite width certificate is sufficient when it covers every declared input
initial state, preserves every verifier-required observation, and closes every
related nonterminal state under one lockstep transition or matching terminal
outcome. Induction over committed transitions then gives observational
equivalence for the finite certified relation. This theorem defines a
fail-closed proof shape; no concrete program or product selector is certified
by it yet.

The experimental checker retains strict JSON schema v1 as structural relation
evidence and adds schema v2 for exact subject binding. V2 carries a proof kind,
source bytes, exact input streams, widths, named observations, finite systems,
and their relation. The retained `QP` v2 fixture binds those bytes explicitly,
while an independent Rust VM test proves complete 14-to-10 projection before
and after the halt.

Positive research selection also receives the externally requested source and
input domain. A v2 certificate can authorize only that byte-exact subject, and
its proof kind must be recognized and checked; legacy v1, a bare boolean `true`,
missing decisions, subject drift, or width drift all retain that certificate
reference width. The published fixtures use N14; the selector no longer treats
that value as a language maximum.

A theorem-specific checker independently certifies initial-halt sources from
checked widths, source capacity/admission, position-dependent decode, and a
first `v`; halt then precedes I/O, encryption, pointer advancement, or other
transition effects. Its decisions are exhaustively cross-checked against the
independent verifier decode model over all graphical cells and all 94 phases.
`QP` remains the retained positive fixture.

A second recognized proof kind certifies a nonempty prefix of decoded `o`
instructions followed by `v`. No-op preserves A and I/O, performs the same
width-independent graphical encryption at the same low address, and advances
C/D equally, so the complete projected state is preserved inductively until
halt. `DP` is the minimum retained certificate; an eight-no-op fixture checks
that induction step-by-step in both endpoint-width VMs.

Input followed directly by halt is also certifiable for both byte and EOF input.
Byte assignment is identical at both widths, and the all-two-trit EOF words are
related by exact projection; the following encryption and pointer advance are
shared. The `uP` fixture checks both lineages and preserves their distinct input
consumption observations.

Input followed by output and halt is certifiable only for exact input domains
whose declared streams are all nonempty. The consumed byte is then identical
across widths and therefore produces the same output; EOF remains projected in
A but has width-dependent byte residue. The `ubO` fixture retains the positive
byte domain and a VM counterexample where EOF diverges exactly at output.

The compositional straight-line checker subsumes those small cases for programs
whose decoded prefix uses `o`, `/`, `<`, one guarded `j`, and guarded `p` before
`v`. It tracks input position and whether A is byte-exact; output is legal only
in that exact state.
Independent bounded composition checks every length-one-through-four prefix over
`o`, `/`, `<`, and at most one `j`, for stream lengths zero through two using
source encodings reconstructed from verifier decode. Repeated data jumps use a
separate exact-address relation instead of being inferred from that bounded
oracle.

D is tracked as either one exact physical address or projection-only. A jump
from exact D preserves projection, while `initial_memory_word` compares concrete
N/14 cell values to decide whether successor D stays exact.

This accepts `jjjv` because cells 41 and 43 are numerically equal at widths 10
and 14.

The derived-width selector remains research-only: no compiler, runtime, or
optimizer module imports it. Product integration must follow the existing trust
boundary in which untrusted optimization evidence is independently admitted. A
derived width may parameterize execution geometry only after that admission; it
must not replace the canonical profile ID, version, fingerprint, or semantic
requirement.

The product VM independently admits narrow proof families rather than importing
that selector. Its initial-halt verifier reuses the canonical profile
loader/decode boundary and issues an opaque source/profile-bound geometry.
Malformed, oversized, or out-of-range subjects fail closed.

The second product verifier accepts a nonempty decoded no-op prefix followed by
halt. DP selects N=10 and executes with 59,049 words through one no-op and halt;
QP is rejected by this family because its prefix is empty, while `DC` is
rejected
because no reached halt follows its admitted no-op prefix.

A third product verifier accepts input followed directly by halt without binding
a particular input stream. `uP` selects N=10 for both byte and EOF execution:
byte `0xA5` leaves A exact and consumes one byte, while EOF leaves A at 59,048
and consumes none. Both lineages halt after two normative steps with no output.
All product proof-family minimum selectors share one policy that advances only
after exact derived `SourceTooLong` rejection.

Input/output/halt requires a stronger authority because EOF is not byte-stable
across widths. The product verifier proves `/ < v` for the universal minimum
input length one and stores that restriction inside the otherwise opaque
execution token. `ubO` selects N=10 for eligible streams and emits their first
byte exactly; EOF machine construction fails before execution. Checkpoint
construction enforces the same hidden token policy.

The product straight-line I/O verifier extends only over `o`, `/`, and `<`
before `v`; it does not import the research checker's jump/crazy state machine.
It counts encountered inputs and raises the token's minimum input length
whenever
an output depends on that ordinal. `uCar_L` therefore selects N=10 with a
two-byte minimum and emits both bytes in six steps, while a one-byte stream is
rejected before load.

A separate product theorem covers only one initial data jump followed by halt.
In `(P`, D=0 reads raw source cell 40, and successor 41 is below every reviewed
modulus. The shared XLAT2 encryption is width-independent, C advances to 1, and
the following `v` halts before using D again.

Repeated jumps now have a separate trusted recurrence checker. It reconstructs
only each reached initial-memory word with the product crazy primitive at both N
and the current N15 reference, preserves D only on numeric equality, and
rejects reads of
already encrypted source code. `('&N` selects N=10 through three exact jumps.
Both `('O` and the projected-D crazy fixture `('<AM` fail at D=41 because their
second jump is projection-only, so the latter never gains trusted crazy-write
authority.

Guarded crazy now covers `j p+ v`. `(=O` and `(=<N` first establish exact D=41,
then retain separate candidate/canonical accumulators across each crazy step.
Every D is advanced without wrap, every write is outside current/future source
code, the canonical initial word must reduce to the N-word, and each canonical
crazy result must reduce to the candidate result. This admits both fixtures at
N=10 without strengthening projection into false equality; unguarded `>P` is
rejected by shape.

A separate product composition proves that byte input can restore exact A after
guarded crazy. The admitted form is `j p+ / < v`: all `p` transitions first
preserve projection at exact D, then non-EOF `/` overwrites both accumulators
with the same byte before `<`. `(=s`M` (`j p / < v`) and `(=<r_L`
(`j p p / < v`) both select N=10 and emit the recovered byte. Their proof tokens
require at least one input byte, so EOF fails before machine construction. The
product verifier independently admits this recovery shape at each reviewed
geometry N=10 through 15.

Within that initial-halt family, product-side minimum selection tries N=10
through the current N15 reference and advances only on exact derived-capacity
failure. QP selects N=10, while a valid 59,050-word initial-halt source selects
N=11. A verified N=10 artifact still retains the canonical N15
`malbolge-2026` requirement and is explicitly unequal to the historical profile
identity.

The live machine and checkpoint now carry a separate opaque execution geometry.
Memory length/domain, modulus/trits, EOF, pointer wrap, and crazy/rotate
arithmetic consume that geometry, while canonical profile identity, opcode
assignment, non-graphical policy, trace identity, and preflight stay unchanged.
`ProfileMachine::from_verified_source` takes source only from the proof
envelope;
QP therefore executes with exactly 59,049 N=10 words, halts in one normative
step, and retains N=10 through checkpoint restore while remaining
`malbolge-2026`.

Indexed state-graph now carries the same opaque geometry in
lineage identity and digest material, and derived QP/N=10 trace replay
materializes the exact runtime checkpoint without restoring N=14. Tiered/native
execution remains canonical-only. Handoff rejects a derived checkpoint before
interpreter fallback. Portable IR v1 also rejects a derived trace before it can
be
promoted to direct-native authority.

The indexed-state path also preserves nontrivial hidden input authority. A
`uCar_L` N=10 machine admitted with minimum input length two is advanced through
five traced effects, including both inputs and outputs, then materialized back
to
the exact runtime checkpoint and geometry token. This proves that indexed
lineage
state preserves the minimum-two premise rather than collapsing it to nonempty.

Optional batch completion validation compares the complete opaque geometry
token.
This includes hidden input-domain authority: `uP` and `ubO` have identical
visible
N=10 geometry/profile values, but a checkpoint from the former cannot satisfy a
request admitted by the latter. The mismatch falls back to the original
safe-Rust
machine rather than treating numeric geometry as sufficient authorization.

The CUDA integration now consumes resident geometry from prepared backend
requests instead of `current_profile()` constants. For every reviewed N=10
through 15, one homogeneous batch covers QP, EOF
input-halt, `uCar_L`, guarded `p p`, crazy
followed by byte-input recovery, and projection-verified rotate, with complete
state compared against safe Rust.

The MBPRN2 byte schema and synchronous process transport are now product Rust
boundaries. An application bridge projects prepared requests to the pure
resident wire transport and reattaches VM authority after transport. Homogeneous
batches are encoded centrally; the process adapter bounds stdout by complete
resident memory plus the maximum step-derived output.

Response framing is decoded fail-closed. The contract intentionally omits hidden
verifier authority. Product completion conversion reattaches the original
admitted token and returns no completion for malformed metadata or invalid
reconstructed state.

Mixed resident widths fail before process launch. The top-level CLI now supplies
separate opt-in controls for trusted adaptive construction and current-profile
resident workers. The worker receives the geometry already admitted by the
selected machine, including derived N10 when adaptive proof succeeds. Live RTX
4060 checks exercise this composition boundary; they establish correctness, not
throughput.

Both checked-in current capsules carry `ubO` with empty input, so the existing
`MinimumLength(1)` proof correctly cannot replace their canonical EOF-visible
execution with N=10.

Product selection now composes the supported theorem families without importing
research evidence. `select_minimum_verified_profile_width` retains only
successful trusted artifacts that are strictly narrower than the canonical
profile and whose hidden input policy admits the exact input.
`ProfileMachine::from_adaptive_source` uses that artifact when construction
succeeds and otherwise returns to canonical `from_source`. QP/empty and
`ubO`/byte input select N=10, while `ubO`/empty remains N=14.

The CLI now exposes this selection as an explicit current-profile policy rather
than changing the default. With `MALBOLGE_PROFILE_ADAPTIVE_WIDTH=1`, QP/empty
reaches the resident wire as N10; with `0`, the same capsule reaches it as N15.
The checked-in `ubO`/EOF capsule remains N15 even when adaptive selection is
enabled. A temporary RTX 4060 check completed QP/N10 through the same CLI,
process transport, MBPRN2, and CUDA adapter path.

A conservative rotate theorem is now product-owned. `(&O` decodes `j * v`; the
initial jump fixes D=41 exactly, and the rotate target lies outside the loaded
source. The verifier independently reconstructs the candidate and canonical
initial words at D, checks ordinary memory projection, computes both width-
specific rotates, and requires the canonical rotate to project before permitting
the physical write. This succeeds for every reviewed N=10 through 15 and the
minimum selector chooses N10.

Rotate is not treated as monotone. The dedicated minimum selector may continue
after `JumpRotateProjection` (or capacity) but still fails immediately on
lexical, decode, or geometry errors. `(CB$M` decodes `j o o * v` and is a
retained
negative: every narrower reviewed width fails rotate projection and only N15
admits, so the composite adaptive selector returns no narrower token.

Jump-code now has a repeated source-backed exact-address theorem. Initial `i`
reads D=0, and every committed code jump advances D exactly without candidate
wrap. Each data read is taken from a mutable shadow of loaded source. The
resulting C, its self-encryption target, and the successor reached after commit
must all remain inside that shadow.

XLAT2 is width-independent, so the verifier mutates the same shadow cell that
the
runtime will encrypt. This is required for later jumps that observe earlier
self-modification. The retained strong fixture reaches `i@0`, `i@99`, `i@39`,
and then `i@38` before `v@79`; cell 38 originally decodes `j`, but the second
jump encrypts it from 96 to 60, which then decodes `i` at C=38. Complete N10
memory and registers project to N15 after the five-step execution.

The proof does not infer exactness from recurrence projection. A data read,
encryption target, or successor outside loaded source returns
`JumpCodeProjection`; D wrap is rejected for the same reason. Short code-jump
sources and chains that leave the source therefore stay canonical under the
composite selector.

There is also a structural barrier for the initial recurrence-backed code
target.
For every N=10 through 14, assume one N15 recurrence word is numerically equal
to its N-width projection; all discarded high trits are then zero. In the next
recurrence step those zero trits occupy the accumulator side of `crazy`.

The normative crazy table has no zero result when the accumulator trit is zero.
Enumerating all `3^(15-N)` possible high parts of the previous data word
confirms
that the successor always regains a nonzero discarded trit. Thus a recurrence-
backed initial `i` cannot have both its encryption target and following C exact,
which justifies the product theorem remaining source-backed rather than merely
being a conservative implementation omission.

Indexed-state evidence now advances all four N10 code jumps and materializes the
checkpoint. The materialized state exactly equals the runtime snapshot,
preserves the opaque geometry token, records all four physical self-encryption
deltas at targets 98, 38, 37, and 78, retains the encrypted `i` decode at cell
38, and finishes the prefix at exact C=79/D=4.

A separate jump-code/rotate theorem continues from that exact C=79/D=4 prefix.
Unlike the earlier `j o* * v` theorem, its rotate target is deliberately inside
loaded source. The verifier therefore reads D from the exact mutated source
shadow, rejects D=C or D=C+1, checks both D and C successors without wrap, and
requires the N15 rotate result to project to the candidate result before the
physical write.

The retained positive sets source[4] to `$` (36), for which rotate is exactly 12
at every N=10 through 15. N10 writes 12 to source[4], self-encrypts the reached
rotate cell at C=79, and halts at C=80 with D=5/A=12; complete memory and
registers project to N15. The negative uses `^` (94): derived widths fail rotate
projection, the specialized minimum verifier reaches only N15, and the composite
selector preserves canonical execution.

Retained post-push evidence required CUDA use for N10 through N14 with this
source-write family included. The current N15 product route independently
requires `used_cuda=true`. The adaptive CLI N10 fixture also
reached `CudaProfileRunAdapter.evaluate` before its marker was written. These
are
full-state/deployment correctness observations, not retained performance
samples.

Rotate projection now also composes with byte recovery. `(CB$q^K` decodes
`j o o * / < v`; the exact jump/no-op prefix reaches D=43 outside the source.
At N10 the rotate writes and loads A=29,517, while canonical N15 reaches
7,174,446. Those values are not numerically equal, but the canonical value
projects exactly to N10.

`JumpRotateIoHaltProjection` now accepts one or more reached `/ <` pairs and
records `MinimumLength(k)` from their exact count. The one-pair fixture remains
the projection witness above. A separate four-pair source verifies at every
reviewed width and selects N10 with `MinimumLength(4)`; three-byte input is
rejected, while `[0xA5,0x3C,0x7F,0x00]` is consumed and emitted exactly.

The longer source changes the recurrence feeding D=43, so its projected rotate
is rechecked rather than inherited from the one-pair case. For the four-pair
fixture N10 writes 29,512 at address 43 and N15 writes 7,174,441. Indexed-state
evidence retains that projected write, cursor 4, all four output bytes, A=0, and
C=12/D=52 across twelve committed effects.

Length compatibility is deliberately non-monotone: the otherwise-valid two-pair
source fails narrower rotate projection and reaches only N15, while the
four-pair source succeeds again. `JUMP_ROTATE_IO_UNSAFE` (`j * / < v`) remains
a distinct
projection negative. The CLI supplies no profile input, so the four-pair source
stays canonical N15 and emits four canonical EOF bytes `0x6A`.

Rotate projection also composes directly with guarded crazy writes, without an
input reset. `(&<;:9K` decodes `j * p p p p v`. The rotate uses exact D=41 but
produces A=29,529 at N10 and A=7,174,458 at N15; those values are numerically
different and project exactly.

The four following `p` transitions keep exact physical D=42..45 and
independently
check each recurrence data word plus crazy result. Their N10 writes are 67,
29,538, 49, and 29,538; canonical N15 writes 67, 7,174,467, 49, and
7,174,467.
Thus the chain alternates exact and merely projected accumulators while complete
memory/register projection remains intact. Indexed-state materialization after
six effects matches the runtime checkpoint at exact C=6/D=46.

The specialized minimum selector only widens around source capacity or an
explicit rotate-projection miss. A guarded-crazy failure after a successful
rotate is fail-closed, matching the existing conservative crazy policy rather
than searching wider widths around missing semantic evidence.

Retained post-push evidence required CUDA use at N10 through N14 with this
multi-write family included. The current N15 product route independently
requires `used_cuda=true`. A separate adaptive CLI run reached
`CudaProfileRunAdapter.evaluate` as N10; its marker was written only after the
CUDA evaluation returned. These are deployment/full-state correctness checks,
not retained throughput measurements.

The same exact prefix now composes with byte-visible I/O in a separate theorem.
`JumpCodeIoHaltProjection` accepts one or more reached `/ <` pairs before halt.
Each non-EOF input overwrites A with the same exact value at N10 and N15, the
following `<` emits that byte, and both ordinary instructions self-encrypt the
same source cells. The token records `MinimumLength(k)` for the exact number of
reached inputs.

A retained two-pair fixture therefore requires two bytes. With
`[0xA5,0x3C]`, the nine-step N10 execution consumes both bytes and emits both
bytes,
and preserves complete memory/register projection. One-byte input is rejected
before load and composite selection returns no narrow token, because the second
input would become width-sensitive EOF before output. Indexed-state evidence
preserves `MinimumLength(2)`, cursor 2, and both output bytes across the first
eight committed effects.

Wire homogeneity is intentionally weaker than verifier authority equality. `uP`
and `ubO` share the same N=10 resident shape and can execute in one CUDA worker
batch, while each returned checkpoint is reconstructed with its original opaque
geometry token. Exact differential comparison includes that token, so the shared
kernel shape cannot collapse `Any` into `MinimumLength(1)` or vice versa.

The derived CUDA differential is no longer limited to immediate halt. One N=10
worker batch now covers initial halt, no-op, EOF input, byte I/O, two-byte
straight-line I/O, repeated jump, guarded crazy, crazy followed by byte-input
recovery, rotate, rotate followed by guarded crazy, rotate followed by byte
recovery/output, source-backed code jump, source-backed code jump followed by
byte input/output, and source-backed code jump followed by rotate. Complete
memory and state equality against safe Rust
remains the oracle; this is semantic correctness evidence rather than
performance
evidence.

`uCar_L` adds a six-transition bound certificate. A `j j p o v` counterexample
shows why projected D is insufficient for writes: both crazy transitions
continue and A still projects, but D names different physical cells, so the
memory relation breaks.

Guarded crazy steps are accepted only after the exact-address jump has separated
D from C, while the resulting D stays in-domain and avoids future source code.
`j p v` and `j p p v` preserve complete endpoint projection; unguarded `p v`
rejects before commit because the crazy result becomes a non-graphical
self-encryption target. Crazy also marks A projection-only, so output requires a
later exact byte input before it can be certified again.

The published N14 certificate is rechecked independently for candidate widths
10 through 13. Each candidate can be the sole accepted width and is selected
exactly; explicit rejection of all four retains that N14 evidence reference
without monotonic inference. Widths 11 through 13 are represented only as
derived execution geometry, never as invented canonical profile identities.

The selector now takes its finite reference width explicitly. Its theorem
helpers and initial-memory reconstruction have no N14 ceiling: direct evidence
checks N15, N20, and N31. Missing or malformed decisions retain the supplied
reference, so each narrower geometry remains an independent proof obligation
without turning any finite certificate width into a language maximum.

The preserved historical decode table is a permutation of all 94 graphical
bytes. Exhausting all 8,836 graphical cell/code-phase pairs therefore proves
that `(cell-33+phase) mod 94` is a complete decode key: the pairs partition into
94 exact classes of size 94. This quotient applies only where the decoded opcode
is the observable; it does not erase raw cell or code-pointer identity needed by
later machine semantics.
The encryption
table is proved to partition the complete
graphical domain into cycles of lengths 2, 4, 5, 6, 9, and 68, so repeated
committed encryption of an otherwise unchanged code cell needs only the visit

residue modulo its cycle length. Repeated rotate updates to one otherwise
unchanged classic ten-trit data cell admit the exact word-specific period
classes 1, 2, 5, and 10, containing 3, 6, 240, and 58,800 words respectively.
Search may therefore retain visits modulo the exact minimal period rather than
always modulo ten. For fixed classic
crazy accumulator/target words, the exact full-data-domain preimage count is the
product of the ten per-trit multiplicities. For checked widths one through 14,
the ordered local inverse sets also give a constructive mixed-radix rank/unrank
bijection over exactly the complete-domain preimages, so a complete enumerator

does not need to test unrelated data words. The doubleton positions are also
exact binary coordinates: binary-reflected Gray order traverses all compatible
words exactly once and changes one trit between consecutive candidates. This
hypercube result is checked against every reachable pair through width four,
every width-14 ambiguity mask, and the complete 16,384-word maximal cube. Any
bijective traversal of `2^k` distinct preimages has `2^k-1` transitions and
therefore costs at least `2^k-1` trit edits; Gray order attains that bound
exactly. The same coordinates identify the one-trit mutation graph with
`Q_k`: every preimage has exactly `k` valid one-trit neighbors, and the graph

has `k*2^(k-1)` edges when `k>0` (zero when `k=0`). These are exact
complete-domain graph/edit identities, not wall-clock lower bounds.

The full coordinate-permutation action also has an exact quotient: two cube
words share an orbit exactly when they have the same Hamming weight, giving
`k+1` classes with sizes `C(k,j)` and canonical representatives `1^j0^(k-j)`.
Transport through the fixed-pair cube isomorphism preserves those abstract
choice orbits. This quotient applies only to analyses invariant under arbitrary
ambiguity-coordinate relabeling, not to position-sensitive Malbolge semantics.

For ordered cube-word pairs, simultaneous coordinate permutation has an exact
four-count refinement. The joint coordinate counts `n00`, `n01`, `n10`, and
`n11` classify each orbit completely, giving `C(k+3,3)` classes with exact
factorial quotient orbit sizes. Grouping coordinates as `11,10,01,00`
constructs a canonical representative that agrees with the existing
single-word canonical form on fixed-zero and diagonal slices. Equivalently, left
weight, right weight, and pair distance form a complete orbit key.

This ordered-pair quotient applies only to analyses invariant under simultaneous
ambiguity-coordinate relabeling.

The same simultaneous coordinate action classifies ordered triples by their
eight joint bit pattern counts. There are exactly `C(k+7,7)` classes, with
multinomial orbit sizes; sorting patterns in descending binary order preserves
the existing pair and single-word canonical representatives on zero slices. At
`k=14`, this is 116,280 classes instead of 4,398,046,511,104 raw triples.
Exhaustive abstract evidence reaches dimension four, class arithmetic reaches
dimension fourteen, and all reachable fixed-pair lifts through width four pass.

If triple endpoint order is also irrelevant, `S_3` acts on the eight joint-
pattern labels. Burnside gives
`(C(k+7,7)+3*tau_k+2*chi_k)/6`, where `tau_k` and `chi_k` count classes fixed
by one endpoint transposition and one endpoint three-cycle. At `k=14`, this is
21,323 classes instead of 116,280 coordinate-only ordered classes or
4,398,046,511,104 raw triples.

The same quotient now has a dense index: retain `n000`/`n111`, sort the three
complementary `(weight1,weight2)` count pairs, and rank their finite multiset by
exact suffix-block counts. Every class roundtrips through dimension fourteen,
while raw endpoint invariance is exhaustive through dimension four. No timing
claim is made.

Ordered quadruples under the same simultaneous coordinate action have sixteen
joint bit-pattern counts and exactly `C(k+15,15)` classes. At `k=14`, that is
77,558,760 canonical classes instead of 72,057,594,037,927,936 raw quadruples;
the descending binary convention reduces exactly to the triple representative
when the fourth word is zero. Exhaustive orbit evidence reaches dimension four,
while recurrence arithmetic and compatibility checks reach dimension fourteen.

If quadruple endpoint order is also irrelevant, `S_4` acts on the sixteen
joint-pattern labels. Its five endpoint conjugacy classes induce label-cycle
types `1^16`, `1^8 2^4`, `1^4 2^6`, `1^4 3^4`, and `1^2 2 4^3`, so Burnside
uses fixed-class weights `1,6,3,8,6`. At `k=14`, the five fixed counts are
77,558,760, 722,696, 43,472, 5,256, and 308, giving 3,419,552 endpoint-
unordered classes.

A dense S4 index now interprets the remaining counts as a weighted K4: four
sorted singleton/complement vertex-count pairs and six weight-two edge counts.
Only permutations inside equal vertex-pair blocks remain, so finite edge-orbit
tables under that residual stabilizer give exact rank/unrank blocks. Canonical
states are exhaustive through dimension four, ranks through dimension six, and
checked boundary/interior roundtrips through dimension fourteen. No timing
claim is made.

Ordered quintuples under the same action have thirty-two joint bit-pattern
counts and exactly `C(k+31,31)` classes. At `k=14`, that is 166,871,334,960
canonical classes instead of 1,180,591,620,717,411,303,424 raw quintuples; the
zero-fifth-word slice reduces exactly to the ordered-quadruple convention.
Exhaustive orbit evidence reaches dimension four, recurrence arithmetic reaches
dimension fourteen, and fixed-pair lifting reaches width three.

If quintuple endpoint order is irrelevant, `S_5` acts on the thirty-two joint-
pattern labels. Its seven endpoint conjugacy classes have weights
`1,10,20,15,30,20,24`; their induced label-cycle types give 1,426,354,541
endpoint-unordered classes at `k=14`. A finer factorization keeps fixed
`00000`/`11111` counts, sorts five singleton/complement vertex-count pairs, and
Burnside-counts ten complementary edge-count pairs under the residual equal-
vertex stabilizer.

For an order-two stabilizer, four edges are fixed while three edge pairs swap
together; treating those swaps as one unordered pair of six-component
compositions gives exact dense residual rank/unrank through mass fourteen. For
an order-six `S_3` stabilizer, one edge is fixed and the remaining edges form
three six-component bundles permuted together; multiset ranking gives another
exact dense residual index through mass fourteen.

For an order-four `S_2 x S_2` stabilizer, nested commuting-involution arithmetic
first gives exact first-quotient, second-fixed, and final residual counts. A
fixed/nonfixed factorization of the descended second involution then gives exact
dense rank/unrank through mass fourteen; the final mass-14 domain has
205,482,000 classes.

For an order-twelve `S_3 x S_2` stabilizer, quotienting the three-vertex block
first and averaging its commuting `S_2` coset gives exact
first-quotient, descended-fixed, and final residual counts. A nondecreasing
three-bundle mass partition plus fixed/nonfixed involution blocks for distinct,
two-equal, and all-equal masses gives exact dense rank/unrank through mass
fourteen; the final mass-14 domain has 68,763,298 classes.

For the order-24 `S_4` stabilizer, sorting the four spoke count-pairs leaves one
of five Young stabilizers of orders `1,2,4,6,24` acting on the six pair-valued
K4 edges; that factorization reproduces all 34,507,258 mass-14 classes. The
`2+1+1` spoke shape has a dense shared-involution edge rank with 2,235,960
mass-14 classes. The `2+2` spoke shape is a row/column V4 quotient with a dense
1,125,240-class mass-14 edge rank. The `3+1` spoke shape is a weighted multiset
of three four-scalar bundles and has 750,160 mass-14 classes.

In the all-equal-spoke stratum, three opposite-edge blocks reduce full S4 to
even V4 flip parity plus S3 block permutation, giving a dense 191,180-class
edge-only rank at mass 14. The trivial distinct-spoke shape uses ordinary
composition ranking; lexicographically prefixing all five spoke shapes now gives
one dense 34,507,258-class order-24 residual rank at mass 14.

The order-120 all-equal-vertex hard core has seven exact conjugacy-cycle types
and 6,962,786 mass-14 edge classes. Exact inversion of all 156 S5 subgroups
shows that 6,689,862 classes have trivial stabilizer; eight nontrivial subgroup
types contain the other 272,924 classes. Rooted-view multiplicity is exactly
automorphism vertex-orbit multiplicity, and the same strata reconstruct the
34,507,258 rooted classes.

Every nontrivial type now has dense rank/unrank. The single-transposition type
filters a 261,450-class weighted S3 normalizer quotient to 239,656 exact-H
classes. The other seven types use the same generic weighted H-edge-orbit,
normalizer-canonicalization, exact-stabilizer-filter, and prefix/select
construction; their mass-14 retained counts sum to 33,268.

The remaining 6,689,862 trivial-stabilizer classes now use the unique
lexicographically minimum rooted S4 view of each free S5 orbit, followed by
prefix/select ranking. Thus every order-120 mass-14 class now belongs to a dense
local rank stratum.

Ordered sextuples have sixty-four joint-pattern counts and exactly
`C(k+63,63)` coordinate classes, or 839,983,521,106,400 at `k=14`. Adding the
S₆ endpoint action yields eleven conjugacy classes and 1,179,940,653,635
endpoint-unordered classes. Sorting the six weight-1/5 complement pair-values
leaves one of eleven Young stabilizers on 52 residual scalar labels; summing
those residual quotients exactly reproduces the full S6 Burnside sequence
through Q14.

The all-distinct vertex-pair stratum has trivial Young stabilizer, so a vertex-
sequence prefix plus 52-part weak-composition rank densely indexes 99,892,279
mass-14 classes. The `(2,1,1,1,1)` vertex multiplicity stratum leaves one
coupled residual involution with 24 fixed scalars and 14 swapped pairs. Its
dense rank covers another 8,308,559,181 mass-14 classes.

The `(3,1,1,1)` stratum reduces to 10 fixed scalars and a multiset of three
14-component vectors; its dense rank covers 89,182,770,767 mass-14 classes. The
remaining eight
nontrivial Young stabilizer strata stay unranked, and no timing claim is made.

Combining that quotient with the exact ambiguity-class distribution gives a
closed global representative count. Width `N` has
`sum_k C(N,k)2^k5^(N-k)C(k+7,7)` canonical ordered preimage triples, equal to
`sum_{j=0}^{min(7,N)} C(7,j)C(N,j)2^j7^(N-j)`. At `N=14`, this is
547,751,638,341,145 representatives instead of 3,243,919,932,521,508,681 raw
ordered triples. This is an exact complete-domain cardinality result only.

Summing the endpoint-unordered triple quotient over the same fixed-pair
distribution gives 124,279,218,052,677 canonical triples at `N=14`. Burnside's
three global fixed counts are 547,751,638,341,145 for the identity,
61,437,730,689,609 for a transposition, and 6,805,238,953,045 for a three-cycle.
Independent width-1-through-4 pair enumeration and transformed generating
functions verify the aggregate through width fourteen; this is a cardinality
result only.

The analogous ordered-quadruple sum is
`sum_k C(N,k)2^k5^(N-k)C(k+15,15)`, equal to
`sum_{j=0}^{min(15,N)} C(15,j)C(N,j)2^j7^(N-j)`. At `N=14`, this is
25,678,405,217,633,865 representatives instead of
9,012,061,295,995,008,299,689 raw ordered quadruples. This is likewise an
exact complete-domain cardinality result only.

Summing the endpoint-unordered quadruple quotient over the same fixed-pair
distribution gives 1,409,733,897,288,413 canonical quadruples at `N=14`.
Burnside's five global fixed counts are 25,678,405,217,633,865,
1,182,834,266,824,809, 180,742,210,147,993, 57,110,313,884,289, and
9,848,929,136,817. The base-seven reachable-pair order composes with the local
dense S4 rank by ambiguity-weighted suffix blocks, giving dense global
rank/unrank through width fourteen. This is exact state accounting under both
stated symmetry actions, not a timing claim.

The ordered-quintuple aggregate is
`sum_k C(N,k)2^k5^(N-k)C(k+31,31)`, equal to
`sum_{j=0}^{min(31,N)} C(31,j)C(N,j)2^j7^(N-j)`. At `N=14`, this is
3,571,359,808,057,227,945 representatives instead of
55,448,176,762,342,779,635,202,921 raw ordered quintuples. This is likewise an
exact complete-domain cardinality result only.

Summing the endpoint-unordered quintuple quotient over the same fixed-pair
distribution gives 34,995,940,605,821,849 canonical quintuples at `N=14`.
The seven global fixed counts are obtained independently by the generic
binomial transform of each endpoint label-cycle generating function. Direct
ambiguity summation, transformed coefficients through width fourteen, and
independent all-pair enumeration through width two agree.

The complete dense local S5 rank now lifts through canonical base-seven
reachable-pair order; ragged-domain enumeration through width four and checked
roundtrips through width fourteen give one dense global interval of
34,995,940,605,821,849 ranks. This is a cardinality and canonical-ranking result
only.

The ordered-sextuple aggregate has 1,584,315,319,509,725,541,225 canonical
representatives at `N=14`, while the endpoint-unordered S₆ aggregate has
2,361,488,883,978,006,005. Both are compared against
`133^14 = 541,904,769,658,563,069,794,308,330,729` raw ordered sextuple cases.
Independent width-1-through-2 pair enumeration, weighted-binomial arithmetic,
and the generic endpoint-cycle transform agree through width fourteen; these
are cardinality results only.

For pair analyses that are also invariant under endpoint swap, the ordered-pair
quotient reduces further. Endpoint swap exchanges `n01` and `n10`; classes with
`n01=n10` are fixed, while every other class pairs with a distinct swapped
class. The exact class count is
`(C(k+3,3)+floor((k+2)^2/4))/2`, giving 372 classes at `k=14`.

Summed over all reachable width-14 fixed pairs, the endpoint-symmetric
quotient has
18,096,618,233,793 representatives instead of 3,937,376,385,699,289 raw
ordered pairs. The parity correction follows from the swap-fixed count and
`(5-2)^N=3^N`; this is an exact complete-domain cardinality result only.
The base-seven reachable-pair order also composes with the local dense pair rank
through ambiguity-weighted suffix block sums, yielding a dense global
`0..E_N-1` rank/unrank. Exhaustive global enumeration reaches width four and
boundary/midpoint roundtrips reach width fourteen.

Orienting the larger Hamming-weight endpoint first gives a canonical key
`(max(wx,wy),min(wx,wy),d)`. The oriented joint counts also have a dense rank:
residual block sizes are `floor((s+2)^2/4)`, and the within-block prefix before
`n01=b` is `b*(s-b+2)`. Exhaustive rank/unrank covers every class through
`k=14` and every raw pair through `k=8`. This refinement applies only when
endpoint order is irrelevant; direction-sensitive analyses retain the ordered-
pair quotient.

Moreover, from any compatible word the exact distance-`j` shell has `C(k,j)`
words, a
radius-`r` ball has `sum_{j=0}^r C(k,j)`, and the cube diameter is exactly `k`.
For endpoints at trit distance `j`, every in-cube one-trit mutation path needs
at least `j` steps, and exactly `j!` shortest paths attain that lower bound.
For radius `r`, any complete cover by centered search balls needs at least
`ceil(2^k / sum_{j=0}^r C(k,j))` centers by volume; overlap may force more, so

this is not claimed as an exact covering number. The caveat is witnessed
exactly by `Q5` at radius one: the volume bound is six while exhaustive
all-906,192 six-center coverage testing plus a seven-center witness proves
minimum seven. For ambiguity dimensions `k=1,3,7`, binary Hamming syndromes
construct exact perfect radius-one covers with minimum center counts `1,2,16`;
every compatible preimage maps canonically to its unique center within one trit.

Conversely, a disjoint radius-one partition requires `k+1` to divide `2^k`, so
through dimension 14 only those same three positive dimensions are possible.
This converse classifies perfect partitions only, not overlapping covers that
may attain a ceiling volume bound.

Across all nontrivial radii `1<=r<k<=14`, exact ball-volume divisibility leaves
precisely `(3,1)`, `(5,2)`, `(7,1)`, `(7,3)`, `(9,4)`, `(11,5)`, and `(13,6)`.
The radius-one Q7 Hamming partition supplies `(7,1)`; every other survivor is
the odd-dimensional antipodal partition at radius `(k-1)/2`, with exactly two
centers. Thus every divisibility survivor has an explicit perfect partition.

The existing all-one target under
accumulator zero therefore has exactly 1,024 data-word preimages, while a zero
target under accumulator zero has none. Exhausting all 59,049 accumulator words
through an independent trit relation proves no fixed classic accumulator/target

pair can exceed 1,024 preimages, so that known case attains the global bound.
The same exhaustive accumulator spectrum proves every nonzero full-domain count
is one of `1,2,4,...,1024`, and every listed power plus zero is attainable. For
each fixed accumulator, an independently constructed maximizing target attains
exactly `2^(10-n2(a))`, where `n2(a)` counts accumulator trits equal to two.
The same state admits exactly `2^(10-n2(a))*3^n2(a)` target words with at
least one complete-domain preimage. Across checked widths `1<=N<=14`, a fixed
accumulator with `m` trits equal to two has exactly `C(N-m,k)*3^m` reachable
targets in preimage class `2^k`; summing recovers the reachable-target count and

preimage-weighting recovers all `3^N` data words. The optimizer exposes both
classic state-level quantities from the normative trit table and exhaustively
checks them against an
independent relation. The optimizer also exposes all eleven accumulator classes;
their counts match both a complete 59,049-word histogram and the binomial
closed form. Summing reachable targets across all accumulator states and
weighting the same eleven classes both yield `7^10 = 282,475,249` reachable
accumulator/target pairs, matching the independent per-trit product. The full
pair distribution has exactly `C(10,k)*2^k*5^(10-k)` members with `2^k`
preimages; its class sum is `7^10`, while weighting by preimage size gives

`59,049^2`, accounting for every classic `(data, accumulator)` input pair. The
same independent trit convolution now checks every width 1 through 14 against
`C(N,k)*2^k*5^(N-k)`, with class sum `7^N` and weighted sum `9^N`.
The seven reachable local accumulator/target symbols also lift to an exact
base-seven rank/unrank bijection over the full `7^N` reachable-pair domain. A
complete reachable-pair enumeration can therefore use canonical codes
`0..7^N-1` without visiting an impossible pair; distinct reachable pairs remain
distinct.
The complement `9^10-7^10 = 3,204,309,152` is therefore globally impossible

before any data-word enumeration. Summing preimage classes above a supplied
budget gives an exact planning lower bound for complete preimage enumeration:
budget 0 exceeds all `7^10` reachable pairs, while budget 1,024 exceeds none.
Inverting the same ordered classes gives the least integer complete-preimage
budget for every requested reachable-pair coverage target at widths 1 through
14; the threshold is always zero for zero coverage or one exact power of two.
This lower bound does not apply to search procedures that do not promise
complete preimage enumeration. Sharing these planning cardinalities does not
imply

general semantic equivalence between accumulator/target pairs.

`src/specification/formal-model/math/specification/correspondence.toml` binds
those equations to exhaustive or composite executable evidence. The classic
crazy/rotate finite domains are checked exhaustively; decode is checked across
all 8,836 graphical cell/phase pairs and its historical table is independently
proved injective; current N15 crazy chunking is checked against scalar
fixtures and real profile execution; and the
self-encryption result independently partitions all 94 graphical cells, checks
every table transition against the VM-owned encryption helper, and then checks
two full independent visits of every orbit for the modular reduction.

The existing versioned benchmark at
`benchmarks/interpreter/evidence/2026-07-26-windows-x86_64/` supplies 15 raw
samples per scalar/table implementation with matching checksums. On that
recorded
host/workload, crazy improved from a 77,456,700 ns scalar median to 7,423,600 ns
(10.43x), and rotate improved from 15,260,300 ns to 10,141,700 ns (1.50x).
These timing results support H1 only for the admitted CPU table-factorization
slice. The self-encryption/rotate-history and exact rotate-period reductions,
crazy preimage count, constructive preimage ranking, exact Gray traversal,
exact Gray edit optimality, exact preimage-cube neighborhood graph, exact
coordinate-permutation cube quotient, exact ordered cube-word pair quotient,
exact ordered cube-word triple, quadruple, and quintuple quotients, exact
endpoint-unordered triple quotient, exact global ordered-triple, ordered-
quadruple, and ordered-quintuple quotient
counts, exact endpoint-symmetric pair quotient, dense local/global rank/unrank,
and its global aggregate, and exact preimage-cube distance
shells/balls, exact mutation geodesics, fixed-radius
covering lower bounds, perfect radius-one Hamming covers, exact checked
perfect-partition dimensions, complete checked perfect-radius classification,
global preimage bound,
discrete preimage spectrum, accumulator-specific
worst-target bound, reachable-target count, fixed-accumulator target preimage
distribution, accumulator-class partition, global reachable-pair count,
classic/profile-width preimage-pair distributions and constructive reachable-
pair ranking, profile-width mean/variance preimage evidence, the exact
Binomial(N, 2/7)
log-preimage exponent law, classic/profile-width unreachable-pair counts,
classic/profile-width preimage-budget exceedance, exact minimum-coverage budget
bounds, ordered/endpoint-unordered canonical-search budget laws, and the
candidate-local binary-verifier lower bounds, all-reachable-pair aggregation,
and binary-decision-tree information bounds are correctness-proved search
reductions, not
measured performance results. None
of these results establishes a universal speedup or proves broader synthesis

lower bounds.

## Threats to Validity

Initial threats include challenge-family bias, hardware/toolchain sensitivity,
search-seed variance, verifier bounds, and overfitting to small Malbolge blocks.
Each experiment must narrow these threats before drawing a conclusion.

## Conclusion

Retain the four proved table/factorization reductions plus the exact
self-encryption, classic rotate-history canonicalization, exact rotate minimal-
period canonicalization, crazy-target preimage cardinality, constructive
preimage rank/unrank, exact preimage-hypercube Gray traversal, edit
optimality, exact one-trit cube neighborhood graph, exact coordinate-
permutation cube quotient, exact ordered cube-word pair quotient, exact
ordered cube-word triple, quadruple, quintuple, and sextuple quotients, the
generic ordered tuple quotient through checked arity eight, its dense
quotient-class rank/unrank, the generic endpoint-unordered quotient from arity
one through eight and exact combined orbit masses and canonical integer keys
through checked arity eight,
exact ordered and endpoint-unordered canonical-search budget exceedance and
inverse coverage laws, the finite candidate-local binary-verifier call lower
bound, tuple specialization, all-reachable-pair aggregation, binary-decision-
tree information lower bound and tuple specialization, and both global checked-
arity transforms, exact endpoint-
unordered triple, quadruple, quintuple, and sextuple quotients, including the
S6 vertex-pair/Young-stabilizer factorization, plus the
established
triple/quadruple global aggregates, dense global unordered-triple and
unordered-quadruple rank/unrank, the generic ambiguity-indexed global
ragged-domain lift, the quintuple global aggregate with dense global S5
rank/unrank, and both sextuple global
aggregates, exact
global ordered-triple and ordered-quadruple
quotient counts, exact endpoint-symmetric pair quotient and dense local/global
rank/unrank,
and
exact binomial distance shells/balls,
diameter,
exact mutation geodesics, fixed-radius
covering lower bounds, perfect radius-one Hamming covers, exact checked
perfect-partition dimensions, complete checked perfect-radius classification,
tight 1,024-
preimage bound, discrete
cardinality spectrum,
accumulator-specific worst-target bound, reachable-target count, exact
fixed-accumulator target preimage distribution, fixed-accumulator budget
exceedance, exact accumulator-class
partition, global reachable-pair count, exact classic and
profile-width preimage-pair distributions, constructive reachable-pair ranking,
exact profile-width mean/variance
preimage evidence, the exact Binomial(N, 2/7) log-preimage exponent law, exact
classic/profile-width unreachable-pair counts, and
exact
classic/profile-width preimage-budget exceedance bounds, exact profile-width
minimum coverage budgets, ordered/endpoint-unordered canonical-search budget
laws, the candidate-local binary-verifier local/global lower bounds, and the
binary-decision-tree information bounds as valid optimization building blocks.
Continue the research for broader canonical forms, synthesis lower bounds
outside the proved binary-question models, and search-space
reductions; those remain unproved and receive no performance claim from this
result.

## References

- [Malbolge 1998 specification and reference interpreter][malbolge-1998]
- [Verification Trust
  Boundary](../../../technical/adr/verification-trust-boundary.md)
- [Research Evidence And Algorithm
  Mirror](../../adr/research-evidence-and-algorithm-mirror.md)

[malbolge-1998]:
  ../../../bibliography/specifications-and-standards/malbolge/malbolge-1998.md
