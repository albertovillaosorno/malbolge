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
- Last reviewed: 2026-08-11

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
formalizes fifty-nine exact reductions: classic five-trit crazy factorization,
general profile-width crazy chunking, exact zero-padded 15-trit crazy
projection and uniform three-lookup factorization for semantic widths 10
through 14, exact decode sum-class
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
classes, exact endpoint-unordered triple quotient under `S_3`, exact ordered
cube-word quadruple quotient into `C(k+15,15)` joint-count classes, exact
endpoint-unordered quadruple quotient under `S_4`, exact ordered cube-word
quintuple quotient into `C(k+31,31)` joint-count classes, exact endpoint-
unordered quintuple quotient under `S_5`, exact ordered sextuple quotient into
`C(k+63,63)` classes, exact endpoint-unordered sextuple quotient under `S_6`,
exact global ordered-triple and endpoint-unordered triple
quotient counts, exact global ordered-quadruple and endpoint-unordered quadruple
quotient counts, exact ordered-quintuple and endpoint-unordered quintuple
quotient counts, exact ordered and endpoint-unordered sextuple quotient counts
across all reachable fixed pairs, exact
endpoint-symmetric pair quotient with
`(C(k+3,3)+floor((k+2)^2/4))/2` classes, plus exact binomial distance
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
For semantic widths `10<=N<=14`, zero-padding both `crazy` operands to fifteen
physical trits adds exactly `C_N=(3^15-3^N)/2` to the output because every
added zero/zero trit maps to one. Therefore `Crazy_15(d,a) mod 3^N` equals the
native `Crazy_N(d,a)` exactly. Exhaustive residual-tail evidence covers every
possible third-chunk operand pair at each admitted width; this is an arithmetic
equivalence only and makes no performance claim.

The same projection yields a fixed physical factorization at those widths. With
`B=243`, split each operand into two complete five-trit chunks plus one residual
tail. Three invocations of the same five-trit table, weighted by `1`, `B`, and
`B^2` and reduced modulo `3^N`, reproduce native `Crazy_N` exactly. Existing
exhaustive table evidence owns the two complete chunks; the padded evidence
exhausts every third-chunk pair and mixed assembly fixtures.

This remains a state-equivalence result, not a timing claim.

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
4,398,046,511,104 raw triples. Exhaustive raw orbits and fixed-pair lifting
reach dimension/width four, count-vector arithmetic reaches dimension fourteen,
and no timing claim is made.

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
unordered classes. Exhaustive raw orbits and fixed-pair lifting reach
dimension/width three, Burnside arithmetic reaches dimension fourteen, and no
timing claim is made.

Ordered quintuples under the same action have thirty-two joint bit-pattern
counts and exactly `C(k+31,31)` classes. At `k=14`, that is 166,871,334,960
canonical classes instead of 1,180,591,620,717,411,303,424 raw quintuples; the
zero-fifth-word slice reduces exactly to the ordered-quadruple convention.
Exhaustive orbit evidence reaches dimension four, recurrence arithmetic reaches
dimension fourteen, and fixed-pair lifting reaches width three.

If quintuple endpoint order is irrelevant, `S_5` acts on the thirty-two joint-
pattern labels. Its seven endpoint conjugacy classes have weights
`1,10,20,15,30,20,24`; their induced label-cycle types give 1,426,354,541
endpoint-unordered classes at `k=14`. Exhaustive raw orbits reach dimension two,
fixed-pair lifting reaches width two, Burnside arithmetic reaches dimension
fourteen, and no timing claim is made.

Ordered sextuples have sixty-four joint-pattern counts and exactly
`C(k+63,63)` coordinate classes, or 839,983,521,106,400 at `k=14`. Adding the
S₆ endpoint action yields eleven conjugacy classes and 1,179,940,653,635
endpoint-unordered classes. Coordinate-quotient orbits are exhausted through Q2,
fixed-pair lifting reaches width two, Burnside arithmetic reaches Q14, and no
timing claim is made.

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
9,848,929,136,817. Independent width-1-through-3 pair enumeration and
transformed generating functions verify the aggregate through width fourteen;
this is a
cardinality result only.

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
independent all-pair enumeration through width two agree; this is a cardinality
result only.

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

Orienting the larger Hamming-weight endpoint first gives a canonical key
`(max(wx,wy),min(wx,wy),d)`. This refinement applies only when endpoint order is
irrelevant; direction-sensitive analyses retain the ordered-pair quotient.

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
proved injective; current 14-trit crazy
chunking is checked against scalar fixtures and real profile execution; and the
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
counts, exact endpoint-symmetric pair quotient and its global aggregate, and
exact preimage-cube distance
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
and classic/profile-width preimage-budget exceedance plus exact minimum-coverage
budget bounds are correctness-proved search
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
ordered cube-word triple, quadruple, quintuple, and sextuple quotients, exact
endpoint-unordered triple, quadruple, quintuple, and sextuple quotients, plus
the
established
triple/quadruple global aggregates, the quintuple global aggregate, and both
sextuple global aggregates, exact global ordered-triple and ordered-quadruple
quotient counts, exact endpoint-
symmetric pair quotient,
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
classic/profile-width preimage-budget exceedance bounds, and exact
profile-width minimum coverage budgets as valid optimization building blocks.
Continue the research for broader canonical forms, universal synthesis lower
bounds, and search-space
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
