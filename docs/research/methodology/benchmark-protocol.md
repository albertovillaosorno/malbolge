# Benchmark and statistical evidence protocol

## Status

Implemented

## Research Question

What evidence and method are required to evaluate benchmark and statistical
evidence protocol?

## Background

Define fair-comparison workloads, warmup, repetitions, confidence/dispersion
reporting, outlier policy, randomized-search treatment, time/quality tradeoffs,
resource normalization, and raw-sample retention rules. Performance claims must
identify uncertainty and may never substitute for semantic verification.

- Status: Implemented
- Record type: Methodology
- Planning identity: `benchmark-and-statistical-evidence-protocol`
- Last reviewed: 2026-07-26

## Prior Work

Prior-work claims must resolve through canonical records under
`docs/bibliography/`.

## Hypothesis

- The protocol fixes fair workload equivalence, warmup, repetitions,
  randomization, stopping rules, raw-sample retention, uncertainty/dispersion
  reporting, and treatment of failed stochastic runs.
- The research record separates observed evidence from interpretation and
  preserves negative/null outcomes that affect the conclusion.
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

Benchmark evidence protocol v1 is validated by
`scripts/validate/benchmark_protocol.py`. A performance record must reference an
Experiment Manifest v1 with `record_kind = "run"`; commit, workload SHA-256,
toolchain, and run outcome therefore come from the reproducible experiment
identity rather than being recopied into statistical metadata. The benchmark
record must agree with that run on host, accelerator, and raw-output path.

Every comparison additionally fixes:

- a question, hypothesis, explicit baseline, and rejection observation;
- one workload identity with `equivalent = true` across compared variants;
- warmup count and policy, at least three retained repetitions, ordering, and a
  stopping rule;
- `retain-all` outlier handling by default, or a preregistered filtering rule
  stated before observing retained samples;
- an explicit center statistic, dispersion statistic, and uncertainty method;
- one or more named objectives plus the time/quality tradeoff policy;
- host, accelerator, and positive memory budget; and
- a retained repository-relative raw-sample file.

Deterministic studies declare zero stochastic trials, zero failures, and no seed
list. Stochastic studies declare a positive trial count, one unique non-negative
seed per trial, and the number of failed trials. Failed trials remain in the
population and raw evidence; they cannot be deleted to improve a success or
time-to-solution distribution.

The checked-in examples under `benchmarks/research/protocol/examples/` are schema
fixtures, not Malbolge performance claims. They demonstrate deterministic and
stochastic records plus linked run manifests and retained raw CSV files.

## Evidence

- `tests/test_benchmark_protocol.py` covers equivalent workload enforcement, raw
  retention, repetition count, preregistered outlier filtering, deterministic
  versus stochastic separation, unique trial seeds, failed-trial retention, and
  linkage to a recorded experiment run.
- `benchmarks/research/protocol/examples/deterministic.benchmark.toml` and
  `stochastic.benchmark.toml` exercise the complete schema with retained raw CSV
  fixtures.
- Their linked `.experiment.toml` records demonstrate that benchmark host,
  accelerator, and raw-output identity must agree with exact source/workload/
  toolchain run provenance.
- `.dependencies/python/3.14.6/Scripts/python-jig.cmd -m
  scripts.validate.benchmark_protocol` validates the checked-in protocol corpus.

## Results

Two protocol fixtures validate: one deterministic comparison and one stochastic
comparison with four preregistered seeds and one retained failed trial. These
fixtures prove policy enforcement only; their numeric sample values are not
performance evidence about Malbolge, CUDA, or any research algorithm.

## Threats to Validity

The validator can prove metadata consistency and required evidence shape, not
that a chosen workload is scientifically representative or that a particular
statistical method is optimal. It intentionally permits several center,
dispersion, and uncertainty methods as long as they are declared before the
claim. Hardware noise, benchmark implementation bias, correlated samples, and
insufficient cross-machine replication remain study-specific threats that must be
discussed in the owning research record.

## Conclusion

Benchmark evidence protocol v1 is the active minimum for research performance
claims. Best-case numbers, changed workloads, discarded stochastic failures,
summary-only outputs, and post-hoc unregistered outlier filtering do not satisfy
the protocol. Statistical evidence remains subordinate to semantic verification.

## References

- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
- [Parametric Multi Objective Algorithm
  Evaluation](../adr/parametric-multi-objective-algorithm-evaluation.md)
