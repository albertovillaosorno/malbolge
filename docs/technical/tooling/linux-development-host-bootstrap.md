# Linux development host bootstrap

## Purpose

Make repository governance and validation usable on Linux development hosts
without replacing Windows behavior or treating ambient PATH as tool authority.

## Scope

This contract covers checkout bootstrap for Python validation launchers, Git,
Rust stable/nightly validation toolchains, Cargo home, and the Linux host-linker
adapter used by Rust. CUDA runtime loading, CUDA package acquisition, LLVM, and
fully hermetic Linux linker/sysroot packaging remain outside this P0 slice.

## Inputs

Bootstrap consumes the repository's pinned Python, Rust, Git, and Jig version
authorities plus already-installed host Rustup/Git/linker observations. Missing
Rustup channels are observations only; bootstrap does not download them.

## Contract

Python keeps native platform launchers and publishes byte-identical neutral Jig
aliases below `.dependencies`. Matching Git and already-installed Rustup
channels are imported below repository-local versioned roots. Jig consumes only
those repository-local aliases. Linux Rust linking receives a generated `cc`
adapter that names the observed host linker explicitly instead of restoring
ambient PATH lookup. Windows keeps its native executable layout behind the same
neutral Jig-facing paths where applicable.

## Failure Modes

Version mismatch, incomplete prior imports, missing required files, invalid
helper directories, or absent supported host tools fail closed or remain
reported as missing. Bootstrap never silently substitutes a different Rustup
channel, downloads one through `rustup which`, or promotes the Linux host linker
to hermetic package authority.

## Verification

Focused bootstrap tests cover platform IDs, Windows/POSIX Python launchers,
neutral validation aliases, Git distribution-version suffixes, Rustup
no-download admission, stable/nightly imports, explicit Linux linker adapters,
and idempotent local-state creation. Repository closure remains
`jig validate --root .`; Linux-only skips must remain explicit rather than being
converted into acceptance evidence.
