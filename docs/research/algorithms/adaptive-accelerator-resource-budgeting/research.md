# Adaptive accelerator resource budgeting

## Status

Proposed

## Research Question

Does `adaptive-accelerator-resource-budgeting` provide a reproducible verified
benefit over its declared baseline for the Malbolge compiler or execution
problem without weakening semantic correctness?

## Background

Discover available memory and compute resources at runtime and choose batch
size, state layout, caches, and search breadth accordingly. Tiny devices around
128 MiB must remain usable; devices around 80 GiB should turn additional
resources into measured throughput instead of hitting fixed artificial limits.

- Status: Proposed
- Research ID: `adaptive-accelerator-resource-budgeting`
- Last reviewed: 2026-07-26

## Prior Work

- `../../../bibliography/platforms-and-runtimes/accelerators/nvidia-cuda.md`

## Hypothesis

- H1: the proposed technique improves at least one preregistered objective under
  an equivalent resource budget while all accepted outputs pass the independent
  verifier.
- H0/rejection condition: the technique is unsound, cannot reproduce its result,
  or provides no meaningful advantage over the declared baseline on the admitted
  challenge distribution.

## Method

The executable mirror lives at
`algorithms/adaptive-accelerator-resource-budgeting/`. Experiments use versioned
configuration, explicit seeds where stochastic behavior exists, fixed resource
budgets, parametric challenge identities, and the same verifier used for
baselines. Raw regenerable output stays in the mirror's Git-ignored `out/`.

## Evidence

Candidate generation, heuristics, models, and accelerators are untrusted. A
research result can compare quality or cost only after the trusted semantic
verifier accepts the candidate under the declared target profile.

- The scheduler runs within measured memory limits from approximately 128 MiB
  through large-memory accelerators and converts additional resources into
  measured throughput/search breadth without fixed-size assumptions.
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
