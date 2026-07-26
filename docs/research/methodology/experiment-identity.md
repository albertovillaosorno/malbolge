# Reproducible experiment identity and manifest

## Status

Proposed

## Research Question

What evidence and method are required to evaluate reproducible experiment
identity and manifest?

## Background

Define a versioned experiment manifest that records algorithm identity, exact
implementation/configuration, target profile, workload hashes, seeds, stopping
rules, host/accelerator identity, memory budget, compiler/tool versions, and
output location so any reported experiment can be reconstructed without editing
source constants.

- Status: Proposed
- Record type: Methodology
- Planning identity: `reproducible-experiment-identity-and-manifest`
- Last reviewed: 2026-07-26

## Prior Work

Prior-work claims must resolve through canonical records under
`docs/bibliography/`.

## Hypothesis

- One manifest is sufficient to reconstruct the exact challenge, algorithm,
  seed, budget, target profile, toolchain, host/accelerator identity, and local
  output location of a reported run.
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
results. Source claims resolve through `docs/bibliography/`. TOML is one
[cataloged configuration
format](../../bibliography/specifications-and-standards/toml.md), but the
experiment schema owns semantics independently of its serialization.

## Evidence

- Expected durable artifact surface: `docs/research/`, `algorithms/`,
  `benchmarks/research/`.
- Required evidence: research question, hypotheses/baselines, source trail,
  experiment manifest, raw-output provenance, results, and threats to validity.
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

- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
