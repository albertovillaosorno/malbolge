# DOOM interoperability quick start

The published DOOM source transform has one user-facing job: take the exact
pinned id Software source tree and materialize the final conditioned,
amalgamated `doom.c`. The repository does not distribute DOOM source or game
data.

`quality/main.rs` still exists, but it is a development transform. Maintainers
use it to work on the normalized multi-file tree before accepting a new final
`doom.c`. Users generating the final artifact need only `amalgamate/main.rs`.

The remaining project milestone is C-to-Malbolge lowering. Native `doom.c` is
the accepted comparison oracle; `doom.malbolge` has not yet been generated or
executed.

## 1. Put original DOOM source under `doom/source/`

Use id Software DOOM commit:

```text
a77dfb96cb91780ca334d0d4cfd86957558007e0
```

Extract that checkout beneath the ignored repository `doom/source/` directory:

```text
doom/
|-- source/
|   |-- LICENSE.TXT
|   |-- linuxdoom-1.10/
|   |-- ipx/
|   |-- sersrc/
|   `-- sndserv/
`-- wad/
    |-- doom.wad
    |-- doom2.wad
    `-- ...
```

The source directory is pinned to the 165 official files from that commit. A
missing, extra, or modified admitted source file fails closed.

WADs are independent external inputs. Keep them under `doom/wad/` or another
user-owned location and never add them to Git.

## 2. Build the `malbolge` command

Linux:

```sh
./src/interface/command-line/composition/scripts/build-unix.sh
```

Windows:

```powershell
src\interface\command-line\composition\scripts\build-windows.cmd
```

The local CLI binary is written beneath
`src/interface/command-line/composition/scripts/bin/`, which is ignored by Git.

## 3. Generate final `doom.c` with one algorithm

Compile the published final transform and run it directly against the original
source tree. Quality output is not an input to this command.

Linux:

```sh
rust=.dependencies/rust/1.97.1/bin/rustc

rm -rf .temp/doom-final-transform .temp/doom-final

"$rust" --edition 2024 -D warnings -C opt-level=2 \
  src/research/algorithms/composition/algorithms/doom/amalgamate/main.rs \
  -o .temp/doom-final-transform

.temp/doom-final-transform doom/source .temp/doom-final
```

The only generated file is:

```text
.temp/doom-final/doom.c
```

The accepted artifact currently has SHA-256:

```text
4d5e7583baabeef6a7e21f3e7c3c560a4e4e44d7f467a8d4a9dcdc92775adc40
```

It is 1,543,214 bytes and 51,096 lines. All `.temp/` products remain local and
ignored.

## 4. Configure video with `settings.json`

Put `settings.json` beside the `doom.c` that you run. On Linux the native debug
adapter reads presentation and render settings before entering the guest.

Recommended configuration:

```json
{
  "resolution": [1920, 1080],
  "render_resolution": [640, 360],
  "maximized": true
}
```

`resolution` is physical window size when not maximized. `render_resolution` is
the corrected visual raster DOOM calculates. They are intentionally separate so
a 1080p desktop window does not require a native 1080p software-rendered world.

Classic DOOM uses 5:6 pixel-aspect correction. Linux converts the visual width
to the raw guest framebuffer width before entering the game:

| JSON `render_resolution` | Raw guest framebuffer | Corrected aspect |
| --- | --- | --- |
| `[640, 360]` | `768x360` | 16:9 |
| `[960, 540]` | `1152x540` | 16:9 |
| `[1280, 720]` | `1536x720` | 16:9 |
| `[1920, 1080]` | `2304x1080` | 16:9 |

Explicit `-render-scale`, `-render-height`, or `-render-width` arguments
override `render_resolution`.

## 5. Play

From the repository root:

```sh
./src/interface/command-line/composition/scripts/malbolge \
  .temp/doom-final/doom.c \
  -iwad doom/wad/doom.wad
```

For `.c`, the CLI performs native debugging only: it detects the DOOM host ABI,
uses the platform host adapter, creates a temporary native executable, and runs
it. This does not claim C-to-Malbolge compilation.

The working directory becomes the directory containing `doom.c`. Put
`settings.json` there when configuring presentation; saves and `default.cfg`
then remain beside the generated artifact rather than in the repository root.

## Maintainers: quality is the development workflow

Do not hand-edit `amalgamate/main.rs`. A new final algorithm is accepted only
after the multi-file quality tree and the resulting single-TU C artifact have
been reviewed and playtested.

The authoring workflow is:

```text
doom/source/                    exact original user source
    |
    v
quality/main.rs                 development-only conditioning transform
    |
    v
quality/out/doom_fixed/         readable multi-file development corpus
    |
    v
amalgamation_oracle.py          deterministic C-aware amalgamator
    |
    v
ignored oracle/doom.c           accepted and playtested final target
    |
    | algorithms/diff binds target against doom/source/
    v
amalgamate/main.rs              standalone user-facing final transform
```

Regenerate authoring artifacts from the repository root with:

```sh
export PYTHONPATH="src/research/algorithms/composition:\
src/research/algorithms/domain:\
src/automation/repository/composition"

python3 -m algorithms.doom.generator.quality
python3 -m algorithms.doom.generator.amalgamation_oracle
python3 -m algorithms.doom.generator.amalgamate
```

`quality.py` and `amalgamation_oracle.py` are development tools. The final
`amalgamate.py` recipe deliberately binds the accepted `doom.c` against the
original pinned `doom/source/` tree, not against quality output.

Repeated final generation must produce the same `amalgamate/main.rs` hash, and
materializing that transform directly from `doom/source/` must reproduce the
accepted oracle byte-for-byte.

## Current boundary

The C baseline is ready: one original-source-to-final-C transform reproduces the
playtested single-player `doom.c`; Windows/Linux native debug adapters, external
WAD handling, scalable Hor+ rendering, audio, input, and saves are established.

The open work is the actual Malbolge stage. See
[TODO.md](TODO.md#todo---doom-playable-generated-code-performance) for the
tracked compiler/runtime performance milestone.
