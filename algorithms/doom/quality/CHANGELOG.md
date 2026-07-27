# DOOM Modernization Changelog

This is the changelog for the DOOM quality corpus inside Malbolge.

I am writing it in first person because I am both the person doing the
modernization and, somehow, the person who played DOOM for the first time while
validating it.

I was born in 2007. I did not arrive with thirty years of DOOM muscle memory.
That turned out to be an unexpectedly effective testing methodology.

This is still **not a DOOM port**. The goal is to make DOOM an unusually
demanding,
portable, deterministic guest for the Malbolge toolchain while keeping operating
system effects behind a generic runtime boundary.

The temporary native runners exist to prove that boundary. They are laboratory
equipment, not the final product.

## Architecture: Source-Bound Generation

The manual modernization oracle is now good enough to stop being the place where
I invent the final algorithm by hand. The next problem is reproducing it.

I moved the DOOM application pipeline from the old `interop/` namespace into
`algorithms/doom/` and introduced a generic `algorithms/diff/` scaffold.

The intended authoring flow is now:

```text
root doom/ + local normalized oracle
             |
             v
algorithms/doom/generator/quality.py
             |
             v
       algorithms/diff
             |
             v
algorithms/doom/quality/main.rs
```

`quality.py` is deliberately boring. It names the source, oracle, output, DOOM
domain policy, and provisional thresholds. DOOM-specific probes belong in the
DOOM generator module. Generic matching, source binding, reconstruction, and
transform emission belong in `algorithms/diff/`.

The exact baseline must reproduce the manual oracle byte-for-byte. A compatible
later source revision may preserve legitimate upstream changes when all
postconditions still pass.

Source identity is intentionally fuzzy enough to survive comments, formatting,
and reasonable upstream edits, but not so fuzzy that the generated transform can
materialize the target from unrelated source. The first experimental recipe
records 0.50 structural similarity, 0.66 stable-anchor coverage, and 0.80
behavior similarity. Those are calibration values, not legal thresholds.

Behavior probes are split into identity, compatibility, and bug probes. In
particular, a future upstream DOOM revision should not be rejected merely
because it already fixed one of the original bugs that this modernization fixed.

The generated transform must remain source-bound: possessing `main.rs` alone is
not enough to reconstruct the local target. The exact cryptographic construction
is intentionally still open and must be independently tested before adoption.

The same generic engine is planned for a second stage later: accepted normalized
DOOM plus a semantically validated local single-file oracle will generate the
source-bound amalgamation transform for canonical `doom.c`.

Implementation has now started behind that contract. The exact authoring layer can
reconstruct the manual oracle byte-for-byte from local source using whole-file
copies, source spans, and local authoring literals. Generic structural/anchor
admission is also executable, while the DOOM domain module now supplies a C-aware
identity view that excludes the WAD and IPX source family from Linux lineage
scoring. Generic behavior admission and portable process-probe execution now also
exist. The DOOM domain has its first executable fixed-point identity probe, while
`algorithms/diff` now also protects exact-plan oracle literals behind source-bound
authenticated payload recovery and emits the exact plan as standalone std-only Rust.
`write_algorithm()` now exposes explicit exact and compatible modes. Exact mode is a
working public generation path; the DOOM `quality.py` recipe deliberately selects
`COMPATIBLE`, which remains fail-closed until the emitted runtime owns canonical
identity, admission, and broader behavior/bug evidence. This prevents a working exact
baseline from silently narrowing the product contract.

The standalone Rust exact-transform smoke is now end to end. The generated source
was 4,655,376 bytes, compiled warning-free with Rust 1.97.1, ran directly against
the ignored original `doom/` tree, and materialized a temporary 152-file output
whose complete snapshot matched the manual oracle. Compilation took about 1.6
seconds and materialization about 12.3 seconds on the development workstation. The
generated `.rs`, executable, and output were all deleted after the smoke.

The protected exact-plan smoke now exercises the complete local authoring corpus
without publishing it. It encrypted 2,116,232 target-only bytes into one RFC 8439
payload, source-bound the key with 127 distributed shares (84 required), and
materialized a temporary 152-file tree whose snapshot matched the manual oracle
exactly. The temporary output was deleted; source and oracle remained read-only.

The first executable behavior calibration uses `m_fixed.c` only. A small MIT
freestanding harness is compiled with pinned LLVM 22.1.8 into a no-CRT Windows
x86-64 PE, then the process exit code is hashed as behavior evidence. The ignored
historical source and the local modernized oracle produced the same transcript
digest without either tree being modified. Repository regression tests use
synthetic fixed-point implementations rather than local DOOM source.

As a local calibration stress test, the 124 selected Linux source C/header files
were compared with their current normalized descendant paths. The current rolling
anchor profile measured 0.780928 structural similarity and 0.766396 stable-anchor
coverage; 94 of 123 anchor-eligible files individually met the provisional 0.66
coverage threshold. This is engineering calibration, not acceptance or legal
evidence.

## Bugs First

A static analyzer can tell me many things. It cannot tell me that a door feels
broken because I assumed Space meant jump.

This section stays near the top on purpose.

### Fixed: E2M1 could crash immediately

I found this by doing the very sophisticated QA procedure of selecting another
episode from the menu.

The first reproducible matrix was:

- E1M1: pass.
- E2M1: access violation.
- E3M1: pass.
- E4M1: pass.

A diagnostic build localized the crash to `R_PointToDist(0, 0)`. A wall vertex
could coincide exactly with the current viewpoint, producing a degenerate fixed
point division and then an invalid `tantoangle` lookup.

Zero displacement now returns zero distance directly.

The same four-episode smoke now passes E1M1 through E4M1.

Human playtesting: 1. Static-only confidence: 0.

### Fixed: `READ THIS!` made the whole game feel broken

My first report was approximately:

> `READ THIS!` froze the audio!

A few seconds later I corrected myself:

> Nope. It is not just the audio. The whole game lost FPS.

The sensation reminded me of opening a DAW, adding too many plugins, and hearing
realtime playback stop behaving like realtime playback.

That description was surprisingly close to the actual failure.

Two independent problems were interacting:

1. The opaque full-screen help page still rendered the entire invisible 3D world
   behind itself.
2. The PCM mixer submitted only one 512-frame block per presentation iteration.

At 44.1 kHz, 512-frame blocks require about 86.13 submissions per second. When
the expensive help path dropped below that cadence, audio starved as a
consequence of the frame loop being late.

The fix was not to hide the symptom:

- invisible world rendering is skipped while the opaque help page covers it;
- the audio pump may fill multiple writable blocks per iteration, with a bounded
  recovery limit;
- menu input and audio continue to pump during historical wipe transitions.

The help page stopped being a tiny realtime scheduling benchmark disguised as a
README from 1993.

### Fixed: the menu was visible but temporarily frozen

The historical melt effect ran its own inner loop. The menu could be visible
while that loop was active, but input was not being processed normally.

This looked ridiculous in practice: I could see the menu while the game animated
behind it, but I could not move the selection for a moment.

The wipe now continues to pump:

- host events;
- menu processing;
- audio.

I tested this by sending menu input immediately after window creation, while the
startup transition was still running. The language selection changed and was
persisted successfully.

### Fixed: Windows occasionally played a mysterious `PURU PUM`

This was not a DOOM sound effect.

The temporary Win32 runner manually translated keyboard events but also called
`TranslateMessage()`. That produced `WM_SYSCHAR`; unhandled system characters
then
reached `DefWindowProc()`, which responded with the normal Windows complaint
sound.

The runner already owned key translation, so `TranslateMessage()` was removed.

The bug took minutes to fix and considerably longer to identify musically. The
full embarrassment is preserved later in this file.

### Fixed: a door appeared to do absolutely nothing

This was mostly a user-interface archaeology problem rather than a broken map.

Classic DOOM uses a dedicated **Use** action bound to Space.

I had assumed:

> Space is jump. Obviously.

DOOM responded by not having a normal jump action at all.

Modern controls now keep Space and add configurable `E` as a secondary Use
binding.

The game immediately became less like a corridor simulator.

### Fixed: the mouse felt like walking on ice

Classic vertical mouse movement drives the player forward and backward.

I interpreted this as a physics bug because I was moving the mouse and the
player
seemed to slide through the level.

Modern controls now use:

- mouse X for horizontal camera rotation;
- mouse Y for no locomotion at all.

The classic behavior remains available when modern controls are disabled.

### Fixed: arrow keys behaved like an archaeological artifact

Classic Left and Right turn the player. Strafing requires an additional
modifier.

That makes historical sense and felt completely insane to me.

The modern default profile now uses:

- `W` or Up: move forward;
- `S` or Down: move backward;
- `A` or Left: strafe left;
- `D` or Right: strafe right;
- mouse X: turn;
- `E` or Space: Use.

The host does not lie about letter keys. `WASD` remains real letter input, so
cheats, menus, and other text-oriented behavior are not broken by fake arrow-key
aliases.

### Fixed: `Graphic Detail: High` was a decorative lie

The old Low/High detail switch survived after low-detail rendering no longer
did.
The menu therefore offered a choice that was permanently forced to High.

I removed the dead option instead of pretending it still did something.

Its old F5 shortcut disappeared with it, which conveniently freed F5 in the
manual runner for an optional FPS display.

### Fixed: the first playable runner flickered like it wanted to hurt me

The earliest Win32 manual runner cleared the whole client area to black before
presenting each frame.

That produced ugly flashing and even made screenshot capture race against a
black
frame.

The runner now retains the last presented framebuffer and repaints it from
`WM_PAINT` instead of erasing the entire surface every presentation.

### Fixed: mouse capture initially behaved like friendly malware

The first manual runner recentered the cursor unconditionally during relative
mouse input.

The result worked, but trying to leave the game felt suspiciously like fighting
an application that did not want me to escape.

Mouse capture now applies only while actual level gameplay wants relative input.
It releases during menus, pause, non-level states, and focus loss, then
recaptures
when gameplay resumes.

### Fixed: renderer modernization exposed real runtime edge cases

The end-to-end smoke tests found bugs that syntax checks did not:

- fixed-width eight-byte WAD names were accidentally treated as NUL-terminated C
  strings in one path;
- a widened visplane sentinel used `-1`, reversing an ordering property that the
  original `0xff` sentinel relied on;
- widescreen floor and ceiling projection incorrectly used physical screen
  center
  where it needed the preserved focal length;
- the old zone initialization silently discarded host memory above 16 MiB.

All four were fixed at their actual abstraction boundary instead of being hidden
inside the test harness.

## Current Open Work

I am deliberately separating "works" from "finished forever".

### Font coverage is still the largest localization limitation

Runtime language selection works. The historical HUD font does not magically
gain
Unicode coverage because I added a selector.

The Freedoom `STCFNxxx` HUD font currently exposes 63 glyphs, from `!` through
`_`.

A WAD-backed validator now reads the actual glyph widths and reports both
missing
glyphs and literal lines wider than the classic 320-pixel surface.

Current broad result:

- English: representable by the current HUD font.
- French: representable by the current HUD font.
- Leetspeak: representable, with all checked literal lines within 320 pixels.
- Spanish, German, Italian, Portuguese, Polish, and Latin: need additional
  accented glyphs.
- Russian, Japanese, Chinese, and Korean: need substantially broader glyph
  coverage.
- Malbolge text is almost representable; the current font lacks
  `` ` { | } ~ ``.

This is documented rather than hidden, and it is not blocking localization from
being considered complete for this benchmark. I am not turning the guest into a
font engine merely to make this look like a polished source port.

### Music fidelity is intentionally provisional

Music is now guest-owned and functional, but the current deterministic
procedural
synthesizer is a portability baseline.

It is not pretending to be a bit-perfect OPL emulator or a perfect General MIDI
synth.

In practical terms, my first reaction was that it sounded a little like a
refrigerator that had learned 8-bit music.

That is an aesthetic problem, not a missing host dependency.

### Native desktop runners are still proof harnesses

The Windows runner proves the architecture using only system APIs and no CRT.
Production-quality runners for all six supported OS/architecture combinations
are
still VM/runtime work.

The guest is already portable across those targets; the desktop integration is
what remains platform-specific.

## Gameplay and UX Changes

These are changes I intentionally made to make the guest pleasant to exercise.
They are not an attempt to silently turn DOOM into a modern source port.

### Modern controls

New configurations default to `modern_controls=1`.

The modern profile provides:

- `W` and Up for forward movement;
- `S` and Down for backward movement;
- `A` and Left for left strafe;
- `D` and Right for right strafe;
- mouse X for yaw;
- mouse Y ignored for locomotion;
- `E` and Space for Use.

`modern_controls=0` restores the classic control model.

The game still does not have conventional free vertical mouse-look. I am not
rewriting the gameplay model just because I initially thought the aiming felt
haunted.

### Menu behavior

Normal non-autostart launch now shows the main menu immediately.

An earlier manual runner accidentally injected `-skill 3`, which enabled
autostart and made me think the title/demo behavior was the menu.

`Esc` now behaves as I expected a menu to behave:

- inside a submenu, it returns to the parent menu;
- at the main menu root, it closes the menu.

The old Backspace behavior still works where appropriate.

### Runtime language selection

Language selection is no longer a compile-time `#include` decision.

The 17 catalogs can be selected at runtime from Options.

The existing `d_*.h` files remain the source of truth. A reproducible generator
builds typed runtime tables containing 280 strings plus four localized chat
hotkeys per language.

Runtime lookup replaced language-frozen static initializers in areas including:

- quit messages;
- pickup and status messages;
- map titles;
- player and chat names;
- finale text;
- cast names.

Customized chat macros remain user overrides. Unmodified defaults follow the
active language.

The Korean catalog remains exactly the intentionally satirical artifact it was.
I did not "fix" the joke out of it while converting the selection mechanism.

## Guest Runtime and Host Boundary

This is the part that matters most to the Malbolge project.

### DOOM no longer depends on a hosted C library

The guest owns the deterministic memory and string subset it needs.

The runtime includes guest implementations for the relevant operations,
including
standard spellings that Clang may synthesize for aggregate operations:

- `memcpy`;
- `memset`;
- `memcmp`;
- `strlen`;
- `strcmp`;
- `strcpy`;
- `strcat`.

Normal source code can use the guest-owned `M_*` helpers, while
compiler-generated
calls still resolve inside the guest instead of escaping to host libc.

The real validator no longer needs the old synthetic `string.h` probe shim.

### The host provides capabilities, not DOOM internals

The guest does not include Win32, Cocoa, X11, ALSA, WASAPI, libc, or other
native
platform interfaces.

The external boundary is the generic `DoomHost_*` capability ABI.

The current semantic capability surface covers:

- guest memory;
- diagnostics and termination;
- video and palette presentation;
- normalized input;
- PCM audio;
- files;
- UDP networking;
- monotonic time and sleeping.

The capability IDs are stable semantic metadata for a lowerer/runtime. They are
not a promise that Malbolge must literally grow a hard-coded `TRAP #0x01`
instruction.

Interpreter, JIT, and AOT implementations may choose different physical calling
mechanisms while presenting the same semantics.

### No native allocator shortcut

The host no longer allocates individual game objects.

It provides a stable memory region. The DOOM zone allocator owns allocation
inside that region.

The old code also truncated the usable zone to 16 MiB even when the host
supplied
more memory. That historical cap is gone: 16 MiB is now a minimum requirement,
not an artificial maximum.

This was discovered while testing a 2304x1080 internal raster. Increasing the
host region from 32 MiB to 64 MiB initially changed nothing because DOOM was
quietly throwing the extra memory away.

That was a very educational use of an hour.

### Fatal errors are formatted inside the guest

The host receives already-formatted diagnostic bytes.

It does not receive a guest `va_list`, and it does not call host `printf` on
behalf
of DOOM.

The formatter intentionally supports the small deterministic format subset the
corpus actually needs rather than recreating all of hosted `printf`.

### No persistent `doom.bytecode` design

There is no required persistent `doom.bytecode` artifact.

Intermediate decoded state, IR, JIT code, or caches may exist transiently or be
reconstructed in memory, but the portable guest artifact remains the Malbolge
program.

LLVM is a build/lowering tool. It is not a runtime dependency that the final
guest
must ask the user to install.

## Core C23 and Data-Model Cleanup

A large part of the modernization was deliberately boring: make the old C mean
exactly what it appears to mean on modern 64-bit targets.

### Types and ownership were made explicit

I removed several categories of historical "the ABI will probably save us"
behavior:

- gameplay `boolean` semantics were normalized;
- network/protocol fields that require exact sizes use fixed-width integer
  types;
- state action callbacks use typed function pointers instead of loose calling
  assumptions;
- config storage no longer relies on pointer/integer punning;
- runtime asset and texture indices are not narrowed back to historical 16-bit
  storage unless the on-disk format actually requires it;
- HUD/message pointers were made `const` where the text is not owned or mutated
  by
  the caller.

### On-disk data is treated as on-disk data

WAD structures use fixed-width representations at the file boundary instead of
assuming that a native C structure has the right size or alignment.

Fixed eight-byte WAD names are normalized before C-string lookup instead of
being
read one byte beyond the field and hoping the next byte happens to be zero.

Texture and level setup paths validate sizes, offsets, counts, and allocation
arithmetic before using WAD-controlled data.

The runtime structures are allowed to be wider than the historical file fields.
The file format stays historical; the in-memory engine does not need to inherit
every old width limitation.

### 64-bit allocation arithmetic was audited

The zone allocator, texture data, renderer workspaces, savegame buffers, and
related size calculations were moved away from 32-bit/pointer-size assumptions.

Temporary allocations that previously depended on hosted `calloc`/`malloc`
behavior were moved into guest-owned zone memory with explicit initialization
when
zero-fill semantics mattered.

### Hosted-libc archaeology was removed instead of wrapped

The corpus no longer needs `stdio`, `stdlib`, locale-sensitive classification,
or
host formatting to run.

Examples of the cleanup include:

- `atoi()` replaced by deterministic integer parsing;
- `abs()` call sites replaced with defined integer/fixed-point logic;
- `sprintf`-style HUD/status/intermission construction replaced by bounded guest
  text builders;
- `strncasecmp`/`strings.h` use replaced by deterministic ASCII comparison;
- temporary `calloc`/`malloc` paths removed from guest code;
- orphaned hosted headers removed.

The goal was not to recreate libc inside DOOM. The goal was to leave a small,
explicit deterministic runtime surface that can lower to Malbolge semantics.

### Historical compiler/linker debris was removed

The old source carried decades of build archaeology that no longer selected any
meaningful behavior in this guest:

- RCSID globals were removed;
- obsolete `__GNUG__` interface/implementation pragmas were removed;
- `NORMALUNIX`/`LINUX` guest conditionals were eliminated;
- the guest no longer needs `_WIN32` or `__APPLE__` branches;
- raw random-state leakage was replaced by an accessor where external
  observation
  was still required;
- an orphan `HU_PlayerName` declaration gained its missing definition.

This is why the same C sources can now be checked against six freestanding
64-bit
ABIs without changing source-level platform macros.

## Renderer and Presentation

This is where a surprising amount of 1993 became runtime state.

### Runtime framebuffer geometry

`SCREENWIDTH` and `SCREENHEIGHT` are no longer compile-time array dimensions.

The renderer uses runtime dimensions and dynamically allocated working storage.

The classic 320x200 coordinate system remains explicit for WAD art and UI, while
the world raster may use larger runtime dimensions.

### Rational internal scaling

The old integer-only idea became a rational vertical transform.

`-render-scale N` remains a convenient shorthand.

`-render-height H` selects a runtime height directly. Classic coordinate
boundaries are mapped using deterministic integer arithmetic, and spans are
formed
from differences between mapped boundaries.

This supports awkward-but-useful tests such as 328x205, where a classic source
pixel may deterministically cover one or two physical pixels depending on its
position.

Real runtime smokes have exercised, among others:

- 320x200;
- 640x400;
- 960x600;
- 1280x800;
- 1280x600 Hor+;
- 1100x600;
- 328x205;
- 2304x1080 Hor+.

### Hor+ widescreen

Extra width is real world space rather than a stretched 4:3 image.

The renderer preserves the classic focal length while allowing additional rays
at
the sides.

The classic UI remains centered in its own 320x200 coordinate space.

The corrected display aspect preserves DOOM's historical 5:6 pixel aspect. For
example, a 1280x600 internal raster presents as exactly 16:9.

A deterministic comparison of the 1280x600 Hor+ path against the equivalent
classic center found matching ray tables, distance tables, and wall clipping.
The first test frame matched 483,833 of 483,840 central pixels.

The remaining seven palette-index differences were isolated to historical
fixed-point visplane span phase, not changed gameplay or a different central
FOV.

I am documenting the seven pixels instead of claiming "pixel identical" because
99.99855% is already impressive enough without lying.

### Dynamic renderer storage

The old fixed capacities were replaced where they were arbitrary implementation
limits rather than game semantics.

This includes runtime storage or growing pools for areas such as:

- drawsegs;
- visible sprites;
- visplanes;
- solid segment clipping;
- view-angle tables;
- plane clipping and caches;
- sprite clipping;
- scanline lookup tables;
- openings and related renderer work buffers.

Stable-object pools are used where live pointers must remain valid while lookup
arrays grow.

### Simulation and presentation are separate

Gameplay simulation remains at the historical deterministic 35 Hz.

Presentation can run much faster.

Render-only interpolation tracks previous camera and actor state and computes
sub-tic presentation without changing gameplay simulation.

Spawn, load, and teleport discontinuities invalidate interpolation history
rather
than interpolating through impossible positions.

Render-only history is not serialized into savegames and does not participate in
collision, RNG, demo logic, or network commands.

## Audio

Audio is now one of my favorite examples of why the host boundary exists.

### SFX are mixed in the guest

The game no longer assumes every DMX sound is 11025 Hz.

The loader validates the DMX header, parses the source sample rate, checks
sample
length, and keeps that rate with the sample.

The Freedoom fixture demonstrated why this mattered. Its sound effects use
multiple source rates rather than a single universal rate.

The guest mixer rescales playback steps deterministically using integer
arithmetic.

### Music is also guest-owned

The host music decoder API is gone.

The guest now handles:

- classic MUS;
- MIDI type 0;
- MIDI type 1;
- running status;
- tempo changes;
- SysEx skipping;
- program changes;
- volume, pan, expression, and sustain;
- pitch bend;
- sequencing and voice synthesis.

All 41 MIDI tracks in the Freedoom fixture pass the guest parser and synthesis
startup harness, including files with up to 19 tracks.

The final host boundary receives stereo signed 16-bit PCM at 44.1 kHz.

### Audio pumping no longer assumes high frame rate

The mixer can fill multiple available host blocks in one presentation iteration.

That prevents an expensive frame from starving audio merely because presentation
cadence temporarily falls below the PCM block cadence.

This fix came directly from the `READ THIS!` disaster.

## WADs, Assets, and Packaging

### The base game is detected from content

IWAD mode is no longer selected by trusting a commercial filename.

The guest inspects WAD contents:

- `MAP01` identifies the commercial map namespace;
- `E4M1` identifies retail content;
- `E2M1` and `E3M1` identify registered-style episode content;
- `E1M1` identifies shareware-style episode content.

Map availability is also content-driven.

The episode menu enables entries when the corresponding map actually exists.

The Freedoom fixture therefore exposes all four populated episodes.

### Map naming and sky selection are centralized

Runtime helpers centralize `MAPnn` versus `ExMy` construction and verify map
existence before level setup.

Sky selection uses one content-aware policy rather than separate conflicting
assignments during new-game and level-load paths.

Historical commercial map ranges still choose their preferred skies, with
content-aware fallback when needed.

### One IWAD, many PWADs

The launcher configuration distinguishes:

- exactly one base `iwad`;
- an ordered list of zero or more `wads` overlays.

The old fixed `MAXWADFILES = 20` array is gone from the guest.

The WAD list now grows dynamically.

A stress execution successfully loaded 64 valid PWADs in one process, proving
that the old twenty-file ceiling is no longer the guest limit.

Later WADs retain normal DOOM lump-override semantics.

### Launcher path semantics are explicit

The temporary runner reads a small host-side `settings.json`.

The guest does **not** parse JSON.

The current shape is:

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

An empty `iwad` means the runner may use its packaged or autodetected base
resource.

Relative paths are resolved from the runner/settings directory, not from an
accidental process working directory.

Absolute native paths also work through the host file backend but are naturally
less portable.

Forward slashes are the recommended JSON spelling even on Windows.

`language` is a default, not a dictator. A language already persisted by the
guest config wins over the launcher default.

### The Freedoom IWAD can be packaged without a giant C array

A freestanding PE harness embeds the raw Freedoom WAD with assembler `.incbin`
into a read-only object section.

The generic file capability exposes those bytes under the same virtual pathname
that the guest would use for an ordinary file.

The executable boots from an otherwise empty working directory with:

- no external WAD;
- no `data` directory;
- no special Freedoom syscall;
- no giant `const unsigned char wad[]` compiled through the C frontend.

Commercial/user-owned IWADs remain external inputs and are not redistributed.

## Savegames and Determinism

Savegames no longer dump native structures and pointers directly.

The guest uses an explicit portable `malbolge-v1` representation with fields
serialized intentionally.

Render-only interpolation history does not enter savegame state.

Gameplay remains integer/fixed-point and 35 Hz.

Visual wipe RNG remains separate from gameplay RNG.

The modernization tries very hard not to turn presentation improvements into
demo, collision, network, or gameplay changes by accident.

## Validation and Numbers

This section exists because "it feels cleaner" is not a benchmark.

### Historical starting point

The original quality scan reported:

- **144,468 unique source findings**;
- **201,966 raw gate reports**;
- **1 tooling/configuration finding**.

I am **not** calling that "144,468 independent bugs fixed".

That would be dishonest. Many reports were duplicates across gates, repeated
instances of the same diagnostic family, or consequences of one architectural
problem that disappeared together after a structural fix.

The useful comparison is the gate state before and after the modernization.

### Current compiler and analyzer state

The guest currently contains 65 C translation units.

The strict syntax matrix passes all six intended 64-bit target combinations:

- Linux x86-64: 65/65;
- Linux AArch64: 65/65;
- Windows x86-64: 65/65;
- Windows AArch64: 65/65;
- macOS x86-64: 65/65;
- macOS AArch64: 65/65.

That is **390/390 strict checks with zero diagnostics**.

The real quality validator also passes the 65 guest translation units with no
synthetic libc/string shim.

The occasional `clang-tidy` wrapper message saying a warning was suppressed by
check filters is tooling output, not a source finding in the corpus.

### Freestanding link boundary

The guest symbol audit is expected to leave only the explicit `DoomHost_*`
capability surface unresolved.

Hosted libc calls are not the escape hatch.

The current Win64 manual runner links with `/nodefaultlib` and imports only
system
facilities used by the host harness:

- `KERNEL32.dll`;
- `USER32.dll`;
- `GDI32.dll`;
- `WINMM.dll`.

No CRT is linked into the proof executable.

### Performance sanity checks

One early manual build was accidentally compiled at `-O0`.

This led to the extremely unfair conclusion that DOOM was running at roughly
40 FPS on hardware that had done absolutely nothing to deserve that accusation.

After rebuilding the guest with optimization and measuring **after** the
historical 35 Hz melt transition:

- 1280x600 Hor+ stable presentation measured roughly 535 FPS in the automated
  benchmark;
- classic 320x200 internal rendering measured roughly 1300 FPS;
- manual playtesting of the current 1280x600 build commonly shows more than
  600 FPS in the title bar.

The current renderer is software and presented through GDI. A discrete GPU is
mostly an innocent bystander in this specific test path.

## Field Notes: I Was Born in 2007 and Had Never Played DOOM

This section is intentionally less formal.

I am not quoting a hired playtester. I am quoting **myself**, the person
creating
this project, discovering thirty-year-old interaction conventions in real time.

This has already found enough real bugs that I am never removing this section.

### "WHY DO THE ARROW KEYS TURN THE CAMERA?!"

That was my first serious cultural disagreement with 1993.

Classic DOOM thought this was normal.

I did not.

Modern mode now makes Left and Right strafe and leaves turning to the mouse.

Suddenly the game felt like an actual game instead of a museum exhibit that had
obtained keyboard focus.

### "Why am I sliding on ice when I move the mouse?"

I genuinely thought movement or interpolation was wrong.

Nope.

Classic mouse Y moves the player forward and backward.

I had been steering with the mouse and moving with the arrows at the same time,
then blaming the engine for my own accidental input combination.

Modern mode ignores mouse Y for locomotion.

This was the moment the controls started feeling **beautiful** instead of merely
historically accurate.

### "The door is broken. Is this whole game just a corridor?"

I killed everything I could see and expected the door to open automatically.

It did not.

I assumed this was our bug.

Then I learned that Space means **Use**.

My immediate response was approximately:

> How the hell is Space Use? Space is jump.

DOOM does not have ordinary jumping.

I added `E` as a secondary Use binding.

The review score of DOOM improved immediately.

### "Wait. These are key CARDS? Then why are they called keys?!"

I spent an embarrassing amount of time searching for the blue key while
imagining a physical metal key.

Then the visual language finally clicked: they are access cards.

This led to a small linguistic crisis about whether English uses "key" for any
object or credential that unlocks something.

It does.

The game had not hidden a tiny brass key in a dark corner. I had simply brought
the wrong noun model to a science-fiction military base.

### "So the exit is already there? I do not complete the level first?"

Another modern-game assumption died here.

I expected "complete the level" to mean the game would unlock the exit after I
satisfied some global objective.

DOOM is much more physical than that. The exit is part of the map. You reach it,
operate it, and leave.

Suddenly several level-design decisions made much more sense.

### "NO WAY. I can shoot the monster above me without looking up?!"

The aiming finally clicked too.

DOOM has no normal vertical mouselook, and its hitscan/projectile targeting uses
classic vertical autoaim rules.

I had been trying to understand the game through a modern crosshair model that
simply was not there.

Once I realized that firing forward can still hit a target above or below the
camera, several moments that had felt like broken aiming became understandable.

I still reserve the right to be bad at DOOM.

### "Why do these enemies take so many shots?"

Part of this was the unfamiliar aiming model.

Part of it was also that I selected a very high difficulty on my first serious
playthrough because apparently self-preservation was not part of the validation
plan.

Entering a military base and immediately losing health while enemies appeared
behind me was therefore not strong evidence that the game was unfairly broken.

It was evidence that I had selected violence and received violence.

### "WHAT THE HELL, I THOUGHT DOORS DID NOT OPEN THEMSELVES"

After spending ages learning that doors do not magically open when every monster
dies, I was later surprised by map actions that did trigger movement and enemies
at exactly the moment I was not emotionally prepared for it.

The result was an actual jump scare from a game released long before I was born.

Good job, 1993.

### "I love the shotgun because it kills those bastards in one shot"

This is where the playtest stopped being purely forensic.

The shotgun is extremely persuasive game design.

Enemies that had annoyed me with weaker weapons suddenly became much more
satisfying to remove from existence.

I began to understand the game.

### "Those worm/tentacle things appear behind me with no sound!"

At this point I was no longer filing every unpleasant surprise as a bug.

Sometimes the level is simply trying to kill me.

This is progress.

### "Wait. The flickering light is intentional?"

I initially suspected a lighting regression because surfaces changed brightness
in a way that looked suspicious during modernization testing.

Then I learned that DOOM deliberately simulates flickering lights.

Not every weird polygon from 1993 is my fault.

This is an important sentence to remember while modernizing old software.

### "READ THIS!? Is the README literally inside the game?"

The name was incredible to me.

My next questions were immediately:

> There is no language option?

and:

> Why does Graphic Detail say High if I cannot lower it?

Those turned into real modernization work:

- runtime language selection now exists;
- the dead Graphic Detail option is gone;
- the help page no longer renders an invisible 3D world behind itself;
- the audio queue no longer depends on absurdly high presentation cadence.

This is a good example of why a first-time user can find problems that
experienced
players mentally edit out before noticing them.

### The Windows beep became an entirely optional music-theory side quest

I knew from the beginning that the sound came from Windows. There was never a
serious theory that DOOM had secretly acquired a system-notification instrument.

The actual reason I chased the notes was much less defensible: I thought that if
I could identify the interval, I might be able to search for the Windows sound
by its pitches. This investigation was therefore not necessary for debugging at
all. I did it because I wanted to.

I heard the sound once. About forty seconds later I reproduced the contour with
my voice into a vocal pitch detector. My voice is fairly low, so I sang it in a
more comfortable register and got an approximation around:

> F2 - G2 - C-sharp3

I already suspected the real notification lived several octaves higher. Roughly
thirty minutes later I opened a piano app on my phone. The interval involving
the C-sharp felt wrong on the keyboard, and that is what pushed me toward the
better reconstruction:

> F4 - G4 - C5

I later found the matching Windows 11 sound under the name **Windows
Background**. That confirmed the F4 - G4 - C5 contour I had settled on with the
piano.

The temporary confusion afterward came from comparing a different Windows
notification sound with a different contour, not from the original Background
transcription being wrong.

So the chronology was:

1. immediately recognize the sound as Windows;
2. decide, for no debugging reason, to identify its notes;
3. wait roughly forty seconds;
4. sing it into a vocal pitch detector in a comfortable lower octave;
5. get approximately F2 - G2 - C-sharp3 from memory;
6. open a phone piano roughly thirty minutes later;
7. notice that the C-sharp interval feels wrong;
8. settle on F4 - G4 - C5;
9. find the Windows Background sound and confirm the contour;
10. accidentally compare another Windows sound and briefly create a second
    mystery;
11. remember that none of this was required to fix DOOM.

No perfect pitch was claimed at any point.

Software engineering occasionally becomes comparative musicology entirely by
choice.

### "I opened another episode and the game crashed"

This was the moment the comedy paid rent.

That report found the real E2M1 zero-distance renderer crash described at the
top
of this file.

There was no historical-control explanation and no skill-issue explanation.

It was simply a bug.

This is why I keep playing the thing instead of trusting only static gates.

### The important ending: I actually like DOOM now

My first impressions included:

- the controls feel ancient;
- the player slides like ice;
- the door is broken;
- the aiming is weird;
- enemies do not die;
- `READ THIS!` broke realtime playback;
- why is there no language selector;
- why can I not lower Graphic Detail;
- why does Windows keep playing a chord at me;
- I do not understand what this game wants from me.

After fixing the actual regressions and learning the historical rules, the
verdict
changed.

The controls now feel good.

The shotgun is excellent.

The monsters are rude in increasingly entertaining ways.

The maps are beginning to make sense.

The autoaim is still hilarious to someone raised on free mouselook.

And, against my initial expectations:

> **I like the game. It is fun.**

That may be the most important end-to-end validation result in this entire file.

## What I Am Deliberately Not Doing

I am not using this benchmark as an excuse to rewrite every design decision in
DOOM.

I am preserving gameplay semantics where practical, especially deterministic
simulation, fixed-point behavior, demos, networking assumptions, and map logic.

Modern presentation and input conveniences are allowed where they can be kept
outside those semantics.

I am also not adding a giant dependency merely because a normal source port
would
use one.

Reference projects such as Chocolate Doom, Wine, Proton, SDL, and platform SDKs
are useful to understand behavior and architecture. The guest modernization is
kept clean-room; those repositories are not code donor bins.

## Reproducibility Notes

Useful reproducible support lives under `algorithms/doom/quality/.temp`.

Examples include:

- machine-language catalog generation;
- runtime-language table generation;
- WAD-backed language glyph/layout validation;
- six-target strict syntax checks;
- freestanding renderer and audio harnesses;
- embedded-WAD packaging tests;
- temporary native playability runners.

The repository-local Python under `.dependencies/python` is preferred for these
scripts so the experiments do not silently depend on whichever Python happens to
be installed globally.

Commit history is not acceptance evidence by itself. Quality remains open until
the generated source-bound transformation reproduces and validates the manual
oracle from admitted source.
