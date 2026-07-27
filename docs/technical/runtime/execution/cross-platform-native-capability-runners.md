# Cross-platform native capability runners

## Status

Proposed

## Purpose

Implement host-side versioned capability adapters for supported 64-bit Windows,
macOS, and Linux runners on x86-64 and AArch64 while preserving one portable
`.malbolge` artifact and one guest-visible capability contract.

## Scope

This document governs the following declared TODO scope:

- `execution/`
- `runtime/`
- `vm/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Proposed Model

Each supported host/architecture pair implements the same versioned capability
ABI behind a native runner adapter. Host APIs, libraries, event loops, file and
network primitives, audio/video devices, and monotonic clocks remain outside the
guest. The same validated guest request must have the same declared semantics on
every runner even when the adapter implementation differs substantially.

The normalized DOOM C corpus currently provides portability evidence at the
source/freestanding-compile boundary across the intended platform/architecture
matrix. That evidence does not yet prove runtime capability adapters or portable
execution of the final generated `.malbolge` payload.

### Implementation Status

Not implemented. No six-target native capability-runner matrix is claimed yet.

## Invariants

- Supported runners cover 64-bit Windows, macOS, and Linux on x86-64 and AArch64
  using the same versioned host-capability semantic contract.
- The same `.malbolge` payload and target-profile identity are accepted across
  supported runners; guest source does not select operating-system branches to
  compensate for adapter differences.
- Capability adapters remain host-side and never expose native pointers, host
  libc ABIs, platform handles, or multimedia-library contracts to guest code.
- An already generated program does not require LLVM/Clang or an externally
  installed multimedia development stack merely to execute.
- Native runner architecture differences cannot change guest memory, capability
  results, diagnostics, byte I/O, effect ordering, or declared failure behavior.
- Availability differences are explicit capability-discovery/failure results,
  never silent substitutions or platform-specific guest semantics.
- Files, network packets, input events, audio/video buffers, and monotonic time
  follow the versioned capability contract rather than undocumented host defaults.
- x86-64 and AArch64 implementations remain adapters behind shared runtime/native
  execution contracts; architecture-specific calling conventions are not VM
  semantics.

## Failure Behavior

An unsupported platform, unavailable required capability, malformed call frame,
or adapter/runtime failure is reported explicitly through the capability/runtime
contract. The runner may not require guest source patches, silently load a host
library with different semantics, or execute an invalid request to preserve
apparent compatibility.

## Verification

- Execute the same canonical capability-frame corpus on every supported
  OS/architecture pair and compare guest memory, results, diagnostics, and effect
  ordering.
- Run malformed-frame, invalid-range, unavailable-capability, startup, and
  shutdown fixtures on every runner.
- Prove generated-program startup/execution does not depend on LLVM/Clang or an
  externally installed multimedia development/runtime package beyond explicitly
  documented operating-system facilities.
- Retain architecture/platform identity and raw results for differential and
  performance evidence.
- Prerequisite completion evidence: `versioned-host-capability-call-abi` and
  `native-x86-64-and-aarch64-backends`.

## References

- [Host CPU And Accelerator Runtime
  Baseline](../../adr/host-cpu-and-accelerator-runtime-baseline.md)
- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)
