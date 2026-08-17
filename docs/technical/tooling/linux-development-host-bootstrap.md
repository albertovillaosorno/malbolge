# Linux development host bootstrap

## Status

Active P0 host-bootstrap work. CUDA runtime packaging and a fully hermetic Linux
linker/sysroot remain separate P2 work.

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
Python keeps native platform launchers and publishes byte-identical neutral Jig
aliases below `.dependencies`. Matching Git and already-installed Rustup
channels are imported below repository-local versioned roots. Missing Rustup
channels are observations only; bootstrap does not download them.

Jig consumes only repository-local validation aliases. Linux Rust linking
receives a generated `cc` adapter that names the observed host linker explicitly
instead of restoring ambient `PATH` lookup. Jig-facing Cargo aliases replace a
validator-supplied target-linker environment value with that repository-local
adapter before entering native Cargo or Clippy. Windows keeps its native
executable layout behind the same neutral Jig-facing paths where applicable.

## Invariants

- Jig-facing Python, Git, and Rust executable authority resolves below
  `.dependencies`.
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
neutral validation aliases, Git distribution-version suffixes, Rustup
no-download admission, stable/nightly imports, explicit Linux linker adapters,
and idempotent local-state creation. Repository closure remains
`jig validate --root .`; Linux-only skips remain explicit rather than becoming
acceptance evidence.

## References

- [Verification trust boundary](../adr/verification-trust-boundary.md)
<!-- jig-ignore-next-line: canonical documentation path is indivisible -->
- [Repository responsibility model](../architecture/repository-responsibility-model.md)
<!-- jig-ignore-next-line: canonical documentation path is indivisible -->
- [CUDA Linux runtime and toolchain](../integrations/accelerators/cuda-linux-runtime-and-toolchain.md)
