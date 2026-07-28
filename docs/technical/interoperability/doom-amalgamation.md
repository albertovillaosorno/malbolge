# User-supplied DOOM source interoperability generator

## Status

Source-level implementation accepted. Malbolge lowering and execution remain
outside this completed stage.

## Purpose

Transform the accepted normalized multi-translation-unit DOOM source into one
canonical `doom.c` without making the ignored single-file oracle a distributable
dependency.

## Current Behavior

`algorithms/doom/generator/amalgamation_oracle.py` constructs a deterministic
single-TU oracle from accepted generated quality output. It embeds project
headers, preserves system includes and provenance, orders translation units, and
isolates private collisions. `generator/amalgamate.py` feeds that source/oracle
pair to generic `algorithms/diff/`, which emits the source-bound
`algorithms/doom/amalgamate/main.rs` transform.

The transform consumes
`quality/out/doom_fixed/linuxdoom-1.10/` and publishes exactly one ignored file,
`amalgamate/out/doom.c`, without requiring the oracle.

## Accepted Identity

- transform SHA-256:
  `ec1ddf2ad07c8664f46739f878ec83b1a6690f45d5c1fbbb5025cb2a79208d1e`;
- canonical C SHA-256:
  `e1d8d2fc12f721815c6fc84e486e40e9d017fe858aeeda58df15b03df5d2b2b1`;
- output size: 2,505,975 bytes / 79,313 lines;
- deterministic repeated generation/materialization: pass;
- wrong, absent, or mutated source rejection before publication: pass;
- byte identity with local oracle and end-to-end fixture: pass.

## Semantic Verification

The generic diff encodes reconstruction but is not the C semantic authority.
Pinned Clang and deterministic native evidence establish that the output
preserves translation-unit preprocessing, internal linkage isolation,
declaration ordering, include behavior, and provenance.

The accepted `doom.c` passes strict six-target Clang validation and builds with
ASan+UBSan plus the Windows adapter. A no-CRT deterministic harness produced
identical multi-TU and single-TU framebuffer/audio transcripts:

```text
92ff55046afd3976
4571f707b08d56cd
912da30aff88aaed
```

## Invariants

- The user-owned root source is never modified.
- Only accepted generated quality output is admitted.
- WAD/data bytes do not enter amalgamation identity or payload.
- The ignored oracle is authoring evidence only.
- The generated transform remains source-bound.
- Partial or mismatched output is never published as accepted.
- Quality and amalgamation remain separate algorithms.

## Malbolge Boundary

This stage ends at canonical C. Guest-C acceptance is evidence that `doom.c` is
prepared for the declared C surface, not proof that the entire program has been
lowered or executed as Malbolge. Complete compatibility requires generating and
running `doom.malbolge` with the versioned capability ABI.

## References

- [DOOM quality and modernization pass](doom-modernization.md)
- [Source-Bound Diff Generator](../tooling/source-bound-diff-generator.md)
- [Compiler Pipeline And Guest Runtime][compiler-runtime]

[compiler-runtime]:
  ../adr/compiler-pipeline-and-guest-runtime.md
