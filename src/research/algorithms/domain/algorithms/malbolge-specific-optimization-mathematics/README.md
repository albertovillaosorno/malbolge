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
has exactly 21,323 classes. Summed over every reachable width-14 fixed pair,
that endpoint-unordered triple quotient has 124,279,218,052,677 canonical
classes.

Ordered quadruples have `C(k+15,15)` classes, or 77,558,760; if quadruple
endpoint order is irrelevant, the additional `S_4` quotient has exactly
3,419,552 classes. Summed over every reachable width-14 fixed pair, that
endpoint-unordered quotient has 1,409,733,897,288,413 canonical classes.

Ordered quintuples have `C(k+31,31)` classes, or 166,871,334,960; if quintuple
endpoint order is irrelevant, the additional `S_5` quotient has exactly
1,426,354,541 classes. Ordered sextuples have `C(k+63,63)` classes, or
839,983,521,106,400 at `k=14`; the additional `S_6` endpoint quotient has
1,179,940,653,635 classes.

Summed over every reachable width-14 fixed pair, the
triple quotient gives
547,751,638,341,145 canonical ordered triples, the quadruple quotient gives
25,678,405,217,633,865 canonical ordered quadruples, and the quintuple quotient
gives 3,571,359,808,057,227,945 canonical ordered quintuples. The endpoint-
unordered quintuple aggregate has 34,995,940,605,821,849 canonical classes at
width 14. At the same width, the ordered sextuple aggregate has
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

If endpoint order is also irrelevant, the exact pair class count
reduces further to
`(C(k+3,3)+floor((k+2)^2/4))/2`, or 372 at `k=14`; summed over every reachable
width-14 fixed pair, this endpoint-symmetric quotient has
18,096,618,233,793 canonical pairs. These quotients apply only to analyses with
the stated coordinate and endpoint symmetries.

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
