# Linux development host bootstrap

## Status

Completed P0 host-bootstrap work. CUDA runtime packaging and a fully hermetic
Linux linker/sysroot remain separate P2 work.

## Purpose

Make repository governance and validation usable on Linux development hosts
without replacing Windows behavior or treating ambient `PATH` as tool
authority.

## Scope

This contract covers checkout bootstrap for Python validation launchers, Git,
Rust stable/nightly validation toolchains, Cargo home, and the Linux host-linker
adapter used by Rust. CUDA runtime loading, CUDA package acquisition, LLVM, and
fully hermetic Linux linker/sysroot packaging remain outside this P0 slice.

## Current Behavior

Bootstrap consumes the repository's pinned Python, Rust, Git, and Jig version
authorities plus already-installed host Rustup, Git, and linker observations.
The checkout initializer reads tracked CUDA index/platform JSON, Rust toolchain
TOML, and Git version TOML through bounded one-MiB regular-file snapshots.
Existing symlink, junction, FIFO, directory, and parent-path redirects fail
closed rather than silently falling back to legacy manifest selection or
blocking on a pipe. An actually missing CUDA index still selects the legacy
direct manifest; a missing direct manifest retains its `missing` readiness
state. Opened file identity and timestamps are checked before/after each read,
and invalid UTF-8, oversized input, or changed inodes produce typed bootstrap
errors before any tool import is attempted. If wrapping an opened bootstrap
authority descriptor as a stream fails, bootstrap closes the descriptor and
reports a typed initialization error preserving the host failure as its cause.
The pinned `uv-toolchain.json`
uses the same one-MiB physical regular-file admission and stable descriptor
checks before its URL, version, artifact, and digest fields are interpreted.
Failed uv manifest stream wrapping closes its owned descriptor and surfaces
a typed bootstrap error with the original host failure as its cause.
Pinned uv executable provisioning rejects symlinked, junction, non-directory,
and multiply linked executable paths before executing an already-installed
binary or creating new files. New uv payloads use an exclusively created
`uv.tmp` descriptor with no-follow admission, exact write count, and descriptor-
bound executable permissions. The original stage inode, single-link count, and
byte size must still match before atomic publication; cleanup unlinks only the
owned stage. An existing staging path is not truncated, and an executable that
appears during provisioning is not overwritten. These checks do not make
arbitrary concurrent ancestor directory swaps atomic.
Python keeps native platform launchers and publishes neutral Jig aliases below
`.dependencies`. On POSIX, BasedPyright and pytest aliases answer only the exact
singleton `--version` probe from the same pinned `expected_tools` authority that
bootstrap verifies, then delegate every other argument vector to the provisioned
native launcher.

The pytest delegation also binds `PYTHONPYCACHEPREFIX` below `.cache`. Ruff
remains a byte-identical alias, and Windows retains native binary aliases for
all three tools. Alias publication now admits only physical tool sources and
neutral targets with no linked parent/leaf, checks source regular-file metadata
and a 256-MiB copy limit, and verifies that copied native bytes came from one
stable descriptor snapshot. A failed source-descriptor stream wrapper
closes that owned descriptor and reports a typed bootstrap error retaining
the original host cause instead of leaking a handle or raw host exception. Existing alias destinations are replaced
through private temporary files rather than followed or truncated; preflight rejects
redirected targets before publishing any of the three aliases. Private Jig tool
alias publication also binds the exact native `mkstemp` receipt to its requested
alias directory and the open descriptor's regular-file inode before any write,
replacement, or cleanup. A single-link inode is required so hardlinked stages
cannot modify foreign files by writing through a shared inode. A forged foreign
pathname is rejected without unlinking or replacing that foreign file; the
owned descriptor is closed on rejection. A failed temporary-output stream
wrapper likewise closes its descriptor, retains the original host error as the
cause of a typed bootstrap failure, and preserves any previously committed
alias or launcher. Before replacement, stage identity, regular-file type,
exclusive link count and exact byte size are rechecked against the admitted
original descriptor. Cleanup unlinks only the original owned inode, leaving
foreign symlink or hardlink replacements untouched on rejection.
Native Windows
CMD and POSIX Python/pytest launcher scripts use the same physical preflight
and private atomic replacement, checking both launcher destinations before
writing either script and preserving platform-specific newlines/modes. Preflight
alone does not guarantee atomicity against arbitrary concurrent ancestor swaps.

Matching Git and already-installed Rustup channels are imported below
repository-local versioned roots. Missing Rustup channels are observations only;
bootstrap does not download them. Optional host Git version/helper-path queries
and Rustup list/which queries each have a 15-second bound. Only an exact native
process result with the original executable/argument list, integer successful
exit and native captured text is accepted. The command passed to the launcher
is an independent copy, so a mutating wrapper cannot forge matching evidence.
Nonzero, forged, malformed, unavailable and timed-out host observations remain
missing rather than authorizing an import or crashing bootstrap. Git helper
folders and Rustup Cargo executable paths must also report exact native boolean
file/directory status; malformed statuses and host filesystem query failures
remain missing instead of authorizing a native tool import.

Jig `doctor` checks the configured repository-local ChkTeX launcher, but
Jig `check` independently attests the first eligible **external** `chktex`
on `PATH`: it excludes executables inside the repository before selecting
an external candidate and regenerates `.dependencies/bin/chktex` as an
attested launcher. The declared version is 1.7.10, so the system 1.7.9 at
`/usr/bin/chktex` does not satisfy the check even when the local launcher
reports 1.7.10. Replacing the generated repository launcher with a native
binary does not resolve the external-tool attestation.

For a host whose default system ChkTeX is older, install a verified, direct
executable ChkTeX 1.7.10 **outside the repository**, such as
`$HOME/.local/bin/chktex`, and confirm its `--version` output. Opt in to that
specific external directory when running validation, for example:

```sh
PYTHONPATH=src/automation/repository/composition \
MALBOLGE_JIG_EXTERNAL_TOOL_BIN="$HOME/.local/bin" \
python3.14 -B -m scripts.validate.jig_runner check
```

The runner admits only one absolute, nonredirected external directory with a
physical executable `chktex`; it rejects symlinks in either path, missing
executables, path-list injection and directories inside the repository.
An explicitly supplied opt-in must be an exact native string; missing values
use normal fallback, but explicit nulls, foreign string subclasses, and path-
like objects cannot silently select default tools or execute their own hooks.
Native filesystem evidence is required: redirect checks and directory and
executable-mode queries must yield exact booleans, and file status must be an
exact native `os.stat_result` with an unsigned 32-bit file-mode integer.
Foreign mode objects and negative or oversized mode values fail before
file-type checks.
A foreign resolved-path object cannot supply path authority.
The explicit directory sits after `.dependencies/bin` and before the system
default on the child `PATH`. If host filesystem status or path resolution
raises a type or runtime exception, pinned launchers are treated as unavailable
and external opt-in directories are rejected with a typed runner error; neither
failure allows a fallback to ambient binaries.

With no opt-in, the original pinned-and-system selection remains unchanged.
Jig still owns version/digest attestation, launcher regeneration, validation
policy and exact exit status; the runner does not bypass any tool proof. The
runner admits an exact native executable path from discovery and accepts only an
exact `CompletedProcess` with native integer return code, the invoked argument
list, and no captured output for this inherited-I/O launch. Expected command
arguments stay separate from the launched list, so a mutating process wrapper
cannot forge matching completion evidence. Forged process receipts or foreign
error formatting cannot falsely report a successful check.
Prefer a dedicated directory containing only the intended external tool if
additional user-local commands should not be visible to Jig.

Direct runner calls require one exact native command string (`check`,
`doctor`, or `validate`) before any equality comparison or tool discovery.
Foreign command objects cannot execute comparison or formatting hooks while
being rejected. The runner authenticates the complete native text write and
flush for CLI help, usage, and its own diagnostics; malformed delivery cannot
claim a successful help exit, and failed stderr delivery preserves nonzero
validation status.

The same entrypoint supports `doctor` and `validate` and fails if either pinned
ChkTeX or LaTeXmk launcher is missing. The runner preflights its configured
launchers as physical executable regular files with no symlink/junction in the
file or any ancestor directory. Redirected paths and nonregular nodes
(including FIFOs) fail before constructing the validation `PATH`.

Jig consumes only repository-local validation aliases. Linux Rust linking
receives a generated `cc` adapter that names the observed host linker explicitly
instead of restoring ambient `PATH` lookup. Jig-facing Cargo aliases replace a
validator-supplied target-linker environment value with that repository-local
adapter before entering native Cargo or Clippy. Linux Rust readiness additionally
requires exact adapter marker bytes and a physical, executable `bin/cc` with the
generated two-line direct-exec shell structure. Both files are admitted through
bounded, stable no-follow reads; stale or redirected markers, oversized data,
linked launcher ancestors, or nonexecutable scripts are not ready evidence.
Adapter publication also preflights the `cc`, marker, and generated neutral
alias destinations before writing, rejecting linked leaves or parent paths
rather than modifying unrelated files through filesystem redirects.
Windows keeps its native
executable layout behind the same neutral Jig-facing paths where applicable.

## Invariants

- Jig-facing Python, Git, and Rust executable authority resolves below
  `.dependencies`; POSIX Jig-driven pytest bytecode resolves below `.cache`.
- POSIX fast version output is admitted only for the exact singleton
  `--version` argument vector and comes from bootstrap's pinned expected-tool
  identity; all other BasedPyright and pytest arguments execute the provisioned
  native tool.
- Bootstrap never downloads a missing Rustup channel as a side effect of
  inspection.
- Linux host-linker observation is explicit and is not described as a hermetic
  linker/sysroot package.
- Windows native executable naming and bootstrap behavior remain supported and
  covered independently from Linux behavior.
- An incomplete repository-local import never becomes ready evidence.

## Failure Behavior

Version mismatch, incomplete prior imports, missing required files, invalid
helper directories, or absent supported host tools fail closed or remain
reported as missing. Bootstrap never silently substitutes a different Rustup
channel, invokes `rustup which` for an uninstalled channel, or promotes the
Linux host linker to hermetic package authority.

## Verification

Focused bootstrap tests cover platform IDs, Windows/POSIX Python launchers,
neutral validation aliases, exact fast-version output, non-version delegation,
Git distribution-version suffixes, Rustup no-download admission, stable/nightly
imports, explicit Linux linker adapters, and idempotent local-state creation.

Repository closure uses the repository-owned Jig runner for `validate` on
Linux. The `scalability.repository-graph` rule still reports `not-evaluated`
until Jig's graph schema and migration contract become authoritative. This
entrypoint does not conceal the gap or claim that the upstream rule passed.
Linux-only skips remain explicit rather than becoming acceptance evidence.

## References

- [Verification trust boundary](../adr/verification-trust-boundary.md)
<!-- jig-ignore-next-line: canonical documentation path is indivisible -->
- [Repository responsibility model](../architecture/repository-responsibility-model.md)
<!-- jig-ignore-next-line: canonical documentation path is indivisible -->
- [CUDA Linux runtime and toolchain](../integrations/accelerators/cuda-linux-runtime-and-toolchain.md)
