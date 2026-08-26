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
`k=14`; summed over every reachable width-14 fixed pair, this gives exactly
547,751,638,341,145 canonical ordered triples. If endpoint order
is also
irrelevant, the exact class count reduces further to
`(C(k+3,3)+floor((k+2)^2/4))/2`, or 372 at `k=14`. These quotients apply only
to analyses with the stated coordinate and endpoint symmetries.

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
