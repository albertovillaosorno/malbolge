# DOOM interoperability quick start

The DOOM source-level pipeline is ready for normal development and native debug
play. It accepts the pinned id Software source, materializes the normalized
single-player tree, materializes one canonical `doom.c`, and runs that C
artifact through the canonical `malbolge doom.c` debug path on Windows or Linux.

The remaining project milestone is different: generate `doom.malbolge`, link the
versioned host capabilities, execute the result under Malbolge semantics, and
make that generated program playable. Native `doom.c` is the comparison oracle,
not proof that the Malbolge compiler stage is complete.

## 1. Put the DOOM source in `doom/`

DOOM source and game data are user-supplied interoperability inputs and are
ignored by Git. The repository does not redistribute them.

Use id Software DOOM commit:

```text
a77dfb96cb91780ca334d0d4cfd86957558007e0
```

Copy the extracted checkout contents into the ignored repository root `doom/`.
At minimum the source layout must include paths such as:

```text
doom/
|-- LICENSE.TXT
|-- linuxdoom-1.10/
|-- ipx/
|-- sersrc/
`-- sndserv/
```

The quality source identity is pinned to the 165 official files from that
commit. A different engine revision fails closed rather than silently producing
a possibly different port.

WADs stay external. A convenient local layout is:

```text
doom/wad/doom.wad
doom/wad/doom2.wad
doom/wad/doomu.wad
...
```

Never add WADs to Git.

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
Re-run the host build script whenever the CLI or native debug adapter changes.

## 3. Materialize normalized DOOM and `doom.c`

The generated Rust transforms are versioned. Normal users do not need the local
quality or amalgamation authoring oracles to use them.

On Linux, from the repository root:

```sh
rust=.dependencies/rust/1.97.1/bin/rustc

rm -rf \
  .temp/doom-quality-transform \
  .temp/doom-quality-output \
  .temp/doom-amalgamate-transform \
  .temp/doom-amalgamate-output

"$rust" --edition 2024 -D warnings -C opt-level=2 \
  src/research/algorithms/composition/algorithms/doom/quality/main.rs \
  -o .temp/doom-quality-transform

.temp/doom-quality-transform \
  doom \
  .temp/doom-quality-output

"$rust" --edition 2024 -D warnings -C opt-level=2 \
  src/research/algorithms/composition/algorithms/doom/amalgamate/main.rs \
  -o .temp/doom-amalgamate-transform

.temp/doom-amalgamate-transform \
  .temp/doom-quality-output/linuxdoom-1.10 \
  .temp/doom-amalgamate-output
```

The final C file is:

```text
.temp/doom-amalgamate-output/doom.c
```

All `.temp/` products are local and ignored.

## 4. Configure video with `settings.json`

Put `settings.json` beside the `doom.c` that you run. On Linux the debug adapter
reads presentation and render settings before entering the guest.

Recommended configuration:

```json
{
  "resolution": [1920, 1080],
  "render_resolution": [640, 360],
  "maximized": true
}
```

`resolution` is the physical window size when the window is not maximized.
`maximized` selects the initial desktop window state.

`render_resolution` is the corrected visual resolution that DOOM should render.
It is intentionally separate from physical presentation resolution. Classic
DOOM uses 5:6 pixel-aspect correction, so the Linux adapter converts the visual
width to the raw guest framebuffer width before calling the game. For example:

| JSON `render_resolution` | Raw guest framebuffer | Corrected aspect |
| --- | --- | --- |
| `[640, 360]` | `768x360` | 16:9 |
| `[960, 540]` | `1152x540` | 16:9 |
| `[1280, 720]` | `1536x720` | 16:9 |
| `[1920, 1080]` | `2304x1080` | 16:9 |

The default Linux presentation is a maximized 1920x1080 window with a 640x360
corrected render target. This keeps the desktop output sharp enough for normal
play without forcing the software renderer to calculate a native 1080p world.

Native 1080p rendering is supported, but it is expensive. `2304x1080` contains
nine times as many guest pixels as `768x360`. The host can upscale a smaller
indexed framebuffer cheaply; a future `doom.malbolge` should not spend Malbolge
instructions drawing millions of extra pixels merely to match desktop output
resolution.

Explicit guest render switches override `render_resolution`, for example:

```sh
.../malbolge doom.c -render-height 360 -render-width 768
```

The raw `-render-width` value is the uncorrected guest framebuffer width.

## 5. Play

From the repository root:

```sh
./src/interface/command-line/composition/scripts/malbolge \
  .temp/doom-amalgamate-output/doom.c \
  -iwad doom/wad/doom.wad
```

The command detects the DOOM host ABI in `doom.c`, compiles the C artifact only
for native debugging, links the platform host adapter, and launches the game.
This is intentionally not C-to-Malbolge compilation.

The working directory becomes the directory containing `doom.c`, so
`settings.json`, saves, `default.cfg`, and other local play data remain beside
the generated artifact instead of polluting the repository root.

## 6. Maintainers: regenerate the two algorithms

Only regenerate the versioned transformations after the manual quality tree and
canonical `doom.c` have been accepted and playtested. Do not regenerate merely
to hide an untested hand edit.

From the repository root:

```sh
export PYTHONPATH="src/research/algorithms/composition:\
src/research/algorithms/domain:\
src/automation/repository/composition"

python3 -m algorithms.doom.generator.quality
python3 -m algorithms.doom.generator.amalgamation_oracle
python3 -m algorithms.doom.generator.amalgamate
```

The intended order is:

```text
pinned user source
    -> accepted quality oracle
    -> quality/main.rs
    -> normalized tree
    -> accepted amalgamation oracle
    -> amalgamate/main.rs
    -> doom.c
```

Repeated generation must produce identical hashes. The generated `doom.c` must
be byte-identical to the accepted amalgamation oracle before the new algorithms
are committed.

## Current boundary

The C base is ready: normalized source, canonical amalgamation, Windows/Linux
native debug adapters, external WAD handling, scalable Hor+ rendering, audio,
input, saves, and the single-player runtime profile are established.

The open work is the actual Malbolge stage. See
[TODO.md](TODO.md#todo---doom-playable-generated-code-performance) for the
tracked compiler/runtime performance milestone.
