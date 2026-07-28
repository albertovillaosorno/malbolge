# Reproducible experiment identity and manifest

## Status

Implemented

## Research Question

What evidence and method are required to evaluate reproducible experiment
identity and manifest?

## Background

Define a versioned experiment manifest that records algorithm identity, exact
implementation/configuration, target profile, workload hashes, seeds, stopping
rules, host/accelerator identity, memory budget, compiler/tool versions, and
output location so any reported experiment can be reconstructed without editing
source constants.

- Status: Implemented
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

Experiment manifest schema v1 is validated by
`scripts/validate/experiment_manifest.py`. TOML is the checked-in serialization,
but the schema owns semantics independently of that format. Every research
mirror carries `algorithms/<id>/experiment.toml` with:

- `schema_version = 1`;
- `[experiment]` identity, record kind, method class, and deterministic seed;
- `[challenge]` family, positive difficulty, and target profile;
- `[budget]` with at least one positive integer stopping bound;
- `[verification]` with `required = true` and an explicit oracle; and
- `[provenance]` with exact implementation, configuration, and local-output
  paths bound to the algorithm ID.

`record_kind = "plan"` freezes intended configuration without pretending a run
already occurred and must not contain a `[run]` table. `record_kind = "run"`
additionally requires a lowercase 40-hex Git commit, lowercase SHA-256 workload
hash, host identity, accelerator identity, toolchain identity, a closed outcome,
and the repository-relative raw-output path. Accepted outcomes include success,
no solution, candidate invalidity, resource exhaustion, and tool failure so
negative evidence remains reconstructible instead of disappearing from analysis.

Algorithm-specific tables may extend the core manifest without weakening these
required identities. Source claims still resolve through `docs/bibliography/`.
TOML is a [cataloged configuration
format](../../bibliography/specifications-and-standards/toml.md).

## Evidence

- All eight current research-mirror manifests validate under schema v1, including
  the checked-in template.
- `tests/test_experiment_manifest.py` proves repository identity, exact run
  commit/workload hashes, retained negative outcomes, fail-closed outcome
  vocabulary, positive stopping bounds, mandatory verification, and strict
  plan-versus-run separation.
- `.dependencies/python/3.14.6/Scripts/python-jig.cmd
  scripts/validate/experiment_manifest.py` validates the checked-in corpus and
  reports the exact manifest count.
- Individual studies still own their hypotheses, raw outputs, interpretation,
  and threats to validity; this schema records identity rather than fabricating
  study-specific evidence.

## Results

Eight checked-in research plans now share one validated schema. Recorded-run
fixtures demonstrate that source commit, workload hash, environment identity,
outcome, and raw-output path are mandatory only when observed evidence is claimed.
The schema therefore distinguishes preregistration/configuration from observation
without requiring placeholder hardware or tool versions for work not yet run.

## Threats to Validity

The validator proves manifest structure and repository identity, not that a
caller supplied truthful host/toolchain strings or that a benchmark methodology
is statistically adequate. Workload selection, hardware effects, replication,
and measurement analysis remain responsibilities of the owning study and the
benchmark protocol. Algorithm-specific extension tables are intentionally not
interpreted by schema v1.

## Conclusion

Experiment manifest schema v1 is the active reproducible-identity contract. A
checked-in plan is not evidence of a run; a recorded run must bind exact source,
workload, environment, outcome, and raw-output identity. This closes manifest
identity while leaving statistical adequacy and study conclusions to downstream
owners.

## References

- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
