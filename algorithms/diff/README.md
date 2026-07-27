# Source-Bound Diff Generator

`algorithms/diff/` is a generic generator for deterministic tree
transformations. It learns how to reproduce a target tree from a required input
tree without making the target tree itself a distributable prerequisite.

The engine is deliberately agnostic to DOOM, C, Malbolge, licenses, and the
quality pipeline. Application-specific policy belongs in the consumer.

## Planned Module Layout

```text
algorithms/diff/
|-- generate.py       # public recipe API/orchestration
|-- model.py          # deterministic transformation data model
|-- canonicalize.py   # identity-only normalization
|-- fingerprints.py   # structural similarity and stable anchors
|-- behavior.py       # identity/compatibility/bug probes
|-- source_binding.py # threshold-bound reconstruction material
|-- emit_rust.py      # deterministic Rust transform emission
`-- tests/
```

The modules are scaffolds until the owning TODO records implementation evidence.

## Core Contract

A consumer supplies two local trees while generating an algorithm:

```text
source tree + local oracle tree
             |
             v
       algorithms/diff
             |
             v
      generated transform
```

The generated transform is later distributed without the local oracle. It must
require a sufficiently compatible source tree before it can materialize the
normalized target.

Possession of the generated transformation alone must be insufficient to
materialize the oracle tree.

This is a technical source-binding invariant, not a legal conclusion about any
particular source tree, license, jurisdiction, or similarity percentage. Legal
and provenance review remains a separate repository responsibility.

## Admission Layers

Input admission is intentionally stronger than a whole-tree byte hash and more
robust than a traditional line patch. The planned engine combines:

1. canonical structural similarity;
2. distributed stable source anchors;
3. behavior and compatibility probes;
4. threshold source binding for target-only material.

Canonicalization is used only to recognize compatible lineage. It may ignore
comments, whitespace, formatting, and line endings for identity calculations.
It must not silently discard comments or provenance from the source bytes used
to construct output.

Content-defined or token-defined anchors should survive harmless insertions and
formatting changes better than absolute byte offsets. An input that is only
accidentally similar in aggregate must still fail if it lacks the required
distributed anchors or behavior.

## Probe Classes

Behavior probes have distinct roles. They must not be collapsed into one score.

- **identity probes** describe stable historical behavior expected from the
  admitted source lineage;
- **compatibility probes** establish preconditions required by a generated
  transform;
- **bug probes** detect whether a known defect is present and therefore whether
  a corrective transformation is required.

A candidate source is not rejected merely because an upstream revision already
fixed a bug that the oracle also fixes. In that case the relevant postcondition
should already hold and the correction can be skipped.

## Threshold Source Binding

Target-only bytes must not simply be stored as an unobfuscated recoverable blob
in the generated transform. The planned design binds recovery material to
distributed source anchors and reconstructs the materialization key only after a
configured threshold of source evidence is present.

The exact cryptographic construction is intentionally not selected by this
scaffold. It must be reviewed independently before implementation. A threshold
secret-sharing construction or an equivalent independently validated mechanism
may be used, but the security property is tested rather than assumed.

Required negative tests include:

- generated transform without source cannot materialize the target;
- unrelated source cannot materialize the target;
- a behavioral clone without sufficient source anchors cannot materialize it;
- anchor coverage below threshold fails before target files are written.

## Exact and Compatible Modes

For the exact baseline used to generate an algorithm:

```text
source + generated transform == oracle byte-for-byte
```

That equality is the strongest regression oracle for generator development.

A later compatible upstream variant may intentionally preserve changed comments
or already-corrected source. Such a result need not have the oracle hash. It must
instead satisfy all generated postconditions, behavior probes, and downstream
quality gates.

## Thresholds

Thresholds are consumer policy and must be calibrated empirically. The first
DOOM quality recipe records exploratory starting values of:

- source similarity: `0.50`;
- stable anchor coverage: `0.66`;
- behavior similarity: `0.80`.

These numbers are not legal thresholds and are not frozen by this scaffold.
Tests must justify any values eventually admitted by a product recipe.

## Required Tests

The generic implementation must use repository-owned synthetic fixtures rather
than third-party source. Tests must cover at least:

- exact byte reconstruction;
- deterministic repeated generation;
- comment-only source changes;
- whole-tree reformatting;
- source insertions that preserve stable anchors;
- behavior-compatible and behavior-incompatible variants;
- thresholds immediately above and below admission boundaries;
- wrong-source and no-source rejection;
- fake behavioral clones without source lineage;
- created, deleted, moved, and modified files;
- binary files and opaque asset policy when a consumer enables them.

See `docs/technical/tooling/source-bound-diff-generator.md` for the durable
technical contract.
