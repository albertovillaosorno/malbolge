# Machine-readable LLM and compiler challenge corpus

## Status

Proposed

## Research Question

What evidence and method are required to evaluate machine-readable llm and
compiler challenge corpus?

## Background

Expose challenge definitions, expected semantics, constraints, oracle behavior,
inputs, difficulty parameters, and evaluation results in a stable machine-
readable format so compiler researchers and LLM-based code/algorithm agents can
generate candidate passes or algorithms and submit them to the same verifier and
benchmark arena. The corpus must test generated ideas without granting an LLM
authority over correctness and must support deterministic replay of every
admitted result.

- Status: Proposed
- Record type: Methodology
- Planning identity: `machine-readable-llm-and-compiler-challenge-corpus`
- Last reviewed: 2026-07-26

## Prior Work

Prior-work claims must resolve through canonical records under
`docs/bibliography/`.

## Hypothesis

- The corpus schema exposes constraints/oracles/difficulty/results for external
  agents while the repository verifier, never an LLM self-assessment, decides
  correctness and replayability.
- The end-to-end fixture demonstrates the intended behavior from admitted
  source/input through the actual generated/executed Malbolge path.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.

## Method

Work under this record uses stable identities, explicit inputs and assumptions,
independent correctness evidence where applicable, and retained negative/null
results. Source claims resolve through `docs/bibliography/`.

## Evidence

- Expected durable artifact surface: `benchmarks/challenges/`, `docs/research/`,
  `verifier/`.
- Required evidence: reproducible build/run commands, expected outputs or
  interaction traces, artifact hashes, and end-to-end verification.
- Research evidence pending: bibliography-backed context, experiment identity,
  reproducible configuration, retained negative/null results, and a reviewed
  conclusion with threats to validity.

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
