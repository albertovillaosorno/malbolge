# CUDA Linux runtime and hermetic toolchain

## Status

Active P0 implementation

## Purpose

Port the existing exact CUDA adapter and repository-local development toolchains
to Linux without weakening hermetic version identity, CPU fallback, or verifier
authority.

## Scope

This contract governs:

- `accelerator/cuda/`
- `scripts/bootstrap/`
- `.jig/version/rust-toolchain.toml`
- `.jig/lang/python/pyrightconfig.json`
- CUDA and bootstrap tests under `tests/`

It does not change guest semantics, candidate acceptance, or the independent CPU
reference path.

## Current Behavior

The active CUDA runtime is Windows x86-64 specific. It loads the Driver API with
`ctypes.WinDLL("nvcuda.dll")`, loads a versioned NVRTC `.dll`, and annotates the
binding surface with `ctypes.WinDLL`. The runtime also constructs the toolkit
root
from `.dependencies/cuda/13.3.1/toolkit` instead of resolving it from a selected
platform manifest.

`src/optimization/accelerator/adapter-outbound/accelerator/cuda/toolchain.json`
correctly pins CUDA 13.3 Update 1 package paths,
versions, sizes, and SHA-256 values, but its only platform is
`windows-x86_64`. The repository Rust channel, Jig launcher, and Pyright
platform
configuration also contain unconditional Windows identities.

`src/automation/repository/composition/scripts/bootstrap/project.py` is now a
platform-aware checkout entrypoint. It
creates ignored local state, provisions native Windows or POSIX Python
launchers,
and reports a mismatched CUDA or Rust manifest as unsupported. This diagnostic
behavior is not Linux CUDA runtime support.

The Linux port is an active lane-4 P0 blocker because accelerator-backed
compiler work on the current development host requires the existing CUDA
adapter to load there. Completion of the broader `cuda-exact-vm-adapter` TODO
is deliberately not a prerequisite: that TODO owns additional semantics,
scaling, and performance work, while this contract owns the platform/toolchain
boundary needed to run its existing implementation on Linux.

## Invariants

- Windows uses the reviewed `WinDLL` calling convention and Windows library
  names; Linux uses `ctypes.CDLL` with reviewed ELF sonames.
- Driver and NVRTC library names come from one typed platform selection, not
  from
  scattered suffix checks or silent search-path guessing.
- CUDA release, platform, package version, archive path, size, and SHA-256
  remain
  exact tracked identity. No unversioned "latest" download is allowed.
- The runtime resolves its toolkit root and NVRTC library from the selected
  manifest; it does not embed `13.3.1` or `.dll` in generic execution logic.
- Missing libraries, unsupported platforms, or manifest disagreement produce a
  typed unavailable result and preserve the mandatory CPU path.
- Linux enablement cannot change CUDA kernel integer semantics, result ordering,
  cleanup lifetime, trusted admission, or failure behavior.
- Windows evidence remains valid and must continue to pass after abstraction.

## Failure Behavior

An absent `libcuda.so.1`, incompatible NVIDIA driver, missing manifest, wrong
host
platform, unavailable versioned NVRTC `.so`, hash mismatch, or missing pinned
native toolchain fails explicitly. The initializer reports optional components
as
missing or unsupported unless `--require-cuda` promotes that condition to
failure.
It never falls back to an arbitrary system CUDA installation while hermetic CUDA
is requested.

## Verification

Completion requires all of the following:

- the tracked CUDA 13.3.1 manifest selects exact Windows x86-64 and Linux
  x86-64 package identities rather than accepting an ambient toolkit;
- Linux provisioning uses NVIDIA-published archive size and SHA-256 identity
  and retains only repository-local toolkit bytes needed by this runtime;
- deterministic loader tests for Windows `WinDLL` plus `nvcuda.dll`/NVRTC
  `.dll`;
- deterministic loader tests for Linux `CDLL` plus `libcuda.so.1` and a
  manifest-selected versioned NVRTC `.so`;
- tracked Windows and Linux CUDA manifests with exact package hashes and toolkit
  roots, selected by normalized host identity;
- no generic runtime literal for `13.3.1`, `nvcuda.dll`, or an NVRTC `.dll`;
- platform-native Rust, Jig, LLVM, Python, and validation paths without an
  unconditional Windows target in shared configuration;
- Linux x86-64 import, unavailable-device, cleanup, CPU-fallback, and exact
  CPU/CUDA differential tests;
- at least one retained Linux NVIDIA device run for every performance or support
  claim, with driver, toolkit, device, and commit identity;
- the existing Windows RTX 4060 suite and retained exactness gates still pass.

## References

### Governing decisions

- [Host CPU And Accelerator Runtime
  Baseline](../../adr/host-cpu-and-accelerator-runtime-baseline.md)
- [Replaceable Accelerator And Algorithm
  Ports](../../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Active implementation

- `src/optimization/accelerator/adapter-outbound/accelerator/cuda/runtime.py`
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
- `src/optimization/accelerator/adapter-outbound/accelerator/cuda/toolchain.json`
- `src/automation/repository/composition/scripts/bootstrap/project.py`
- `src/automation/repository/composition/scripts/bootstrap/python_validation.py`
