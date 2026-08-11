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
- Last reviewed: 2026-08-11

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
natural enumeration order as `deterministic-enumeration-v1` and a seed-stable
SplitMix64 sparse partial Fisher-Yates proposal order as
`splitmix64-sparse-partial-fisher-yates-v1` over opaque candidate indices. The
seeded scheduler samples without replacement and stores state proportional to
the evaluation budget, not the logical candidate count. The shared
`finite-verifier-gated-comparison-v1` runner executes both orders under the same
candidate count and evaluation budget through one caller-supplied trusted
verifier. It records evaluation-count time-to-first, total verified count, best
verified quality/index, and an explicit no-verified-candidate outcome after the
full budget. The companion
`finite-verifier-gated-dual-bound-comparison-v1` also applies the preregistered
wall-clock bound to both schedules through an injected monotonic nanosecond
clock, records first-hit elapsed time plus the exact stop reason, and rejects
invalid or backward clocks. Wall-clock checks occur between synchronous verifier
calls; the harness does not claim hard preemption of a verifier callback that
fails to return. The preregistered `classic-verified-block-search-v1` pilot is
now concrete before measurements: candidate indices bijectively enumerate all
$94^2=8,836$ two-graphical-byte classic sources in lexicographic order. The
independent `classic-two-word-no-io-halt-v1` verifier accepts only sources that
halt in one or two exact semantic transitions without prior input or output;
quality is the transition count to halt, so one is better than two. This is a
whole-program miniature, not reusable internal-block equivalence, and search
order never grants acceptance authority.
The pure `superoptimization-run-record-v1` renderer can now combine one
bounded-comparison result with the frozen plan and caller-supplied exact commit,
workload hash, host, toolchain, outcome, accelerator identity, and raw-output
path. It emits the shared schema-v1 `[run]` identity plus algorithm-specific
schedule metrics, rejects result/plan bound drift, requires the result candidate
count and provenance workload SHA-256 to match the frozen concrete challenge,
and delegates core commit/outcome/path validation to the repository's
experiment-manifest authority. It does not write evidence or discover
provenance. The `pilot.py` orchestration layer separately revalidates the plan's
challenge/verifier/workload identity before constructing the exact dual-bound
request and wiring only the concrete semantic verifier into the runner. Import,
plan validation, and synthetic zero-evaluation wiring tests are not
measurements.
No concrete run is recorded by this slice.

## Evidence

Repository validators close the plan identity across the research mirror,
experiment manifest, lifecycle record, target-profile fingerprint, concrete
challenge extension, and ignored output directory. Challenge tests exhaust all
8,836 candidates against independent low-level classic decode/entry/prefix
transfer, locking the candidate bijection, workload SHA-256, and accepted-set
digest. Exactly ten sources satisfy the challenge semantics: eight halt in one
transition and two in two transitions. That count characterizes the frozen
verifier/corpus before search measurement; it is not comparative search
evidence.
Schedule tests lock natural enumeration, exact seed replay,
no-replacement membership, seed separation, fail-closed dimensions, and sparse
operation over the maximum unsigned-64 logical corpus. Runner tests additionally
prove equal scheduled evaluation counts, verifier-gated first/best evidence,
full-budget retained null outcomes, and fail-closed malformed verifier quality.
Dual-bound tests additionally lock wall-clock, evaluation-budget, and finite
corpus stop identities plus fail-closed clock regression. Run-record tests prove
deterministic rendering, shared schema-v1 admission, retained verified/null
schedule metrics, plan/result bound closure, candidate-corpus/workload closure,
and shared commit-shape authority. Pilot-orchestration tests additionally prove
plan-to-request identity and fail-closed workload/verifier drift without
executing a candidate. The plan preserves a non-success outcome vocabulary for
later runs rather than
making success a prerequisite for retained evidence.

The broader study at `../../studies/superoptimization-program.md` remains the
human synthesis record. This mirrored plan supplies reproducible configuration
for its first hypothesis only; comparative raw output, dispersion, failures,
and a reviewed conclusion remain pending.

## Results

Candidate semantics, candidate-order mechanics, and equal-budget verifier-gated
execution under both preregistered evaluation and wall-clock bounds are
implemented and replay-locked before measurement. The complete challenge corpus
has ten independently verified accepted members, but no comparative search run,
raw timing evidence, or performance result is recorded yet.

## Threats to Validity

A single classic pilot can be dominated by challenge-family bias, search-seed
variance, evaluator overhead, verifier cost, candidate-language choices, and
hardware or toolchain effects. Even a positive pilot would not establish that
stochastic search dominates synthesis, equality saturation, or other workload
families.

## Conclusion

The first comparison now has reproducible challenge, verifier, workload, plan,
and candidate-order identities, but no technique is promoted and no performance
conclusion is accepted before recorded, independently verified runs exist.

## References

- [Superoptimization Program](../../studies/superoptimization-program.md)
- [Verification Trust
  Boundary](../../../technical/adr/verification-trust-boundary.md)
- [Research Evidence And Algorithm
  Mirror](../../adr/research-evidence-and-algorithm-mirror.md)
