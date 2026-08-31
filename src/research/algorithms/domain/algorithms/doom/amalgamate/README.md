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
  `e4ba6b14ec067b3836cc59b86f096b6f450651a2cb0eb6453a6f8c0de651cc39`;
- `doom.c` SHA-256:
  `4d5e7583baabeef6a7e21f3e7c3c560a4e4e44d7f467a8d4a9dcdc92775adc40`;
- 1,543,214 bytes and 51,096 lines;
- 63 translation units and 19 private bindings;
- 65 unique embedded project headers;
- 128 expanded includes, 529 duplicate-header elisions, one guarded cycle
  elision.

The generated transform compiles with pinned Rust 1.97.1 and `-D warnings`.
Materializing it from a fresh accepted normalized tree reproduces the ignored
single-TU oracle byte-for-byte. That output is also byte-identical to the
`doom.c` exercised by the canonical Linux native-debug playtest.

## Semantic Evidence

Pinned Clang remains the authority for the C surface. The current materialized
file passes the canonical pre-Malbolge C preflight. The upstream normalized tree
passes the complete validator across all 63 translation units, and a fresh
quality materialization is byte-identical to the accepted quality oracle.

The canonical Linux `malbolge doom.c` debug path compiles the exact single-TU C
artifact with the SDL2 host adapter. Interactive play confirmed normal WAD load,
world rendering, HUD, input, audio, and single-player gameplay. Presentation
resolution is host-side configuration and does not change the accepted C
artifact. Native-debug success is comparison-oracle evidence only; it is not a
claim that the C has already executed under Malbolge semantics.

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
