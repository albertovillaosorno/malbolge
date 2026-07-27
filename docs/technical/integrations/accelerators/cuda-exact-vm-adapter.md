# CUDA exact VM adapter

## Status

Active

## Purpose

Implement the first GPU adapter with exact discrete Malbolge semantics and
massively parallel independent VM execution for candidate evaluation and test
batches.

## Scope

This document governs the following declared TODO scope:

- `accelerator/`
- `algorithms/`
- `optimizer/`
- `benchmarks/accelerator/`
- `tests/optimizer/`

## Current Behavior

### Active Model

CUDA is an optional implementation of hardware-neutral accelerator requests. It
never defines VM semantics or compiler/verifier acceptance. The CPU reference
remains available without GPU execution and supplies differential correctness
evidence.

### Implementation Status

The first exact CUDA slice is implemented for classic ten-trit `rotate` and
`crazy` batches. Integer-only kernels under `accelerator/cuda/` compile at runtime
with NVRTC for the selected device architecture and execute through the CUDA
Driver API. The adapter uses synchronous copies/launches deliberately in this
correctness-first slice; streams, overlap, and throughput tuning remain future
performance work.

Windows x86-64 development pins CUDA 13.3 Update 1 under ignored
`.dependencies/cuda/13.3.1/`. `accelerator/cuda/toolchain.json` records the exact
NVIDIA redistributable paths, component versions, archive sizes, and SHA-256
values. The active adapter binds the reviewed NVRTC/Driver subset directly with
standard-library `ctypes`; it has no additional Python package dependency. CUDA
handles and argument lifetimes stay encapsulated inside `accelerator/cuda/`, and
kernel-parameter owners remain alive through synchronized launch completion.

Development execution on an NVIDIA GeForce RTX 4060 reports `sm_89` and matches
the independent CPU scalar implementation for boundary-heavy and deterministic
4,096-element `rotate`/`crazy` batches.

A compact classic-step adapter is now active as the first VM-semantic CUDA slice.
`ClassicStepRequest` supplies registers, I/O counters, optional next input byte,
and at most four explicitly keyed memory cells. One CUDA thread evaluates one
specification-mode classic transition and returns status/termination/error,
fetched/decoded bytes, committed I/O, final registers/counters, and at most two
actual memory writes. Missing required cells fail as an invalid compact request;
there is no implicit read from undeclared guest memory.

`tests/vm/cuda_step.rs` does not trust a Python CPU clone. It runs the normative
safe-Rust `Machine::step_traced()` first, projects the resulting `StepTrace` to a
fixed-width versioned process protocol, invokes the CUDA worker externally, and
requires exact equality for fourteen fixtures spanning all seven instructions,
no-op, EOF, non-graphical termination, rejected jump atomicity, pointer wrap,
data/self-encryption aliasing, and already-terminated state.

Resident classic execution is now active through the hardware-neutral
`ClassicRunRequest`/`ClassicRunResult` contract. Each request contains the complete
59,049-word memory image, registers, deterministic input, prior output, termination
state, and an explicit bounded step budget. One CUDA thread owns one independent
memory image in device memory and loops over the complete semantic transition
function without host state transfers between steps. The kernel preserves atomic
rejection: a failing self-encryption step contributes no register, I/O, or memory
mutation, while earlier committed steps remain visible.

`tests/vm/cuda_run.rs` serializes complete states to a binary CUDA worker and
requires byte-exact agreement with normative Rust across nine fixtures, including
budget exhaustion, input/output/halt, EOF, non-graphical termination, resumed and
already-terminated execution, rejected jump atomicity, pointer wrap, and
data/encryption aliasing. Every one of the 59,049 memory words is compared. CUDA
unavailability keeps this optional path unavailable rather than changing VM
correctness.

Resident allocations are now budgeted from live driver evidence rather than a
fixed batch constant. `cuMemGetInfo_v2` supplies current free/total bytes and
`cuDeviceGetAttribute` supplies multiprocessor count and maximum threads per
block. The hardware-neutral planner reserves the larger of 8 MiB or 1/16 of total
memory, preserves request order across automatically split chunks, and rejects
any request that cannot fit alone before allocation. There is no configured VRAM
ceiling: backend-specific integer/addressing limits cause additional chunks rather
than rejection or truncation. Current-profile resident execution and performance
claims remain open.

## Invariants

- CUDA kernels implement exact discrete VM semantics for independent batches and
  are differentially checked against the CPU reference across randomized and
  boundary-heavy corpora.
- A CPU/reference path remains sufficient for correctness, and accelerator
  failure/unavailability changes performance rather than semantic acceptance.

## Failure Behavior

Missing hardware, resource exhaustion, or accelerator disagreement falls back or
fails explicitly without changing correctness rules.

## Verification

- Expected durable artifact surface: `accelerator/`, `algorithms/`,
  `optimizer/`, `benchmarks/accelerator/`, `tests/optimizer/`.
- `tests/optimizer/test_exact_accelerator_primitives.py` executes the reviewed
  CUDA kernels when a device is available and compares every result to the CPU
  adapter. Missing CUDA is reported as unavailable/skip; actual execution
  disagreement is a test failure.
- The current workstation evidence is RTX 4060 / `sm_89`; toolchain smoke also
  verifies NVRTC -> PTX -> Driver API execution with the pinned CUDA 13.3 Update
  1 redistributables.
- Compact classic-step differential evidence covers VM state/I/O/mutation trace
  projections and atomic rejection. Resident classic evidence additionally
  compares complete 59,049-word states after bounded multi-step execution against
  normative Rust. Adaptive resource limits, product-level batch routing, throughput
  benchmarks, and current-profile coverage remain required before this TODO can
  complete.
- Prerequisite completion evidence: `replaceable-accelerator-boundary`,
  `batch-vm-execution`.
## References

### Host Architecture Baseline

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`

- [Replaceable Accelerator And Algorithm
  Ports](../../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md`
- `docs/technical/adr/verification-trust-boundary.md`
