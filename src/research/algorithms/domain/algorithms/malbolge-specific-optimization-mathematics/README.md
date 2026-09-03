# Malbolge-specific optimization mathematics

This directory is the executable mirror for research ID
`malbolge-specific-optimization-mathematics`. The human research record uses the
same ID under `docs/research/algorithms/`, and its mathematical contract, when
present, uses the same ID under `math/algorithms/`.

Implementations in Rust, C, CUDA, Python, or another justified language live
together here because the algorithm, not the language, owns the research.
Regenerable results belong in `out/` and remain Git ignored.

The active first experiment studies exact CPU VM table/factorization reductions.
Its versioned configuration is `experiment.toml`; raw performance evidence lives
under `benchmarks/interpreter/evidence/2026-07-26-windows-x86_64/`, while
semantic acceptance is owned by
`src/specification/formal-model/math/specification/correspondence.toml`.

The profile-width crazy factorization is parametric for every semantic width
`N>=10`. Let `P_N=5*ceil(N/5)`. Only the final partial five-trit chunk is
zero-padded to `P_N`; padding adds the exact constant
`(3^P_N-3^N)/2`, so reducing modulo `3^N` recovers native crazy semantics
without enlarging semantic memory. This is an arithmetic identity, not a timing
claim.

Equivalently, every admitted width uses `ceil(N/5)` invocations of the same
243-by-243 five-trit table. N14 is `5+5+4`, N15 is `5+5+5`, N16 is
`5+5+5+1`, and the rule continues without a mathematical maximum. The final
lookup alone is zero-padded when N is not divisible by five; semantic memory
remains exactly `3^N`.

Checked width projection is not uniformly semantic. Successor and `crazy`
commute with radix projection, while `rotate` and byte output have exact
additional conditions. Output compatibility from width `M` to `N` holds for
exactly the embedded `3^N` low words and is nested across narrower widths.

Source admission is likewise monotone across checked widths when the lexical
and decode contract is unchanged. Once admitted, the complete width-N initial
memory equals the projected prefix of width M because source cells agree and
the fill recurrence preserves projection by induction.

Graphical decode agrees across projected pointers only when the wide code
pointer already lies inside the narrow address domain. Once both executions
select the same graphical encryption target, the `XLAT2` transformation itself
is width-invariant because its input and output remain graphical bytes.

Input assignment also projects exactly, including EOF. Graphical fetch
classification does not: high-quotient wide words whose narrow residue is one
of the 94 graphical bytes terminate only in the wide execution, so a certificate
must rule those states out.

Rotate compatibility checks trit `N` against trit zero and is not monotone
across candidate widths; even projected EOF values can later emit different
bytes. For any subset of candidate widths 10 through 13, each additional
rotate-compatibility constraint removes exactly two thirds of the 14-trit word
domain; all four together leave 59,049 compatible words.

A finite lockstep relation with initial coverage, observation equality, and
transition closure is therefore the admitted sufficient certificate shape. No
program-width selector is promoted by this research result alone.

The reusable research implementation is `algorithms.profile_width.certificate`.
It remains experimental and has no runtime or trusted-verifier authority.

For the published N14 certificate set, independently verified candidate widths
10 through 13 use 14 as that evidence set's fail-closed reference. The selector
now accepts an explicit reference width instead of treating N14 as a semantic
maximum. Missing certificate results therefore cannot narrow execution, and no
monotonicity assumption is made between candidate widths.

The current research surface also exposes an exact classic crazy-target
full-domain preimage count. Its product-of-per-trit-multiplicities equation and
the derived tight 1,024-preimage global ceiling, exact zero-or-power-of-two
cardinality spectrum, accumulator-specific `2^(10-n2(a))` worst-target bound,
exact `2^(10-n2(a))*3^n2(a)` reachable-target count, and
`C(10,k)*2^(10-k)` accumulator-class cardinality, the exact `7^10`
reachable accumulator/target-pair count, and the exact
`C(10,k)*2^k*5^(10-k)` nonzero preimage-pair distribution and exact
`9^10-7^10` unreachable-pair count are registered in the mathematical
correspondence manifest; all are correctness/search-bound results,
not benchmark-derived speedup claims. The optimizer exposes both state-level
counts, the complete eleven-class accumulator partition, the global
reachable-pair count, all eleven nonzero preimage-pair classes, and the exact
unreachable complement directly from the normative trit table. The checked
width family also admits an exact inverse planning bound: for any requested
reachable-pair coverage target, the minimum complete-preimage enumeration budget
is zero or the first power-of-two class whose cumulative count reaches it.
Classic rotate history also has an exact per-word canonical refinement: minimal

periods are 1, 2, 5, or 10 with exact class sizes 3, 6, 240, and 58,800.
The reachable crazy pair domain also has a constructive base-seven canonical
index: each reachable per-trit accumulator/target pair is one of seven symbols,
so checked width `N` ranks bijectively into `0..7^N-1`.

The classic decode reduction is exact at the opcode boundary: preserved `xlat1`
is a 94-byte permutation, so all 8,836 graphical cell/phase pairs quotient into
94 equal classes keyed by `(cell-33+phase) mod 94`. This does not canonicalize
whole machine states whose later semantics still need cell or pointer identity.

Reachable fixed crazy pairs also admit a constructive full-domain inverse: each
local inverse set has radix one or two, so mixed-radix rank/unrank enumerates
exactly the `2^k` preimages for checked width `N<=14` without scanning the other
`3^N-2^k` data words. The `k` doubleton positions form an exact binary
hypercube, so binary-reflected Gray order visits every compatible word exactly
once while changing one trit between consecutive candidates. Among bijective
complete traversals, this also attains the exact minimum aggregate trit-edit
cost `2^k-1`. The same cube coordinates give the exact one-trit mutation graph:
every preimage has degree `k`, with `k*2^(k-1)` total edges for `k>0` and zero
for `k=0`.

Coordinate-symmetric single-word analyses quotient these cubes into `k+1`
Hamming-weight classes; the same simultaneous coordinate action quotients
ordered cube-word pairs into `C(k+3,3)` joint-count classes with exact orbit
sizes while preserving endpoint direction. Ordered triples under the same
coordinate action have `C(k+7,7)` exact joint-count classes, or 116,280 at
`k=14`; if triple endpoint order is irrelevant, the additional `S_3` quotient
has exactly 21,323 classes. Its dense rank keeps the fixed `000`/`111` counts,
sorts three complementary weight-one/weight-two count pairs, and uses exact
finite suffix-block counts for rank/unrank through dimension fourteen.

Summed over every reachable width-14 fixed pair, that endpoint-unordered triple
quotient has 124,279,218,052,677 canonical classes. The same base-seven digit
DP used for pair ranking composes with the local S3 rank, giving dense global
rank/unrank across exactly those classes through width fourteen.

Ordered quadruples have `C(k+15,15)` classes, or 77,558,760; if quadruple
endpoint order is irrelevant, the additional `S_4` quotient has exactly
3,419,552 classes. A dense local index sorts four singleton/complement vertex-
count pairs and then ranks the six weighted-K4 edges under the residual equal-
vertex stabilizer. Its block totals reproduce Burnside through dimension 14.

Summed over every reachable width-14 fixed pair, that endpoint-unordered
quadruple quotient has 1,409,733,897,288,413 canonical classes. The base-seven
reachable-pair DP composes with the local S4 rank, giving dense global
rank/unrank across exactly those classes through width fourteen.

The same construction is generic: any finite local quotient family whose class
identity depends only on ambiguity dimension can be lifted once it supplies an
exact dense local rank. Independent synthetic enumeration proves the ragged
block partition, and S2, S3, and S4 specializations reproduce their exact
width-14 global totals. The theorem does not supply a missing local dense rank.

Ordered quintuples have `C(k+31,31)` classes, or 166,871,334,960; if quintuple
endpoint order is irrelevant, the additional `S_5` quotient has exactly
1,426,354,541 classes. Its structural factorization sorts five complementary
vertex-count pairs, then quotients ten complementary K5 edge-count pairs by the
residual equal-vertex stabilizer. Order-two and order-six `S_3` residual
stabilizers now have exact dense edge-orbit rank/unrank through mass 14.

The order-four `S_2 x S_2` residual stabilizer now also has exact dense
rank/unrank through mass 14 via a nested fixed/nonfixed diagonal-involution
factorization. The order-twelve `S_3 x S_2` stabilizer now also has exact
dense rank/unrank through mass 14 by nondecreasing three-bundle mass blocks and
fixed/nonfixed involution ranks.

The order-24 `S_4` residual stabilizer has an exact sorted-spoke/K4-edge
stabilizer decomposition through mass 14. The `2+1+1` spoke shape has exact
dense edge rank/unrank under its shared S2 involution, the `2+2` shape has exact
dense row/column V4 rank/unrank, and the `3+1` shape has dense edge rank/unrank
as a weighted S3 multiset.

The all-equal-spoke full-S4 edge core has exact dense rank/unrank via
opposite-edge blocks and one all-moving parity bit. The trivial distinct-spoke
shape uses ordinary composition ranking, so prefixing all five spoke shapes now
gives complete dense order-24 residual rank/unrank through mass 14.

The order-120 all-equal-vertex hard core now has an exact seven-conjugacy-type
edge cycle index/count and exact 156-subgroup automorphism-stabilizer inversion
through mass 14. Rooted-view multiplicity is exactly the automorphism vertex-
orbit count, giving every trivial-stabilizer class a unique minimum rooted rank.

Every nontrivial exception further reduces to a normalizer quotient of order at
most six. All eight populated nontrivial stabilizer types now have dense
rank/unrank by canonicalizing weighted H-edge-orbit states under `N(H)/H`,
filtering to exact stabilizer H, and prefix/select ranking the retained states.
At mass 14 these ranks cover all 272,924 symmetric classes.

The 6,689,862 trivial-stabilizer classes now use the unique lexicographically
minimum rooted S4 view of each free S5 orbit, followed by prefix/select ranking.
Every order-120 mass-14 class therefore has a dense local rank stratum.
Cumulative offsets across the nine disjoint stabilizer strata give one complete
dense 6,962,786-class S5 rank interval.

Ordered sextuples have
`C(k+63,63)` classes, or
839,983,521,106,400 at `k=14`; the additional `S_6` endpoint quotient has
1,179,940,653,635 classes. Sorting its six weight-1/5 complement pair-values
leaves one of eleven Young stabilizers acting on 52 residual scalar labels; this
factorization reproduces the full Burnside sequence through mass 14.

The all-distinct vertex-pair stratum has trivial stabilizer and dense
rank/unrank by vertex-sequence prefix plus a 52-part weak-composition rank,
covering 99,892,279
mass-14 classes. The `(2,1,1,1,1)` stratum has residual cycle type `1^24 2^14`
and a dense coupled-involution rank covering 8,308,559,181 mass-14 classes. The
`(3,1,1,1)` stratum is 10 fixed scalars plus a multiset of three 14-component
vectors and has a dense rank covering 89,182,770,767 mass-14 classes.

The `(2,2,1,1)` stratum has a nested V4 rank with `X=(12;6,6)` and `Z=(6;4,4)`
involution shapes, covering 39,233,740,619 mass-14 classes. The `(2,2,2)`
stratum has both the exact V4-first quotient/commuting-coset count and dense
stabilizer-chain rank/unrank, yielding 13,145,545,602 mass-14 classes.

The `(3,2,1)` S3-times-S2 stratum has a dense
S3-first bundle-multiset rank followed by a diagonal involution, covering
180,275,648,841 mass-14 classes.

The `(3,3)` stratum now also has dense rank/unrank under residual `S3 x S3`.
Its 52 residual labels split into four fixed coordinates, four invariant
three-coordinate blocks, and four invariant nine-coordinate blocks. A
nonabelian stabilizer chain canonicalizes one block at a time, while exact
Burnside suffix counts preserve dense prefixes. It reproduces the independent
residual sequence through mass 14 and gives 28,825,612,500 complete mass-14
classes.

The top-level `(4,2)` stratum now has an exact S4-first decomposition. Quotient
the fourfold block by S4, then the commuting swap of the two equal endpoints
descends to an involution on S4 classes. Its fixed-set count is the average over
the swap coset.

At residual mass 14 the S4 quotient has 2,549,713,246,880 classes, and
1,494,366,928 are fixed by the descended swap. The final S4-times-S2 quotient
has 1,275,603,806,904 classes. Prefixing `(4,2)` vertex sequences gives
122,060,462,590 complete mass-14 classes.

Dense rank/unrank is now constructive for every residual mass reachable inside
total mass 14. The 48-element action splits the 52 labels into blocks of sizes
`12,8,8,6,6,4,4,4`. The size-12 block is handled first by the pair-valued K4
S4 rank followed by the singleton-component swap; its stabilizer then drives
Burnside suffix counts over the seven smaller blocks.

Residual rank/unrank is checked through mass 12, the largest residual mass
reachable after a `(4,2)` vertex prefix, and the complete stratum rank reaches
mass 14. Only top-level `(6)` remains without dense rank/unrank.

Its 52 residual labels now also have an exact rooted-S5 decomposition. At
residual mass 14 there are
85,431,118,919 unrooted S6 classes and 511,090,971,734 classes with one
distinguished endpoint, so the six-root deficit is 1,495,741,780. The paired
weight-two/four layer has deficit 6,635,545 and the weight-three layer has
deficit 92,506. These are weighted missing rooted-view multiplicities, not
symmetric-class counts.

The exact stabilizer spectrum is now available. S6 has 56 subgroup conjugacy
classes and 1,455 actual subgroups. At residual mass 14, 84,008,008,841 of the
85,431,118,919 classes have trivial automorphism stabilizer, leaving
1,423,110,078 symmetric classes across 34 populated nontrivial subgroup types.
Their normalizer quotients have orders only `1,2,4,6,8,12,24`. The rooted-view
multiplicity spectrum is `1:1046, 2:91227, 3:4215311, 4:63923215,
5:1354879279, 6:84008008841`, whose weighted sum independently recovers the
511,090,971,734 rooted classes. Dense full-S6 rank/unrank remains open.

The `(4,1,1)` stratum now factors again into four fixed scalars, four
six-component vertex bundles, and six four-component K4-edge bundles, leaving
second-layer stabilizers `1/S2/V4/S3/S4`. The all-distinct bundle case now has
dense rank/unrank and contributes 167,523,430,983 complete mass-14 S6 classes.

The `(2,1,1)` second-layer S2 case now adds 113,906,741,533 classes, so
281,430,172,516 classes in `(4,1,1)` are densely ranked. The `(3,1)` S3
second-layer case adds another 17,436,163,856 classes. The `(2,2)` V4 case now
has complete dense rank/unrank and adds 2,954,772,356 classes.

The full-S4 widened edge core and its single quadruple-repeated bundle are now
composed as well, adding 829,746,428 classes. Fixed cumulative offsets across
all five second-layer stabilizers give one complete dense `(4,1,1)` interval of
302,650,855,156 classes. Five top-level Young-stabilizer strata remain
incomplete. The largest,
`(5,1)`, now factors into two fixed scalars, five two-component vertex bundles,
and ten four-component K5-edge bundles.

Sorting the five vertex bundles leaves seven Young stabilizers and reconstructs
all 310,719,486,939 mass-14 classes. The all-distinct trivial-stabilizer case
has dense rank/unrank and contributes 1,124,927,130 classes.

The `(3,1,1)` S3 and `(2,1,1,1)` S2 cases contribute 86,903,339,017 and
26,007,971,192 classes respectively. The `(4,1)` S4 and `(2,2,1)` V4 cases
are now also densely ranked, leaving two second-layer stabilizers open.

The `(4,1)` slice further factors its four widened spokes into five Young
stabilizers whose complete mass-14 contributions sum to 96,141,721,711 classes.
The all-distinct spoke stratum now has dense rank/unrank and contributes
35,347,204,706 complete mass-14 S6 classes. The `(2,1,1)` S2 spoke stratum now
has dense rank/unrank and contributes another 45,289,854,118 classes.

The `(2,2)` V4 spoke stratum adds 2,603,914,760 classes with dense rank/unrank.
The `(3,1)` S3 spoke stratum adds another 11,867,845,606 classes. The all-equal
full-S4 spoke stratum adds the remaining 1,032,902,521 classes with dense local
rank/unrank, so all five spoke stabilizers now have constructive local ranks.

Fixed cumulative offsets concatenate them into one dense residual S4 edge
interval of 100,371,765,432 mass-14 classes. Composing the four-plus-one bundle,
two fixed scalars, and top-level prefix gives one dense `(5,1;4,1)` interval of
96,141,721,711 classes. The four completed second-layer shapes now cover
210,177,959,050 of the 310,719,486,939 mass-14 `(5,1)` classes.

The `(2,2,1)` V4 branch has a dense widened K5-edge rank whose residual
mass-14 interval contains 601,406,812,712 classes and matches the independent
V4 Burnside sequence. Composing its two repeated bundle pairs, singleton, fixed
scalars, and top-level prefix gives 35,397,909,316 complete mass-14 classes.
Dense `(5,1)` coverage is therefore 245,575,868,366 of 310,719,486,939 classes.

The `(3,2)` branch has a dense widened S3-times-S2 K5-edge rank whose residual
mass-14 interval contains 200,608,118,832 classes. Composing the triple- and
double-repeated bundle keys, fixed scalars, and top-level prefix gives
36,950,581,606 complete mass-14 classes. These first six second-layer shapes
cover 282,526,449,972 of the 310,719,486,939 mass-14 `(5,1)` classes.

The final `(5,)` branch now has an exact widened full-S5 K5-edge hard core. Its
Burnside sequence reaches 20,103,708,128 residual mass-14 classes and matches
direct S5 orbits through mass two. Subgroup-lattice inversion shows
19,963,566,552 trivial-stabilizer classes and 140,141,576 symmetric classes.

The symmetric mass splits into eight nontrivial conjugacy strata with
normalizer quotients of orders 6, 4, 2, 6, 2, 1, 1, and 1. Transitive V4, S3,
D8, S3-times-S2, and S4 strata have dense rank/unrank for 39,352 combined
mass-14 classes. The disjoint-V4 quotient has 1,842,416 H-fixed classes; sparse
exclusion of 9,080 ranks fixed by its five strict supergroups gives a complete
1,833,336-class exact rank.

Together with the bounded symmetric strata and the two exact order-two ranks
below, all 140,141,576 nontrivial-stabilizer mass-14 classes are constructive.
The trivial stratum is also constructive via ordered edge-equality patterns and
strictly increasing four-component edge values, completing the full-S5 hard
core at 20,103,708,128 mass-14 classes.

The single-transposition H-fixed quotient now has complete exact rank/unrank.
One
fixed four-vector prefixes an S3 multiset of three eight-scalar bundles for the
137,230,360-class quotient, while pairwise-distinct bundle keys give a
133,547,296-class normalizer-free interval. Canonical S3-fixed edge assignments
map exactly 22,280 mass-14 ranks into that interval, matching the independent S3
stabilizer spectrum at every mass through fourteen. Sparse exclusion of those
ranks yields the exact 133,525,016-class single-transposition interval.

The double-transposition H-fixed quotient now has both an exact residual-V4
cycle index and scalable dense rank/unrank. The rank factors the V4 action into
an independent weight-two swap and a diagonal weight-one/weight-two swap.
Restricting both factors to moving orbits gives the normalizer-free rank; only
four mass-5 and sixteen mass-10 ranks have larger S5 stabilizers. Skipping those
exceptions yields a complete exact rank of 4,743,872 mass-14 classes.

The trivial-stabilizer stratum separates equality geometry from numeric edge
values. Sorting distinct four-component values by mass and composition rank
turns each state into an ordered partition of the ten K5 edges. A stabilizer
chain selects each ordered block only up to the stabilizer of the preceding
blocks and retains exactly chains ending at the identity.

For each ordered block-size composition, strictly increasing values reduce to
nondecreasing mass sequences and ordinary strict combinadics. Across all 512
block-size compositions this gives a dense exact rank of 19,963,566,552 mass-14
classes, matching independent subgroup-lattice inversion.

Two stabilizers occur only below the mass-14 boundary: D10 contributes four
classes at mass 5 and sixteen at mass 10, while full S5 contributes one class at
mass 0 and four at mass 10. Their two-five-edge-orbit and one-ten-edge-orbit
geometries give direct dense ranks. Concatenating these with the nine populated
mass-14 types yields a complete dense full-S5 edge rank at every residual mass
through fourteen, ending at 20,103,708,128 classes.

The final `(5,)` second-layer branch prefixes one two-component bundle value
repeated five times, two fixed scalars, and the complete residual full-S5 edge
rank after the canonical top-level `(5,1)` vertices. It contributes exactly
28,193,036,967 mass-14 classes. Fixed offsets across all seven second-layer
shapes reconstruct the parent count sequence at every mass through fourteen and
give a complete dense `(5,1)` interval of 310,719,486,939 mass-14 classes.

The top-level `(2,2,2)` stratum now also has dense rank/unrank for its residual
`S2^3` Young action. The 52 residual labels split into eight fixed coordinates,
six invariant two-coordinate blocks, six invariant four-coordinate blocks, and
one invariant eight-coordinate block. Sequential block canonicalization updates
the remaining subgroup, while suffix-count dynamic programming provides dense
prefixes. This reproduces the exact residual Burnside sequence through mass 14
and yields 13,145,545,602 complete mass-14 `(2,2,2)` classes.

Summed over every reachable width-14 fixed pair, the
triple quotient gives
547,751,638,341,145 canonical ordered triples, the quadruple quotient gives
25,678,405,217,633,865 canonical ordered quadruples, and the quintuple quotient
gives 3,571,359,808,057,227,945 canonical ordered quintuples. The endpoint-
unordered quintuple aggregate has 34,995,940,605,821,849 canonical classes at
width 14, now with dense global rank/unrank from the generic reachable-pair
ragged lift and the complete local S5 rank. At the same width, the ordered
sextuple aggregate has
1,584,315,319,509,725,541,225 classes and its endpoint-unordered `S_6` quotient
has 2,361,488,883,978,006,005 classes.

The ordered coordinate quotient is now parameterized for checked endpoint
arities one through eight. Arity `m` has exactly
`C(k+2^m-1,2^m-1)` joint-count classes in a dimension-`k` preimage cube; at
`k=14`, arities seven and eight have 7,227,209,188,850,973,120 and
84,466,573,066,471,253,216,128 classes. Summed over every reachable width-14
fixed pair, those two arities have 2,119,509,834,155,204,235,011,305 and
7,093,373,076,831,030,274,633,041,897 canonical ordered tuples. The statement
keeps endpoint order visible and applies only under simultaneous ambiguity-
coordinate relabeling; it is not a Malbolge semantic-equivalence or timing
claim.

Those same joint-count vectors now have a dense canonical integer index.
Stars-and-bars separator positions use colexicographic combinadic rank, covering
exactly `0..C(k+2^m-1,2^m-1)-1`, with constructive unranking through checked
arity eight and dimension fourteen.

For endpoint-order-sensitive analyses, those ordered quotient sizes also define
exact complete-search budget thresholds. Strict growth with ambiguity dimension
gives both the exact reachable-pair exceedance count for any integer budget and
the minimum budget covering any requested number of reachable pairs, through
checked arity eight and width fourteen.

Full endpoint symmetry is now parameterized for checked arities one through
eight using symmetric-group conjugacy partitions and the induced permutation
cycles on binary joint labels. S1 reproduces the coordinate quotient and S2
reproduces the endpoint-symmetric pair formula exactly.

At `k=14`, the new S7 and S8 quotients have 1,442,705,743,162,885 and
2,103,669,236,921,739,401 classes. Across every reachable width-14 fixed pair,
the corresponding global counts are 432,496,703,839,294,883,265 and
178,151,458,860,093,866,748,569. These counts apply only when endpoint order is
irrelevant in addition to coordinate labels; they are exact search-space
identities and make no timing claim.

Each such canonical endpoint-unordered class also has an exact raw mass. The
coordinate factor is the joint-count multinomial, while the endpoint factor is
the size of that count vector's `S_m` orbit; their product reconstructs the
combined `S_k x S_m` orbit. Exhaustive small tuple domains and all one-
coordinate weight orbits through S8 reproduce their complete raw mass exactly.

Endpoint-unordered classes also receive a canonical integer key without claiming
a new dense numbering. The key is the minimum existing ordered combinadic rank
over every endpoint permutation of the joint-count vector; two vectors have the
same key exactly when they occupy the same endpoint orbit. Small domains are
exhaustive, and one-coordinate classes reach checked arity eight.

Those quotient sizes also give exact complete-search budget thresholds. For each
checked width and arity, the required canonical count grows strictly with fixed-
pair ambiguity dimension, so the exact number of reachable pairs exceeding any
integer budget is the corresponding ambiguity-class tail. Inverting those
strict thresholds gives the minimum canonical-enumeration budget covering any
requested number from zero through all `7^N` reachable pairs. These are bounded
completeness-planning laws, not requirements on incomplete or stochastic search.

A finite candidate domain searched only through candidate-local binary verifier
answers also has an exact query lower bound. With one valid candidate, every
deterministic order has worst case `R` and uniform-target mean `(R+1)/2`; any
randomized strategy has some target with expected cost at least `(R+1)/2`, and a
uniform random order attains that bound. Absence certification requires all `R`
queries. Substituting the ordered or endpoint-unordered tuple class count gives
checked Malbolge-specific verifier-call bounds without making a timing claim.

The same model adds exactly across all `7^N` reachable fixed pairs: worst-case
calls equal the global canonical tuple count and minimax expected calls equal
`(global_count + 7^N)/2`, provided no verifier answer carries information across
fixed pairs.

If search can ask arbitrary binary questions rather than only verify one
candidate, decision-tree leaf capacity gives worst-case identification depth
`ceil(log2 R)`. For a uniformly hidden target, the exact optimal mean is
`h+2-2^(h+1)/R` with `h=floor(log2 R)`, attained by a balanced prefix tree.
Substituting the same ordered/unordered quotient counts gives checked
information
lower bounds; oracles with more than two outcomes remain outside this
theorem.

If endpoint order is also irrelevant, the exact pair class count
reduces further to
`(C(k+3,3)+floor((k+2)^2/4))/2`, or 372 at `k=14`; summed over every reachable
width-14 fixed pair, this endpoint-symmetric quotient has
18,096,618,233,793 canonical pairs. These quotients apply only to analyses with
the stated coordinate and endpoint symmetries.

Those endpoint-symmetric pair classes now also have a dense constructive index.
For canonical joint counts with `n01<=n10`, residual block sizes are
`floor((s+2)^2/4)` and the row prefix before `n01=b` is `b*(s-b+2)`; exact
rank/unrank spans `0..U_k-1` through `k=14` and rejects noncanonical inputs.

A second digit-DP composes that local index with the base-seven reachable-pair
order. Each higher pair digit fixes its ambiguity contribution; suffix block
weights sum `C(i,j)*2^j*5^(i-j)*U_(a+j)` over the remaining positions. This
yields dense global rank/unrank across the ragged union of all fixed-pair
quotients, with exactly 18,096,618,233,793 ranks at width fourteen.

Distance shells are also exact: every origin has `C(k,j)` compatible words at
trit distance `j`, radius `r` contains `sum_{j=0}^r C(k,j)` words, and

the diameter is `k`. Endpoints at distance `j` need exactly `j` one-trit
mutation steps and have exactly `j!` shortest in-cube paths. A radius-`r`
complete cover also needs at least `ceil(2^k / sum_{j=0}^r C(k,j))` centers by
volume; overlap can make the true covering number larger. `Q5` at radius one
is an exact checked strict case: volume gives six centers while the minimum is
seven. For ambiguity dimensions `k=1,3,7`, binary Hamming syndromes attain the
radius-one volume lower bound exactly with `1,2,16` centers and map every cube

word canonically to its unique center within one bit/trit. Conversely, through
dimension 14 no other positive ambiguity dimension admits a perfect radius-one
partition. These metric/graph results say nothing about incomplete corpus
membership or wall-clock speed.

Across all nontrivial radii through dimension 14, exact divisibility leaves
only seven perfect-partition parameter pairs. The Q7 radius-one Hamming case is
one; the other six are odd-dimensional antipodal partitions at radius
`(k-1)/2`, each with exactly two centers. This is a bounded coding-theoretic
classification, not a timing result.
