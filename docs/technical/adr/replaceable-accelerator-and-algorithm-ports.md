# Replaceable Accelerator And Algorithm Ports

## Status

Accepted.

## Decision ID

`jig.malbolge.technical.replaceable-accelerator-and-algorithm-ports`

## Context

Candidate search and batch VM execution can benefit from GPUs, but binding the
compiler to CUDA would make one vendor API part of architecture and would mix
hardware choice with optimization strategy.

## Decision

Hardware acceleration and search algorithms are independent ports.

Hardware adapters provide capabilities such as batch execution, candidate
evaluation, memory/resource reporting, and asynchronous work submission. CPU is
the mandatory reference implementation and CUDA is the supported GPU adapter.
Additional hardware adapter projects are not in scope without new approval.

Algorithm adapters describe enumerative, stochastic, Monte Carlo, evolutionary,
learned, hybrid, pruning, or future strategies independently from the hardware
that executes their batches.

The early CPU optimizer must express its candidate batches, exact state
identity, pruning and cost semantics in bounded, indexable GPU-projectable
records. CPU-native and CUDA-native memory layouts or workgroup schedules may
differ, but one common candidate/verifier contract must survive projection.
Exercise a bounded real CPU/CUDA batch when hardware is available before P6
locks in representation choices; if CUDA is unavailable, record a feasibility
mapping without fabricating a device result. P8 requires a measured live-device
scaling benefit, not merely a CUDA-compatible interface.

Runtime resource budgeting adapts batch size, state layout, caches, and search
breadth to measured device capacity rather than fixed VRAM assumptions.

## Advantages

- Makes the replaceable accelerator and algorithm ports boundary explicit,
  reviewable, and stable before implementation depends on it.

## Disadvantages

- The decision increases cross-backend implementation and validation cost.

## Consequences

- CUDA can accelerate the compiler without becoming a target/runtime dependency
  of generated `.malbolge` programs.
- Benchmarks record both algorithm and hardware identity.
- More memory or compute can increase measured throughput but no exponential
  scaling claim is accepted without evidence.

## Rejected Alternatives

### CUDA-owned optimizer architecture

Rejected because optimization semantics and research strategy would become tied
to NVIDIA-specific APIs.

### Separate algorithms per hardware backend

Rejected because it prevents fair comparison of the same strategy across
supported CPU and CUDA backends.

## Evidence

Unsupported hardware/algorithm combinations fail explicitly. Correctness remains
verifier-owned even when candidate evaluation occurs on an accelerator.
