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
than rejection or truncation.

Scalable resident execution is active through `ProfileRunGeometry` and the
`ProfileRunRequest`/`ProfileRunResult` contract. Geometry is explicit and
fail-closed: memory size equals the ternary word modulus, EOF equals modulus minus
one, and the modulus must equal `3^word_trits`. Scalable memory is represented as
contiguous 32-bit words rather than boxed Python integers. The shared resident
kernel specializes crazy width, rotate high-trit weight, EOF, wrap modulus, and
memory geometry at NVRTC compile time while retaining the same instruction tables
and atomic transition rules.

`tests/vm/cuda_profile_run.rs` obtains geometry exclusively from canonical Rust
`current_profile()` and compares eight complete `malbolge-2026.2` cases against
`ProfileMachine`. The RTX 4060 / `sm_89` differential compares every one of the
4,782,969 final memory words plus registers, input/output, termination, step
counts, and rejection details. Cases cover the real six-step current program with
input and EOF, rejected jump atomicity, non-graphical termination, maximum-pointer
wrap, bounded budget exhaustion, live checkpoint resumption, and
already-terminated execution. CUDA remains optional and is not profile
authority. Rust product-batch integration additionally exercises the real classic
and current workers through hardware-neutral backend traits; unavailable,
deferred, or structurally invalid attempts fall back to untouched safe-Rust
states. The retained RTX 4060 baseline measures 15 samples per complete-snapshot
batch point and originally reached about 40.08 VMs/s at batch 32. Device-side
replication now copies one shared initial image from host and expands it into
private per-VM regions in VRAM; post-change batch 32 reaches about 51.67 VMs/s
with median upload time about 6.93x lower. Persistent profile sessions keep those
private states resident across bounded launches and reach about 2.00 million
64-step VM segments/s at batch 128 when setup, observation, and snapshots are
outside the timed region. Validated `ProfileMemoryImage` inputs additionally
reuse their geometry/domain proof across calls: retained batch-32 validation and
planning falls to about 0.23 ms and complete-snapshot throughput reaches about
93.68 VMs/s. These are backend measurements, not CPU-relative or cross-device
speedup claims.

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
  projections and atomic rejection. Resident classic evidence compares complete
  59,049-word states; scalable resident evidence compares complete 4,782,969-word
  current-profile states against normative Rust. Product-level batch routing, an
  RTX 4060 current-profile baseline, device-side shared initialization,
  validated-memory, direct-snapshot, and persistent-session evidence are retained.
  The hardware-neutral exact-primitive candidate bridge also executes 257-item
  classic crazy and rotate corpora on live CUDA and matches CPU evidence exactly.
  Verification-assist now reuses exact candidate evidence through the same live
  CUDA backend over a deterministic 257-item rotate corpus; those results remain
  untrusted hints and malformed optional evidence becomes no hint. The bounded
  `classic-rotate-target-search-v1` strategy now uses live CUDA candidate
  evaluation through the neutral search port over 257 deterministic candidates,
  records CUDA as the actual backend, matches CPU proposals, and leaves acceptance
  to an independent CPU verifier. A separate protocol-compliant full-domain run
  retains 15 CPU and 15 CUDA samples over 59,049 candidates. CPU median is
  401.185 ms and CUDA median is 412.570 ms on the RTX 4060, yielding 0.972x
  CUDA/CPU and rejecting the speedup hypothesis for this complete host-heavy
  route. Exact proposal equality and CPU admission still pass for every sample.
  The companion phase profile attributes 99.5% of CUDA median total time to named
  phases: about 57.0% host-side and 42.5% backend evaluation. Batch construction
  plus proposal selection consume about 173.081 ms. Hardware-neutral prepared
  search state is now active: CPU-prepared immutable request/batch state executes
  unchanged through the matching CUDA strategy, while forged or mismatched proof
  identity fails closed. Prepared execution removes repeated batch build/validation
  from the timed repeated-search path, and rotate-target selection avoids a second
  full corpus decode. The retained four-route comparison records CUDA ordinary
  and prepared medians of 306.872 and 162.693 ms (1.886x). CPU prepared reaches
  148.590 ms, leaving prepared CUDA about 9.5% slower (0.913x
  CPU-prepared/CUDA-prepared). Preparation is outside timed intervals, so this is
  repeated-search evidence rather than one-shot latency. The retained prepared
  phase profile attributes 138.320 ms, or 81.2% of CUDA median total time, to
  backend evaluation and 31.912 ms, or 18.7%, to proposal selection. Proof/result
  validation is negligible. Primitive CUDA evidence now returns one fixed-width
  packed byte buffer instead of 59,049 logical-ID/bytes objects. Batch order carries
  identity, malformed packed shape fails closed, and rotate search consumes packed
  u32 values directly. Verification-assist materializes only when explicit hints
  are requested. Retained packed evidence lowers CUDA ordinary/prepared medians
  from 306.872/162.693 to 230.144/91.199 ms (1.333x/1.784x). Backend evaluation
  falls from 138.320 to 67.202 ms (2.058x), and selection from 31.912 to
  22.288 ms (1.432x). Packed CUDA prepared remains about 18.0% slower than packed
  CPU prepared. Rotate prepared state now includes one validated decoded
  `PrimitiveBatch` produced independently of CUDA identity. Matching CUDA execution
  consumes that state without repeating candidate ID validation or payload decode;
  forged type/kind/evaluator state fails before device work. Ordinary search still
  prepares locally. Post-commit evidence is pending, while primitive transfer now
  precedes resident or fused search. Broader live-hardware evidence, synthesis/search
  strategies, resident search designs, and ROCm work remain before this TODO can
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
