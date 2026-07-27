# Source-Bound Diff Generator

## Status

Active. Exact authoring/materialization, generic identity primitives, tree-level
structural/stable-anchor admission, the first language-aware consumer identity
adapter, generic behavior-evidence semantics, a portable bounded process-probe
executor, the first DOOM identity behavior program, and threshold source-bound key
unlock are implemented. Broader DOOM compatibility/bug probes, authenticated
target-payload recovery, and Rust emission remain unfinished.

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

The generic anchor primitive scans sliding byte windows with a deterministic 64-bit
polynomial rolling hash and selects windows from that content-derived value. Only
selected windows receive SHA-256 fingerprints. Selection therefore depends on
window content rather than absolute position while avoiding a cryptographic hash at
every byte offset. Unchanged windows remain recognizable after insertions shift
their offsets. Duplicate SHA-256 digests count once for coverage, and a deterministic
minimum-rolling-hash fallback prevents a non-empty sparse input from producing no
evidence.

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

### First Language-Aware Consumer Identity

`algorithms/doom/generator/doom.py` provides the first domain identity adapter.
It restricts identity to C/header files under `linuxdoom-1.10`, so the large WAD
and the separate IPX source family do not affect Linux source-lineage scores. The
adapter applies C line splicing before comment handling, preserves comment-internal
newlines, protects string/character literals, frames preprocessing tokens
unambiguously, and records preprocessor-directive line termination while ignoring
ordinary presentation whitespace.

Synthetic tests prove comment/formatting equivalence, comment-looking bytes inside
literals, whitespace-sensitive punctuator boundaries, preprocessor line endings,
backslash-newline splicing, malformed-comment failure, and source-tree selection.
The generic engine remains language-agnostic; this adapter is consumer policy, not
a C mode hidden inside `algorithms/diff`.

A local calibration smoke compared the 124 selected source identity files against
the current normalized oracle descendant. All 124 source paths were present in the
oracle view. With the provisional 0.50 structural and 0.66 anchor thresholds, the
aggregate structural score was 0.780928, aggregate anchor coverage was 0.766396,
and 94 of 123 anchor-eligible source files individually met 0.66 coverage. This is
useful stress evidence, not final compatibility calibration and not legal evidence.

### Behavioral Identity

The implemented evaluator supports three probe classes supplied by a consumer:

- identity probes for stable lineage behavior;
- compatibility probes for transform preconditions;
- bug probes for conditional corrections.

Every identity probe must execute. Matching identity observations contribute
equally to the configured behavior-similarity threshold. Compatibility probes are
hard preconditions. Bug probes classify the candidate as defect `present`, already
`fixed`, or `unknown`; present defects route a named correction to apply, fixed
defects route that correction to skip, and unknown state fails closed. Bug probes
therefore remain deliberately separate from identity probes.

`gate.py` combines source-lineage and behavior evidence conjunctively. Behavioral
evidence never replaces source evidence, and source scores never replace failed
behavior preconditions. Synthetic tests include a perfect-behavior/unrelated-source
clone and prove it is rejected. The generic evaluator consumes normalized
observations only; executing application-specific probes remains consumer work.

### Portable Behavior Programs

The generic execution layer now has a process-program representation designed to
be reproducible by the future Rust emitter. Commands never use shell interpolation.
Executables are logical tool references or rooted artifacts; argv paths are
structured beneath authorized source, repository, or scratch roots. Commands carry
explicit timeouts, expected exit status, bounded stdout/stderr capture, optional
stdin, plus explicit flags selecting stdout and/or process exit code into the
observation transcript. A command may instead require one exact exit code when its
return value is a success precondition rather than behavior data.

A probe batch copies the candidate source into an isolated temporary mirror before
execution. Programs receive the mirror path rather than the user input path. Any
program that changes the mirror is rejected, while the original tree is verified
unchanged. Compile-then-run programs are possible because one command may create a
scratch executable consumed by a later command.

Behavior authoring runs identity programs on the original source. Bug programs run
on both original source and the local corrected oracle; their selected-stdout
transcripts must differ. Those two digests become the portable `present` and `fixed`
baselines. Candidate execution matching neither baseline produces `unknown` and
fails closed. Compatibility programs contribute success/failure rather than an
identity digest. Application-specific harnesses and logical tool resolution remain
consumer policy; the generic engine only owns execution and transcript semantics.

### First DOOM Executable Identity Probe

The first consumer program is
`windows-x86_64-clang22-v1:fixed-point-arithmetic`. It is intentionally an identity
probe, not a bug probe. The DOOM domain asks pinned Clang 22.1.8 to compile the
candidate mirror's `linuxdoom-1.10/m_fixed.c` together with a repository-owned MIT
freestanding harness and minimal standard-header shims. `lld-link` produces a
no-CRT x86-64 PE with a private entry point. The process exit code encodes selected
`FixedMul`/`FixedDiv` results and becomes the transcript observation.

A local read-only smoke over the historical ignored source and the local modernized
oracle produced the same transcript digest for both trees:
`f0b37d59c86384e4ee628ec0e637c60aaa7ca35e5ecdb826687fc35c37d133e2`.
The value is calibration evidence for this versioned Windows profile, not a legal
identifier and not a claim that one probe is sufficient for final 0.80 behavior
admission. Repository tests use synthetic MIT `m_fixed` fixtures instead of local
DOOM bytes and prove semantically equivalent implementations produce equal probe
transcripts.

The attempted `R_PointToDist(0, 0)` bug probe remains deliberately uncommitted. Its
containing renderer translation unit retains many unrelated externally visible
roots under the available COFF/LTO toolchain. Rather than introduce fake semantic
stubs or force unresolved symbols, that bug stays pending until it has an honest
isolation strategy or a different executable harness.

### Source Binding

The first source-binding layer is now implemented for high-entropy reconstruction
key material. The generator selects canonical stable-anchor windows across source
files by content digest, round-robins them across files, and computes
`T = ceil(N * configured_fraction)`. The secret is split T-of-N over GF(256). Each
share is XOR-masked with HKDF-SHA-256 output whose input key material is the exact
canonical anchor window and whose context also binds the source path, anchor digest,
share coordinate, and transform context. A SHA-256 commitment rejects incorrect
reconstruction. Recovery independently enforces the configured minimum number of
distinct source files, so many surviving anchors from one large file cannot satisfy
the distributed-evidence requirement by themselves.

The anchor sample is deliberately content-ranked rather than offset-ranked. In a
local read-only DOOM calibration with 127 bound shares and the provisional 0.66
threshold, the modernized oracle retained 105 recoverable shares; 84 were required,
and the synthetic 32-byte key recovered successfully. The earlier offset-ranked
sample retained only 59, demonstrating why positional sampling was rejected rather
than weakening the threshold. This smoke is engineering calibration, not a legal
criterion.

Repository-owned synthetic tests cover the RFC 5869 SHA-256 vector, every exact
T-of-N combination in the fixture, T-1 failure, empty/unrelated source rejection,
metadata tampering, deterministic generation, multi-file distribution, and source
insertions that shift anchor offsets.

This does **not** yet make target literals distributable. Shamir coefficients are
derived deterministically from the high-entropy secret to preserve byte-identical
generation, so the current layer claims computational source binding rather than
information-theoretic secrecy. The authenticated payload cipher/serialization
format remains intentionally blocked pending independent review; `emit_rust.py`
must not serialize oracle literals until that layer exists.

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
