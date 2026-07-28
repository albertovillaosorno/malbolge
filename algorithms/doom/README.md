# DOOM Algorithm Suite

`algorithms/doom/` is an optional large-program interoperability suite. It is
not the main architecture of the repository and it is not a general-purpose
DOOM source port. Its job is to prove that the source-bound C pipeline can
survive a real, old, inconvenient codebase.

## Progress at a glance

The source-level pipeline is complete:

```text
lawful ignored root doom/
        |
        v
quality.py + algorithms/diff
        |
        v
quality/main.rs
        |
        v
quality/out/doom_fixed/
        |
        v
amalgamation_oracle.py
        |
        v
amalgamate.py + algorithms/diff
        |
        v
amalgamate/main.rs
        |
        v
amalgamate/out/doom.c
```

The next stage is still open: compile the accepted `doom.c` to
`doom.malbolge`, link the versioned host capabilities, execute it under
Malbolge semantics, and measure generated-code performance.

## Responsibilities

| Component | Responsibility |
| --- | --- |
| `generator/doom.py` | Exact DOOM source identity, provenance, and probes. |
| `generator/quality.py` | Configure source-to-normalized-tree generation. |
| `quality/main.rs` | Materialize the accepted 151-file normalized tree. |
| `generator/amalgamation_oracle.py` | Build the ignored single-TU oracle. |
| `generator/amalgamate.py` | Configure normalized-tree-to-`doom.c`. |
| `amalgamate/main.rs` | Materialize exactly one canonical `doom.c`. |
| `cli/adapters/doom/` | Native debugging and capability scaffolds. |
| `algorithms/diff/` | Generic binding, protection, and Rust emission. |

The generated `main.rs` files are not hand-edited. Their headers identify the
real artifact path and their payload literals are wrapped to the repository's
80-column limit.

## Required local inputs

These inputs are intentionally Git ignored:

- `doom/`: exact pinned id Software source plus optional external `data/`;
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
   `algorithms/doom/quality/main.rs`.
2. `amalgamation_oracle` consumes accepted generated quality output and rewrites
   only the ignored local `in/oracle/doom.c` authoring evidence.
3. `amalgamate` binds the normalized source/oracle pair and rewrites
   `algorithms/doom/amalgamate/main.rs`.

Running each recipe twice must produce identical SHA-256 values.

## Materialize the generated outputs

Compile the generated transforms with the pinned Rust toolchain. The example
uses clean temporary output roots, so it is safe when canonical local outputs
already exist:

```powershell
$rustRoot = "C:/Repos/mit/jig/.dependencies/rust"
$rust = "$rustRoot/stable-1.97.1-x86_64-pc-windows-gnu/bin/rustc.exe"

Remove-Item .temp/doom-quality-output -Recurse -Force `
  -ErrorAction SilentlyContinue
Remove-Item .temp/doom-amalgamate-output -Recurse -Force `
  -ErrorAction SilentlyContinue

& $rust --edition 2024 -D warnings -C opt-level=2 `
  algorithms/doom/quality/main.rs `
  -o .temp/doom-quality-transform.exe

& .temp/doom-quality-transform.exe `
  doom `
  .temp/doom-quality-output

& $rust --edition 2024 -D warnings -C opt-level=2 `
  algorithms/doom/amalgamate/main.rs `
  -o .temp/doom-amalgamate-transform.exe

& .temp/doom-amalgamate-transform.exe `
  .temp/doom-quality-output/linuxdoom-1.10 `
  .temp/doom-amalgamate-output
```

The quality transform publishes one normalized tree. The amalgamation transform
publishes one file named `doom.c`. Existing output roots are rejected rather
than merged.

## Current artifact identity

### Quality transform

- Path: `algorithms/doom/quality/main.rs`
- Size: 5,228,952 bytes (4.99 MiB)
- Lines: 73,347
- SHA-256:
  `83f9c400ffd7ca17c75cc1cbc7a654794452ef37eac2adbf21af42a335766bd8`

### Amalgamation transform

- Path: `algorithms/doom/amalgamate/main.rs`
- Size: 5,748,320 bytes (5.48 MiB)
- Lines: 80,560
- SHA-256:
  `7bcd19b073c5839c4c9119a0b871e4e4cd6e63dbedeb7571b6099f234e92f439`

### Canonical C output

- Path: `algorithms/doom/amalgamate/out/doom.c` (ignored)
- Size: 2,507,561 bytes (2.39 MiB)
- Lines: 79,336
- SHA-256:
  `a7fbecc1a6faba9fb974399d2b1def32c52734f1a557c0d8dbcdbc9357daab80`

The two Rust artifacts have a maximum physical line length of 80 characters.
The canonical `doom.c`, its ignored oracle, repeated materialization, and the
ignored application fixture are byte-identical.

## Validation summary

- 65/65 normalized C translation units pass the guest-C validator.
- Final `doom.c` passes strict Clang 22.1.8 on six target combinations.
- Generated Rust compiles with Rust 1.97.1 and `-D warnings`.
- Multi-TU and single-TU framebuffer/audio transcripts are identical.
- ASan+UBSan and the Windows adapter build successfully.
- Roughly 20 minutes of native play did not reproduce the autoaim crash.
- Missing or mutated source fails before target publication.

This proves source-level guest-C readiness. It does not prove complete Malbolge
compatibility because `doom.malbolge` has not been generated or executed.

See `amalgamate/CHANGELOG.md`, `quality/CHANGELOG.md`, and the contracts
under `docs/technical/interoperability/` for detailed history and evidence.
