# CPU exact accelerator reference

This directory owns the mandatory deterministic reference implementation for
hardware-neutral accelerator contracts.

The current scalar adapter implements classic ten-trit `rotate` and `crazy`
independently from the Rust lookup tables. It is intentionally slower and simple:
CUDA/ROCm implementations must match its exact observable results before their
throughput is relevant.
