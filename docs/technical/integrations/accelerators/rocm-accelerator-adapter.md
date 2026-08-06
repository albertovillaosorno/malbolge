# ROCm accelerator adapter reservation

## Status

Reserved; not implemented and not part of the supported release matrix.

## Purpose

Preserve a hardware-neutral adapter slot for a possible future ROCm/HIP backend
without making AMD packages, drivers, hardware, or benchmarks a dependency of
the compiler or its completion gate.

## Current behavior

No ROCm implementation exists. Adapter selection must report a stable
unavailable/not-implemented result. Shared code and public bootstrap do not
install or import ROCm packages.

## Invariants

- CPU/reference execution remains sufficient for correctness.
- CUDA and ROCm types do not leak into the hardware-neutral port.
- ROCm absence changes no semantic or verifier decision.
- No support claim exists without exact supported GPU, OS, runtime, package,
  differential-test, and live-device evidence.

## Future implementation boundary

Implementation is intentionally deferred until supported AMD hardware and a
maintainer are available. That work must be proposed as a new reviewed TODO;
this reservation alone never authorizes a support or performance claim.

## References

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`
- `docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md`
- `docs/technical/adr/verification-trust-boundary.md`
