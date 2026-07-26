# Research Evidence And Algorithm Mirror

## Status

Accepted.

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

Research conclusions may recommend promotion, rejection, or retirement, but an
experiment does not modify trusted compiler semantics or production policy by
itself. Promotion requires an explicit owning technical decision or contract.

Product algorithms remain with their owning subsystem when they do not pose a
genuine research question.

## Alternatives Considered

### Put all algorithms under the research mirror

Rejected because it would force routine engineering transformations into fake
papers and obscure their actual product owner.

### Keep research documentation separate from executable experiments without a
stable identity

Rejected because results, code, and later papers would lose deterministic
traceability.

## Consequences

- Research can be reproduced and cited independently from production code.
- Null and negative results remain durable evidence.
- Product architecture is not accidentally determined by whichever experiment
  was written first.
- Multiple implementation languages can coexist under one algorithm identity.

## Implementation Notes

External sources resolve through `docs/bibliography/`. Generated experiment
artifacts remain under the owning algorithm `out/` directory and are ignored by
Git unless deliberately promoted into a versioned documentation artifact.
