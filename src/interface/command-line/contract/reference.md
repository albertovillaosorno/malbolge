# Malbolge CLI

`cli/` owns the top-level developer command:

```text
malbolge <path-to-program.c>
malbolge <path-to-program.malbolge>
```

The two extensions intentionally mean different things. `--help` and `-h` are
accepted only as standalone arguments; combining help with a path or another
argument fails closed instead of hiding malformed input. Invoking the command
without a source path also fails with a diagnostic on stderr and points to
`--help`; it does not print successful help text to stdout.

## `.malbolge`: canonical guest execution

`malbolge program.malbolge` executes the supplied Malbolge artifact in the
repository VM. Raw source uses classic interpreter-authority semantics. A
versioned capsule selects the profile carried by that capsule before classic
fallback is considered. The CLI does not compile the Malbolge program into a
persistent native executable. Empty input therefore exposes the selected word
width: classic raw source emits EOF low byte `0xA8`, while the annual and 2026.3

14-trit capsules emit `0x78`. A malformed modern frame fails capsule parsing
before the historical fallback bytes can execute.

The current VM input model is pre-buffered rather than interactive. The CLI does
not fake real-time input by reading the terminal to EOF before startup.
Interactive DOOM input belongs to the versioned host-capability runner work.

## `.c`: fast native debugging only

`malbolge program.c` compiles the C file directly for the current host, runs the
temporary executable with inherited stdin/stdout/stderr, and removes the native
artifact after the process exits. This path deliberately does **not** translate
C to Malbolge. It is for fast behavioral debugging of the future single-TU
`doom.c`, not Malbolge performance or conformance evidence.

The C driver is selected in this order:

1. `MALBOLGE_CC` when explicitly set.
2. Repository-local Zig 0.16.0 under `.dependencies/zig/0.16.0/`.
3. `zig` on `PATH`.
4. `clang`, `cc`, or `gcc` on `PATH`.
5. Repository-local Clang 22.1.8 under `.dependencies/llvm/22.1.8/bin/`.

On Windows the repository development setup prefers Zig 0.16.0 as the portable
C frontend/linker and retains pinned Clang 22.1.8 as a final repository-local
debug fallback when neither Zig nor a host compiler is available. Both are
development tooling; generated
`.malbolge` programs must not require either compiler at execution time.

When a C file declares the version-one `DoomHost_*` ABI, the Windows CLI links
`src/interface/command-line/adapter-outbound/adapters/doom/windows.c` as a
separate host-only translation unit. The adapter supplies the debug window,
keyboard/mouse input, audio, files, and clock. It does not embed an IWAD and is
never part of `doom.c` or `doom.malbolge`.

When executable C tokens reference the function-like identifier
`__malbolge_output_byte`, the CLI links
`src/interface/command-line/adapter-outbound/adapters/guest/output.c` as a
separate host-only debug translation unit. Lexical discovery applies C line
splicing and ignores comments, string literals, character literals, identifier
prefixes, and non-function-like uses. The guest source still includes no hosted
headers and calls no host libc routine. The adapter maps the byte-output
boundary to native stdout only for `.c` debug execution. It is not linked into
generated `.malbolge` artifacts and is not evidence that C-to-Malbolge lowering,

the guest runtime, libc, or `libm` is implemented.

DOOM debug execution uses the directory containing `doom.c` as its working
directory. Put `settings.json`, local WADs, `default.cfg`, and saves beside that
file; the amalgamation input directory is ignored. Explicit command-line options
win over `settings.json`. Settings win over the CLI's external IWAD fallback.
Without either, the CLI checks `MALBOLGE_DOOM_IWAD`, compatible filenames beside
`doom.c`, `doom/data/wad/`, and the accepted quality output's passthrough data

directory. WAD files remain external user-provided assets.

The Windows adapter reads `iwad`, `wads`, `language`, `maximized`, `resolution`,
`vsync`, and `show_fps` from `settings.json`. The settings file must fit wholly
inside the fixed 65536-byte parser buffer; oversized files, short reads,
embedded NUL bytes, truncated top-level structure, malformed JSON values,
invalid escapes, and malformed requested values are ignored rather than parsed
from a prefix. Key
lookup inspects only top-level object members, skips syntactically valid
quoted/nested decoys, rejects malformed unknown members before a requested key,
and rejects duplicate instances of the requested key, including equivalent JSON
escape spellings, rather than selecting one implicitly. A missing, empty, or
oversized execution-source environment value clears the adapter's provenance
override rather than retaining stale process state. Rebuilt debug argument
vectors reserve and write the required null
sentinel after `argv[argc]`; malformed or over-capacity vectors fail before the

guest entry point is called. Gameplay uses centered relative mouse capture;
pause, menus, automap, demos, and focus loss release the cursor. Native
capture ownership is verified before the adapter hides/centers the cursor, and
a failed cursor warp does not leave a synthetic-centering event armed. A failed
capture release likewise keeps the adapter marked captured so a later update can
retry instead of diverging from Win32 state. Focus loss also emits releases for
tracked held keys and mouse buttons so an unfocused button-up

cannot leave guest input latched on the next activation. Losing relative mouse
capture independently releases any held mouse buttons for the same reason. If
the bounded input queue is full, pending key presses/releases and the latest
mouse-button state remain tracked and are retried during later polling instead
of being forgotten, including ordinary focused key/button transitions. A
physical key-up cancels an undelivered pending press, while a re-press waits
behind its older pending release so guest event order remains coherent.
Close/quit requests use the same fail-closed retry principle rather than
disappearing when

the ring is full. Polling and capture requests after video shutdown are inert,
so they cannot consume unrelated thread messages or leak capture intent into a
later video session.

Indexed presentation admits only the logical dimensions established at video
initialization. The retained 8-bit frame is allocated to that exact logical
geometry with checked stride/size arithmetic, so documented high-resolution
rasters such as 2304-by-1080 are not rejected by an obsolete fixed backing-store
ceiling. Each row is copied with DWORD-aligned DIB stride and zero padding before
GDI sees the frame. Uncompressed `BI_RGB` publishes `biSizeImage = 0`, as allowed
by GDI, rather than narrowing a host-size byte count to `DWORD`. DIB metadata
owns a real 256-entry palette object whose header/palette layout is asserted
compatible with the `BITMAPINFO` prefix passed to GDI, so

palette access does not depend on over-indexing a one-element C array. The
hand-declared Win32 structures are compile-time checked against the supported
64-bit ABI sizes, including the SDK-compatible packed 18-byte `WAVEFORMATEX`.
Native client/window rectangle spans are widened and validated before subtraction
so malformed host geometry cannot trigger signed overflow. The
video ABI's borderless request selects a popup window style. Negative minimum

presentation rates are rejected at admission. Optional launcher-side 60 Hz
pacing is disabled when the guest requires a higher minimum presentation rate,
so the launcher does not deliberately throttle below that request. Repeated
video or audio initialization is rejected while the matching host resource is
already live, so re-entry cannot overwrite an owned native handle. Video startup
also requires both the process module handle and system arrow cursor before
class/window creation. A pre-existing same-name window class is reused only when
its registered procedure and relevant class ownership fields match the adapter's

expected class, so an unrelated registration cannot silently capture messages.
Video and audio initialization publish newly acquired
native handles only after their open operations succeed. Video shutdown
invalidates the old frame, queued input, pacing counters, and the trace-title
refresh timer before a later video session can use them.
Guest trace text remains owned by the running guest across window re-init. A
failed native window destroy, retained-frame release, or audio close retains
the corresponding owned resource, disables further use as needed, and blocks

re-initialization until a later teardown succeeds. File-handle slots likewise
remain occupied when native close fails, preventing a still-live handle from
being silently recycled.
Failed file-open and currently unsupported network resolve/receive calls clear
their caller-visible handle/endpoint outputs rather than leaving stale tokens
behind.
Zero-length file reads/writes admit null data storage as no-op payloads; a
zero-length random read returns without changing the native file pointer.
`FileWriteAll` continues across positive partial native writes and rejects a

zero-progress success rather than reporting a truncated file as complete. If a
write-all handle cannot close, the adapter retains it and blocks later writes
until cleanup succeeds instead of losing ownership of a live native handle. The
debug clock publishes its frequency/origin only after both queries succeed and
rejects impossible or unrepresentable timing samples without publishing
regressive state. FPS window accounting saturates before signed or scaled
arithmetic can overflow even if a nonzero host clock stalls. Sleep requests
round up to milliseconds without unsigned overflow and split long finite waits

so the Win32 `INFINITE` sentinel is never introduced by conversion.

When `show_fps` is enabled, language-neutral execution telemetry drives titles
such as `FPS 232 - C doom.c:258 R_RenderPlayerView(...)` and, for the future
capability-linked artifact, `FPS 60 - MALBOLGE doom.malbolge@4782969 [j]`.

`src/interface/command-line/adapter-outbound/adapters/doom/abi.malbolge` and
`windows.malbolge` currently reserve the annotated module contracts with
intentionally empty canonical payloads. They are not executable adapters yet.
The open capability-runner TODO requires automatic loading only when a
`.malbolge` capsule explicitly declares `doom.host.v1`.

## Debug DOOM with Clang sanitizers

The Windows debugging launcher validates both `doom.c` and the host adapter with
standalone pinned Clang 22.1.8 using strict warnings and `-Werror`. It then uses
Zig's Clang frontend and Windows linker support to build one local executable
with AddressSanitizer, UndefinedBehaviorSanitizer, symbols, and frame pointers.
Debug executables and logs stay beside `doom.c` under the ignored `.debug/`
directory.

Validate and build without launching:

```powershell
.dependencies\python\3.14.6\Scripts\python.exe `
  scripts\debug\doom.py --build-only
```

Play normally while recording a sanitizer report:

```powershell
.dependencies\python\3.14.6\Scripts\python.exe scripts\debug\doom.py
```

Launch under LLDB and forward ordinary DOOM arguments after `--`:

```powershell
.dependencies\python\3.14.6\Scripts\python.exe `
  scripts\debug\doom.py --lldb -- -warp 1 1
```

If LLDB stops on a failure, use `bt all` to print every thread's stack. The IWAD
remains external and is discovered with the same local-data policy as the normal
CLI; use `--iwad <path>` to select one explicitly.

## Build the CLI

The Rust frontend is `src/interface/command-line/composition/main.rs` and the
Cargo binary name is `malbolge`. Generated host binaries stay local under
`cli/bin/`.

Windows:

```powershell
cli\build-windows.cmd
```

If `cargo.exe` is not on `PATH`, set `MALBOLGE_CARGO` to a Rust 1.97.1 Cargo
executable before running the build script.

Linux/macOS:

```bash
./src/interface/command-line/composition/scripts/build-unix.sh
```

## Install the `malbolge` command

### Windows

The installer deliberately does not edit the registry. It writes shims into a
directory that is **already** on `PATH`:

```powershell
powershell -ExecutionPolicy Bypass -File .\cli\install-windows.ps1
```

The installer prefers `%USERPROFILE%\bin` when it is already on `PATH`;
otherwise it uses `%LOCALAPPDATA%\Microsoft\WindowsApps` when available. A
different existing PATH entry can be selected with `-Destination`.

Two shims are installed: `malbolge.cmd` for PowerShell/cmd and an extensionless
`malbolge` launcher for Git Bash.

### Linux/macOS

```bash
./src/interface/command-line/composition/scripts/install-unix.sh
```

This installs a symlink in `~/.local/bin` by default. Pass another destination
as the first argument when desired.

## Examples

From the repository root after installation:

```bash
cd <repository-root>
malbolge examples/example.malbolge
malbolge algorithms/doom/amalgamate/in/doom.c
```

Arguments after a `.c` path are forwarded to the native debug program.
Additional arguments for `.malbolge` execution are intentionally rejected until
interactive runtime input/capability semantics are explicit.
