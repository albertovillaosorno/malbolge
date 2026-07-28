# AMD ROCm

## Status

Verified as of 2026-07-26.

## Subject

AMD ROCm, the open software stack for GPU-accelerated computing on supported AMD
GPU and accelerator hardware.

## Repository Use

ROCm is the software/runtime identity for the first AMD-family GPU adapter. The
adapter may provide batch VM execution, candidate evaluation, search, and
superoptimization capacity without becoming a semantic dependency.

## Provenance

AMD's current ROCm documentation describes ROCm as an open GPU-computing stack
containing runtimes, compilers, performance/system utilities, and optimized math
and compute libraries. The documentation also identifies HIP and other supported
programming interfaces.

## Identity And Version

- Authority: Advanced Micro Devices, Inc.
- Canonical product: ROCm.
- Current documentation observed: ROCm 7.14.0.
- Review date: 2026-07-26.

## License Or Terms

ROCm is an external software ecosystem with component-specific licenses. This
record does not collapse those licenses into the Malbolge MIT license; any
vendored component requires its own dependency/license review.

## Evidence

- ROCm is a concrete software/runtime stack rather than a generic vendor label.
- Its compilers, runtimes, libraries, and tooling make `rocm` the appropriate
  adapter identity for this repository.
- Backend availability and performance are hardware/runtime facts and cannot
  alter Malbolge semantic acceptance.

### Unresolved

Supported-device matrices, runtime availability, and performance vary by ROCm
release and hardware. Malbolge acceptance and throughput claims therefore still
require versioned local adapter evidence.

## Sources

- <https://rocm.docs.amd.com/>
- <https://rocm.docs.amd.com/en/latest/about/what-is-rocm.html>
- accessed 2026-07-26.
