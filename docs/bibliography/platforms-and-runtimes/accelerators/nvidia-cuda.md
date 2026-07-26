# NVIDIA CUDA Programming Model

## Status

Verified; evidence verified.

## Subject

- Canonical name: CUDA Programming Guide
- Subject class: Accelerator programming model and platform documentation
- Stable identifier: NVIDIA CUDA Programming Guide
- Publisher or authority: NVIDIA

## Repository Use

CUDA is the first planned accelerator adapter for batched exact VM execution,
candidate evaluation, synthesis, and superoptimization. CUDA is not a semantic
dependency of the compiler.

## Provenance

The official NVIDIA guide is the primary source for the CUDA programming model,
GPU execution concepts, memory hierarchy, and compilation/runtime interfaces.

## Identity And Version

- Canonical name: CUDA Programming Guide
- Subject class: Accelerator programming model and platform documentation
- Stable identifier: NVIDIA CUDA Programming Guide
- Publisher or authority: NVIDIA

## License Or Terms

This is external material. Citation does not relicense the source or import its
terms into the repository MIT license.

## Evidence

### Verified

- CUDA is a parallel computing platform/programming model for NVIDIA GPUs.
- The guide distinguishes the language-independent programming model from
  language-specific GPU programming interfaces.
- CUDA exposes hierarchical execution and memory concepts relevant to batched
  candidate evaluation.

### Unresolved

Performance and memory behavior are hardware-dependent. No throughput or VRAM
scaling claim is accepted without repository measurements on identified devices.

## Sources

- <https://docs.nvidia.com/cuda/cuda-programming-guide/index.html> - accessed
  2026-07-26.
