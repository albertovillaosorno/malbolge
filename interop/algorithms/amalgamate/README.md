# DOOM Amalgamation Algorithm

## Purpose

This is the second DOOM interoperability algorithm. It consumes the already
accepted, normalized multi-file C tree produced by the quality stage and turns
it into one deterministic C translation artifact without changing program
semantics.

The goal is not to concatenate files. C translation units have independent
preprocessor environments, internal linkage, declarations, macros, and ordering
rules. A correct amalgamator must preserve those semantics when many source
files become one file.

As with the quality stage, user-owned DOOM source and generated output remain
local and ignored by Git. The durable artifact is the reproducible algorithm in
`main.rs` plus its evidence.

## Local Development Layout

```text
interop/algorithms/amalgamate/
|-- README.md
|-- main.rs
|-- in/
|   `-- doom/               # normalized quality-stage result; ignored by Git
`-- out/
    `-- doom_amalgamated.c  # generated single-file result; ignored by Git
```

`in/doom/` is **not** the original DOOM source. It is the cleaned and normalized
multi-file tree accepted by the quality algorithm.

`out/doom_amalgamated.c` is the canonical local result that `main.rs` must
reproduce deterministically.

## How the Algorithm Is Built

The development method again uses a manual reference result before automation is
trusted.

1. Run the quality stage and place its accepted normalized tree in `in/doom/`.
2. Build that multi-file tree natively and record the baseline behavior,
   translation-unit inventory, preprocessing state, symbols, and provenance.
3. Construct a correct single-file result locally while preserving those
   semantics. This reference output is a development oracle, not a versioned
   artifact.
4. Record every operation required to reach that result: preprocessing,
   declaration materialization, symbol renaming, ordering, include handling,
   provenance retention, and any other translation-unit repair.
5. Implement those operations as deterministic logic in `main.rs`.
6. Regenerate `out/doom_amalgamated.c` from the untouched normalized input.
7. Compare the generated file with the accepted reference and rebuild it
   natively.
8. Differentially compare the normalized multi-file build with the amalgamated
   build. Any unexplained behavioral difference is a hard failure.
9. Remove dependence on every manual edit. The algorithm is accepted only when
   `main.rs` reproduces the single-file artifact from input alone.

The manual `out/` result is therefore scaffolding used to discover the
transformation. It is not the implementation.

## Why Concatenation Is Incorrect

Two valid C source files cannot generally be joined byte-for-byte and
expected to retain their meaning. The algorithm must account for at least:

- translation-unit-specific macro and preprocessing state;
- conditional compilation and include expansion;
- declarations that were visible only inside one translation unit;
- internal-linkage identifiers with the same spelling in different files;
- ordering dependencies between declarations and definitions;
- file-local static objects and functions;
- generated or platform-specific declarations that should not survive verbatim;
- required copyright, license, and source provenance; and
- deterministic naming and output ordering.

Where these properties affect semantics, the implementation must use pinned
Clang preprocessing/AST evidence or another explicitly equivalent semantic
model. Plain textual concatenation is never the accepted algorithm.

## Semantic Composition

A typical amalgamation pass conceptually performs these stages:

1. **Inventory** - identify every admitted translation unit and its compile
   configuration.
2. **Preprocess and parse** - obtain exact macro, include, declaration,
   type, and linkage facts.
3. **Build provenance** - associate every emitted construct with its source and
   transformation history.
4. **Resolve collisions** - deterministically rename internal-linkage symbols
   that would collide after translation units are merged.
5. **Materialize interfaces** - emit the declarations required when former
   translation-unit boundaries disappear.
6. **Order definitions** - produce one stable dependency-respecting sequence.
7. **Emit canonical C** - generate one deterministic source file.
8. **Verify** - compile both forms and compare observable native behavior.

Given the same normalized input and toolchain facts, repeated runs must produce
byte-identical output.

## Pipeline Position

This algorithm runs **after** quality:

```text
user-supplied DOOM
        |
        v
quality/main.rs
        |
        v
normalized multi-file C tree
        |
        v
amalgamate/main.rs
        |
        v
doom_amalgamated.c
        |
        v
later C-to-Malbolge pipeline
```

The amalgamator never cleans the original DOOM tree and never substitutes for
the quality pass. Its only responsibility is semantics-preserving aggregation
of an already accepted normalized tree.

## Repository Boundary

Neither the upstream source nor generated amalgamated source is committed merely
because it is used during development. The repository stores the algorithm and
its reproducibility evidence, not the user-owned corpus.

Relevant authorities:

- `docs/technical/interoperability/doom-amalgamation.md`
- `docs/technical/interoperability/doom-modernization.md`
- the `user-supplied-doom-source-interoperability-generator` typed TODO under
  `docs/todo/open/applications/`;
- `docs/legal/adr/legal-research-and-repository-boundary.md`
