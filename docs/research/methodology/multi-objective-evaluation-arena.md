# Multi-objective compiler algorithm evaluation arena

## Status

Active. Initial offline analyzer implemented; performance evidence pending.

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

- Status: Active (offline evidence analysis only)
- Record type: Methodology
- Planning identity: `multi-objective-compiler-algorithm-evaluation-arena`
- Last reviewed: 2026-10-28

## Prior Work

Prior-work claims must resolve through canonical records under
`docs/bibliography/`.

## Hypothesis

- Authoritative comparisons retain capacity curves and Pareto frontiers; an
  aggregate score, if offered, is explicitly secondary and cannot hide
  time/quality/memory/size/verifier trade-offs.
- The arena measures every available execution/compiler stage without making
  a later target backend a prerequisite for the evaluation infrastructure; final
  `.malbolge` measurements are added when verified artifacts become available.
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

`benchmarks/arena/analyze.py` now implements one deterministic offline input
boundary, documented under `benchmarks/arena/README.md`. Its version-one JSON
keeps one explicit study question, hypothesis, baseline, falsification
observation, compiler/execution stage, target and host/toolchain identities,
positive time/memory budgets, and ordered cost objectives. Per-trial records
retain algorithm, challenge family/version/difficulty/seed, workload SHA-256,
trial number, outcome, named external verifier, verdict, exact paths to
experiment identity and raw sample, and measured cost dimensions. Claimed
verified timings above the study time budget, or reported resident memory
above its budget, fail admission without authorizing unmeasured resource use.

The analyzer compares only cohorts with identical seeds, workload digests, and
trial numbers at each challenge difficulty. The named verifier must agree
for each matched challenge and trial across compared algorithms. Unmatched,
duplicate, or unverifiable comparisons fail closed. Every comparison requires
the declared baseline. An independently
named verifier and an accepted verdict are required to *report* success;
rejection, exhaustion, no-solution, and tool failures remain visible.

The analyzer does not replay that verifier or authenticate the references yet.

Curves retain trial counts, exact success fractions, per-outcome counts, and
cost medians conditional on verified success. Medians are exact integer
fractions, including even-sized and very large samples. Observed ranges
and exact median absolute deviations describe successful-cost dispersion,
while an all-attempt elapsed-time summary exposes failed-run cost. These
statistics are descriptive, not confidence intervals or inferential evidence.

The Pareto relation
minimizes declared costs and maximizes verified trial count inside each matched
cohort; zero-success algorithms remain in curves but are omitted from the
conditional frontier. The reported highest verified difficulty is observed,
not extrapolated, and there is no single aggregate performance score.

An opt-in evidence preflight under `benchmarks/arena/evidence.py` now imports
the repository's existing experiment-run manifest parser. It matches each
reported trial to its named run, challenge family/difficulty/seed, target
profile, workload fingerprint, host/toolchain, oracle, outcome, and raw output.
Repository-root relative manifest files must be bounded, canonical, regular,
and parseable; referenced raw samples must be present, nonempty, and ordinary.

The preflight also supports an opt-in `arena-raw-v1` CSV check using
`--require-raw-rows`. This verifies that the complete raw CSV row multiset
matches the reported trial identities, outcomes and exact integer costs,
including failed trials. SHA-256 fingerprints of the inspected file bytes
support later reproducibility checks.

The additional opt-in `--require-trial-run-identity` mode extends each
experiment run manifest with a versioned `[arena_trial]` table containing the
exact trial number and SHA-256 of the full referenced `arena-raw-v1` CSV. It
requires one distinct run manifest per observation and automatically enables
complete raw-row checking; one unscoped aggregate run cannot stand in for
multiple purportedly independent repetitions. These producer-declared
bindings are not proof of physical replication or verifier execution.

A separate opt-in `--require-budget-agreement` mode reads every governed
experiment run's `[budget]` table and requires explicit positive integer
`seconds` and `memory_mib` declarations. Those values must convert exactly to
the study's declared `time_ns` and `memory_bytes`, without rounding or allowing
one algorithm a different recorded resource budget. This is a reporting
consistency check only, not physical runtime or peak-memory enforcement.

A raw match cannot independently prove that the CSV was measured accurately,
that a verifier actually ran, or that resource budgets were enforced.
The test fixtures establish only evidence linkage, not performance results.

A secondary paired baseline view now reports each candidate against the
predeclared baseline on exactly matched trials. Verification outcomes retain
four categories: both solved, baseline-only, candidate-only, and neither.
Cost wins/losses and exact median signed differences are computed only from
pairs where both solutions passed the named independent verifier. This avoids
pretending that a failed run has a successful solution size or cost. The paired
view does not replace the authoritative multidimensional frontier or supply
an inferential confidence bound.

This first slice intentionally does not require an executable final `.malbolge`
backend; the study's `stage` can describe available compiler or execution
boundaries. All results from real studies must separately pass experiment
manifest validation, benchmark protocol, independent semantic verification,
and raw evidence review before any performance conclusion is published.

## Retained historical comparisons

The read-only `benchmarks/arena/historical_pairs.py` adapter now admits two
existing September 4, 2026 source-pinned classic research records through the
same arena analysis engine. It requires the registered experiment run and
benchmark protocol to agree on challenge, host, raw path, outcome, target
profile, and pairing. It checks complete repeated strategy pairs, registered
quality-map fingerprints, complete registered raw CSV schemas, exact
structural counts, and source-byte hashes. The independent retained
`source-commit.txt` must agree with the manifest's recorded Git revision.
An explicit evidence-status marker states `source-reported-not-reverified`.

The prefix-decomposition study reports 8,836 versus 8,742 verifier calls,
with baseline/candidate timing medians of 831,921,051 and 835,180,632 ns.
Only two of five retained timing pairs favor the candidate; the observed
median speedup hypothesis is not supported on that host.

The verified-block-reuse study reports 17,672 versus 8,836 verifier calls,
with medians of 1,617,672,749 and 851,323,429 ns. All five retained pairs
favor reuse. This is a within-corpus, recorded-host result, not a generalized
performance or difficulty-scaling conclusion.

These are separate challenge families with different difficulty settings, so
their trials never share a comparison frontier. Only elapsed-time costs enter
the imported Pareto projection; registered verifier-call counts are presented
as a separate structural evidence field. The adapter cannot reproduce the
original host measurements or replay the independently recorded verifier.
The original study records remain the result authority.

## Evidence

- Expected durable artifact surface: `benchmarks/arena/`,
  `docs/research/methodology/`, `algorithms/`.
- Required evidence: reproducible run commands, retained challenge and
  algorithm identities, raw multidimensional samples, and independent verifier
  outcomes for every measured stage.
- `benchmarks/arena/analyze.py` admits and compares version-one JSON studies.
  The synthetic regressions under `benchmarks/arena/tests/test_analyze.py`
  exercise exact cohorts, conditional Pareto fronts, failed-trial retention,
  huge exact medians, descriptive dispersion, failure-inclusive elapsed costs,
  deterministic ordering, paired baseline win/loss and failure categories,
  forged verifier status, mismatched verifier cohorts, invalid objective data,
  and fail-closed CLI output.
- `benchmarks/arena/evidence.py` binds reported observations to the governed
  experiment-manifest run parser and to nonempty repository-local raw files.
  Synthetic regressions reject forged profile, challenge, oracle, algorithm,
  workload, host, outcome, and raw path identities; unsafe/missing file links
  and malformed/oversized manifests fail closed.
- `benchmarks/arena/raw_samples.py` optionally matches retained CSV content
  exactly against the reported trial set. Synthetic regressions cover missing,
  extra, duplicate and mismatched rows, plus malformed CSV inputs.
- `benchmarks/arena/trial_runs.py` admits a versioned per-trial manifest
  extension under strict opt-in preflight. Synthetic regressions check
  distinct trial-run bindings, raw-file digests, complete shared CSVs, malformed
  trial/schema metadata, aggregate-manifest reuse, and fail-closed CLI output.
- `benchmarks/arena/budget_links.py` optionally requires exact resource
  budget declarations from each linked run, rejecting missing/forged integers,
  unit mismatches, and one-unit study drift with fail-closed CLI regressions.
- `benchmarks/arena/historical_pairs.py` replays the two retained classic
  five-pair research sources into arena reports. Source-backed regressions
  assert exact observed medians, paired results, fingerprints, and rejection
  of corrupted raw timing, verifier counts, or preregistered identities.
- `benchmarks/arena/pyrightconfig.json` runs a separate standard-level
  BasedPyright check over the arena package, which is not part of the root
  repository's selected strict Pyright source roots. This complements pinned
  Ruff checks without changing shared tooling policy.
- Research evidence pending: raw sample content authentication,
  protocol-level manifest linkage, bibliography-backed context, real experiment
  configurations, retained negative/null results, and a reviewed conclusion
  with threats to validity.
- Performance evidence pending: raw measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.

## Results

The offline comparison implementation and synthetic regression evidence
exist. The historical adapter additionally projects already-retained host
measurements from the two classic research records above without generating
new samples. Its tests establish replay and cross-record consistency, not
original semantic correctness. No new capacity-scaling result is claimed.

## Threats to Validity

The default analyzer verifies structure, cohort matching, and reported
outcome consistency, but cannot establish that the named verifier ran or that
referenced samples and manifests exist. Opt-in linked-run preflight checks
manifest identities and nonempty sample presence, without verifying their
content or physical execution. It cannot establish actual resource budget
enforcement (only reported overages fail admission).

Median costs conditional on success can hide how long failed runs took;
verified counts remain a separate Pareto objective. For real experiments,
implementation bias, workload selection, hardware variation, truncated trials,
and insufficient replication remain threats.

## Conclusion

Open. The offline comparison slice is implemented; authentic evidence intake,
real stage measurements, protocol-level resource accounting, and reviewed
research conclusions remain. No technique is promoted to product architecture
until independently admitted evidence supports it.

## References

- [Parametric Multi Objective Algorithm
  Evaluation](../adr/parametric-multi-objective-algorithm-evaluation.md)
- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
- [Verification Trust
  Boundary](../../technical/adr/verification-trust-boundary.md)
