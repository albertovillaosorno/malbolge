# AMD ROCm

## Status

Verified as of 2026-07-26.

## Subject

AMD ROCm, the open software stack for GPU-accelerated computing on supported AMD
GPU and accelerator hardware.

## Repository Use

This is an external software-platform bibliography record, not an active
adapter reservation or a feature in the Malbolge roadmap. An earlier proposal
to reserve an AMD-family adapter was withdrawn from project scope in 2026.
No ROCm support, integration or future delivery is planned.

## Provenance

AMD's current ROCm documentation describes ROCm as an open GPU-computing stack
containing runtimes, compilers, performance/system utilities, and optimized math
and compute libraries. The documentation also identifies HIP and other supported
programming interfaces.

## Identity And Version

- Stable identifier: AMD ROCm documentation
- Authority: Advanced Micro Devices, Inc.
- Canonical product: ROCm.
- Current documentation observed: ROCm 7.14.0.
- Review date: 2026-07-26.

## License Or Terms

ROCm is an external software ecosystem with component-specific licenses. This
record does not collapse those licenses into the Malbolge MIT license; any
vendored component requires its own dependency/license review.

## Evidence

- ROCm is a concrete external software/runtime stack, not a generic vendor.
- The vendor documentation identifies its compilers, runtimes, libraries,
  and tooling; this does not commit Malbolge to an adapter implementation.
- Backend availability and performance are hardware/runtime facts, not part
  of Malbolge's semantic acceptance rules.

### Unresolved

Supported-device matrices, runtime availability, and performance vary by ROCm
release and hardware. This record makes no Malbolge compatibility, integration,
throughput or future-support claim.

## Sources

- <https://rocm.docs.amd.com/>
- <https://rocm.docs.amd.com/en/latest/about/what-is-rocm.html>
- accessed 2026-07-26.
