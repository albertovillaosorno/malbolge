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
|-- exact.py          # exact authoring plan and materializer
|-- canonicalize.py   # identity-only normalization
|-- fingerprints.py   # content-defined stable-anchor primitives
|-- admission.py      # tree-level structural/anchor admission
|-- behavior.py       # behavior profile/observation evaluation
|-- probe_exec.py     # bounded no-shell portable probe programs
|-- behavior_programs.py # source/oracle probe authoring and observation
|-- gate.py           # conjunctive lineage + behavior admission
|-- source_binding.py # threshold-bound reconstruction material
|-- emit_rust.py      # deterministic Rust transform emission
`-- tests/
```

Exact authoring, generic identity primitives, tree-level structural/anchor
admission, behavior-evidence semantics, the portable process-probe executor, and
the threshold source-bound key-unlock primitive are implemented. Broader DOOM
probes, target-payload protection/recovery, and Rust emission remain active work
under the owning TODO.

## Implemented Exact Authoring Baseline

The first executable layer is deliberately stricter than later compatibility
admission. `build_exact_plan()` snapshots the local source and oracle, reuses
whole source files when their bytes already match, and represents modified
same-path files as deterministic source slices plus local oracle literals. The
current byte matcher uses fixed source blocks only to discover exact reusable
spans; those blocks are **not** the future stable admission anchors.

`materialize_exact_plan()` requires the exact source snapshot, writes into a
deterministic staging directory, verifies the complete target snapshot, and only
then publishes the output tree. Symlinks and special filesystem entries fail
closed. Empty directories are outside the version-one byte-tree model.

`ExactAuthoringPlan` is intentionally non-distributable. Its target-only literal
segments are local generator state. `source_binding.py` must transform that
material into source-bound recovery data before `emit_rust.py` is allowed to
serialize a public transform. This separation lets exact diff correctness be
tested without weakening the final source-binding invariant.

## Implemented Identity Primitives

`canonicalize.py` now provides deterministic line-ending normalization and an
explicit opt-in ASCII-whitespace canonicalizer. The whitespace helper is generic
and syntax-agnostic; it must not be used to claim C equivalence because literals,
preprocessor structure, and token boundaries require a language-aware consumer
canonicalizer. DOOM-specific lexical identity therefore remains outside the
generic engine.

`fingerprints.py` scans sliding content windows with a deterministic 64-bit
polynomial rolling hash. The rolling value selects sparse windows independent of
absolute offset, then selected windows receive SHA-256 fingerprints. Insertions can
therefore shift later bytes without invalidating unchanged anchor content while
avoiding a cryptographic hash at every byte offset. A deterministic minimum-rolling
fallback covers small/sparse inputs, and coverage is measured over unique SHA-256
digests. These fingerprints are lineage evidence, not encryption keys or a
completed source-binding construction.

## Implemented Tree Admission

`admission.py` consumes an explicit tree of already-canonicalized identity files.
The consumer decides which files belong to source identity; generic admission does
not infer language, asset type, or licensing policy. Candidate-only files do not
raise a score, and reference files receive equal aggregate weight regardless of
byte size. A large opaque asset therefore cannot dominate a source decision merely
by being large.

Structural similarity is symmetric overlap over a denser set of content-defined
fingerprints. Stable-anchor coverage remains asymmetric reference-anchor survival.
The two metrics are evaluated independently. Anchor coverage is averaged per
reference file rather than over one global anchor pool, and policy additionally
requires a minimum number of files with real matched anchors above the configured
per-file threshold. A single strongly matching file cannot satisfy a distributed
source-evidence requirement.

Structural admission is independently necessary but not sufficient. `gate.py`
combines source-lineage and behavior evidence conjunctively, so neither family can
offset failure in the other. Source binding remains a later independent gate.

## Implemented Behavior Semantics

`behavior.py` models deterministic behavior profiles and candidate observations.
Identity probes must all execute; successful identity observations contribute
equally to the configured behavior-similarity threshold. Compatibility probes are
hard preconditions. Bug probes classify a historical defect as `present`, `fixed`,
or `unknown`: `present` routes its correction to apply, `fixed` routes the
correction to skip without rejecting the source, and `unknown` fails closed.

`probe_exec.py` supplies the generic execution primitive without embedding
application semantics. A portable program is an ordered sequence of bounded process
commands with no shell interpolation. Executables are either logical consumer tool
IDs or artifacts beneath authorized roots; path arguments are structured under
`source`, `repository`, or per-program `scratch` roots. Timeouts and captured output
are bounded. Programs run against an isolated source mirror, and modifying that
mirror invalidates the probe while leaving user input untouched.

`behavior_programs.py` authors identity baselines from the original source and bug
baselines from both original source and corrected oracle. A bug program must produce
distinct selected-stdout transcript digests for `present` and `fixed`; candidate
output matching neither becomes `unknown`. Compatibility programs are success
preconditions. The domain still owns the actual programs and tool bindings.

`gate.py` then requires both source-lineage admission and behavior admission. Tests
explicitly prove that perfect behavior cannot rescue unrelated source and that
perfect source lineage cannot rescue a failed compatibility precondition.

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
in the generated transform. `source_binding.py` now implements the key-unlock
layer: a high-entropy secret is split T-of-N over GF(256), each share is masked
with HKDF-SHA-256 material derived from one canonical stable-anchor window, and a
commitment rejects malformed or incorrectly reconstructed keys. Selected anchors
are sampled by content digest and round-robin across files rather than by leading
file offset, so insertions can move surviving windows without changing their
binding identity.

This is deliberately **not** the payload format yet. Polynomial coefficients are
derived deterministically from the secret so repeated generation is byte-stable;
the construction therefore makes a computational source-binding claim, not an
information-theoretic perfect-secret-sharing claim. Target literals remain local
authoring state until an independently reviewed authenticated-encryption payload
construction is selected and integrated.

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
