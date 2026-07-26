# Replaceable Accelerator And Algorithm Ports

## Status

Accepted.

## Context

Candidate search and batch VM execution can benefit from GPUs, but binding the
compiler to CUDA would make one vendor API part of architecture and would mix
hardware choice with optimization strategy.

## Decision

Hardware acceleration and search algorithms are independent ports.

Hardware adapters provide capabilities such as batch execution, candidate
evaluation, memory/resource reporting, and asynchronous work submission. CPU is
the mandatory reference implementation; CUDA is the first GPU adapter; AMD and
future devices can implement the same contract.

Algorithm adapters describe enumerative, stochastic, Monte Carlo, evolutionary,
learned, hybrid, pruning, or future strategies independently from the hardware
that executes their batches.

Runtime resource budgeting adapts batch size, state layout, caches, and search
breadth to measured device capacity rather than fixed VRAM assumptions.

## Alternatives Considered

### CUDA-owned optimizer architecture

Rejected because optimization semantics and research strategy would become tied
to NVIDIA-specific APIs.

### Separate algorithms per hardware backend

Rejected because it prevents fair comparison of the same strategy across CPU,
CUDA, AMD, and future devices.

## Consequences

- CUDA can accelerate the compiler without becoming a target/runtime dependency
  of generated `.malbolge` programs.
- Benchmarks record both algorithm and hardware identity.
- More memory or compute can increase measured throughput but no exponential
  scaling claim is accepted without evidence.

## Implementation Notes

Unsupported hardware/algorithm combinations fail explicitly. Correctness remains
verifier-owned even when candidate evaluation occurs on an accelerator.
