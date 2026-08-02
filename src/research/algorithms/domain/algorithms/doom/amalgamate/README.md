# DOOM Amalgamation Algorithm

## Status

Accepted exact source stage. C-to-Malbolge lowering remains separate and open.

## Purpose

This second DOOM source transformation consumes only the accepted normalized
multi-file C tree from quality and materializes one deterministic canonical
`doom.c` without changing program semantics.

The implementation is not a hand-written concatenator. A deterministic C-aware
oracle builder establishes the accepted single-TU form; the thin
`generator/amalgamate.py` recipe then uses generic `algorithms/diff/` source
binding to emit `amalgamate/main.rs`.

## Local Development Layout

```text
algorithms/doom/
|-- generator/
|   |-- amalgamation_oracle.py
|   `-- amalgamate.py
`-- amalgamate/
    |-- main.rs             # generated source-bound transform
    |-- in/oracle/doom.c    # ignored authoring evidence
    `-- out/doom.c          # ignored materialized product
```

The source is `quality/out/doom_fixed/linuxdoom-1.10/`, not original DOOM and
not WAD data. The generated transform does not require the local single-file
oracle at materialization time.

## Accepted Artifact

- generated transform SHA-256:
  `7bcd19b073c5839c4c9119a0b871e4e4cd6e63dbedeb7571b6099f234e92f439`;
- `doom.c` SHA-256:
  `a7fbecc1a6faba9fb974399d2b1def32c52734f1a557c0d8dbcdbc9357daab80`;
- 2,507,561 bytes and 79,336 lines;
- 65 translation units and 19 private bindings;
- 83 unique embedded project headers;
- 148 expanded includes, 564 duplicate-header elisions, one guarded cycle
  elision.

Repeated recipe generation and materialization are byte-identical. Empty and
mutated normalized source trees are rejected before publication. The accepted
output is byte-identical to the ignored oracle and to
`tests/applications/doom/out/doom.c`.

## Semantic Evidence

Pinned Clang remains the authority for the C surface. The materialized file:

- passes strict Clang 22.1.8 with `-Werror` on Linux, Windows, and macOS for
  x86-64 and AArch64;
- builds with ASan+UBSan and links with the Windows host adapter;
- produces the same deterministic framebuffer/audio transcript as the 65-TU
  normalized build: `92ff55046afd3976`, `4571f707b08d56cd`,
  `912da30aff88aaed`;
- is byte-identical to the native artifact manually played for roughly 20
  minutes without reproducing the reported autoaim crash.

## Source Binding

Possessing `main.rs` alone is insufficient to materialize `doom.c`. The exact
normalized source snapshot must match and recover the authenticated payload.
Wrong, missing, or mutated source fails before output publication.

## Malbolge Boundary

Passing guest-C and Clang validation means `doom.c` is accepted input for the
future compiler. It does **not** prove complete Malbolge compatibility. That
requires C-to-Malbolge lowering, capability linking, generation of
`doom.malbolge`, and execution under Malbolge semantics.

## Repository Boundary

User-owned source, WADs, local oracles, generated C, native executables,
and debug
logs remain ignored. The repository versions the recipes, builder, generated
source-bound Rust transform, tests, contracts, and aggregate evidence.
