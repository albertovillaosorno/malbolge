# DOOM Quality and Modernization Algorithm

## Purpose

This is the first DOOM interoperability algorithm. It turns a local,
user-supplied DOOM source tree into a deterministic, modernized C tree that can
satisfy the repository's C quality and lowerability contracts before any source
files are amalgamated.

The algorithm is developed against a local DOOM corpus, but the DOOM source is
not committed to this repository. Both `in/` and `out/` are ignored working
areas. The durable artifact is the transformation logic in `main.rs`, together
with tests, contracts, and reproducible evidence.

## Scope: Interoperability Corpus, Not a DOOM Port

This algorithm does not aim to become a general-purpose DOOM source port, a
preservation project, or a replacement for projects that maintain DOOM as an
end-user game. DOOM is used here because it is a demanding C interoperability
corpus. The implementation only needs enough modern host support to exercise
the quality and C-to-Malbolge pipeline meaningfully.

The engine source and game data are separate inputs. Running the corpus requires
a compatible IWAD, but no commercial id Software WAD is part of the algorithm
or its versioned artifacts. Local tests use `in/doom/data/freedoom1.wad`. That
WAD is a local test fixture, is not modified by the quality pass, and is not
committed by this algorithm. A developer may supply another compatible IWAD
that they are legally entitled to use. The engine must not depend specifically
on Freedoom.

The normal local fixture layout is:

```text
in/doom/data/
`-- freedoom1.wad    # local test IWAD; ignored and not versioned
```

An explicit `-iwad <path>` selection takes precedence over automatic discovery
under `doom/data`. Automatic discovery exists only to make local validation
convenient.

## Local Development Layout

```text
interop/algorithms/quality/
|-- README.md
|-- main.rs
|-- in/
|   `-- doom/          # local user-owned input corpus; ignored by Git
`-- out/
    `-- doom_fixed/    # generated normalized tree; ignored by Git
```

`in/doom/` is a local working copy of the DOOM source used to discover and
classify required transformations. It must never become a way to smuggle the
upstream game source into Git history.

`out/doom_fixed/` is the reproducible result that `main.rs` must eventually
produce from the admitted input. Generated output is inspectable locally but is
not the source of truth.

## How the Algorithm Is Built

Development intentionally starts with a manual reference result.

1. Put the user-supplied DOOM source in `in/doom/`.
2. Run the complete applicable quality stack over that tree: compiler
   diagnostics, repository linters, Jig governance, `tools/tidy` when available,
   and the explicit interoperability checks owned by this project.
3. Group findings by transformation class instead of treating thousands of
   diagnostics as unrelated one-off edits.
4. Establish the desired corrected form locally. This may include fixing
   demonstrable source defects, removing unsupported or host-specific behavior,
   modernizing platform boundaries, and satisfying the deterministic C profile.
5. For every manual repair, implement an equivalent reusable transformation in
   `main.rs`.
6. Regenerate `out/doom_fixed/` from the original admitted input.
7. Compare the generated tree with the accepted local reference and run the full
   validation stack again.
8. Delete or revert any manual-only repair once `main.rs` reproduces it. A
   fix is not part of the algorithm until generation recreates it
   deterministically.

This makes the manually cleaned tree an oracle used while constructing the
algorithm, not a permanent hidden dependency.

## Transformation Model

The pass is semantics-aware. C scope, types, macros, linkage, control flow, ABI,
and preprocessing state must be handled through Clang/AST evidence or another
explicitly equivalent semantic representation. Regex and direct textual edits
are allowed only for transformations proven to be purely textual.

Expected transformation families include:

- deterministic fixes for undefined, implementation-defined, or unsupported C;
- repeated linter and `tools/tidy` diagnostic families;
- explicit ABI and lowerability normalization;
- platform adapters for video, input, timing, audio, and game-data access;
- deliberate resolution/frame-pacing modernization where the contract allows it;
- reproducible repairs for source defects whose intended behavior is supported
  by tests or authoritative upstream evidence; and
- comment cleanup that preserves required copyright, licensing, and provenance.

A blanket lint suppression is never a transformation. If a diagnostic is valid,
the source or the governing contract must be fixed.

## Correctness Rule

The original user-owned input is not modified by the accepted pipeline.
`main.rs` must be able to start from the admitted source and recreate the
normalized result without hidden hand edits.

Behavior-preserving transformations are checked differentially against the
native baseline. Deliberate bug fixes or platform changes are recorded as such
and require explicit behavioral evidence instead of being disguised as
normalization.

The quality stage is complete only when the generated multi-translation-unit
tree is stable, reproducible, and accepted by all required gates.

## Completion Criteria

The quality stage is accepted only at zero findings across every applicable
quality, compiler, portability, and interoperability gate. Passing lint alone is
not sufficient: the generated tree must also be a deliberately modernized,
runnable interoperability corpus rather than a mechanically reformatted copy.

The accepted result must:

- keep the game/core C independent of CPU-specific assumptions and remain
  suitable for supported 64-bit architectures, including x86-64 and ARM64;
- provide clean platform boundaries for current Windows, macOS, and Linux,
  without hardcoding one host into gameplay or rendering logic;
- run correctly on current 64-bit Windows, including working in-process audio;
- support modern scalable/high-resolution presentation without forcing a single
  resolution, with borderless-window operation as a first-class mode;
- decouple rendering from the historical 35 Hz game clock so presentation can
  sustain at least 60 FPS while preserving intended gameplay timing;
- remove obsolete DOS, 32-bit, legacy Unix, and end-of-life Windows assumptions
  from the required compatibility surface; and
- modernize unsafe, undefined, implementation-defined, host-specific, and
  unnecessarily obsolete C as far as the behavioral contract permits; and
- keep the normalized repository-facing tree English-only: source comments,
  diagnostics/messages owned by this pass, documentation, maintained names,
  and generated explanatory text must not introduce or retain other languages.

Compatibility with obsolete operating systems, 32-bit targets, or historical
platform APIs is explicitly outside this algorithm's scope. A downstream port
may add such support, but this pass does not carry compatibility debt for it.

## Separation from Amalgamation

Quality and amalgamation are intentionally separate algorithms. Quality owns
semantic cleanup and produces the canonical normalized multi-file C tree.
Amalgamation is a later optional lowering experiment, not part of source
quality. Keeping the boundary explicit also preserves a future design in which
the Malbolge C frontend can accept a directory of translation units directly
without forcing every program through a single generated C file.

## Pipeline Position

This algorithm runs **first**:

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
one canonical C translation artifact
```

Amalgamation must consume the normalized output of this stage. It must not skip
quality and operate directly on the original user-owned tree.

## Repository Boundary

DOOM source and generated DOOM trees stay outside Git through the repository
ignore policy. What is versioned is the knowledge required to reproduce the
result: `main.rs`, this README, contracts, tests, manifests, and validation
logic.

Relevant authorities:

- `docs/technical/interoperability/doom-modernization.md`
- `docs/todo/open/applications/doom-quality-and-modernization-pass.mdc`
- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/legal/adr/legal-research-and-repository-boundary.md`
