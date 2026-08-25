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
formalizes thirty-five exact reductions: classic five-trit crazy factorization,
general profile-width crazy chunking, exact decode sum-class canonicalization,
classic rotate
lookup, graphical self-encryption orbit canonicalization,
classic rotate-history canonicalization, exact classic rotate minimal-period
partition, exact crazy-target preimage cardinality, constructive mixed-radix
preimage rank/unrank through width 14, exact one-trit Gray traversal of
preimage hypercubes, exact `2^k-1` minimum aggregate trit-edit cost for
bijective complete traversal, exact binary-cube one-trit neighborhood
structure plus exact binomial distance shells/balls, diameter, and shortest-
path lower bounds/counts plus fixed-radius covering lower bounds and perfect
radius-one Hamming covers, the tight
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
complete-domain graph/edit identities, not wall-clock lower bounds. Moreover,
from any compatible word the exact distance-`j` shell has `C(k,j)` words, a
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
exact Gray edit optimality, exact preimage-cube neighborhood graph, and exact
preimage-cube distance shells/balls, exact mutation geodesics, fixed-radius
covering lower bounds, and perfect radius-one Hamming covers,
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
optimality, exact one-trit cube neighborhood graph, and exact binomial
distance shells/balls, diameter, exact mutation geodesics, fixed-radius
covering lower bounds, and perfect radius-one Hamming covers, tight 1,024-
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
