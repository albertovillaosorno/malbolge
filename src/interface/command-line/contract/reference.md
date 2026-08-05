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
14-trit capsules emit `0x78`.

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

On Windows the repository development setup pins Zig 0.16.0 as the portable C
frontend/linker. Zig itself is development tooling; generated `.malbolge`
programs must not require it at execution time.

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
`vsync`, and `show_fps` from `settings.json`. Gameplay uses centered relative
mouse capture; pause, menus, automap, demos, and focus loss release the cursor.
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
