# Replaceable accelerator boundary

## Status

Active

## Purpose

Define a hardware-neutral interface for candidate evaluation, batch VM
execution, search, and verification. Compiler and verifier code must not depend
directly on CUDA APIs.

## Scope

This document governs the following declared TODO scope:

- `accelerator/`
- `algorithms/`
- `optimizer/`
- `benchmarks/accelerator/`
- `tests/optimizer/`

## Current Behavior

### Active Model

The shared accelerator surface is capability-oriented and hardware-neutral.
`accelerator/exact_primitives.py` defines immutable request/result/capability
types plus the `ExactPrimitiveAdapter` protocol. The first admitted operation
family batches classic ten-trit `rotate` and `crazy`; malformed shape or word
domain is rejected before any backend executes.

### Implementation Status

The first replaceable slice is implemented. `accelerator/cpu/` supplies the
mandatory scalar reference and `accelerator/cuda/` supplies an optional NVIDIA
adapter behind the same request/result contract. CUDA APIs occur only inside the
CUDA adapter. Compiler, verifier, VM, and shared accelerator code remain
hardware-neutral.

Backend capability records expose stable backend ID plus device name/architecture
for evidence. Accelerator unavailability and execution failure have distinct
typed errors; neither changes candidate validity or CPU-reference semantics. Full
VM batching, candidate evaluation/search/verification ports, and ROCm remain
open.

## Invariants

- Compiler/verifier code depends on a hardware-neutral capability contract;
  CUDA/ROCm/CPU adapters can be substituted without changing compiler semantics
  or candidate validity rules.
- A CPU/reference path remains sufficient for correctness, and accelerator
  failure/unavailability changes performance rather than semantic acceptance.

## Failure Behavior

Missing hardware, resource exhaustion, or accelerator disagreement falls back or
fails explicitly without changing correctness rules.

## Verification

- Expected durable artifact surface: `accelerator/`, `algorithms/`,
  `optimizer/`, `benchmarks/accelerator/`, `tests/optimizer/`.
- `tests/optimizer/test_exact_accelerator_primitives.py` checks CPU known edges,
  malformed shared requests, CUDA lifecycle failure, and CPU/CUDA differential
  equality over boundary values plus deterministic 4,096-element corpora.
- Current development GPU evidence identifies an NVIDIA GeForce RTX 4060 as
  `sm_89`; no performance claim is made from this correctness slice.
- Remaining evidence includes full VM/candidate ports, unavailable-device
  orchestration at product call sites, ROCm substitution, resource metadata, and
  benchmark samples for any future speedup claim.
- Prerequisite completion evidence: `batch-vm-execution`,
  `compiler-algorithm-experimentation-platform`.
## References

### Host Architecture Baseline

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`

- [Replaceable Accelerator And Algorithm
  Ports](../../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md`
- `docs/technical/adr/verification-trust-boundary.md`
