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

The official NVIDIA Programming Guide is the primary source for the CUDA
programming model, GPU execution concepts, and memory hierarchy. The official
CUDA Driver API is the primary source for low-level runtime interfaces used by
the repository adapter. The official Best Practices Guide is the primary source
for constant-memory access and warp-level performance behavior used by
structural memory diagnostics.

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
- CUDA Driver API 13.3.1 defines `cuFuncGetAttribute` for querying one loaded
  `CUfunction` and assigns `CU_FUNC_ATTRIBUTE_SHARED_SIZE_BYTES = 1`,
  `CU_FUNC_ATTRIBUTE_CONST_SIZE_BYTES = 2`,
  `CU_FUNC_ATTRIBUTE_LOCAL_SIZE_BYTES = 3`, and
  `CU_FUNC_ATTRIBUTE_NUM_REGS = 4`. Attribute zero is
  `CU_FUNC_ATTRIBUTE_MAX_THREADS_PER_BLOCK`.
- Those attributes report static shared bytes per block, user-allocated constant
  bytes, local bytes per thread, registers per thread, and the function/device
  maximum threads per block respectively. They are resource observations, not
  semantic authority.
- `CU_DEVICE_ATTRIBUTE_MAX_THREADS_PER_MULTIPROCESSOR = 39` reports the maximum
  resident threads per multiprocessor.
- The Driver API function
  `cuOccupancyMaxActiveBlocksPerMultiprocessor` returns the maximum active
  blocks per multiprocessor for a specific function, intended block size, and
  dynamic
  shared-memory size. The repository uses the actual 256-thread launch and zero
  dynamic shared bytes, so the result is theoretical launch capacity rather than
  observed runtime utilization.
- CUDA Best Practices Guide 13.3 states that constant memory is cached and that
  different constant-memory addresses requested by threads in one warp are
  serialized, with cost scaling with the number of unique addresses. It also
  identifies 32 as the warp size on current GPUs. Repository address-fanout
  evidence uses those statements only to model serialization pressure; it does
  not claim physical cache hit or miss counts.

### Unresolved

Performance and memory behavior are hardware-dependent. No throughput or VRAM
scaling claim is accepted without repository measurements on identified devices.

## Sources

- <https://docs.nvidia.com/cuda/cuda-programming-guide/index.html> - accessed
  2026-07-26.
- <https://docs.nvidia.com/cuda/cuda-driver-api/group__CUDA__EXEC.html> - CUDA
  Driver API 13.3.1 execution-control reference, accessed 2026-09-04.
- <https://docs.nvidia.com/cuda/cuda-driver-api/group__CUDA__TYPES.html> - CUDA
  Driver API 13.3.1 function-attribute enumeration, accessed 2026-09-04.
- <https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/> - CUDA C++ Best
  Practices Guide 13.3 constant-memory and warp guidance, accessed 2026-09-04.
- <https://developer.download.nvidia.com/compute/cuda/redist/> - accessed
  2026-08-05.
