# Superoptimization research program

## Status

Active

## Research Question

Under identical classic-profile challenge identity, stopping bounds, and
independent verification, does a STOKE-style stochastic proposal search reach a
verified candidate sooner or produce a better verified candidate than stable
deterministic enumeration?

## Background

The broader study maps stochastic search, synthesis over IR, and equality
saturation into separate falsifiable Malbolge hypotheses. This mirrored record
preregisters only the first comparison so its inputs and stopping rules exist
before measurements. It does not promote stochastic search or claim that the
pilot challenge generalizes to other Malbolge workloads.

- Status: Active
- Research ID: `superoptimization-research-program`
- Last reviewed: 2026-08-09

## Prior Work

- `../../../bibliography/publications/superoptimization/stoke.md`
- `../../../bibliography/publications/superoptimization/souper.md`
- `../../../bibliography/publications/superoptimization/egg.md`

The initial pilot tests only the STOKE-style hypothesis. Souper-style synthesis
and `egg`-style equality saturation remain separate future comparisons rather
than being inferred from one search result.

## Hypothesis

- H1: under the same `classic-verified-block-search-v1` challenge, classic
  target
  profile, independent verifier, and stopping bounds, stochastic proposal search
  reaches the first verified candidate sooner or yields a strictly better
  verified candidate than deterministic enumeration.
- H0/rejection condition: no preregistered objective improves, verifier
  acceptance differs between compared paths, or the result cannot be reproduced
  from the declared seed and configuration.

## Method

The executable mirror carries a schema-one `plan` manifest with seed zero,
`malbolge-1998` plus its canonical profile fingerprint, a 60-second wall-clock
bound, a 10,000-candidate evaluation bound, and a 512 MiB memory bound. A run
must stop when its governing harness reaches the applicable declared bound; both
strategies receive the same bounds and challenge identity.

Deterministic enumeration is the baseline. The executable substrate now fixes
natural enumeration order and a seed-stable SplitMix64 sparse partial
Fisher-Yates proposal order over opaque candidate indices. The seeded scheduler
samples without replacement and stores state proportional to the evaluation
budget, not the logical candidate count. It does not define the
`classic-verified-block-search-v1` candidate language or execute a candidate.
Candidate generation remains untrusted, and `trusted-semantic-verifier` remains
mandatory for every accepted candidate. Future recorded runs must add exact
commit, workload hash, host, toolchain, outcome, accelerator identity, and
raw-output path through the repository's run manifest contract. No such run is
recorded by this slice.

## Evidence

Repository validators close the plan identity across the research mirror,
experiment manifest, lifecycle record, target-profile fingerprint, and ignored
output directory. Schedule tests lock natural enumeration, exact seed replay,
no-replacement membership, seed separation, fail-closed dimensions, and sparse
operation over the maximum unsigned-64 logical corpus. The plan preserves a
non-success outcome vocabulary for later runs rather than making success a
prerequisite for retained evidence.

The broader study at `../../studies/superoptimization-program.md` remains the
human synthesis record. This mirrored plan supplies reproducible configuration
for its first hypothesis only; comparative raw output, dispersion, failures,
and a reviewed conclusion remain pending.

## Results

Candidate-order mechanics are implemented and replay-locked. No experiment run
or comparative performance result is recorded yet.

## Threats to Validity

A single classic pilot can be dominated by challenge-family bias, search-seed
variance, evaluator overhead, verifier cost, candidate-language choices, and
hardware or toolchain effects. Even a positive pilot would not establish that
stochastic search dominates synthesis, equality saturation, or other workload
families.

## Conclusion

The first comparison now has reproducible plan and candidate-order identities,
but no technique is promoted and no performance conclusion is accepted before
recorded, independently verified runs exist.

## References

- [Superoptimization Program](../../studies/superoptimization-program.md)
- [Verification Trust
  Boundary](../../../technical/adr/verification-trust-boundary.md)
- [Research Evidence And Algorithm
  Mirror](../../adr/research-evidence-and-algorithm-mirror.md)
