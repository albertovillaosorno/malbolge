# Source-Bound Diff Generator

## Status

Active. Exact authoring/materialization, generic identity primitives, and
tree-level structural/stable-anchor admission are implemented. Language-aware
consumer identity, behavior probes, source binding, payload recovery, and Rust
emission remain unfinished.

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

### Exact Authoring Baseline

The implemented exact layer snapshots regular files by normalized relative path,
rejects symlinks and special entries, and models the target as deterministic file
instructions. Byte-identical target files reuse source files directly. Modified
same-path files reuse exact source byte spans discovered by a deterministic block
matcher and retain only unmatched oracle bytes as local authoring literals.

This local plan is verification evidence, not a distributable transform. Raw
`OracleLiteral` bytes must never cross the public emission boundary. A later
source-binding stage must convert them to recovery material that cannot be
materialized without sufficient admitted source evidence.

Exact materialization verifies the source snapshot before writing, constructs the
result under a staging path, verifies the complete target snapshot, and publishes
only after exact equality succeeds. The matcher used for source-span reuse is
separate from future canonical identity and stable admission anchors.

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

### Implemented Stable-Anchor Primitive

The generic anchor primitive scans sliding byte windows, hashes them with SHA-256,
and selects windows using a digest-derived sampling predicate. Because selection
depends on content rather than absolute position, unchanged windows remain
recognizable after insertions shift their offsets. Duplicate digests are counted
once for coverage, and a deterministic minimum-digest fallback prevents a
non-empty small/sparse input from accidentally producing no evidence.

This primitive does not by itself admit a tree. Tree-level distribution rules,
minimum anchor counts, canonical language-aware views, ambiguous-match handling,
and the configured coverage threshold still belong to the unfinished admission
layer. Anchor digests are evidence only and must not be treated as source-binding
secrets.

### Implemented Tree-Level Admission

The generic admission layer accepts only consumer-selected canonical identity
files. It is reference-driven: candidate-only files do not improve similarity.
Each reference file has equal aggregate weight, so large binary/opaque files cannot
dominate merely through byte count or number of fingerprints. Consumers are still
expected to exclude files that do not belong to source identity.

Structural similarity uses a denser content-defined fingerprint view and a
symmetric overlap score. Stable-anchor coverage uses the sparse anchor primitive
and asymmetric reference-anchor survival. Coverage is averaged per eligible file,
not over a global anchor bag. Policy separately requires a minimum number of files
with at least one real matching anchor and per-file coverage at or above the
configured threshold. This prevents one concentrated region from satisfying the
distributed lineage requirement.

Synthetic tests exercise exact and insertion-compatible admission, unrelated
source rejection, the representable floating-point boundary immediately above and
below both thresholds, concentration in only one file, and candidate-only opaque
assets. These checks remain necessary but insufficient until behavior and source
binding also pass.

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
