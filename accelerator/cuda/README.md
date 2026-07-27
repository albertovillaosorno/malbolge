# CUDA exact accelerator adapter

This directory owns the optional NVIDIA CUDA implementation behind the shared
accelerator contract. It is not a semantic dependency of the compiler, verifier,
or VM.

The first active slice evaluates exact classic `rotate` and `crazy` batches with
integer-only CUDA kernels. A narrow standard-library `ctypes` runtime binds only
the reviewed NVRTC and CUDA Driver API calls needed by the adapter; compiler,
verifier, VM, and shared accelerator code never import CUDA APIs. CPU reference
results remain the differential correctness oracle.

The repository pins CUDA 13.3 Update 1 for Windows x86-64 through
`toolchain.json`. Binary redistributables live under ignored
`.dependencies/cuda/13.3.1/`, and every downloaded archive is checked against
the recorded NVIDIA SHA-256. The active adapter requires no third-party Python
packages beyond the repository's pinned Python runtime.

Development evidence on an NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB) runs
NVRTC-generated PTX through the Driver API and matches the CPU reference for
boundary-heavy plus deterministic `rotate`/`crazy` batches. This is correctness
evidence, not a speedup claim.

Full VM state batching, adaptive resource sizing, asynchronous transfer/stream
tuning, benchmark evidence, and CUDA superoptimization remain open.
