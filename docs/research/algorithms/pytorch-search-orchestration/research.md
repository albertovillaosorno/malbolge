# PyTorch search orchestration

## Status

Proposed

## Research Question

Does `pytorch-search-orchestration` provide a reproducible verified benefit over
its declared baseline for the Malbolge compiler or execution problem without
weakening semantic correctness?

## Background

Use PyTorch for batched candidate/state representation, experiment
orchestration, and heuristic models where useful while purpose-built kernels
retain exact semantic execution where tensor operations are a poor fit.

- Status: Proposed
- Research ID: `pytorch-search-orchestration`
- Last reviewed: 2026-07-26

## Prior Work

- `../../../bibliography/platforms-and-runtimes/accelerators/pytorch.md`
- `../../../bibliography/platforms-and-runtimes/accelerators/nvidia-cuda.md`

## Hypothesis

- H1: the proposed technique improves at least one preregistered objective under
  an equivalent resource budget while all accepted outputs pass the independent
  verifier.
- H0/rejection condition: the technique is unsound, cannot reproduce its result,
  or provides no meaningful advantage over the declared baseline on the admitted
  challenge distribution.

## Method

The executable mirror lives at `algorithms/pytorch-search-orchestration/`.
Experiments use versioned configuration, explicit seeds where stochastic
behavior exists, fixed resource budgets, parametric challenge identities, and
the same verifier used for baselines. Raw regenerable output stays in the
mirror's Git-ignored `out/`.

## Evidence

Candidate generation, heuristics, models, and accelerators are untrusted. A
research result can compare quality or cost only after the trusted semantic
verifier accepts the candidate under the declared target profile.

- PyTorch is restricted to representation/orchestration/heuristic guidance where
  useful; exact semantic evaluation remains in deterministic implementations
  when tensor semantics are unsuitable.
- Training corpora are verifier-labeled and versioned; model/checkpoint identity,
  feature schema, and held-out challenge results are retained with every claim.
- The CPU/reference path and independent verifier remain sufficient when PyTorch
  or a trained model is absent.
- A CPU/reference path remains sufficient for correctness, and accelerator
  failure/unavailability changes performance rather than semantic acceptance.

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
