# DOOM quality and modernization pass

## Status

Active implementation. The manual oracle is accepted as generator input; the
source-bound generator and emitted transform remain incomplete.

## Purpose

Normalize a lawful user-supplied DOOM source tree before optional amalgamation.
The quality stage owns the target behavior, guest/runtime boundary,
deterministic
C profile, and validation postconditions. Generic source-tree matching and
source-bound reconstruction are delegated to `algorithms/diff/`.

## Scope

- `doom/`
- `algorithms/diff/`
- `algorithms/doom/generator/`
- `algorithms/doom/quality/`
- `algorithms/doom/adapters/`
- `algorithms/doom/quality/out/doom_fixed/`
- `tools/tidy/`

## Current Behavior

### Generation Model

The repository intentionally separates recipe, generic generator, domain policy,
and emitted transform.

```text
root doom/ -----------------------------+
                                        |
local quality/in/doom oracle --------+  |
                                     |  |
                                     v  v
                         generator/quality.py
                                  + doom.py
                                     |
                                     v
                              algorithms/diff
                                     |
                                     v
                            quality/main.rs
                                     |
                                     v
                         quality/out/doom_fixed/
```

`quality.py` is a thin recipe. It declares paths, a profile identity, and the
DOOM
domain module. The domain hard-pins the official source revision; generic
similarity
thresholds remain engine research parameters rather than DOOM product admission.
The
recipe must not grow a parallel diff implementation.

`doom.py` is the allowed home for DOOM-specific source lineage, compatibility,
behavior, and bug probes that cannot remain declarative.

`algorithms/diff/` remains generic and is governed by
`docs/technical/tooling/source-bound-diff-generator.md`.

`quality/main.rs` is ultimately generated output from the authoring step. It is
then versioned as the distributable transformation logic. The local oracle is
not
required to run it.

### Current Oracle State

Repository-root `doom/` is the untouched local baseline. Its official engine
source
is pinned to `id-Software/DOOM@a77dfb96cb91780ca334d0d4cfd86957558007e0`; 165
official files are verified against snapshot SHA-256
`20f6b67369b98c3f62b7c8ff34493ef9647c88bce7b85c82b9ecd72bad336d8b`. External
`data/` is outside that code pin. The ignored `algorithms/doom/quality/in/doom/`
tree
is the manually modernized oracle.

The current oracle contains 65 C translation units and passes:

- the real guest quality validator;
- 390/390 strict syntax checks across Windows, macOS, and Linux on x86-64 and
  AArch64;
- the runtime/manual-play evidence recorded by the quality README/changelog.

This means the oracle is ready to drive generator development. It does **not**
mean the quality stage is complete: generated `out/doom_fixed/` must still
reproduce and validate that oracle.

The checked-in comparison report is an older progress snapshot that recorded
143,662 unique findings in the baseline and 38,462 in an earlier oracle state.
It
must be regenerated only after accepted generated output exists.

### Source Admission

Exact whole-tree hashing is insufficient as the only admission mechanism because
harmless source changes would make the transformation needlessly fragile. The
DOOM recipe therefore intends to combine:

- canonical structural similarity;
- distributed stable source anchors;
- identity and compatibility behavior probes;
- conditional bug probes;
- threshold source binding for target-only transformation material.

The initial recipe records exploratory thresholds of 0.50 structural similarity,
0.66 anchor coverage, and 0.80 behavior similarity. These are technical starting
points for calibration, not legal thresholds.

Comments and formatting may be ignored when measuring lineage identity, but
required legal/provenance comments remain part of output correctness.

A source revision that already fixes a known original bug may remain compatible
when the generated postcondition is already true. Bug presence is not an
identity
requirement.

### Generated quality acceptance

The quality recipe now emits the real deterministic
`src/research/algorithms/composition/algorithms/doom/quality/main.rs`
from the exact pinned source revision, with `data/` outside the static source
snapshot
and authenticated as runtime passthrough policy. The generated transform
materializes
151 files under `quality/out/doom_fixed/` and the full tree matches the clean
local
oracle byte-for-byte. Its current transform SHA-256 is
`83f9c400ffd7ca17c75cc1cbc7a654794452ef37eac2adbf21af42a335766bd8`.

Generated output passes the 65-unit guest validator and the 390/390 six-target
strict
syntax matrix. Repeated generation/materialization are deterministic, wrong or
absent
source fails before publication, fixed-point behavior matches the authoring
source and
oracle, and provenance checks preserve the source LICENSE-MIT plus historical
attribution.
The compact comparison evidence now uses the generated tree as the after corpus.
The final regenerated quality transform SHA-256 is:

`83f9c400ffd7ca17c75cc1cbc7a654794452ef37eac2adbf21af42a335766bd8`

Its accepted output is the exact source for the completed amalgamation
stage, whose canonical `doom.c` SHA-256 is:

`a7fbecc1a6faba9fb974399d2b1def32c52734f1a557c0d8dbcdbc9357daab80`


## Invariants

- The ignored root source is never modified.
- The ignored manual oracle is authoring evidence, not a runtime dependency.
- Possessing generated `main.rs` without enough admitted source cannot
  materialize the normalized source tree.
- The exact authoring baseline materializes byte-identically to the oracle.
- Compatible later variants preserve legitimate upstream differences only when
  all transformation postconditions and validation gates pass.
- Blanket linter suppression is not an accepted modernization technique.
- Required upstream legal/provenance material is preserved.
- Platform effects remain behind explicit guest/host capabilities.
- Behavior-affecting fixes retain explicit differential/runtime evidence.
- Amalgamation consumes only an accepted generated multi-file tree.

## Failure Behavior

Unsupported source lineage, insufficient anchors, failed mandatory probes,
failed source binding, unresolved platform assumptions, malformed transform
material, provenance loss, or failed postconditions reject materialization.
Partially written output is not published as accepted quality output.

## Verification

Acceptance requires:

- exact baseline reconstruction against the manual oracle;
- deterministic repeated generator output;
- deterministic repeated materialization;
- the real guest validator at zero findings;
- the six-target 64-bit strict compile matrix;
- source-binding wrong/no-source rejection;
- identity/compatibility/bug-probe fixtures;
- native/runtime differential evidence for behavior-affecting fixes;
- adapter/capability tests;
- legal/provenance preservation checks;
- `jig validate --root .`.

Only after generated output is accepted should the compact comparison report be
refreshed to describe the baseline versus generated tree.

## References

- [Source-Bound Diff Generator](../tooling/source-bound-diff-generator.md)
- [Deterministic C Surface And Clang
  Tooling](../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Legal Research And Repository
  Boundary](../../legal/adr/legal-research-and-repository-boundary.md)
