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
4,096-element `rotate`/`crazy` batches. This does not yet implement complete VM
state execution or establish a performance advantage.

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
- Complete VM state/I/O/mutation traces, adaptive resource limits, throughput
  benchmarks, and independent-profile coverage remain required before this TODO
  can complete.
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
