# Source-Bound Diff Generator

## Status

Scaffolded and active. Public recipe types, DOOM integration scaffolds, contracts,
and fail-closed behavior exist; matching, source binding, payload recovery, and
Rust emission are not implemented.

## Purpose

Define `algorithms/diff/`, a generic generator that learns deterministic
source-tree transformations from a local source/oracle pair and emits a
distributable transform that still requires sufficiently compatible source
material to reconstruct the target.

The engine is generic infrastructure. It must not contain DOOM-specific C
knowledge, source paths, bug lists, or host/runtime policy.

## Scope

- `algorithms/diff/`
- repository-owned synthetic fixtures under `algorithms/diff/tests/`
- thin consumer recipes such as `algorithms/doom/generator/quality.py`
- source-bound transform emission and materialization contracts

Application-specific behavior probes and compatibility policy remain with the
consumer rather than inside the generic engine.

## Current Behavior

### Generation Model

Generation has two distinct phases.

During authoring, a local recipe supplies an admitted source tree, local
target/oracle tree, output policy, structural/behavioral thresholds, and an
optional domain module. The oracle is development evidence and is not a required
distributable input.

During materialization, the emitted transform receives a candidate source tree.
Before writing target files it must establish enough compatible source evidence to
satisfy the recipe policy. It then reconstructs target output from admitted
source plus source-bound transformation material.

Possession of the generated transform alone must be insufficient to materialize
the local oracle.

### Canonical Identity

Whole-tree byte equality is too fragile for admission. Canonical identity may
ignore comments, whitespace, formatting, and line endings when computing
structural similarity and stable anchors.

Canonicalization is an identity mechanism only. It does not authorize dropping
comments, copyright/provenance text, or other source bytes from reconstructed
output. Output construction uses admitted source material and explicit
transformation rules.

Stable anchors should be token- or content-defined so harmless insertions do not
shift every anchor in a file. Aggregate similarity alone never authorizes
materialization.

### Behavioral Identity

The engine supports three probe classes supplied by a consumer:

- identity probes for stable lineage behavior;
- compatibility probes for transform preconditions;
- bug probes for conditional corrections.

Bug probes are not identity requirements. A compatible upstream revision that
already satisfies a postcondition must not be rejected merely because the
original defect disappeared.

Behavioral evidence supplements structural lineage; it never replaces the source
requirement. A separately written behavioral clone without enough admitted source
anchors must fail.

### Source Binding

Target-only material must be source-bound before distribution. The intended
construction derives or unlocks reconstruction material only after a configured
threshold of distributed source anchors is available.

The exact cryptographic primitive is intentionally unspecified at scaffold time.
Before implementation, the selected construction requires independent review and
negative tests. Threshold secret sharing is one candidate, not a pre-approved
choice.

### Exact Baseline and Compatible Variants

For the exact source tree used during generation:

```text
source + generated transform == oracle byte-for-byte
```

A later compatible source variant may preserve legitimate upstream differences
rather than matching the historical oracle hash. Such output must satisfy all
declared postconditions, behavior probes, provenance checks, and downstream
validators.

### Threshold Policy

Similarity percentages are consumer configuration, not generic constants. The
first DOOM quality recipe records exploratory values of 0.50 structural
similarity, 0.66 stable-anchor coverage, and 0.80 behavior similarity. Those
values remain provisional until calibration fixtures justify them.

### DOOM Consumers

The first consumer is DOOM quality generation:

```text
root doom/ + local normalized oracle
             |
             v
algorithms/doom/generator/quality.py
             |
             v
       algorithms/diff
             |
             v
algorithms/doom/quality/main.rs
```

A later consumer reuses the same generic engine for deterministic amalgamation:
normalized multi-file DOOM plus a local accepted single-file oracle produces the
source-bound transformation used to materialize canonical `doom.c`.

## Invariants

- The engine remains agnostic to DOOM, C, Malbolge, and license-specific policy.
- Canonicalization used for identity cannot silently delete source provenance.
- Behavior-only similarity cannot replace source-lineage evidence.
- Target material is not materialized before configured source-binding evidence
  succeeds.
- Exact-baseline generation/materialization is deterministic and byte-identical.
- Ordering does not depend on filesystem enumeration, locale, current time, or
  unversioned randomness.
- Similarity percentages are technical policy, not legal thresholds.
- Source binding is not documented as proof of copyright/license compliance or
  any jurisdictional conclusion.

## Failure Behavior

The generator and emitted transform fail explicitly on insufficient structural
similarity, insufficient anchor coverage, failed mandatory probes, failed source
binding, ambiguous source matches, malformed transform data, violated
preconditions, or failed output postconditions.

Source-binding failure occurs before accepted target files are published. Partial
target trees are never treated as accepted output.

## Verification

Generic tests use only repository-owned synthetic fixtures and cover:

- exact byte reconstruction;
- repeated deterministic generation/materialization;
- comment-only edits and whole-tree reformatting;
- source insertions that preserve stable anchors;
- created, deleted, moved, and modified files;
- binary payload policy when enabled;
- candidates immediately above/below admission thresholds;
- mandatory behavior mismatch and bug-already-fixed compatibility;
- wrong-source, no-source, and behavior-clone rejection;
- source-binding failure before target publication.

Repository closure uses `jig validate --root .` after focused tests pass.

## References

- `algorithms/diff/README.md`
- `algorithms/doom/generator/README.md`
- `docs/technical/interoperability/doom-modernization.md`
- `docs/technical/interoperability/doom-amalgamation.md`
- `docs/legal/adr/legal-research-and-repository-boundary.md`
