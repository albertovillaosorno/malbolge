# Publication-grade paper pipeline

## Status

Methodology for the single final comprehensive Malbolge paper

## Research Question

What evidence and method are required to evaluate publication-grade paper
pipeline?

## Background

Create a reproducible LaTeX paper pipeline under `docs/research/papers/` capable
of turning mature investigations into publication-quality papers with canonical
bibliography, equations, figures, tables, experiment provenance, limitations,
and regenerated results without making publication a prerequisite for ordinary
engineering work.

- Status: Supporting method; one P10 paper is the only deliverable
- Record type: Methodology
- Planning identity: `malbolge-machine-model-and-c-compilation-paper`
  (single final publication TODO)
- Last reviewed: 2026-07-26

## Prior Work

Prior-work claims must resolve through canonical records under
`docs/bibliography/`.

## Hypothesis

- A mature research capsule can generate a reproducible paper with canonical
  citations, equations, figures/tables derived from recorded experiments,
  limitations, and artifact provenance.
- The research record separates observed evidence from interpretation and
  preserves negative/null outcomes that affect the conclusion.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.

## Method

Work under this record uses stable identities, explicit inputs and assumptions,
independent correctness evidence where applicable, and retained negative/null
results. Source claims resolve through `docs/bibliography/`. The [LaTeX
bibliography record](../../bibliography/tooling/latex.md) defines the
publication tool family. The final paper consumes reproducible compiler,
VM, CPU/CUDA, DOOM, Apollo, RV32I, self-hosting and historical-capability
results without blocking their
earlier P2-P9 engineering acceptance.

## Evidence

- Expected durable artifact surface: `docs/research/`, `algorithms/`,
  `benchmarks/research/`.
- Required evidence: research question, hypotheses/baselines, source trail,
  experiment manifest, raw-output provenance, results, and threats to validity.
- Research evidence pending: bibliography-backed context, experiment identity,
  reproducible configuration, retained negative/null results, and a reviewed
  conclusion with threats to validity.

## Results

This methodology is guidance for the one final paper. It does not assert a
completed manuscript or create a second publication objective.

## Threats to Validity

Implementation bias, workload selection, hardware effects, and incomplete
replication remain threats until measured in the final paper.

## Conclusion

Supporting methodology only; acceptance and publication are owned by the
single final P10 paper in `TODO.md`. No additional paper or pipeline task is
scheduled.

## References

- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
