# User-supplied DOOM source interoperability generator

## Status

Pending quality acceptance and generic source-bound diff implementation.

## Purpose

Transform the accepted normalized multi-translation-unit DOOM source into one
canonical C translation artifact without making the local single-file oracle a
distributable dependency.

This is the planned second DOOM consumer of `algorithms/diff/`.

## Scope

- `algorithms/diff/`
- `algorithms/doom/generator/`
- `algorithms/doom/quality/out/doom_fixed/`
- `algorithms/doom/amalgamate/main.rs`
- `algorithms/doom/amalgamate/out/doom_amalgamated.c`
- `tests/applications/doom/out/doom.c`

## Current Behavior

### Generation Model

A future thin amalgamation recipe will pair:

- accepted generated multi-file quality output;
- a local ignored single-file oracle that has already passed semantic
  amalgamation validation.

`algorithms/diff/` then emits the source-bound `amalgamate/main.rs` transform.
The transform materializes `doom_amalgamated.c` from sufficiently compatible
normalized source without requiring the local oracle.

The generic diff is **not** the semantic authority for C amalgamation. The DOOM
domain policy and pinned Clang tooling must establish that the oracle and
materialized result preserve:

- translation-unit boundaries and preprocessing environments;
- internal-linkage collisions;
- declaration/definition ordering;
- include and macro semantics;
- required legal/provenance material.

### Exact and Compatible Inputs

For the exact normalized baseline used during authoring:

```text
normalized tree + generated transform == single-file oracle byte-for-byte
```

Compatible later normalized trees may preserve legitimate upstream differences
only when the materialized single-file result satisfies all semantic and
validation postconditions.

## Invariants

- The original user-owned root source is never modified by this stage.
- Only accepted generated quality output is admitted as amalgamation input.
- The local single-file oracle remains ignored authoring evidence.
- The generated transform is source-bound and cannot materialize the target from
  transform bytes alone.
- Plain concatenation and source-specific hand patches are not accepted
  implementations.
- Quality and amalgamation remain separate stages with independent evidence.
- The final accepted `doom_amalgamated.c` is copied byte-for-byte to the ignored
  end-to-end `tests/applications/doom/out/doom.c` fixture.

## Failure Behavior

Insufficient source admission, source-binding failure, unresolved Clang semantic
conflicts, provenance loss, native differential mismatch, or nondeterministic
output reject the artifact. Partial output is not published as accepted.

## Verification

- exact baseline reconstruction against the local single-file oracle;
- deterministic repeated recipe generation/materialization;
- pinned-Clang structural/provenance evidence;
- normalized multi-file versus single-file native differential tests;
- source-binding no-source/wrong-source rejection;
- byte identity between accepted amalgamated output and the end-to-end fixture;
- `jig validate --root .`.

### Future Pipeline Role

The canonical single-file C artifact is the source-level handoff to the later
C-to-Malbolge pipeline. The long-term goal is one portable DOOM source artifact
that can be lowered to Malbolge without requiring a separate persistent bytecode
sidecar or host libc. Runtime platform capabilities remain a separate concern.

## References

- [DOOM quality and modernization pass](doom-modernization.md)
- [Source-Bound Diff Generator](../tooling/source-bound-diff-generator.md)
- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
