# NVIDIA CUDA Programming Model

- Review status: Verified
- Evidence status: Verified
- As-of date: 2026-07-26

## Identity

- Canonical name: CUDA Programming Guide
- Subject class: Accelerator programming model and platform documentation
- Stable identifier: NVIDIA CUDA Programming Guide
- Publisher or authority: NVIDIA

## Repository Relevance

CUDA is the first planned accelerator adapter for batched exact VM execution,
candidate evaluation, synthesis, and superoptimization. CUDA is not a semantic
dependency of the compiler.

## Source Quality And Provenance

The official NVIDIA guide is the primary source for the CUDA programming model,
GPU execution concepts, memory hierarchy, and compilation/runtime interfaces.

## Verified Claims

- CUDA is a parallel computing platform/programming model for NVIDIA GPUs.
- The guide distinguishes the language-independent programming model from
  language-specific GPU programming interfaces.
- CUDA exposes hierarchical execution and memory concepts relevant to batched
  candidate evaluation.

## Unresolved Evidence

Performance and memory behavior are hardware-dependent. No throughput or VRAM
scaling claim is accepted without repository measurements on identified devices.

## Sources

- <https://docs.nvidia.com/cuda/cuda-programming-guide/index.html> - accessed
  2026-07-26.
