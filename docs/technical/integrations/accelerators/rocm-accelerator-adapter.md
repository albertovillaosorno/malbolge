# ROCm accelerator adapter reservation

## Status

Reserved; not implemented and not part of the supported release matrix.

## Purpose

Preserve a hardware-neutral adapter slot for a possible future ROCm/HIP backend
without making AMD packages, drivers, hardware, or benchmarks a dependency of
the compiler or its completion gate.

## Scope

- The hardware-neutral accelerator port and a reserved ROCm adapter identity.
- Stable unavailable/not-implemented selection behavior.
- No ROCm package installation, runtime loading, benchmark, or support claim.

## Current Behavior

### Proposed Model

No ROCm implementation exists. Adapter selection reports a stable unavailable or
not-implemented result. Shared code and public bootstrap do not install or
import
ROCm packages.

### Implementation Status

Intentionally deferred until supported AMD hardware and an explicit maintainer
are available.

## Invariants

- CPU/reference execution remains sufficient for correctness.
- CUDA and ROCm types do not leak into the hardware-neutral port.
- ROCm absence changes no semantic or verifier decision.
- ROCm is not a dependency of the turnkey C-to-Malbolge completion gate.
- No support claim exists without exact GPU, OS, runtime, package, differential
  test, and retained live-device evidence.

## Failure Behavior

Selecting ROCm reports an exact unavailable/not-implemented result. CPU fallback
occurs only when the caller explicitly permits accelerator fallback; no package
or driver is installed as a side effect.

## Verification

Required evidence is limited to the reviewed contract, stable unavailable
behavior, and proof that CPU and CUDA paths do not depend on ROCm packages. A
future implementation requires a new reviewed TODO and live-device evidence.

## References

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`
- `docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md`
- `docs/technical/adr/verification-trust-boundary.md`
- `docs/todo/open/accelerator/rocm-accelerator-adapter.mdc`
