# Academic research methodology and evidence model

## Status

Active methodology

## Research Question

What minimum evidence permits a Malbolge compiler/runtime research record to
support, weaken, reject, or promote a technical claim without conflating
correctness, performance, and interpretation?

## Background

Malbolge is both an implementation project and a compiler-research platform.
Research therefore needs a stricter boundary than “the benchmark got faster.” A
candidate may be fast and wrong, correct but slower, useful only for one
profile,
or statistically noisy. All four outcomes are scientifically meaningful.

External prior art reinforces two design choices used here. ACM SIGSOFT's
Empirical Standards are method-specific rather than one universal checklist, and
their benchmarking/optimization guidance emphasizes reproducible setup,
appropriate baselines, repeated stochastic or noisy measurements, raw-result
retention, and explicit separation of evidence from interpretation. The ACM
artifact-evaluation practice additionally motivates documented, exercisable
artifacts and automated reproduction paths. Malbolge defines its own acceptance
rules around those ideas.

- Status: Active methodology
- Record type: Methodology
- Planning identity: `academic-research-methodology-and-evidence-model`
- Last reviewed: 2026-07-26

## Prior Work

- [ACM SIGSOFT Empirical Standards for Software
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
  Engineering](../../bibliography/provenance-and-methodology/research/acm-sigsoft-empirical-standards.md)
  provides method-specific prior art for engineering research, benchmarking,
  optimization studies, and replication.
- [ACM-style artifact evaluation and
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
  reproducibility](../../bibliography/provenance-and-methodology/research/acm-artifact-evaluation.md)
  provides prior art for documented, consistent, complete, exercisable research
  artifacts and reproducible computational results.
- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md) defines the
  repository
  boundary between genuine algorithm research and ordinary product engineering.

## Hypothesis

The repository can prevent most accidental research overclaiming if every
research record fixes the following before interpreting results:

1. a bounded question and applicable research class;
2. a falsifiable hypothesis or, for exploratory work, an explicit decision rule;
3. the baseline and the observation that would reject or materially weaken the
   proposed technique;
4. an independent correctness oracle/verifier where the claim can affect program
   semantics;
5. experiment identity, workload/resource budgets, and stochastic controls;
6. primary metrics and analysis rules before looking at comparative outcomes;
7. durable raw evidence including failures, negative results, and null results;
8. a separate interpretation/conclusion that does not rewrite observed data.

This methodology is itself rejected as insufficient if a later research record
can satisfy all required fields while still making an unsupported promotion or
performance claim without an explicit documented deviation.

## Method

### Research Class

Every research record declares one primary class and any applicable overlays.
The class selects additional evidence requirements; it does not change the
repository's correctness trust boundary.

- **Class:** `engineering`
  - **Use in Malbolge:** New compiler/runtime artifact or technique
  - **Additional required evidence:** Need/relevance, artifact description,
                                      limitations, justified
                                      alternative/baseline comparison

- **Class:** `benchmarking`
  - **Use in Malbolge:** Performance, scalability, latency, memory, throughput
  - **Additional required evidence:** Exact workload/setup, raw samples,
                                      repetitions/stability, resource identity,
                                      uncertainty/dispersion

- **Class:** `optimization`
  - **Use in Malbolge:** Search, superoptimization, heuristics, ML-guided search
  - **Additional required evidence:** Search/solution space, fitness functions,
                                      baseline, parameters, stochasticity,
                                      seeds/trials, distribution/quality
                                      comparison

- **Class:** `replication`
  - **Use in Malbolge:** Deliberate repeat of an earlier result
  - **Additional required evidence:** Original study/result identity,
                                      replication motivation, exact
                                      preserved/changed factors, outcome
                                      comparison

- **Class:** `mathematical`
  - **Use in Malbolge:** Proof, exhaustive correspondence, algebraic reduction
  - **Additional required evidence:** Explicit domain, assumptions,
                                      theorem/property statement, proof or
                                      exhaustive/machine-checked correspondence

- **Class:** `exploratory`
  - **Use in Malbolge:** Question-forming work without a defensible directional
                         hypothesis
  - **Additional required evidence:** Scope, observation protocol, stopping
                                      rule, retained observations, criteria for
                                      promoting a later hypothesis

A record may combine classes, for example `engineering + benchmarking` or
`optimization + benchmarking`. It must satisfy each applicable overlay. Do not
apply causal-experiment validity language mechanically to mathematical proofs or
artifact engineering when the construct does not exist.

### Before Running Comparative Experiments

A comparative record freezes or versions:

- research ID and research class;
- question and hypothesis/decision rule;
- exact baseline(s) and why each is appropriate;
- rejection/material-weakening observation;
- correctness oracle or verifier and its authority boundary;
- target profile and input/workload identities;
- implementation/configuration/toolchain identity;
- resource budget, stopping rule, timeout/failure policy;
- seeds and stochastic sources when applicable;
- primary metrics and analysis procedure;
- raw-output destination and retention policy.

“Preregistered” in this repository means these items are committed or otherwise
content-addressed before the result being interpreted is generated. It does not
claim registration with an external registry.

Exploratory work may omit a directional hypothesis, but it must label itself
exploratory and cannot retrospectively present an observed pattern as a
preregistered confirmatory hypothesis. A subsequent confirmatory study receives
a
new experiment identity.

### Correctness Before Quality

Correctness evidence and optimization quality are separate channels.

For semantics-affecting compiler/runtime research, a candidate result is not
eligible for performance interpretation until the trusted verifier/oracle
accepts
it under the declared target profile. A faster invalid result is recorded as a
correctness failure, not a performance win.

Correctness evidence should be independent of the optimized implementation where
practical: differential implementation, exhaustive bounded comparison,
translation validation, property oracle, or machine-checked correspondence.
Where independence is impossible, the record states the shared assumptions as a
threat to validity.

### Observations Versus Interpretation

Research records use the following evidence discipline:

- **Layer:** `plan`
  - **Contains:** question, class, hypothesis, baseline, metrics, rejection rule
  - **May be rewritten after results?:** only by versioned deviation note

- **Layer:** `raw evidence`
  - **Contains:** samples, logs, verifier outcomes, failures, environment facts
  - **May be rewritten after results?:** no; append/re-run under new experiment
                                         identity

- **Layer:** `derived evidence`
  - **Contains:** summaries, confidence/dispersion, Pareto/quality metrics
  - **May be rewritten after results?:** reproducibly regenerated from raw
                                         evidence

- **Layer:** `interpretation`
  - **Contains:** explanation, implications, limitations
  - **May be rewritten after results?:** yes, with evidence references

- **Layer:** `conclusion`
  - **Contains:** supported/weakened/rejected/inconclusive/promotion
                  recommendation
  - **May be rewritten after results?:** yes when new evidence is added, never
                                         by deleting contrary evidence

A result table must make it possible to distinguish an observed value from the
researcher's explanation of that value.

### Negative, Null, And Failed Runs

Negative and null results are first-class evidence when they affect the research
question. They remain in the research record even when the technique is rejected
or superseded.

Failed runs are classified rather than silently dropped:

- `candidate-invalid`: verifier/correctness failure;
- `experiment-invalid`: environment/protocol failure making the sample unusable;
- `resource-exhausted`: declared budget reached;
- `tool-failure`: implementation/infrastructure failure;
- `valid-negative`: valid run whose outcome weakens/rejects the technique.

Exclusion from quantitative summaries requires a predeclared rule or an explicit
post-hoc deviation note. The raw failure evidence remains retained.

### Benchmarking Overlay

Benchmark claims require:

- equivalent semantic workloads and target profiles across compared systems;
- exact hardware/OS/compiler/runtime configuration;
- warmup policy when relevant;
- enough repetitions/duration to assess stability, or a justification when
  repetition is impractical;
- every raw sample retained before aggregation;
- stated outlier/exclusion policy;
- central tendency plus dispersion/uncertainty appropriate to the data;
- resource consumption relevant to the claim, not wall time alone when another
  scarce resource materially differs;
- no best-of-N claim unless best-of-N is itself the declared decision problem.

Existing classic batch measurements, for example, cannot be reused as evidence
for current-profile batching without measuring that distinct workload.

### Optimization/Search Overlay

Optimization, superoptimization, heuristic, ML-guided, or randomized search
records additionally define:

- solution representation and complete admitted search-space constraints;
- objective/fitness equations and optimization direction;
- justified baseline, including random/brute-force floor where appropriate;
- algorithm/heuristic identities and parameter values;
- all sources of stochasticity;
- deterministic seed set or seed-generation rule;
- multiple trials for stochastic approaches unless resource limits are
  justified;
- stopping rule independent of whether a favorable result has appeared;
- distributions/variation and solution quality, not only the best candidate;
- deterministic verifier acceptance before a candidate counts as valid.

Search hashes/caches may accelerate lookup but cannot replace semantic
verification.

### Replication

A replication record identifies the exact prior result and labels factors as
`preserved`, `intentionally changed`, or `uncontrolled`. Re-running the same raw
data/analysis is reproduction; collecting or generating a new experimental run
is treated as replication in the repository record. Disagreement is retained as
evidence rather than normalized away.

### Promotion Boundary

Research evidence never promotes itself into trusted product semantics.

A research conclusion may recommend:

- `promote`: evidence supports engineering integration under a separate owning
  technical contract/ADR;
- `retain-experimental`: promising but evidence or portability is incomplete;
- `reject`: evidence materially rejects the technique for the declared scope;
- `inconclusive`: evidence does not distinguish the technique from baseline;
- `superseded`: later work replaces the technique while retaining its record.

Promotion requires the owning product contract to name the research evidence and
rerun or translate the relevant correctness gates. A research algorithm remains
untrusted until that engineering boundary is crossed explicitly.

## Evidence

The durable evidence model is now explicit in this methodology and the research
record template. It is bibliography-backed by ACM SIGSOFT method-specific
standards and ACM-style artifact-evaluation practice.

Repository evidence required by this methodology includes:

- stable research/experiment identities;
- plan fields fixed before comparative interpretation;
- independent correctness evidence where applicable;
- raw and derived evidence provenance;
- explicit negative/null/failure retention;
- method-specific overlays;
- threats to validity and documented deviations;
- a conclusion state that cannot silently rewrite product architecture.

This methodology intentionally does not claim that every future research record
is reproducible merely because the template exists. Individual records still
need their own executable artifacts, manifests, raw evidence, and replication
where claimed.

## Results

The repository now has a concrete evidence contract suitable for downstream
algorithm research. It distinguishes research planning from observation and
interpretation, separates correctness from performance, defines negative/null
retention, and provides method-specific requirements for the compiler research
classes expected in this project.

The immediate downstream test of this methodology is the algorithm-mirror
contract and later Malbolge-specific optimization/state-graph research. If those
records cannot state a baseline, falsification condition, verifier boundary, and
retained evidence using this model, the methodology must be revised rather than
silently bypassed.

## Threats to Validity

- The policy is tailored to computational/compiler research and is not a general
  human-subjects research protocol.
- A committed plan reduces hindsight bias but is not equivalent to external
  preregistration or independent peer review.
- Exact reproducibility can still be limited by unavailable hardware,
  proprietary
  systems, nondeterministic platforms, or external datasets; deviations must be
  recorded rather than hidden.
- Method classification is a judgment call. Records combining multiple methods
  may need multiple overlays.
- A trusted verifier can itself be wrong; verifier authority and independent
  differential evidence remain separate technical concerns.

## Conclusion

Adopt this evidence model for repository research. No compiler/runtime research
claim is eligible for promotion merely because it improved one metric. The
record must first survive its declared correctness boundary, baseline,
falsification rule, provenance requirements, applicable method overlays, and
threats-to-validity review.

## References

- [ACM SIGSOFT Empirical Standards for Software
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
  Engineering](../../bibliography/provenance-and-methodology/research/acm-sigsoft-empirical-standards.md)
- [ACM-style artifact evaluation and
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
  reproducibility](../../bibliography/provenance-and-methodology/research/acm-artifact-evaluation.md)
- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
