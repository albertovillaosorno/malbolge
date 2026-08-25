# Research Evidence And Algorithm Mirror

## Status

Accepted.

## Decision ID

`jig.malbolge.research.research-evidence-and-algorithm-mirror`

## Context

The repository is both a product implementation and a compiler-research
platform. Experimental algorithms need academic evidence and executable code,
but ordinary engineering transformations such as DOOM source normalization do
not become research merely because they contain algorithms.

Research also needs to preserve failed ideas instead of letting performance
experiments silently become production architecture.

## Decision

Genuine algorithm research uses a stable research ID mirrored between
`docs/research/algorithms/<id>/` and `algorithms/<id>/`.

The documentation side owns the research question, hypotheses, prior work,
method, correctness boundary, measurements, results, threats to validity, and
conclusion. The executable side owns implementations, experiment configuration,
tests, verifier integration, and Git-ignored local `out/` artifacts.

`src/automation/repository/composition/scripts/validate/research_mirror.py`
enforces the repository shape. Every direct
research ID under either mirror root must exist on both sides. The documentation
half requires `README.md` and `research.md`; the executable half requires
`README.md`, `experiment.toml`, and `tests/`. The validator asks Git itself, via
`check-ignore --no-index`, whether `algorithms/<id>/out/` is ignored. Optional
`math/algorithms/<id>.tex` remains a research-specific addition rather than a

universal mirror requirement.

Research conclusions may recommend promotion, rejection, or retirement, but an
experiment does not modify trusted compiler semantics or production policy by
itself. Promotion requires an explicit owning technical decision or contract.

Product algorithms remain with their owning subsystem when they do not pose a
genuine research question.

## Advantages

- Makes the research evidence and algorithm mirror boundary explicit,
  reviewable, and stable before implementation depends on it.

## Disadvantages

- The decision constrains future implementation until a later ADR deliberately
  supersedes it.

## Consequences

- Research can be reproduced and cited independently from production code.
- Null and negative results remain durable evidence.
- Product architecture is not accidentally determined by whichever experiment
  was written first.
- Mirror drift, documentation-only research, executable-only research, missing
  experiment/test structure, and tracked local-output policy fail validation.
- Multiple implementation languages can coexist under one algorithm identity.

## Rejected Alternatives

### Put all algorithms under the research mirror

Rejected because it would force routine engineering transformations into fake
papers and obscure their actual product owner.

### Keep research documentation separate from executable experiments without a
stable identity

Rejected because results, code, and later papers would lose deterministic
traceability.

## Evidence

External sources resolve through `docs/bibliography/`. Generated experiment
artifacts remain under the owning algorithm `out/` directory and are ignored by
Git unless deliberately promoted into a versioned documentation artifact.

Executable evidence:

- `.dependencies/python/3.14.6/Scripts/python-jig.cmd
  src/automation/repository/composition/scripts/validate/research_mirror.py`
  currently validates eight mirrored IDs, including the repository template;
- `tests/test_research_mirror.py` covers the current repository plus
  documentation-only, executable-only, empty-mirror, and product-algorithm
  exception boundaries;
- the explicit non-research suites `algorithms/diff/` and `algorithms/doom/`
  share the executable algorithms root but are not forced into academic mirrors.
