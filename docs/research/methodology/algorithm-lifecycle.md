# Algorithm promotion rejection and retirement lifecycle

## Status

Implemented

## Research Question

What evidence and method are required to promote, reject, or retire a research
algorithm without confusing experimental promise with production authority or
deleting negative scientific history?

## Background

Research algorithms need stable identity after an experiment succeeds, fails, or
is superseded. A production path must not appear merely because an algorithm is
interesting, and a failed or retired algorithm must not disappear in a way that
makes later comparisons unreconstructible.

- Status: Implemented
- Record type: Methodology
- Planning identity: `algorithm-promotion-rejection-and-retirement-lifecycle`
- Last reviewed: 2026-07-27

## Prior Work

- `scientific-method.md`
- `experiment-identity.md`
- `benchmark-protocol.md`
- `../adr/research-evidence-and-algorithm-mirror.md`

## Hypothesis

A lifecycle with evidence-linked promotion gates and durable
rejection/retirement
decisions prevents experimental work from silently acquiring production status
while preserving enough history to reproduce negative and superseded results.

The policy is rejected or materially weakened if an algorithm can reach
`promoted` without correctness, reproducibility, maintainability, portability,
and measured-benefit evidence, or if `rejected`/`retired` can erase the evidence
that explains the decision.

## Method

Every executable research mirror with `experiment.toml` also carries
`lifecycle.toml`. Schema v1 is validated by
`src/automation/repository/composition/scripts/validate/algorithm_lifecycle.py`
and binds the stable algorithm ID to its
research record and experiment manifest.

### States

`experimental`
: Default state. The research identity exists, but no promotion claim is made.
  Promotion and decision tables are forbidden so experimental metadata cannot
  masquerade as accepted evidence.

`promotion-candidate`
: The algorithm has durable evidence for all five promotion gates but has not
  received a production decision.

`promoted`
: All five promotion gates remain linked and an explicit dated decision records
  the rationale and durable decision evidence.

`rejected`
: A dated decision records the rejection rationale and must retain a repository
  path to the negative/null evidence that materially supports the decision.

`retired`
: A previously promotion-eligible algorithm keeps its promotion evidence, a
dated
  retirement decision, and the stable ID of the successor that supersedes it.
  Retirement preserves the old research identity rather than rewriting it into
  the successor.

### Promotion Gates

Promotion evidence is path-based rather than boolean. A promotion candidate,
promoted algorithm, or retired formerly promoted algorithm must link existing
repository evidence for:

1. correctness;
2. reproducibility;
3. maintainability;
4. portability; and
5. measured benefit.

Measured benefit remains subject to the benchmark/statistical evidence protocol;
correctness remains subject to the trusted verifier and cannot be inferred from
performance evidence.

### Allowed Lifecycle Movement

The intended forward lifecycle is:

- `experimental` -> `promotion-candidate` or `rejected`;
- `promotion-candidate` -> `experimental`, `promoted`, or `rejected`;
- `promoted` -> `retired` when a successor replaces it.

`rejected` and `retired` are historical terminal states for the same stable ID.
A materially revised technique that should be reconsidered receives a new stable
research ID rather than overwriting the rejected or retired record. Git history
remains additional provenance but is not a substitute for the checked-in
lifecycle state.

## Evidence

- All eight current research mirrors carry `lifecycle.toml` and validate as
  `experimental`; no current algorithm is falsely labeled promotion-ready.
- `src/automation/repository/composition/scripts/validate/research_mirror.py`
  now requires `lifecycle.toml` alongside
  `experiment.toml`, so new mirrors cannot omit lifecycle state.
- `tests/test_algorithm_lifecycle.py` verifies all five promotion gates,
  promoted-decision requirements, retained negative evidence for rejection,
  successor identity for retirement, and fail-closed experimental metadata.
- The lifecycle validator requires repository-relative evidence references and,
  for checked-in records, verifies that linked evidence paths exist.
- `tests/test_research_mirror.py` keeps the two-sided mirror identity and
  ignored
  output contract intact while lifecycle metadata becomes mandatory.

## Results

Lifecycle schema v1 is active. The repository currently reports eight
`experimental` algorithms and zero promotion candidates, promoted algorithms,
rejections, or retirements. That result is intentional: implementing lifecycle
policy does not fabricate promotion evidence for current research.

## Threats to Validity

The validator proves static evidence linkage and state-specific metadata, not
the
scientific quality of the linked evidence. A reviewer can still dispute whether
a correctness proof, benchmark distribution, maintainability argument, or
portability result is sufficient. Git history is needed to audit when a state
changed, while the checked-in record represents the current lifecycle state.

The schema does not automatically compare two algorithm versions or decide
whether a revision deserves a new stable ID; that remains a reviewed research
governance decision.

## Conclusion

Algorithm lifecycle schema v1 is the active promotion/rejection/retirement
contract. Experimental work cannot claim promotion without five durable evidence
classes and a decision record; rejection preserves negative evidence; retirement
preserves prior promotion history and successor identity. No algorithm is
promoted by this methodology record itself.

## References

- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
- [Experiment Identity](experiment-identity.md)
- [Benchmark Protocol](benchmark-protocol.md)
- [Scientific Method](scientific-method.md)
