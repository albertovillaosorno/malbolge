# CUDA Linux runtime and hermetic toolchain

## Status

Completed

## Purpose

Port the existing exact CUDA adapter and repository-local development toolchains
to Linux without weakening hermetic version identity, CPU fallback, or verifier
authority.

## Scope

This contract governs:

- `accelerator/cuda/`
- `scripts/bootstrap/` and native validation/build orchestration
- `tooling/native-analysis/`, `compiler/c-frontend/`, and `tools/tidy/`
- `.jig/version/rust-toolchain.toml`
- `.jig/lang/python/pyrightconfig.json`
- CUDA and bootstrap tests under `tests/`

It does not change guest semantics, candidate acceptance, or the independent CPU
reference path.

## Current Behavior

The CUDA runtime now selects one exact tracked platform contract before native
loading. Windows x86-64 retains the existing byte-identical `toolchain.json`,
`ctypes.WinDLL`, `nvcuda.dll`, versioned NVRTC DLL, and DLL-directory lifetime.
Linux x86-64 selects a separate CUDA 13.3.1 manifest, `ctypes.CDLL`, the host
Driver API soname `libcuda.so.1`, and repository-local versioned NVRTC ELF
libraries. Linux preloads the manifest-declared
`libnvrtc-builtins.so.13.3` through `RTLD_GLOBAL` before NVRTC because the
published NVRTC ELF does not carry
an RPATH/RUNPATH for that required companion library.

The bootstrap has an explicit `--provision-cuda` operation. It downloads only
the package identities in the selected host manifest, validates tracked byte
size and SHA-256 before extraction, rejects archive traversal, stages inside the
repository, and atomically publishes a completion-marker-bound toolkit. Normal
bootstrap remains offline with respect to CUDA and reports a missing toolkit
instead of installing one implicitly. The current Linux package surface is the
NVIDIA CUDA 13.3.1 NVRTC 13.3.33 redistributable; the installed host driver is a
runtime capability and is not copied into `.dependencies`.

Live Fedora evidence at pre-documentation commit `bc2ebf7b` constructs the
exact adapter on an NVIDIA GeForce RTX 4060 (`sm_89`). The measured identity is
display driver `610.57.04`, Driver API `13030`, NVRTC `13.3`, CPython `3.14.6`,
and Linux toolchain-manifest SHA-256
`deaa908864ba3e3f85def6e983aa66d3d30892598423feddb9e9a006bd0491a7`.
The CUDA/runtime/bootstrap slice passes 185 tests with only five explicit
Windows-retained-evidence skips, while a representative exact CPU/CUDA
comparison set passes 113 tests. These are correctness/support observations;
there is no Linux performance claim and retained Windows ticket-admission timing
profiles remain Windows-specific.

The LLVM development-toolchain surface is now platform-neutral where shared
validation requires it. Linux admits exact Fedora 44 LLVM/Clang 22.1.8
development RPM bytes into
`.dependencies/llvm-dev/22.1.8`; the runtime remains
under `.dependencies/llvm/22.1.8`. CMake/Ninja builds the clang-tidy plugin as a
loadable ELF module and the normalized C frontend as a relocatable ELF whose
RUNPATH resolves the repository-local LLVM libraries. Windows retains its
reviewed MSVC/DIA registry-bridge branch.

The P0 is complete. Remaining Windows `.exe`/`.dll`, COFF, sanitizer, and
adapter paths are explicitly Windows-scoped evidence or implementation branches
rather
than shared Linux authority. No new Windows live-device result is claimed from
this Fedora session.

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
