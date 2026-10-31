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
errors before any tool import is attempted. The pinned `uv-toolchain.json`
uses the same one-MiB physical regular-file admission and stable descriptor
checks before its URL, version, artifact, and digest fields are interpreted.
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
stable descriptor snapshot. Existing alias destinations are replaced through
private temporary files rather than followed or truncated; preflight rejects
redirected targets before publishing any of the three aliases. Preflight alone
does not guarantee atomicity against arbitrary concurrent ancestor swaps.

Matching Git and already-installed Rustup channels are imported below
repository-local versioned roots. Missing Rustup channels are observations only;
bootstrap does not download them.

Jig `check` can resolve ChkTeX through ambient `PATH` even when `doctor`
correctly identifies the configured repository-local executable. A user-local
ChkTeX 1.7.10 may therefore shadow pinned 1.7.9 and abort the gate. Linux
validation now supports `python3.14 -B -m scripts.validate.jig_runner check`.
This entrypoint constrains tool lookup to `.dependencies/bin` and the system
default, without altering the installed Jig, its policies, or its exit status.

The same entrypoint supports `doctor` and `validate` and fails if either pinned
ChkTeX or LaTeXmk launcher is missing. Jig validates launcher admission as
physical executable regular files with no symlink/junction in the file or any
ancestor directory. Redirected paths and nonregular nodes (including FIFOs)
fail before the validation `PATH` is constructed; a linked alias cannot silently
substitute an ambient version for the repository-pinned launcher. Set
`PYTHONPATH=src/automation/repository/composition` before invoking it.

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
