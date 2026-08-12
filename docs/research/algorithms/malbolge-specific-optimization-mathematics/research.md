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
formalizes seventeen exact reductions: classic five-trit crazy factorization,
general profile-width crazy chunking, decode phase reduction, classic rotate
lookup, graphical self-encryption orbit canonicalization, classic rotate-history
canonicalization, exact crazy-target preimage cardinality, the tight classic
1,024-preimage global bound, the exact zero-or-power-of-two preimage spectrum,
the accumulator-specific `2^(10-n2(a))` worst-target bound, and the exact
`2^(10-n2(a))*3^n2(a)` reachable-target count, and the exact
`C(10,k)*2^(10-k)` cardinality of accumulator class `k`, the exact `7^10`
count of reachable accumulator/target pairs, and the exact
`C(10,k)*2^k*5^(10-k)` count of pairs in preimage class `2^k`, the exact
profile-width `C(N,k)*2^k*5^(N-k)` distribution for `1<=N<=14`, the exact
`9^10-7^10 = 3,204,309,152` unreachable-pair count, and the exact threshold sum
for reachable pairs whose full preimage set exceeds a nonnegative enumeration
budget. The encryption
table is proved to partition the complete
graphical domain into cycles of lengths 2, 4, 5, 6, 9, and 68, so repeated
committed encryption of an otherwise unchanged code cell needs only the visit
residue modulo its cycle length. Repeated rotate updates to one otherwise
unchanged classic ten-trit data cell likewise need only the visit residue modulo
ten; no minimal-period-ten claim is made for individual words. For fixed classic
crazy accumulator/target words, the exact full-data-domain preimage count is the
product of the ten per-trit multiplicities. The existing all-one target under
accumulator zero therefore has exactly 1,024 data-word preimages, while a zero
target under accumulator zero has none. Exhausting all 59,049 accumulator words
through an independent trit relation proves no fixed classic accumulator/target
pair can exceed 1,024 preimages, so that known case attains the global bound.
The same exhaustive accumulator spectrum proves every nonzero full-domain count
is one of `1,2,4,...,1024`, and every listed power plus zero is attainable. For
each fixed accumulator, an independently constructed maximizing target attains
exactly `2^(10-n2(a))`, where `n2(a)` counts accumulator trits equal to two.
The same state admits exactly `2^(10-n2(a))*3^n2(a)` target words with at
least one complete-domain preimage. The optimizer exposes both state-level
quantities from the normative trit table and exhaustively checks them against an
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
The complement `9^10-7^10 = 3,204,309,152` is therefore globally impossible
before any data-word enumeration. Summing preimage classes above a supplied
budget gives an exact planning lower bound for complete preimage enumeration:
budget 0 exceeds all `7^10` reachable pairs, while budget 1,024 exceeds none.
This lower bound does not apply to search procedures that do not promise
complete preimage enumeration. Sharing these planning cardinalities does not
imply
general semantic equivalence between accumulator/target pairs.

`src/specification/formal-model/math/specification/correspondence.toml` binds
those equations to exhaustive or composite executable evidence. The classic
crazy/rotate finite domains are checked exhaustively; decode is checked across
every classic code pointer and all 94 graphical cells; current 14-trit crazy
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
slice. The self-encryption/rotate-history reductions, crazy preimage count,
global preimage bound, discrete preimage spectrum, accumulator-specific
worst-target bound, reachable-target count, accumulator-class partition,
global reachable-pair count, classic/profile-width preimage-pair distributions,
exact unreachable-pair count, and preimage-budget exceedance bound are
correctness-proved search
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
self-encryption and classic rotate-history canonicalizations, crazy-target
preimage cardinality, tight 1,024-preimage bound, discrete cardinality spectrum,
accumulator-specific worst-target bound, reachable-target count, exact
accumulator-class partition, global reachable-pair count, exact classic and
profile-width preimage-pair distributions, exact unreachable-pair count, and
exact preimage-budget
exceedance bound as valid optimization building blocks.
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
