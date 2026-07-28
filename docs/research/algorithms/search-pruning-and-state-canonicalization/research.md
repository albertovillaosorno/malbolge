# Search pruning and state canonicalization

## Status

Active exploratory research

## Research Question

Does `search-pruning-and-state-canonicalization` provide a reproducible verified
benefit over its declared baseline for the Malbolge compiler or execution
problem without weakening semantic correctness?

## Background

Develop exact pruning, dominance rules, partial-equivalence checks, canonical
states, admissible heuristics, and profile-aware constraints before relying on
raw hardware scale.

- Status: Active exploratory research
- Research ID: `search-pruning-and-state-canonicalization`
- Last reviewed: 2026-07-26

## Prior Work

- `../../../bibliography/publications/superoptimization/stoke.md`
- `../../../bibliography/publications/superoptimization/souper.md`
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
`algorithms/search-pruning-and-state-canonicalization/`. Experiments use
versioned configuration, explicit seeds where stochastic behavior exists, fixed
resource budgets, parametric challenge identities, and the same verifier used
for baselines. Raw regenerable output stays in the mirror's Git-ignored `out/`.

The first slice is exploratory correctness work rather than a preregistered
performance comparison. Its baseline evaluates every pre-identity candidate byte
sequence. The candidate rule partitions that same ordered corpus by complete byte
equality and retains the first occurrence of each class. Hash equality, prefix
relations, similar lengths, and heuristic state keys are explicitly excluded.
The rule is rejected as unsound if any two byte-distinct inputs share a
representative. A corpus with no duplicates is the required null case and must
show zero reduction in candidate evaluations.

## Evidence

Candidate generation, heuristics, models, and accelerators are untrusted. A
research result can compare quality or cost only after the trusted semantic
verifier accepts the candidate under the declared target profile.

- Every pruning/dominance/canonicalization rule is justified by equivalence or
  admissibility evidence and has adversarial tests that would catch an unsound
  discarded state.
- A CPU/reference path remains sufficient for correctness, and accelerator
  failure/unavailability changes performance rather than semantic acceptance.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.

## Results

The exploratory exact-duplicate correctness fixtures pass. On the fixed
duplicate-rich eight-item corpus, five exact representatives remain, so three
redundant candidate evaluations are removed by construction. On the four-item
all-unique corpus, all four representatives remain and the measured evaluation
reduction is zero. One-byte differences, shared prefixes, nearby lengths, and an
empty corpus all preserve the required exact partition.

These are deterministic evaluation-count observations, not wall-time speedup
measurements. The fixture-specific plan was not committed before the first run,
so no confirmatory performance conclusion is claimed from this slice.

## Threats to Validity

Initial threats include challenge-family bias, hardware/toolchain sensitivity,
search-seed variance, verifier bounds, and overfitting to small Malbolge blocks.
Each experiment must narrow these threats before drawing a conclusion.

## Conclusion

Exact byte-duplicate pruning is supported as a conservative correctness rule for
pre-identity candidate sequences and is retained experimentally. It cannot help
an all-unique corpus, and this evidence does not justify stronger semantic state
canonicalization, dominance rules, or a general performance claim. The broader
research hypothesis remains inconclusive pending preregistered challenge and
performance experiments.

## References

- [Replaceable Accelerator And Algorithm
  Ports](../../../technical/adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust
  Boundary](../../../technical/adr/verification-trust-boundary.md)
- [Research Evidence And Algorithm
  Mirror](../../adr/research-evidence-and-algorithm-mirror.md)
