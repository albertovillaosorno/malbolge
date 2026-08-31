# DOOM Algorithm Suite

`algorithms/doom/` is an optional large-program interoperability suite. It is
not the main architecture of the repository and it is not a general-purpose
DOOM source port. Its job is to prove that the source-bound C pipeline can
survive a real, old, inconvenient codebase.

## Progress at a glance

The user-facing source-level path is one transform:

```text
doom/source/                 exact pinned original DOOM
        |
        v
amalgamate/main.rs           standalone source-bound final transform
        |
        v
doom.c                       conditioned + amalgamated single TU
```

Quality remains a development workflow used to author and validate the target
that the final transform reproduces:

```text
doom/source/
    -> quality/main.rs
    -> quality/out/doom_fixed/
    -> amalgamation_oracle.py
    -> ignored accepted oracle/doom.c
    -> algorithms/diff against doom/source/
    -> amalgamate/main.rs
```

The next stage is still open: compile the accepted `doom.c` to
`doom.malbolge`, link the versioned host capabilities, execute it under
Malbolge semantics, and measure generated-code performance.

## Responsibilities

| Component | Responsibility |
| --- | --- |
| `generator/doom.py` | Exact DOOM source identity, provenance, and probes. |
| `generator/quality.py` | Configure source-to-normalized-tree generation. |
| `quality/main.rs` | Materialize the accepted 130-file normalized tree. |
| `generator/amalgamation_oracle.py` | Build the ignored single-TU oracle. |
| `generator/amalgamate.py` | Bind original source directly to final `doom.c`. |
| `amalgamate/main.rs` | User-facing original-source-to-final-C transform. |
| `cli/adapters/doom/` | Native debugging and capability scaffolds. |
| `algorithms/diff/` | Generic binding, protection, and Rust emission. |

The generated `main.rs` files are not hand-edited. Their headers identify the
real artifact path and their payload literals are wrapped to the repository's
80-column limit.

## Required local inputs

These inputs are intentionally Git ignored:

- `doom/source/`: exact pinned id Software source;
- `doom/wad/`: optional user-owned external WADs;
- `algorithms/doom/quality/in/doom/`: accepted modernization oracle;
- `algorithms/doom/amalgamate/in/oracle/doom.c`: accepted single-TU oracle;
- WADs, generated C trees, native executables, sanitizer logs, and play data.

No WAD bytes are stored in either generated Rust transform.

## Regenerate the algorithms

Run from the repository root with the repository Python:

```powershell
$env:PYTHONPATH = (Get-Location).Path
$python = ".dependencies/python/3.14.6/Scripts/python.exe"

& $python -m algorithms.doom.generator.quality
& $python -m algorithms.doom.generator.amalgamation_oracle
& $python -m algorithms.doom.generator.amalgamate
```

The commands have separate responsibilities:

1. `quality` verifies the exact pinned source/oracle and rewrites
   `src/research/algorithms/composition/algorithms/doom/quality/main.rs`.
2. `amalgamation_oracle` consumes accepted generated quality output and rewrites
   only the ignored local `in/oracle/doom.c` authoring evidence.
3. `amalgamate` binds the accepted final `doom.c` oracle directly against the
   exact original `doom/source/` snapshot and rewrites the standalone
   `src/research/algorithms/composition/algorithms/doom/amalgamate/main.rs`.

Running each recipe twice must produce identical SHA-256 values.

## Materialize the final user artifact

Users need only the final transform. Compile it with the pinned Rust toolchain
and point it directly at the original source tree:

```sh
rust=.dependencies/rust/1.97.1/bin/rustc
rm -rf .temp/doom-final-transform .temp/doom-final

"$rust" --edition 2024 -D warnings -C opt-level=2 \
  src/research/algorithms/composition/algorithms/doom/amalgamate/main.rs \
  -o .temp/doom-final-transform

.temp/doom-final-transform doom/source .temp/doom-final
```

The output root contains exactly one file, `doom.c`. Maintainers may separately
materialize `quality/main.rs` while developing the normalized multi-file corpus,
but that intermediate tree is not a prerequisite for final artifact generation.

## Current artifact identity

### Quality transform

- Path: `src/research/algorithms/composition/algorithms/doom/quality/main.rs`
- Size: 3,092,640 bytes
- Lines: 43,667
- SHA-256:
  `27c3d2b0dba2ba043a4fb6ecc37c148643898552cab17a400840a2e60e0f3699`

### Amalgamation transform

- Path: `src/research/algorithms/composition/algorithms/doom/amalgamate/main.rs`
- Size: 3,590,586 bytes
- Lines: 50,583
- SHA-256:
  `668586c9e90721e524158cfc313bc1c99f42e883685900fb52e5c6c86f7a8afb`

### Canonical C output

- Path: `algorithms/doom/amalgamate/out/doom.c` (ignored)
- Size: 1,543,214 bytes
- Lines: 51,096
- SHA-256:
  `4d5e7583baabeef6a7e21f3e7c3c560a4e4e44d7f467a8d4a9dcdc92775adc40`

The normalized tree contains 130 files: 63 C translation units, 66 headers,
and the root license file. The accepted quality oracle and generated quality
materialization have aggregate tree SHA-256
`7bf0723d2abca8e33a1db7eade698d90b3c7bf4c2611eccdccd6606cbeed1923`.

The current amalgamation uses 63 translation units, 19 private bindings, 65
unique embedded project headers, 128 expanded project includes, 529 duplicate
header elisions, and one guarded include-cycle elision. The generated `doom.c`
is byte-identical to the ignored amalgamation oracle and to the interactively
playtested C artifact.

## Validation summary

- 63/63 normalized C translation units pass the complete pre-Malbolge validator.
- The canonical `doom.c` passes the pinned Clang pre-Malbolge C preflight.
- Both generated Rust transforms compile with Rust 1.97.1 and `-D warnings`.
- Fresh materialization reproduces the accepted quality tree byte-for-byte.
- Fresh final materialization directly from the 165-file upstream source
  reproduces the playtested `doom.c` byte-for-byte.
- Canonical `malbolge doom.c` native debugging works on Linux and Windows host
  boundaries; the Linux path uses SDL2 and external `settings.json` presentation
  configuration.
- An interactive Linux playtest confirmed world rendering, HUD, input, audio,
  WAD loading, and ordinary single-player gameplay with the canonical C
  artifact.
- Missing or mutated admitted source fails before target publication.

This proves the source-level C baseline is ready. It does not prove complete
Malbolge compatibility because `doom.malbolge` has not yet been generated or
executed.

See `amalgamate/CHANGELOG.md`, `quality/CHANGELOG.md`, and the contracts
under `docs/technical/interoperability/` for detailed history and evidence.
