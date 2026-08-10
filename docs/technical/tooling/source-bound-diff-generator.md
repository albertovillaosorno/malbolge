# Source-Bound Diff Generator

## Status

Active. Exact authoring/materialization, generic identity primitives, tree-level
structural/stable-anchor admission, the first language-aware consumer identity
adapter, generic behavior-evidence semantics, a portable bounded process-probe
executor, the first DOOM identity behavior program, and threshold source-bound
key
unlock, RFC 8439 ChaCha20-Poly1305, protected exact-plan materialization, and
standalone std-only Rust emission for the exact baseline are implemented.
Broader DOOM
compatibility/bug probes and compatible-variant admission/placement remain
unfinished.

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
- thin consumer recipes such as
  `src/research/algorithms/domain/algorithms/doom/generator/quality.py`
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
Before writing target files it must establish enough compatible source evidence
to
satisfy the recipe policy. It then reconstructs target output from admitted
source plus source-bound transformation material.

Possession of the generated transform alone must be insufficient to materialize
the local oracle.

All implemented public metadata boundaries now admit exact runtime types before
using them as evidence or touching output. Numeric thresholds and counts reject
boolean aliases. Identity trees, anchors, behavior observations, probe programs,
provenance pins, mapped and semantic edits, exact, relocatable, and compatible
plans, and source-bound shares require immutable exact records. Cryptographic
key, nonce, plaintext, AAD, and payload fields require exact bytes. Invalid
direct Python construction fails through the owning domain error rather than
relying on coercion or leaking `TypeError`, `AttributeError`, or `OverflowError`.
Compatible consumer mappers and output postconditions also wrap callback failures
and reject foreign return records before publication.

### Exact Authoring Baseline

The implemented exact layer snapshots regular files by normalized relative path,
rejects symlinks and special entries, and models the target as deterministic
file
instructions. Byte-identical target files reuse source files directly. Modified
same-path files reuse exact source byte spans discovered by a deterministic
block
matcher and retain only unmatched oracle bytes as local authoring literals.

This local plan is verification evidence, not a distributable transform. Raw
`OracleLiteral` bytes must never cross the public emission boundary. A later
source-binding stage must convert them to recovery material that cannot be
materialized without sufficient admitted source evidence.

Exact materialization verifies the static source snapshot before writing,
constructs
the result under a staging path, verifies the static target snapshot, and
publishes
only after equality succeeds. Recipes may declare authenticated
`passthrough_roots`
for external runtime inputs. Such roots must match source/oracle during
authoring, are
then excluded from static snapshots/source binding, and are copied recursively
from
the runtime candidate into staging. Symlinks and special entries still fail
closed. Recursive snapshot and passthrough enumeration also surfaces filesystem
scan failures instead of treating an inaccessible subtree as absent.
The matcher used for source-span reuse remains separate from canonical identity
and
stable admission anchors.

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

The generic anchor primitive scans sliding byte windows with a deterministic
64-bit
polynomial rolling hash and selects windows from that content-derived value.
Only
selected windows receive SHA-256 fingerprints. Selection therefore depends on
window content rather than absolute position while avoiding a cryptographic hash
at
every byte offset. Unchanged windows remain recognizable after insertions shift
their offsets. Duplicate SHA-256 digests count once for coverage, and a
deterministic
minimum-rolling-hash fallback prevents a non-empty sparse input from producing
no
evidence.

This primitive does not by itself admit a tree. Tree-level distribution rules,
minimum anchor counts, canonical language-aware views, ambiguous-match handling,
and the configured coverage threshold still belong to the unfinished admission
layer. Anchor digests are evidence only and must not be treated as
source-binding
secrets.

### Implemented Tree-Level Admission

The generic admission layer accepts only consumer-selected canonical identity
files. It is reference-driven: candidate-only files do not improve similarity.
Each reference file has equal aggregate weight, so large binary/opaque files
cannot
dominate merely through byte count or number of fingerprints. Consumers are
still
expected to exclude files that do not belong to source identity.

Structural similarity uses a denser content-defined fingerprint view and a
symmetric overlap score. Stable-anchor coverage uses the sparse anchor primitive
and asymmetric reference-anchor survival. Coverage is averaged per eligible
file,
not over a global anchor bag. Policy separately requires a minimum number of
files
with at least one real matching anchor and per-file coverage at or above the
configured threshold. This prevents one concentrated region from satisfying the
distributed lineage requirement.

Synthetic tests exercise exact and insertion-compatible admission, unrelated
source rejection, the representable floating-point boundary immediately above
and
below both thresholds, concentration in only one file, and candidate-only opaque
assets. These checks remain necessary but insufficient until behavior and source
binding also pass.

### First Language-Aware Consumer Identity

`src/research/algorithms/domain/algorithms/doom/generator/doom.py` provides the
first domain identity adapter.
It restricts identity to C/header files under `linuxdoom-1.10`, so the large WAD
and the separate IPX source family do not affect Linux source-lineage scores.
The
adapter applies C line splicing before comment handling, preserves
comment-internal
newlines, protects string/character literals, frames preprocessing tokens
unambiguously, and records preprocessor-directive line termination while
ignoring
ordinary presentation whitespace.

Synthetic tests prove comment/formatting equivalence, comment-looking bytes
inside
literals, whitespace-sensitive punctuator boundaries, preprocessor line endings,
backslash-newline splicing, malformed-comment failure, and source-tree
selection.
The generic engine remains language-agnostic; this adapter is consumer policy,
not
a C mode hidden inside `algorithms/diff`.

A local calibration smoke compared the 124 selected source identity files
against
the current normalized oracle descendant. All 124 source paths were present in
the
oracle view. With the provisional 0.50 structural and 0.66 anchor thresholds,
the
aggregate structural score was 0.780928, aggregate anchor coverage was 0.766396,
and 94 of 123 anchor-eligible source files individually met 0.66 coverage. This
is
useful stress evidence, not final compatibility calibration and not legal
evidence.

### Behavioral Identity

The implemented evaluator supports three probe classes supplied by a consumer:

- identity probes for stable lineage behavior;
- compatibility probes for transform preconditions;
- bug probes for conditional corrections.

Every identity probe must execute. Matching identity observations contribute
equally to the configured behavior-similarity threshold. Compatibility probes
are
hard preconditions. Bug probes classify the candidate as defect `present`,
already
`fixed`, or `unknown`; present defects route a named correction to apply, fixed
defects route that correction to skip, and unknown state fails closed. Bug
probes
therefore remain deliberately separate from identity probes.

`gate.py` combines source-lineage and behavior evidence conjunctively.
Behavioral
evidence never replaces source evidence, and source scores never replace failed
behavior preconditions. Synthetic tests include a
perfect-behavior/unrelated-source
clone and prove it is rejected. The generic evaluator consumes normalized
observations only; executing application-specific probes remains consumer work.

### Portable Behavior Programs

The generic execution layer now has a process-program representation designed to
be reproducible by the future Rust emitter. Commands never use shell
interpolation.
Executables are logical tool references or rooted artifacts; argv paths are
structured beneath authorized source, repository, or scratch roots. Commands
carry
explicit timeouts, expected exit status, bounded stdout/stderr capture, optional
stdin, plus explicit flags selecting stdout and/or process exit code into the
observation transcript. A command may instead require one exact exit code when
its
return value is a success precondition rather than behavior data.

A probe batch copies the candidate source into an isolated temporary mirror
before
execution. Programs receive the mirror path rather than the user input path. Any
program that changes the mirror is rejected, while the original tree is verified
unchanged. Compile-then-run programs are possible because one command may create
a
scratch executable consumed by a later command.

The executor validates the complete process description before snapshotting,
copying, or launching anything: roots/enums, executable records, argv tuples,
stdin bytes, exit codes, timeout/output limits, digest flags, program batches,
tool bindings, and source-immutability flags all use exact admitted types.

Behavior authoring runs identity programs on the original source. Bug programs
run
on both original source and the local corrected oracle; their selected-stdout
transcripts must differ. Those two digests become the portable `present` and
`fixed`
baselines. Candidate execution matching neither baseline produces `unknown` and
fails closed. Compatibility programs contribute success/failure rather than an
identity digest. Application-specific harnesses and logical tool resolution
remain
consumer policy; the generic engine only owns execution and transcript
semantics.

### First DOOM Executable Identity Probe

The first consumer program is
`windows-x86_64-clang22-v1:fixed-point-arithmetic`. It is intentionally an
identity
probe, not a bug probe. The DOOM domain asks pinned Clang 22.1.8 to compile the
candidate mirror's `linuxdoom-1.10/m_fixed.c` together with a repository-owned
MIT
freestanding harness and minimal standard-header shims. `lld-link` produces a
no-CRT x86-64 PE with a private entry point. The process exit code encodes
selected
`FixedMul`/`FixedDiv` results and becomes the transcript observation.

A local read-only smoke over the historical ignored source and the local
modernized
oracle produced the same transcript digest for both trees:
`f0b37d59c86384e4ee628ec0e637c60aaa7ca35e5ecdb826687fc35c37d133e2`.
The value is calibration evidence for this versioned Windows profile, not a
legal
identifier and not a claim that one probe is sufficient for final 0.80 behavior
admission. Repository tests use synthetic MIT `m_fixed` fixtures instead of
local
DOOM bytes and prove semantically equivalent implementations produce equal probe
transcripts.

The attempted `R_PointToDist(0, 0)` bug probe remains deliberately uncommitted.
Its
containing renderer translation unit retains many unrelated externally visible
roots under the available COFF/LTO toolchain. Rather than introduce fake
semantic
stubs or force unresolved symbols, that bug stays pending until it has an honest
isolation strategy or a different executable harness.

### Source Binding

The first source-binding layer is now implemented for high-entropy
reconstruction
key material. The generator selects canonical stable-anchor windows across
source
files by content digest, round-robins them across files, and computes
`T = ceil(N * configured_fraction)`. The secret is split T-of-N over GF(256).
Each
share is XOR-masked with HKDF-SHA-256 output whose input key material is the
exact
canonical anchor window and whose context also binds the source path, anchor
digest,
share coordinate, and transform context. A SHA-256 commitment rejects incorrect
reconstruction. Recovery independently enforces the configured minimum number of
distinct source files, so many surviving anchors from one large file cannot
satisfy
the distributed-evidence requirement by themselves.

The anchor sample is deliberately content-ranked rather than offset-ranked. In a
local read-only DOOM calibration with 127 bound shares and the provisional 0.66
threshold, the modernized oracle retained 105 recoverable shares; 84 were
required,
and the synthetic 32-byte key recovered successfully. The earlier offset-ranked
sample retained only 59, demonstrating why positional sampling was rejected
rather
than weakening the threshold. This smoke is engineering calibration, not a legal
criterion.

Repository-owned synthetic tests cover the RFC 5869 SHA-256 vector, every exact
T-of-N combination in the fixture, T-1 failure, empty/unrelated source
rejection,
metadata tampering, deterministic generation, multi-file distribution, and
source
insertions that shift anchor offsets.

Recovery also admits the distributable binding structure before inspecting the
candidate source: threshold/minimum-file counts are positive exact integers,
share coordinates and source-anchor identities are unique, paths are canonical,
and digest/share lengths are exact. Malformed metadata cannot lower a threshold
(for example via a negative or boolean value) or be ignored merely because
enough other shares survive.

The authenticated-encryption primitive itself is now implemented separately
using
RFC 8439 ChaCha20-Poly1305. Its Section 2.8.2 test vector matches exactly,
including
ciphertext and Poly1305 tag; a development cross-check against Node crypto
produced
the same bytes. The Python implementation remains deterministic
authoring/reference
code; the emitted exact Rust runtime now carries the fixed-limb runtime
implementation.

`protected.py` now combines key binding and authenticated encryption for exact
authoring plans. Every `OracleLiteral` is moved into one deterministic plaintext
stream. Protected instructions retain only source slices or offsets into that
stream.
The stream is encrypted as one ChaCha20-Poly1305 message; source/target
snapshots,
context, output paths, expected hashes, source paths, segment types, offsets,
and
lengths are authenticated as AAD. The 256-bit payload key is then bound to
canonical
source anchors. Recovery must unlock that key and authenticate the full payload
before
the transactional exact materializer can create its staging output.

A read-only DOOM exact-baseline smoke generated 152 protected instructions and a
2,116,232-byte ciphertext with a 16-byte tag. The binding contained 127 shares
with
an 84-share threshold and a 32-file minimum. After the payload key schedule was
strengthened to include unserialized canonical source bytes, the smoke was
rerun:
materialization under `.temp` again reproduced the 152-file local oracle
snapshot
exactly, while fresh source and oracle snapshots proved both input trees
remained
unchanged. The generated 4,655,420-byte Rust source also compiled through Rust
1.97.1
with `-D warnings --emit=obj`; executable linking on this workstation is blocked
only
by absent Windows SDK import libraries. All smoke outputs were deleted
afterward.

After the DOOM source revision was hard-pinned, the product recipe moved back to
the
exact emitter with `data/` as an authenticated passthrough root. A clean
temporary
oracle mirror excluding the already-detected accidental PowerShell root produced
a
4,646,568-byte Rust transform. Rust GNU 1.97.1 compiled and executed it
successfully
against the untouched root `doom/`; the output contained 151 files and matched
the
clean mirror byte-for-byte, while the WAD was copied from the runtime input. The
temporary mirror, transform, executable, and output were deleted afterward. The
unexpected entry was subsequently removed explicitly, and the accepted real
oracle
and transform were regenerated.

Shamir coefficients and the payload key are derived deterministically to
preserve
byte-identical generation. The payload key schedule includes a digest over the
consumer-selected canonical source identity bytes that is not serialized into
the
transform, together with authenticated-plan and literal-stream digests.
Transform
metadata plus a guessed target plaintext is therefore insufficient to reproduce
the
payload key without source evidence. The property remains computational source
binding
and authenticated reconstruction rather than information-theoretic secrecy or
DRM;
possessing admitted source is intentionally sufficient to unlock the transform.

The Python Poly1305 implementation is reference/authoring code. The emitted
exact Rust
runtime uses a fixed-limb implementation, derives raw anchor evidence from the
actual
candidate source tree, authenticates the payload before publication, and is the
current
distributable exact-baseline format. Compatible/fuzzy emission remains
fail-closed
until the runtime can reproduce consumer-selected canonical identity, structural
and
anchor admission, behavior probes, bug routing, and compatible placement
semantics.

### First Compatible Placement Primitive

`relocatable.py` now removes absolute-offset dependence from source-backed exact
segments. Authoring stores only SHA-256 boundary-window locators for each source
range. A candidate materializer requires each boundary to resolve uniquely and
copies
the current candidate bytes between the resolved boundaries. This preserves
insertions
inside an otherwise stable source range and preserves whole-file candidate
differences
for source-copy instructions. Missing, duplicate, reversed, or contracted
placement
evidence rejects transactionally.

This is deliberately a placement primitive, not compatible admission. Synthetic
tests
also prove a byte change at a required boundary still rejects. That negative
fixture
locks the reason for the next domain-mapped token layer: C comments and
formatting may
be irrelevant to identity while changing raw boundary bytes, so semantic
placement
must locate canonical units and map them back to candidate byte spans.
Target-only
literals remain local authoring material until compatible protection/emission
wraps
this layer. Exact and relocatable plan records now reject boolean range aliases,
mutable segment collections, foreign plan/instruction records, and non-Path
filesystem roots before placement begins.

### Mapped Semantic Compatible Placement

The second placement layer removes the byte-boundary limitation. Generic
`MappedView`
records canonical units together with the raw source span that produced each
unit.
`semantic.py` hashes those units with domain separation, authors non-equal
source to
target ranges using deterministic sequence matching, and stores only hashed
source
unit/context locators plus local target replacement bytes. Candidate placement
requires
a unique semantic range, edits only its mapped raw span, preserves all other
candidate
bytes, and re-maps the output to verify the exact intended canonical unit
sequence.

The first domain mapper is DOOM C. It retains raw spans through line-ending
normalization, comments, literals, directive line ends, and backslash-newline
splicing
without changing the existing identity stream. Synthetic tests preserve
candidate
comments, formatting, and an unrelated upstream function while applying a
semantic
replacement. Format-only oracle differences produce zero edits. A changed
required
semantic region remains fail-closed; later bug routing may explicitly skip a
named
correction when behavior evidence classifies that defect as already fixed.

A read-only equivalence smoke over the original and normalized local trees
processed
273 C/header files and 549,978 mapped units with zero mismatches against the
existing
canonicalizer. This proves identity-equivalent mapping, not final
compatible-tree
correctness. Mapped units now require exact byte streams, integer coordinates,
and immutable unit records; semantic locators/edits/plans require exact SHA-256
digests and immutable records, and build/apply validate views, context width,
plan, and mapper before placement.

`compatible.py` now composes admission, behavior evidence, file topology,
semantic
placement, conservative opaque-file gates, candidate-only preservation,
target-only
conflict checks, and transactional postconditions into an in-memory compatible
plan.
Bug correction routing remains intentionally fail-closed until correction IDs
are
attached to specific semantic edits; target-only bytes also remain local
authoring
material until compatible source-bound serialization exists.

The first full DOOM compatible-authoring smoke exposed a scalability defect in
generic
sequence matching and did not finish within the runner limit. The replacement
matcher
uses unique canonical k-grams at widths 8/4/2/1, a monotonic LIS anchor chain,
common
prefix/suffix trimming, and recursive gap partitioning. With that matcher the
same
read-only plan finishes in 11.159 seconds: 117 semantic-patch files, 7 mapped
candidate
copies, 2 opaque exact-gated files, and 26 target-only creates across 152 target
paths.
Those semantic files contain 6,257 edits and 251,933 raw replacement bytes.

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
src/research/algorithms/domain/algorithms/doom/generator/quality.py
             |
             v
       algorithms/diff
             |
             v
src/research/algorithms/composition/algorithms/doom/quality/main.rs
```

The second exact consumer now reuses the same generic engine for deterministic
amalgamation:
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

Source-binding failure occurs before accepted target files are published.
Partial
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

- `src/research/algorithms/composition/algorithms/diff/README.md`
- `src/research/algorithms/domain/algorithms/doom/generator/README.md`
- `docs/technical/interoperability/doom-modernization.md`
- `docs/technical/interoperability/doom-amalgamation.md`
- `docs/legal/adr/legal-research-and-repository-boundary.md`
