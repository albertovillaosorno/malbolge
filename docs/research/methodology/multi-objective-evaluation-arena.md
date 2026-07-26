# Multi-objective compiler algorithm evaluation arena

## Status

Proposed

## Research Question

What evidence and method are required to evaluate multi-objective compiler
algorithm evaluation arena?

## Background

Evaluate compiler and execution algorithms over scalable challenge families and
produce capacity curves and Pareto frontiers rather than one pass/fail score.
Measure time-to-verified-solution, generated-code size, runtime instructions,
peak memory/VRAM, verifier cost, energy or device utilization when available,
success probability for stochastic methods, and maximum solved difficulty under
fixed budgets. Preserve raw evidence so an algorithm that is faster at easy
instances but scales worse than another remains distinguishable instead of both
appearing equally "perfect" after crossing an arbitrary threshold.

- Status: Proposed
- Record type: Methodology
- Planning identity: `multi-objective-compiler-algorithm-evaluation-arena`
- Last reviewed: 2026-07-26

## Prior Work

Prior-work claims must resolve through canonical records under
`docs/bibliography/`.

## Hypothesis

- Authoritative comparisons retain capacity curves and Pareto frontiers; an
  aggregate score, if offered, is explicitly secondary and cannot hide
  time/quality/memory/size/verifier trade-offs.
- The end-to-end fixture demonstrates the intended behavior from admitted
  source/input through the actual generated/executed Malbolge path.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.
- Performance conclusions use equivalent workloads and report raw-sample
  provenance, resource budgets, dispersion/uncertainty, and failure/success
  behavior rather than only a best-case number.

## Method

Work under this record uses stable identities, explicit inputs and assumptions,
independent correctness evidence where applicable, and retained negative/null
results. Source claims resolve through `docs/bibliography/`.

## Evidence

- Expected durable artifact surface: `benchmarks/arena/`,
  `docs/research/methodology/`, `algorithms/`.
- Required evidence: reproducible build/run commands, expected outputs or
  interaction traces, artifact hashes, and end-to-end verification.
- Research evidence pending: bibliography-backed context, experiment identity,
  reproducible configuration, retained negative/null results, and a reviewed
  conclusion with threats to validity.
- Performance evidence pending: raw measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.

## Results

No completed research result or implementation claim is made by this proposed
record.

## Threats to Validity

The record is proposed; implementation bias, workload selection, hardware
effects, and incomplete replication remain threats until measured.

## Conclusion

Open. No technique is promoted to product architecture until the declared
evidence supports it.

## References

- [Parametric Multi Objective Algorithm
  Evaluation](../adr/parametric-multi-objective-algorithm-evaluation.md)
- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
- [Verification Trust
  Boundary](../../technical/adr/verification-trust-boundary.md)
