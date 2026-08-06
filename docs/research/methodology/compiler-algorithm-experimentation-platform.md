# Compiler algorithm experimentation platform

## Status

Accepted methodology and implemented platform

## Research Question

What evidence and method are required to evaluate compiler algorithm
experimentation platform?

## Background

Make the repository a reproducible laboratory for compiler research, not merely
an implementation of one fixed C-to-Malbolge pipeline. Experimental algorithms
use the `docs/research/algorithms/<id>/` and `algorithms/<id>/` mirror, while
ordinary product algorithms remain inside their owning responsibility. Provide
stable experiment boundaries for alternate IRs, lowering passes, graph
simplifiers, superoptimizers, search strategies, code generators, execution
tiers, and cost models. Experiments must be selectable without editing trusted
semantic code, record exact configuration/seeds/inputs, compare against common
correctness oracles, and emit reproducible evidence so a new algorithm can be
accepted, rejected, or retired without becoming architecture by accident.

- Status: Accepted and implemented
- Record type: Methodology
- Planning identity: `compiler-algorithm-experimentation-platform`
- Last reviewed: 2026-07-26

## Prior Work

Prior-work claims must resolve through canonical records under
`docs/bibliography/`.

## Hypothesis

- A new experimental compiler algorithm can be added, configured, compared
  against a baseline, verified, and removed without editing trusted VM/compiler
  semantics.
- The authoritative rule/specification is deterministic, versionable, and does
  not depend on undocumented host behavior.
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

- Seven non-template algorithm families use the mirrored research taxonomy.
- Fifty-three experiment manifests and 45 retained benchmark experiment
  manifests record stable identity, inputs, configuration, hypotheses, and
  evidence ownership.
- Repository validators enforce algorithm lifecycle, mirror identity,
  experiment-manifest schema, benchmark protocol, retained evidence, and local
  output boundaries.
- Negative and null results remain retained beside promoted optimizations; the
  accelerator evidence explicitly preserves routes that were slower or failed
  their overlap hypotheses.

## Results

The platform supports adding, validating, comparing, retaining, and retiring
experimental algorithms without editing VM semantic authority. Product
algorithms remain within their owning functions, while executable research uses
stable mirrored identities and explicit experiment manifests.

## Threats to Validity

The platform does not make every experiment reproducible on every host. Hardware
availability, external toolchains, workload selection, measurement noise, and
retained-environment drift remain experiment-specific threats that each result
must state independently.

## Conclusion

Accepted. The repository has a reusable compiler-algorithm experimentation
platform. Individual techniques remain untrusted until their own evidence and
promotion gates pass.

## References

- [Repository Responsibility
  Boundaries](../../technical/adr/repository-responsibility-boundaries.md)
- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
- [Parametric Multi Objective Algorithm
  Evaluation](../adr/parametric-multi-objective-algorithm-evaluation.md)
