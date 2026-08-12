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
- Last reviewed: 2026-08-12

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
measurements. The committed measurement extension freezes five retained cold
repetitions, fixed enumeration-then-seeded ordering, no warmup, retain-all
outlier policy, median center, and observed-range evidence before the first run.
The first measured pilot is retained under
`benchmarks/research/evidence/2026-08-11-classic-superopt-pilot-windows/` and
binds pre-run commit `23dd86d6`.

A second technique is now preregistered without measurement.
`classic-history-residue-canonicalization-v1` binds the proved encryption-orbit
and rotate-history equations to raw visit-count state under equal 10,000
evaluation, 60-second, and 512 MiB bounds. Applicability requires stable address
identity and no intervening write; unique search states is the primary metric,
and accepted-set drift is a rejection condition. Results remain forbidden until
a versioned canonicalization challenge and runner are registered. The pure
`exact-history-residue-state-v1` substrate is now implemented below that gate.
It accepts caller-owned encryption semantics, derives a closed graphical orbit
period before reduction, reduces rotate visits modulo ten, and rejects any
changed-address or intervening-write applicability. It does not search or
measure candidates.

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
executing a candidate. Measurement tests lock the five-repetition retain-all
protocol without real timing; recorded-evidence tests then validate the tracked
run/benchmark records and recompute exact semantic and median timing results
from retained CSV without rerunning the experiment. The plan preserves a
non-success outcome vocabulary rather than making success a prerequisite for
retained evidence. History-canonicalization tests inject the repository classic
verifier successor across all 94 graphical starts, recover orbit periods
`2,4,5,6,9,68`, verify modulo-ten rotate history, and fail closed on unproved
applicability or malformed injected orbits.

The broader study at `../../studies/superoptimization-program.md` remains the
human synthesis record. This mirrored plan now has one retained host-specific
pilot for its first hypothesis plus one unmeasured canonicalization plan. Larger
challenge families, the canonicalization challenge/runner, other techniques,
independent-host replication, and stronger statistical power remain pending.

## Results

The first measured seed-zero comparison retained five cold repetitions on
Microsoft Windows 10.0.26200 x64 with Python 3.14.6. Both schedules exhausted
all
8,836 candidates and verified the same ten accepted sources in every repetition;
both reached best quality 1. Deterministic enumeration first verified candidate
705 at evaluation 706, while the seeded order first verified candidate 4576 at
evaluation 250. That evaluation-count difference is exact for the frozen corpus
and schedule identities. Median first-hit elapsed time was 18,506,300 ns for
enumeration and 6,119,900 ns for seeded order. Median full-corpus time was
227,928,500 ns versus 227,433,600 ns, with overlapping observed ranges, so this
pilot does not establish a total-throughput advantage.

## Threats to Validity

This single-host, seed-zero, five-repetition pilot is dominated by possible
challenge-family bias, fixed enumeration-then-seeded ordering, Python verifier
overhead, evaluator cost, candidate-language choices, and hardware/toolchain
effects. The two-word corpus is deliberately tiny, and no cross-seed or
cross-host dispersion is available. The positive first-hit result therefore does
not establish that stochastic search dominates other seeds, larger Malbolge
workloads, synthesis, equality saturation, or other workload families.

## Conclusion

For this frozen seed-zero corpus, H1 is supported only on the first-hit
objective: seeded proposal order requires 250 evaluations versus 706 for
enumeration and also had a lower first-hit median on this host. Best quality
ties
and full-corpus timing is effectively inconclusive. This is retained pilot
evidence, not sufficient basis to promote stochastic search to product
architecture or generalize beyond the recorded challenge/seed/host.

## References

- [Superoptimization Program](../../studies/superoptimization-program.md)
- [Verification Trust
  Boundary](../../../technical/adr/verification-trust-boundary.md)
- [Research Evidence And Algorithm
  Mirror](../../adr/research-evidence-and-algorithm-mirror.md)
