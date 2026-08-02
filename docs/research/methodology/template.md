# Research Record Template

## Status

Proposed

## Research Question

State one bounded research question that can be answered by the evidence this
record can realistically collect.

## Background

- Status: Proposed
- Research ID: `{stable-id}`
- Research class:
  `{engineering|benchmarking|optimization|replication|mathematical|exploratory}`
- Applicable overlays: `{zero or more additional classes}`
- Target profile(s): `{exact canonical identity/fingerprint where applicable}`
- Plan identity: `{commit/content hash/manifest identity}`

Explain why the question matters and what is deliberately outside scope.

## Prior Work

Cite canonical bibliography records. Identify state-of-the-art alternatives and
the exact baseline(s) used here, or explain why a direct comparison is
impractical.

## Hypothesis

State the falsifiable hypothesis before interpreting comparative results.
Exploratory work instead states an explicit decision/observation rule and labels
itself exploratory.

Record:

- primary hypothesis or exploratory decision rule;
- baseline expectation;
- observation that would reject or materially weaken the technique;
- observation that would be inconclusive rather than supportive.

## Method

Define before comparative execution:

- workload/input identities and target profile;
- implementation/configuration/toolchain identity;
- correctness verifier/oracle and authority boundary;
- resource budgets, timeout, stopping rules, and failure policy;
- seeds and all stochastic sources;
- primary/secondary metrics and analysis procedure;
- raw-output destination and retention policy;
- applicable method-overlay requirements from `scientific-method.md`.

Document any post-plan deviation explicitly instead of editing history.

## Evidence

### Correctness Evidence

State independently how candidate semantics/correctness are established. Invalid
candidates remain failures and do not enter performance-winning populations.

### Raw Evidence

Identify immutable or append-only raw samples/logs/verifier outcomes and their
experiment identity.

### Derived Evidence

Identify reproducible scripts/commands that turn raw evidence into summaries,
distributions, confidence/dispersion, Pareto metrics, figures, or tables.

### Evidence/Interpretation Boundary

Keep observations distinct from explanations. A useful form is:

- **Evidence identity:** `{artifact/sample}`
  - **Observed fact:** `{measurement/verifier fact}`
  - **Interpretation:** `{explanation}`
  - **Supports/weakens:** `{claim}`

## Results

Retain positive, negative, null, resource-exhausted, tool-failure, and
candidate-invalid outcomes when they affect the question. Apply only declared
exclusion rules; preserve raw excluded evidence.

## Threats to Validity

State method-appropriate limitations, confounders, generalization limits,
shared-oracle assumptions, environment sensitivity, selection effects, and
unresolved evidence. Do not mechanically claim causal-validity categories that
do not apply to the chosen research class.

## Conclusion

Choose one evidence state and justify it:

- `promote` (recommendation only; requires separate product contract/ADR);
- `retain-experimental`;
- `reject`;
- `inconclusive`;
- `superseded`.

State only conclusions supported by the retained evidence and declared scope.

## References

- [Academic research methodology and evidence model](scientific-method.md)
- Canonical external evidence is recorded under `docs/bibliography/`.
