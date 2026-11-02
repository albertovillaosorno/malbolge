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
enforces the repository shape. The shared research layout discovery also
rejects linked algorithm directories and redirected in-root directory
ancestors before admitting an `experiment.toml` identity. Discovery admits only
native immediate children of the domain research root. It requires exact native
filesystem stat receipts, integer file-mode members, and boolean junction
results before interpreting modes or truthiness; forged host results fail
closed.

The direct research-mirror validator separately requires native stat containers,
exact integer file-mode fields, and boolean junction receipts for each path
component and discovered algorithm ID; foreign modes and truthiness hooks
cannot certify mirror identity. Directory scans admit only native immediate
children of the inspected root, not foreign or unrelated paths from an
untrusted directory iterator. Shared discovery receipts must be native tuples
of distinct IDs and canonical executable paths; duplicated or redirected ID
projections cannot satisfy the mirror contract. Both directory scanners
reject repeated entries before sets or maps can silently collapse their
identity.

Every direct research ID under either mirror root must exist on both sides.
The special composition state-graph experiment and domain algorithm
directories must not publish the same research ID: discovery rejects a collision
instead of silently replacing either physical experiment.

Mirror identity also
rejects research IDs differing only under Unicode case folding and canonical NFC
normalization:
those names are distinct on some POSIX filesystems but can alias on
case-insensitive or normalization-insensitive hosts.

Each research ID must also be one portable path component: `.`/`..`, forward
or backward separators, colons (including Windows drive-relative names),
Windows device names, and trailing dots or spaces are not admissible, even on
POSIX hosts.

The documentation half requires `README.md` and `research.md`; the executable
half requires
`README.md`, `experiment.toml`, and `tests/`. The validator asks Git itself, via
`check-ignore --no-index`, whether `algorithms/<id>/out/` itself is ignored.
A rule matching only a synthetic child filename cannot satisfy this
directory-level output policy.

The Git ignore probe has a 15-second timeout
and requires a native completed process whose exact native command arguments
match the requested directory and whose integer exit is zero (ignored) or one
(not ignored). Boolean, floating-point, missing, or foreign process receipts
cannot establish output policy.

Injected output-ignore predicates must also
return an exact native Boolean for each research ID: a truthy integer, string,
or foreign truthiness hook cannot certify that local artifacts are isolated.
CLI diagnostics preserve the validator's errors without invoking arbitrary
host-exception formatting hooks.

Optional `math/algorithms/<id>.tex` remains a
research-specific addition rather than a universal mirror requirement.

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
- Required document/executable/test paths are physical in-repository regular
  files and directories; symlink and junction aliases (including parent
  components and direct research IDs) never satisfy the mirror contract.
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

- `.dependencies/python/3.14.7/Scripts/python-jig.cmd
  src/automation/repository/composition/scripts/validate/research_mirror.py`
  currently validates nine mirrored IDs, including the repository template;
- `tests/test_research_mirror.py` covers the current repository plus
  documentation-only, executable-only, empty-mirror, and product-algorithm
  exception boundaries;
- the explicit non-research suites `algorithms/diff/` and `algorithms/doom/`
  share the executable algorithms root but are not forced into academic mirrors.
