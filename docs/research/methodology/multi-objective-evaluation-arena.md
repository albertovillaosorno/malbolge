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
trial numbers at each challenge difficulty. Unmatched or duplicate trials
fail closed. Every comparison requires the declared baseline. An independently
named verifier and an accepted verdict are required to *report* success;
rejection, exhaustion, no-solution, and tool failures remain visible.

The analyzer does not replay that verifier or authenticate the references yet.

Curves retain trial counts, exact success fractions, per-outcome counts, and
cost medians conditional on verified success. Medians are exact integer
fractions, including even-sized and very large samples. The Pareto relation
minimizes declared costs and maximizes verified trial count inside each matched
cohort; zero-success algorithms remain in curves but are omitted from the
conditional frontier. The reported highest verified difficulty is observed,
not extrapolated, and there is no single aggregate performance score.

This first slice intentionally does not require an executable final `.malbolge`
backend; the study's `stage` can describe available compiler or execution
boundaries. All results from real studies must separately pass experiment
manifest validation, benchmark protocol, independent semantic verification,
and raw evidence review before any performance conclusion is published.

## Evidence

- Expected durable artifact surface: `benchmarks/arena/`,
  `docs/research/methodology/`, `algorithms/`.
- Required evidence: reproducible run commands, retained challenge and
  algorithm identities, raw multidimensional samples, and independent verifier
  outcomes for every measured stage.
- `benchmarks/arena/analyze.py` admits and compares version-one JSON studies.
  The synthetic regressions under `benchmarks/arena/tests/test_analyze.py`
  exercise exact cohorts, conditional Pareto fronts, failed-trial retention,
  huge exact medians, deterministic ordering, forged verifier status, invalid
  objective data, and fail-closed CLI output.
- Research evidence pending: linked manifest admission, raw sample content
  authentication, bibliography-backed context, real experiment configurations,
  retained negative/null results, and a reviewed conclusion with threats to
  validity.
- Performance evidence pending: raw measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.

## Results

The offline comparison implementation and synthetic regression evidence
exist. These tests establish **analysis behavior only**. They are not run
samples or performance results from compiler algorithms, hosts, or target
profiles. No real result or capacity claim is made here.

## Threats to Validity

The analyzer verifies structure, cohort matching, and reported outcome
consistency, but cannot yet establish that the named verifier ran, that raw
samples and experiment manifests exist or agree with their contents, or that
resource budgets were actually enforced (only reported overages fail
admission). Median costs conditional on success can hide
how long failed runs took; verified counts remain a separate Pareto objective.
For real experiments, implementation bias, workload selection, hardware
variation, truncated trials, and insufficient replication remain threats.

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
