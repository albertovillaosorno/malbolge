# Linux CUDA runtime port design

## Status

Approved for autonomous implementation by the repository owner on 2026-08-17.

## Goal

Make the existing exact CUDA adapter usable on Linux x86-64 without weakening
Windows behavior, CPU fallback, deterministic verifier authority, or exact CUDA
package identity. The immediate target host is Fedora x86-64 with an NVIDIA RTX
4060 and an installed NVIDIA driver, while the repository remains responsible
for the CUDA toolkit/NVRTC bytes it uses.

## Priority and dependency boundary

`cuda-linux-runtime-and-hermetic-toolchain` becomes the active P0 lane-4 task.
It depends on the completed Linux development-host bootstrap and documentation
readiness gate. It no longer waits for completion of the broader
`cuda-exact-vm-adapter` research/product TODO: the existing adapter already
provides the implementation surface being ported, and Linux enablement must not
require every later CUDA optimization or benchmark experiment to finish first.

The existing CUDA exact-VM task remains P2 and continues to own broader GPU
semantics, scaling, and performance work. This P0 owns only the platform/runtime
and repository-local toolchain boundary required to execute that existing work
on Linux.

## Architecture

The generic CUDA runtime consumes one validated platform-toolchain selection.
That selection owns:

- normalized platform identity;
- toolkit root;
- Driver API library name and loader kind;
- NVRTC library path/name;
- exact CUDA release and component versions;
- exact package archive path, byte size, and SHA-256 identity.

Windows keeps `ctypes.WinDLL`, `nvcuda.dll`, and the reviewed Windows NVRTC DLL.
Linux uses `ctypes.CDLL`, `libcuda.so.1`, and the manifest-selected NVRTC shared
object inside the repository-local CUDA toolkit. Generic execution code does not
contain platform suffix branches or a literal CUDA 13.3.1 toolkit path.

## Manifest and provisioning

The tracked CUDA manifest becomes platform-indexed rather than describing only
Windows. Both Windows x86-64 and Linux x86-64 retain exact CUDA 13.3.1 component
identity. Linux packages are taken only from NVIDIA's official CUDA redistributable
manifest and are verified by size and SHA-256 before extraction.

Bootstrap remains fail-closed and repository-local. It may provision exact
tracked CUDA redistributables when explicitly requested, but it must not use an
ambient `/usr/local/cuda`, unversioned `latest`, or arbitrary system NVRTC as a
substitute for the pinned toolkit. The installed NVIDIA driver is a host runtime
capability and is not copied into `.dependencies`.

## Runtime data flow

1. Normalize the host platform.
2. Load and validate the tracked CUDA manifest.
3. Select the exact platform entry.
4. Resolve the repository-local toolkit and NVRTC library.
5. Load the NVIDIA Driver API through the platform loader contract.
6. Load NVRTC through the same selected contract.
7. Bind the existing Driver API/NVRTC symbol surface.
8. Measure runtime/toolchain identity.
9. Expose the existing CUDA adapter only after every required step succeeds.
10. Preserve CPU execution and verifier-owned acceptance when any CUDA step is
    unavailable.

## Failure behavior

Unsupported platform, absent driver, absent pinned toolkit, missing NVRTC,
manifest mismatch, archive/hash mismatch, loader failure, version mismatch, or
cleanup failure remains an explicit accelerator-unavailable condition. No
failure may silently select a different CUDA installation. CUDA unavailability
changes performance/capability only; it never changes guest semantics or final
verification authority.

## Windows compatibility

Windows-specific loader behavior remains covered by deterministic tests. Shared
platform abstractions must make Windows behavior explicit rather than replacing
it with POSIX assumptions. Existing retained Windows evidence remains historical
benchmark/support evidence and is not rewritten as Linux evidence.

## Testing strategy

The implementation proceeds in small commits with tests first where practical:

1. planning/P0 dependency regression;
2. typed platform CUDA manifest parsing/selection;
3. deterministic Windows and Linux loader-name/loader-kind tests;
4. repository-local Linux NVRTC provisioning and bootstrap readiness tests;
5. missing driver/library/platform mismatch and CPU fallback regressions;
6. live Linux runtime identity on the current RTX 4060 host;
7. exact CPU/CUDA primitive differential evidence on Linux;
8. broader existing CUDA tests where hardware and disk budget permit;
9. exhaustive Jig validation on committed HEAD.

Support claims require a live Linux device run. Performance claims require
separate retained benchmark evidence and are outside the minimum P0 completion
unless needed to prove a regression did not invalidate existing behavior.

## Disk discipline

Reuse `.dependencies/cuda/13.3.1` and repository caches. Download only the
minimal CUDA 13.3.1 redistributable components required by the existing NVRTC
runtime, verify them before extraction, and avoid duplicating archives after a
verified toolkit is materialized. Check disk space before any operation expected
to exceed 1 GiB.
