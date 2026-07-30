# CUDA exact accelerator adapter

This directory owns the optional NVIDIA CUDA implementation behind the shared
accelerator contract. It is not a semantic dependency of the compiler, verifier,
or VM.

The active slices evaluate exact classic `rotate`/`crazy` batches, compact
one-step classic transitions, and complete resident bounded runs with integer-only
CUDA kernels. The resident kernel is geometry-bound: classic uses 10 trits and
59,049 words, while `malbolge-2026.2` uses 14 trits and 4,782,969 words. One GPU
thread owns one independent complete memory image and performs its whole step
budget without round-tripping guest state through the host between steps. A narrow
standard-library `ctypes` runtime binds only the reviewed NVRTC and CUDA Driver API
calls needed by the adapter. Normative Rust execution remains the differential
correctness oracle.

Hardware-neutral `evidence-bound-ticket-route-admission-v1` now gives ticket
grouping an explicit evidence gate. It validates exact backend, device, and
workload identity plus exact output, lower candidate median, and a strict
paired-win majority; malformed or duplicate route records fail closed. Plans
preserve input order, minimize chunk count, then measured median cost, and
prefer synchronous ties. The retained
`rtx4060-full-domain-crazy-ticket-admission-2026-07-29-v1` profile binds the RTX
4060 `sm_89` capability and full-domain CRAZY workload to source commit
`431f542ab6321eeb12b7bcb9195318f25cf376a5`. It admits synchronous groups 2/4/8
and rejects streamed routes 1/2/4/8; a ten-ticket queue therefore selects groups
2+8 at a 7.3271 ms estimated median. The opt-in executor validates the packed
workload SHA-256, reverse-waits each group, restores input order, and closes
every ticket. Eleven tests cover fallback, positive/negative evidence,
duplicate/malformed records, exact profile matching, and two live CUDA routes.
This is not driver/toolchain, cross-device, or other-workload evidence, and it
does not change the global synchronous default.

The repository pins CUDA 13.3 Update 1 for Windows x86-64 through
`toolchain.json`. Binary redistributables live under ignored
`.dependencies/cuda/13.3.1/`, and every downloaded archive is checked against
the recorded NVIDIA SHA-256. The active adapter requires no third-party Python
packages beyond the repository's pinned Python runtime.

This is not yet a cross-platform runtime. `runtime.py` currently uses
`ctypes.WinDLL`, `nvcuda.dll`, a versioned NVRTC `.dll`, and a literal 13.3.1
repository path. The pending [CUDA Linux runtime and hermetic toolchain
contract](../../docs/technical/integrations/accelerators/cuda-linux-runtime-and-toolchain.md)
requires `ctypes.CDLL` plus reviewed `.so` identities on Linux and moves CUDA
release/path selection into per-platform manifests. The project initializer
reports a non-Windows CUDA manifest mismatch as unsupported rather than claiming
fallback support.

Development evidence on an NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB) runs
NVRTC-generated PTX through the Driver API and matches the CPU reference for
boundary-heavy plus deterministic `rotate`/`crazy` batches. Rust integration also
sends fourteen compact transition fixtures through an external CUDA worker and
requires exact equality with normative `Machine::step_traced()` across all seven
instructions, no-op, EOF, non-graphical termination, rejected jump atomicity,
pointer wrap, data/encryption aliasing, and already-terminated state. A second
Rust integration sends nine complete classic resident states through a binary
worker and compares all 59,049 memory words plus registers, I/O, termination,
step counts, and atomic rejection. A scalable integration separately supplies
canonical geometry from Rust `current_profile()` and compares eight complete
`malbolge-2026.2` outcomes across all 4,782,969 final memory words, including real
I/O, EOF, non-graphical termination, rejected jump atomicity, maximum-pointer
wrap, bounded budget exhaustion, live checkpoint resumption, and
already-terminated execution. This is correctness evidence, not a
speedup claim.

The classic resident path now measures free/total device memory with
`cuMemGetInfo_v2` and SM/thread capacity with `cuDeviceGetAttribute`, then applies
the hardware-neutral resource planner before allocation. There is no fixed
RTX-specific batch ceiling. Classic launches also split before their 32-bit memory-index product can
overflow. Very large VRAM therefore expands total capacity without requiring one
unsafe monolithic launch. Scalable profile execution uses the same live resource
planner and compact contiguous 32-bit host memory representation. Rust product
batch ports now route both classic and current-profile requests through the real
CUDA workers while retaining safe-Rust fallback. The original current-profile
RTX 4060 baseline remains under
`benchmarks/accelerator/evidence/2026-07-27-current-profile-throughput-rtx4060/`.
Post-optimization evidence under
`benchmarks/accelerator/evidence/2026-07-27-current-profile-resident-session-rtx4060/`
uses device-to-device replication for shared initial memory: complete-snapshot
batch 32 reaches about 51.67 VMs/s, about 1.289x the retained baseline, and
median upload time falls about 6.93x. Persistent profile sessions separately
reach about 2.00 million 64-step VM segments/s at batch 128 when setup, compact
observation, and snapshots are outside the timed `advance()` region. Validated
`ProfileMemoryImage` inputs now reuse their geometry/domain proof across calls;
retained complete-snapshot batch 32 reaches about 93.68 VMs/s and median
validation/planning is about 0.23 ms. Complete-snapshot materialization,
asynchronous transfer/stream tuning, broader hardware evidence, and CUDA
superoptimization remain open.

Direct current-profile snapshot evidence is retained under
`benchmarks/accelerator/evidence/2026-07-27-current-profile-direct-snapshot-rtx4060/`.
The adapter downloads complete memory directly into each final `array('I')`;
batch 32 reaches about 93.68 VMs/s and batch 1 about 60.43 VMs/s on the
retained RTX 4060 workload. This removes redundant packed host staging/copying;
it does not remove the requested full-state transfer.

