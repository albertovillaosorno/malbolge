# DOOM Amalgamation Algorithm

## Purpose

This is the optional second DOOM source-transformation stage. It consumes only an
accepted normalized multi-file C tree from quality and materializes one
deterministic canonical C translation artifact without changing program
semantics.

The final implementation is not a hand-written concatenator. The planned
authoring flow reuses `algorithms/diff/`: a thin DOOM recipe compares accepted
normalized input with a local semantically validated single-file oracle and emits
source-bound `amalgamate/main.rs`.

Pinned Clang evidence remains mandatory because a generic tree diff cannot decide
C translation-unit semantics.

## Local Development Layout

```text
algorithms/doom/
|-- generator/              # future amalgamation recipe/domain policy
`-- amalgamate/
    |-- main.rs             # generated source-bound transform
    |-- in/
    |   `-- doom/           # accepted normalized input; ignored
    `-- out/
        `-- doom_amalgamated.c
```

The input is **not** original DOOM. It is accepted generated output from the
quality stage. The future single-file oracle is local authoring evidence and is
not required by the generated transform.

## Authoring Flow

1. Complete quality and materialize accepted `quality/out/doom_fixed/`.
2. Build the normalized multi-file tree and record exact preprocessing, linkage,
   symbol, provenance, and native behavior evidence.
3. Construct and validate a local single-file oracle that preserves those
   semantics.
4. Configure a thin DOOM amalgamation recipe with normalized source, local
   single-file oracle, domain probes, and admission policy.
5. Use `algorithms/diff/` to emit source-bound `amalgamate/main.rs`.
6. Materialize `out/doom_amalgamated.c` from the exact normalized baseline and
   require byte identity with the local oracle.
7. Compile both normalized multi-file and materialized single-file forms and run
   differential behavior/provenance validation.
8. Re-run recipe generation and materialization to prove determinism.

For later compatible normalized inputs, byte identity to the historical oracle is
not mandatory when preserving legitimate upstream differences. All semantic and
validation postconditions still are.

## Why Plain Concatenation Is Incorrect

Independent C translation units can contain:

- translation-unit-specific macro/preprocessor state;
- declarations visible only in one unit;
- internal-linkage names that collide after merging;
- ordering dependencies between declarations and definitions;
- file-local static objects/functions;
- required copyright, license, and source provenance.

Where these affect semantics, pinned Clang preprocessing/AST evidence or an
explicitly equivalent semantic model is required. Generic diff machinery only
encodes/reconstructs the accepted transformation; it does not prove C semantics.

## Source Binding

The generated transform must retain the same source-bound property as quality:
possessing `main.rs` alone is insufficient to materialize the accepted
single-file source. Insufficient compatible normalized input fails before target
publication.

The source-binding mechanism is generic `algorithms/diff` responsibility. DOOM
policy must not implement a second private version.

## Separation from Quality

Quality and amalgamation remain separate algorithms. The normalized multi-file
tree is valid output in its own right, and future C frontends may accept multiple
translation units directly. Single-file C must not become an accidental global
architectural requirement.

## Pipeline Position

```text
user-supplied DOOM
        |
        v
quality recipe + diff -> quality/main.rs
        |
        v
normalized multi-file C
        |
        v
amalgamation recipe + diff -> amalgamate/main.rs
        |
        v
canonical doom_amalgamated.c
        |
        v
later C-to-Malbolge pipeline
```

The accepted `doom_amalgamated.c` is eventually copied byte-for-byte to the
ignored `tests/applications/doom/out/doom.c` end-to-end fixture.

## Repository Boundary

User-owned source, local oracles, and generated DOOM source remain ignored. The
repository versions generator infrastructure, thin recipes, emitted transforms,
contracts, tests, and aggregate evidence.

Relevant authorities:

- `docs/technical/tooling/source-bound-diff-generator.md`;
- `docs/technical/interoperability/doom-amalgamation.md`;
- `docs/technical/interoperability/doom-modernization.md`;
- `docs/todo/open/applications/`
  `user-supplied-doom-source-interoperability-generator.mdc`;
- `docs/legal/adr/legal-research-and-repository-boundary.md`.
