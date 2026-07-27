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

The repository pins CUDA 13.3 Update 1 for Windows x86-64 through
`toolchain.json`. Binary redistributables live under ignored
`.dependencies/cuda/13.3.1/`, and every downloaded archive is checked against
the recorded NVIDIA SHA-256. The active adapter requires no third-party Python
packages beyond the repository's pinned Python runtime.

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
planner and compact contiguous 32-bit host memory representation. Product-level
batch routing, current-profile throughput evidence, asynchronous transfer/stream
tuning, broader hardware evidence, and CUDA superoptimization remain open.
