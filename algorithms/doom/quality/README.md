# DOOM Quality and Modernization Algorithm

## Purpose

This is the first DOOM application algorithm. It turns a local, user-supplied
DOOM source tree into a deterministic modernized C tree that satisfies the
repository's guest-C quality and lowerability contracts before optional
amalgamation.

The DOOM source and manual oracle are local development inputs and are not
committed. The durable authoring surface is intentionally split:

- `algorithms/doom/generator/quality.py` is a thin declarative recipe;
- `algorithms/doom/generator/doom.py` owns DOOM-specific probe/policy knowledge;
- `algorithms/diff/` owns generic matching, source binding, reconstruction, and
  transform emission;
- `algorithms/doom/quality/main.rs` is the generated transformation artifact.

The generated transformation requires the exact pinned id Software source revision
used by this profile. Possessing `main.rs` alone must not be enough to reconstruct the
local manual oracle, and a different DOOM source revision is a different profile rather
than an implicitly accepted compatibility variant.

## Scope: Interoperability Corpus, Not a DOOM Port

This algorithm does not aim to become a general-purpose DOOM source port, a
preservation project, or a replacement for projects that maintain DOOM as an
end-user game. DOOM is used because it is a demanding C interoperability corpus
that exercises the quality and C-to-Malbolge pipeline.

The engine source and game data are separate inputs. Running the corpus requires
a compatible IWAD, but no commercial id Software WAD is part of the algorithm or
its versioned artifacts. Local tests use the ignored
`in/doom/data/wad/freedoom1.wad` fixture. The engine must not depend
specifically on Freedoom.

## Local Development Layout

```text
algorithms/doom/
|-- generator/
|   |-- quality.py       # thin recipe
|   `-- doom.py          # DOOM-specific probes/policy
`-- quality/
    |-- main.rs          # generated transform
    |-- in/
    |   `-- doom/        # manual local oracle; ignored by Git
    `-- out/
        `-- doom_fixed/  # generated normalized tree; ignored by Git

repository root/doom/    # lawful source supplied by the developer; ignored
```

The root `doom/` tree contains two logically separate inputs. The official engine
source must be byte-identical to `id-Software/DOOM` commit
`a77dfb96cb91780ca334d0d4cfd86957558007e0`; the domain validates all 165 official
files against deterministic snapshot SHA-256
`20f6b67369b98c3f62b7c8ff34493ef9647c88bce7b85c82b9ecd72bad336d8b`. `data/` is
external game-data/test input and is deliberately outside that source-code pin.
`algorithms/doom/quality/in/doom/` is the manually modernized oracle used to author
and test the generated transform. Neither tree is repository source.

`out/doom_fixed/` is the reproducible materialization result. For the exact
baseline used to generate the transformation, it must be byte-identical to the
manual oracle.

## How the Algorithm Is Built

Development intentionally started with a manual reference result. That phase is
now the oracle-discovery phase, not the final implementation strategy.

1. Keep the lawful upstream source under ignored root `doom/`.
2. Maintain the ignored manual oracle under `quality/in/doom/` while discovering
   required bug fixes, host-boundary changes, and deterministic modernization.
3. Drive the oracle to zero accepted findings and validate its behavior.
4. Run `generator/quality.py`. The DOOM domain first requires the exact pinned
   upstream source revision and validates the local oracle surface; only then may the
   generic generator author transformation material.
5. The generic diff engine learns file creation/deletion/movement/modification,
   structural anchors, behavioral preconditions, and source-bound reconstruction
   material, then emits `quality/main.rs`.
6. Run generated `main.rs` against the exact root source.
   `out/doom_fixed/` must match the manual oracle byte-for-byte.
7. Run the full guest validator, six-target 64-bit compile matrix, behavior
   probes, native/runtime smokes, provenance checks, and Jig over generated
   output.
8. Re-run generation and materialization to prove deterministic byte identity.
9. Only after generated output is accepted, refresh comparison evidence and
   retire the manual oracle as an implementation dependency.

Canonical similarity may ignore comments and formatting **for identity only**.
The transformation must still preserve required source comments and provenance.

Identity, compatibility, and bug probes remain useful transformation and
postcondition evidence, but they no longer widen source-version admission for this
DOOM profile. A different upstream revision requires an explicit new pin/profile.

The recipe still records the generic engine's exploratory `0.50` / `0.66` / `0.80`
structural, anchor, and behavior thresholds for research and regression coverage. They
are not the product source-admission boundary for DOOM quality; the exact source pin is.

The source-binding and generator contract is documented in
`docs/technical/tooling/source-bound-diff-generator.md`.

## Guest Runtime Contract

The normalized DOOM core is not allowed to depend directly on a desktop OS or
on the identity of the launcher. Platform effects cross the explicit ABI in
`doom_host.h`. A conforming host supplies:

- runtime services for a stable guest-memory region, fatal diagnostics, and
  guest termination;
- video/input services for indexed-frame presentation, palette changes, and
  normalized keyboard/mouse events;
- a PCM16 audio sink; SFX mixing plus MIDI/MUS sequencing and synthesis remain
  guest-owned;
- opaque file handles with size/read-at/write-all operations;
- opaque UDP endpoints for nonblocking network transport; and
- monotonic time and sleep services.

The host ABI deliberately does not expose Win32, POSIX file descriptors, socket
structures, DNS APIs, terminal streams, or native audio-device handles to game
code. Windows, macOS, Linux, Malbolge, or another launcher may implement the
same contract independently.

The SFX mixer is in-process and deterministic. DMX sound-lump headers are
validated, sample counts are bounded, and each effect retains its declared
sample rate; the integer 16.16 playback step combines that source rate with the
historical pitch table before producing the guest's 44100 Hz stereo PCM stream.
This matters for the redistributable fixture, whose sound effects legitimately
span 11025, 16000, 17990, 22050, and 44100 Hz. Music is now guest-owned as well:
`i_music.c` validates and sequences MIDI type 0/1 and classic MUS, then mixes a
deterministic integer-only procedural synthesizer into the same PCM stream. The
Freedoom fixture currently contains 41 MIDI tracks; all 41 pass the guest parser
and synthesis-start harness, including files with running status, tempo changes,
SysEx, pitch bend, controller automation, and up to 19 tracks. The procedural
synth is a portability baseline rather than an OPL/General-MIDI fidelity claim; a
higher-fidelity guest synthesizer remains an audio-quality improvement.

A second, smaller boundary is the deterministic freestanding C runtime. The
core may use target-independent memory/string primitives such as `memcpy`,
`memmove`, `memset`, `memcmp`, `strlen`, `strcmp`, `strcpy`, `strncpy`, and
`strcat`. These are runtime semantics, not host capabilities, and should be
provided once by the Malbolge C runtime rather than reimplemented ad hoc inside
DOOM. Locale-sensitive character classification and formatting APIs are not
part of this boundary; the normalized core uses explicit ASCII helpers and
bounded text construction instead.

The deterministic memory/string runtime is now part of the guest corpus itself.
The quality validator therefore analyzes the full 65-translation-unit tree
directly with no synthetic `string.h` shim, and the freestanding symbol audit
resolves compiler-generated `memcpy`/`memset` calls to guest implementations
rather than a host libc.

## Portable Malbolge End State

The intended portable application artifact is the generated `.malbolge` program,
not a persistent `doom.bytecode` sidecar. Compiler IR, compact bytecode, decoded
execution IR, or native machine code may exist transiently in RAM or in explicitly
rebuildable execution caches, but they are implementation details. A packaged
DOOM build should therefore be conceptually launchable as `malbolge doom.malbolge`
on every supported host. The `.malbolge` file is the portable program; the native
VM/runner is the platform adapter.

The current memory bootstrap reflects that rule explicitly: `DoomHost_GuestMemoryRegion`
provides storage for the guest address space, while the DOOM zone allocator
performs all object allocation within that storage. The host does not expose a
general-purpose malloc-like service to the guest. The guest requires at least
16 MiB, but no longer truncates a larger host-provided region to that historical
minimum; the entire validated region becomes the zone heap. This matters at high
internal resolutions: the 2304x1080 integration smoke succeeds with a 32 MiB
guest region once that artificial 16 MiB cap is removed.

The current DOOM corpus now satisfies that rule at the object-symbol boundary.
Its deterministic guest runtime implements the memory/string subset it needs,
including the standard `memcpy`/`memset` spellings that Clang may synthesize for
aggregate operations. A freestanding symbol audit resolves every non-host symbol
inside the guest; only `DoomHost_*` capabilities remain external. The quality
validator therefore runs directly over the corpus without a synthetic `string.h`
shim.

The guest must not link against or call the host's native libc as a shortcut.
The supported C runtime surface, including memory and string operations and the
guest allocator, is part of the program/runtime that ultimately executes under
Malbolge semantics. The compiler may recognize such operations as intrinsics for
optimization, but their observable semantics must remain guest semantics rather
than becoming hidden calls to `msvcrt`, glibc, musl, libSystem, or another host C
library. Several `doom_host.h` services began as bootstrap conveniences, but the memory
and diagnostic boundaries are now cleaner. The host no longer allocates guest
objects: it exposes one stable writable guest-memory region, and `Z_Malloc` owns
allocation policy inside that region. Fatal-message formatting also happens in
the guest; the host receives already formatted text bytes. Music parsing, timing,
and synthesis now likewise remain in the guest, so the host audio boundary is a
PCM sink rather than a hidden media implementation. The final lowering path
retains only true external capabilities at the host boundary.

A freestanding Windows x86-64 integration harness also links the complete guest
without a CRT and boots the real `data/wad/freedoom1.wad` through the version-1
host boundary. It reaches the live game loop, validates a non-zero indexed frame
and palette, and submits guest-mixed PCM after at least 30 presentations. The
same smoke passes with internal render scales 1x, 2x, 3x, and 4x (320x200,
640x400, 960x600, and 1280x800), with a 1280x600 Hor+ raster whose corrected
display aspect is exactly 16:9, and with a non-standard 1100x600 raster whose
corrected display aspect is 55:36. Rational vertical scaling is exercised at
328x205 (1.025x classic height) and at a full-width 2304x1080 Hor+ raster; both
boot the real Freedoom fixture through renderer, palette, game loop, and PCM
submission. This runtime test exposed and fixed issues
that syntax analysis alone could not, including non-NUL-terminated eight-byte
WAD names escaping into C string lookup, a visplane sentinel whose signed
widening reversed the ordering relied on by the historical span builder, and a
plane-stepping formula that incorrectly used the physical screen center instead
of the preserved focal length in widescreen views.

The current source ABI has 24 external operations and carries a versioned set of
stable semantic capability IDs (`DOOM_HOST_ABI_VERSION == 1`). IDs are grouped by
runtime, video/input, PCM audio, file, UDP network, and monotonic-time effects.
They are lowering metadata, not an instruction encoding: for example, the ID for
indexed-frame presentation does not imply that Malbolge contains a literal
`TRAP` opcode with that number. A VM interpreter, AOT backend, or JIT may realize
the same capability through different guarded call mechanisms while preserving
the same guest-visible ABI. Argument marshalling and the VM call-frame format
belong to the general runtime ABI, not to DOOM-specific source code.

`doom_host.h` is a source-level capability ABI, not a commitment to a literal
`TRAP` instruction. A backend may lower a host call to a VM service opcode, a
validated mailbox/protocol, a conventional runtime call, or another mechanism
defined by the selected modern Malbolge profile. What matters is the boundary:
gameplay, parsing, allocation, formatting, hashing, and other guest algorithms
remain in the guest; the host supplies effects that inherently cross into the
outside world, such as display presentation, input events, PCM audio-device
output, monotonic time, persistence/raw file access, and network transport.

Clang/LLVM belongs to the build pipeline, not to the normal execution contract.
Clang is useful for parsing and type-checking C before `.malbolge` emission, but a
user should not need LLVM installed merely to run an already generated program.
Likewise, AOT and JIT are optional VM accelerators. Self-modifying Malbolge makes
native translation harder, not impossible: versioned code-state guards, cache
invalidation, and deoptimization can accelerate stable or observed regions while
the interpreter remains the semantic fallback. Interpreter-only execution must
remain available.

A single `.malbolge` file cannot literally execute itself on Windows, macOS, and
Linux without some Malbolge runtime being present; operating systems do not share
one executable format or a built-in Malbolge loader. "No installation" therefore
means that distribution may include a small native runner for each supported
OS/architecture, or a per-platform wrapper that embeds that runner, while the
same `.malbolge` payload remains unchanged. A double-clickable one-file package
would necessarily be a different native wrapper per platform, even when each
wrapper contains the identical Malbolge guest.

For assets, two modes are compatible with this contract. A redistributable
self-contained demonstration may link Freedoom data directly into packaged
payload data so startup requires no external IWAD. The linker/packager should
embed raw asset bytes as data rather than force a giant C array through the
source frontend. Packaged resources and ordinary host files intentionally share
the same generic `DoomHost_File*` namespace: for example, the guest may open
`data/wad/freedoom1.wad` without knowing whether the runner resolves that name to
bytes carried inside the payload or to an external file. No Freedoom-specific
syscall, native filesystem ABI, or guest-side libc is required.

A freestanding Windows packaging harness validates this model by assembling the
28,795,076-byte Freedoom IWAD directly into a read-only object section with an
`.incbin` resource, linking that object beside the unchanged guest, and mounting
its byte range behind the normal file capabilities. The resulting PE boots to
the live game loop with palette, non-zero framebuffer output, and PCM submission
from an otherwise empty working directory: no `data` directory, no external WAD,
and no explicit `-iwad` argument are present. The PE is only a proof of the
resource-mount contract; the same mechanism can be implemented by a Malbolge
payload packager/runner without changing the DOOM guest.

User-owned commercial IWADs remain external inputs and use the same opaque host
data capability instead of being redistributed. Savegames and other persistence
also remain host-backed raw data operations even when the base IWAD is packaged.

The temporary desktop runner also exercises a small launcher-side `settings.json`
schema. JSON remains a host/launcher concern; the DOOM guest does not parse JSON.
The current schema is:

```json
{
  "iwad": "",
  "wads": [],
  "language": "english",
  "maximized": true,
  "resolution": [1280, 720],
  "vsync": false,
  "show_fps": true
}
```

`iwad` selects exactly one base IWAD. An empty string means that the runner may
use its packaged/autodetected resource, which is Freedoom in the current manual
harness. `wads` is an ordered list of zero or more PWAD/mod files; later files are
added after earlier files and therefore participate in DOOM's normal later-lump
override semantics. The guest-side WAD list now grows dynamically rather than
retaining the historical fixed `MAXWADFILES = 20` array. A stress run loaded 64
valid PWADs successfully. The temporary JSON parser currently reserves space for
512 PWAD paths, but that is a harness implementation bound, not a guest/runtime
contract.

Relative launcher paths are resolved from the directory containing the runner and
`settings.json`, not from whatever working directory happened to launch the
process. Absolute host paths are also accepted by the native file backend but are
inherently less portable. Forward slashes are the recommended JSON spelling on
all supported hosts; Windows absolute paths may also use escaped backslashes. The
guest treats paths as opaque names passed to `DoomHost_File*` and never parses
Windows drive letters or POSIX path syntax itself.

`language` is a launcher **default**, using a stable textual identifier such as
`english`, `spanish-latam`, `portuguese-pt`, `korean`, `leetspeak`, or
`malbolge`. A language already persisted by the in-game config takes precedence,
so changing the menu option survives restart rather than being reset by the JSON
file.

As a guest-side portability check, the normalized corpus currently passes the
full strict compile gate for all 65 translation units on six freestanding 64-bit
targets: x86-64 and AArch64 for Windows, macOS, and Linux. No `LINUX`,
`NORMALUNIX`, `_WIN32`, or `__APPLE__` conditional is required by the guest
source. This demonstrates source/ABI portability of the guest, not completion of
the six native host runners; window, audio-device, persistence, timing, and
network adapters remain runner responsibilities.

The host runner itself may use operating-system facilities, because talking to
the window system, audio device, clock, filesystem, or network is its purpose.
However, "no external installation" must be evaluated per platform. Win32 and
macOS provide stable system frameworks for these effects. Linux has no single
desktop graphics/audio library guaranteed on every installation, so a Linux
runner must use explicitly supported system protocols/backends or package the
required adapter code; assuming that Xlib, ALSA, PulseAudio, or PipeWire is
always preinstalled would violate the portability claim.

## Runtime Localization

Language selection is runtime state rather than a compile-time `#include` choice.
The existing `d_*.h` catalogs remain the source of truth; the reproducible
`.temp/generate_runtime_languages.py` script generates a typed table for 280
localized strings plus four language-dependent chat hotkeys across 17 catalogs.
The Options menu exposes a Language row that cycles the active catalog without
restarting the game. Quit text, pickup/status messages, map names, chat defaults,
finale text, and cast names resolve through the active table at use time instead
of being frozen in static initializers. `Esc` now returns from a submenu to its
parent and closes the menu only at the main-menu root.

The historical melt/wipe no longer owns a modal mini-event-loop: host events, menu
ticks, and PCM pumping continue while the transition advances. An automated Win32
probe sent `O -> Enter -> L -> Right` immediately after window creation, during
the startup transition, and the resulting language change persisted correctly.
This directly covers the human-playtest report that menu options were visible but
unresponsive while the game animated behind them.

Font coverage is a separate limitation. The current Freedoom HUD font exposes
only `STCFN033` through `STCFN095` (63 glyphs). The diagnostic
`.temp/validate_doom_languages.py` reads those real patch widths from the WAD,
resolves catalog aliases, reports unsupported characters, and checks literal line
widths against the classic 320-pixel surface. English, French, and Leetspeak need
no additional glyphs; most accented Latin catalogs need diacritics, Malbolge text
needs `` ` { | } ~ ``, and CJK/Korean/Russian require much larger glyph coverage.
The selector intentionally exists independently of that future font work: missing
glyph support is reported honestly rather than hidden behind compile-time language
selection.


## Presentation Model

The normalized renderer separates **simulation**, **internal rasterization**, and
**physical presentation**. Gameplay simulation remains fixed at the historical
35 Hz clock, while presentation may run independently at 60 Hz or faster.
Render-only history on players and mobjs interpolates camera position, view
height, actor position, and actor rotation between simulation ticks. Spawn and
teleport discontinuities explicitly invalidate interpolation. These render-only
fields do not participate in savegames, demos, network commands, RNG, collision,
or thinker simulation.

Classic WAD art and UI continue to use the original 320x200 coordinate system,
identified explicitly as `DOOM_UI_WIDTH`/`DOOM_UI_HEIGHT`. The world framebuffer
has runtime dimensions and defaults to the same 320x200 geometry. The
`-render-scale N` option remains a compatibility shorthand for an integer
internal height (`200 * N`): scale 1 is 320x200, scale 2 is 640x400, scale 3 is
960x600, and so on. `-render-height H` selects the height directly; `H` must be
at least 200 and divisible by 5 so the corrected classic 4:3 raster width
`8 * H / 5` remains integral. `-render-scale` and `-render-height` are mutually
exclusive. Renderer-owned clip tables, view-angle tables, plane/sprite
working buffers, visplane column storage, drawseg pools, visible-sprite pools,
and solid-segment clip storage are runtime allocated rather than encoded as
fixed 320x200 array types or 1993-era hard limits. Drawsegs, visible sprites, and
visplanes grow as needed without invalidating live renderer references.

UI/WAD patches are composed in classic coordinates and nearest-neighbor scaled
to the runtime framebuffer. A dedicated classic 320x200 composition surface is
used for operations such as the status bar, reduced-view border, finale tiled
backgrounds, and bunny-scroll frames so those scenes preserve their historical
proportions at higher internal scales. Native framebuffer overlays such as the
pause patch and automap marks use an explicit scaled-native drawing path. A
freestanding Windows PE harness exercises the real `v_video.c` scaler at 2x and
verifies 640x400 allocation plus exact 2x2 expansion for classic patches, native
scaled patches, and classic-surface rectangle copies.

The logical image carries an explicit corrected display aspect in
`doom_host_video_config_t`. DOOM's indexed raster retains the historical 5:6
pixel-aspect correction, so the display aspect is derived as
`(render_width * 5):(render_height * 6)` and reduced before crossing the host
boundary. A 320x200 raster therefore remains 4:3, while 1280x600 is exactly
16:9. The host owns the final physical window/display size and should preserve
the supplied aspect with letterboxing or pillarboxing only when the physical
surface itself requires it.

The vertical/classic-UI transform is rational and integer-only rather than being
restricted to an integer multiplier. With `-render-height H`, every classic
coordinate boundary is mapped by the exact `H/200` ratio and spans are formed
from differences between mapped boundaries, so fractional scales distribute
nearest-neighbor pixels deterministically without floating point. For example,
`-render-height 205` produces a 328x205 corrected-4:3 raster and exercises a
1.025x transform whose source pixels alternate between one- and two-pixel
coverage. `-render-scale N` produces the same geometry as `-render-height 200*N`.

`-render-width W` may select any even width at least the corrected classic width
for the chosen height. Extra width is Hor+ world space rather than stretched or
letterboxed game content: the focal length remains tied to the classic-width
projection, the status bar/menu/HUD remain centered in the classic 320x200
coordinate surface, and `screenblocks=10` expands the world viewport across the
full raster width. Thus `-render-height 1080 -render-width 2304` is an internal
2304x1080 Hor+ raster whose corrected display aspect is exactly 16:9.

Differential renderer probes verify that classic reduced views retain identical
central ray tables, distance tables, wall clipping, and final viewport pixels
when placed inside a wider framebuffer. For a full-width `screenblocks=10`
1280x600 Hor+ view, the central 960x504 region has identical ray, distance, and
wall-clipping geometry to the 960x600 classic render while both 160-pixel side
wings contain real rendered world data. The first deterministic test frame
matches in 483,833 of 483,840 central pixels (99.99855%); the remaining seven
palette-index differences are confined to one floor/ceiling scanline and arise
from historical fixed-point visplane span phase when wider traversal changes
span segmentation. This is treated as rasterization noise, not a gameplay or
projection difference, rather than being hidden behind a claim of bit-identical
Hor+ output.

The reproducible test IWAD lives at `in/doom/data/wad/freedoom1.wad`. `-iwad`
remains authoritative when supplied explicitly; otherwise the core searches
`data/wad` before local fallback directories and determines the game mode from
WAD contents rather than from commercial filenames. Map availability is also
content-driven: the engine centralizes `MAPnn` versus `ExMy` naming and starts a
map only when that lump is actually present. Episode-menu entries are enabled
from the loaded WAD rather than from shareware/registered/retail labels, so the
fixture exposes all four of its populated episodes. Edition labels remain only
where they select genuinely different game semantics or namespaces. User-owned
commercial IWADs may be supplied locally but are not required or distributed by
this fixture.

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
the generated `main.rs` must be able to start from the admitted source and
recreate the normalized result without the local oracle or hidden hand edits.

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
- depend on host capabilities rather than a specific orchestrator identity: a
  packaged result may be launched as `malbolge doom.malbolge`, but the game
  core must remain usable with another conforming launcher/runtime;
- run correctly on current 64-bit Windows, including working in-process audio;
- support modern scalable/high-resolution presentation without forcing a single
  resolution, with borderless-window operation as a first-class mode;
- decouple rendering from the historical 35 Hz game clock so presentation can
  sustain at least 60 FPS while preserving intended gameplay timing;
- remove obsolete DOS, 32-bit, legacy Unix, and end-of-life Windows assumptions
  from the required compatibility surface; and
- modernize unsafe, undefined, implementation-defined, host-specific, and
  unnecessarily obsolete C as far as the behavioral contract permits; and
- keep repository-facing source comments, diagnostics owned by this pass,
  documentation, maintained names, and generated explanatory text English-only;
  explicit user-facing localization catalogs are the intentional exception and
  may contain their target languages.

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
result: the thin generator recipe, generated `main.rs`, this README, contracts,
tests, manifests, and validation logic.

Relevant authorities:

- `docs/technical/interoperability/doom-modernization.md`
- `docs/todo/open/applications/doom-quality-and-modernization-pass.mdc`
- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/legal/adr/legal-research-and-repository-boundary.md`
