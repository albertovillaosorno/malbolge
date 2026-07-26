# Stochastic and guided search

## Status

Proposed

## Research Question

Does `stochastic-and-guided-search` provide a reproducible verified benefit over
its declared baseline for the Malbolge compiler or execution problem without
weakening semantic correctness?

## Background

Evaluate Monte Carlo, evolutionary, STOKE-like stochastic, learned, and hybrid
search with deterministic final verification and reproducible research seeds.

- Status: Proposed
- Research ID: `stochastic-and-guided-search`
- Last reviewed: 2026-07-26

## Prior Work

- `../../../bibliography/publications/superoptimization/stoke.md`
- `../../../bibliography/publications/superoptimization/souper.md`

## Hypothesis

- H1: the proposed technique improves at least one preregistered objective under
  an equivalent resource budget while all accepted outputs pass the independent
  verifier.
- H0/rejection condition: the technique is unsound, cannot reproduce its result,
  or provides no meaningful advantage over the declared baseline on the admitted
  challenge distribution.

## Method

The executable mirror lives at `algorithms/stochastic-and-guided-search/`.
Experiments use versioned configuration, explicit seeds where stochastic
behavior exists, fixed resource budgets, parametric challenge identities, and
the same verifier used for baselines. Raw regenerable output stays in the
mirror's Git-ignored `out/`.

## Evidence

Candidate generation, heuristics, models, and accelerators are untrusted. A
research result can compare quality or cost only after the trusted semantic
verifier accepts the candidate under the declared target profile.

- Search variants run under identical budgets/seeds/corpora where applicable and
  report time-to-first-verified candidate plus quality distributions, not only
  the best lucky run.
- A CPU/reference path remains sufficient for correctness, and accelerator
  failure/unavailability changes performance rather than semantic acceptance.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.
- Performance conclusions use equivalent workloads and report raw-sample
  provenance, resource budgets, dispersion/uncertainty, and failure/success
  behavior rather than only a best-case number.

## Results

No experiment result is recorded yet.

## Threats to Validity

Initial threats include challenge-family bias, hardware/toolchain sensitivity,
search-seed variance, verifier bounds, and overfitting to small Malbolge blocks.
Each experiment must narrow these threats before drawing a conclusion.

## Conclusion

No conclusion is accepted before reproducible evidence exists.

## References

- [Replaceable Accelerator And Algorithm
  Ports](../../../technical/adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust
  Boundary](../../../technical/adr/verification-trust-boundary.md)
- [Research Evidence And Algorithm
  Mirror](../../adr/research-evidence-and-algorithm-mirror.md)
