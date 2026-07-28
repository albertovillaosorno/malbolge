# Malbolge CLI

`cli/` owns the top-level developer command:

```text
malbolge <path-to-program.c>
malbolge <path-to-program.malbolge>
```

The two extensions intentionally mean different things.

## `.malbolge`: canonical guest execution

`malbolge program.malbolge` executes the supplied Malbolge artifact in the
repository VM. Raw source uses classic specification semantics. A versioned
capsule selects the profile carried by that capsule. The CLI does not compile the
Malbolge program into a persistent native executable.

The current VM input model is pre-buffered rather than interactive. The CLI does
not fake real-time input by reading the terminal to EOF before startup. Interactive
DOOM input belongs to the versioned host-capability runner work.

## `.c`: fast native debugging only

`malbolge program.c` compiles the C file directly for the current host, runs the
temporary executable with inherited stdin/stdout/stderr, and removes the native
artifact after the process exits. This path deliberately does **not** translate C
to Malbolge. It is for fast behavioral debugging of the future single-TU
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
`cli/adapters/doom/windows.c` as a separate host-only translation unit. The
adapter supplies the debug window, keyboard/mouse input, audio, files, and clock.
It does not embed an IWAD and is never part of `doom.c` or `doom.malbolge`.

DOOM debug state is written under ignored `cli/run/doom/`. Pass `-iwad <path>`
to select an asset explicitly. Without `-iwad`, the CLI checks
`MALBOLGE_DOOM_IWAD`, then compatible filenames under `doom/data/wad/`, then the
accepted quality output's passthrough data directory. The WAD remains an external
user-provided file.

## Build the CLI

The Rust frontend is `cli/main.rs` and the Cargo binary name is `malbolge`.
Generated host binaries stay local under `cli/bin/`.

Windows:

```powershell
cli\build-windows.cmd
```

If `cargo.exe` is not on `PATH`, set `MALBOLGE_CARGO` to a Rust 1.97.1 Cargo
executable before running the build script.

Linux/macOS:

```bash
./cli/build-unix.sh
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
./cli/install-unix.sh
```

This installs a symlink in `~/.local/bin` by default. Pass another destination as
the first argument when desired.

## Examples

From the repository root after installation:

```bash
cd <repository-root>
malbolge examples/example.malbolge
malbolge algorithms/doom/amalgamate/in/doom.c
```

Arguments after a `.c` path are forwarded to the native debug program. Additional
arguments for `.malbolge` execution are intentionally rejected until interactive
runtime input/capability semantics are explicit.
