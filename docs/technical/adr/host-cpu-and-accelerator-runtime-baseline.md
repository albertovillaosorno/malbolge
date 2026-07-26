# Host CPU And Accelerator Runtime Baseline

## Status

Accepted.

## Decision ID

`jig.malbolge.technical.host-cpu-and-accelerator-runtime-baseline`

## Context

Malbolge needs one exact CPU path that remains usable without a GPU and optional
native and accelerator paths that can improve execution or search throughput.
Naming an accelerator by hardware vendor alone is too vague because the project
integrates concrete compiler/runtime software stacks, while supporting only one
host ISA would make portability debt part of the initial architecture.

## Decision

The supported 64-bit host CPU baseline is x86-64 and AArch64 from the first
implementation slice. The portable CPU VM, deterministic optimizer, verifier,
and benchmark harness must be able to run on both architectures without changing
guest semantics.

Native execution has independent x86-64 and AArch64 code-generation backends
behind one execution-IR contract. A backend may use architecture-specific
instruction selection and calling conventions, but those details never become
Malbolge semantics.

GPU acceleration is named by the software runtime boundary that the repository
integrates. CUDA is the first NVIDIA GPU adapter and ROCm is the first AMD GPU
computing adapter. CPU, CUDA, ROCm, and future adapters implement replaceable
capability ports; none of them is required for semantic correctness beyond the
portable CPU baseline.

The initial host baseline does not promise 32-bit x86 or AArch32 support. Adding
a new host ISA or accelerator runtime requires explicit evidence for the same
semantic and verifier contracts rather than widening shared code with platform
conditionals by accident.

## Advantages

- x86-64 and AArch64 receive equal architectural status before implementation
  choices make one of them a retrofit.
- CUDA and ROCm identify concrete software/runtime integration boundaries
  instead of conflating a GPU vendor with an API contract.
- The CPU path remains a portable correctness and fallback baseline when no GPU
  is available.
- Native code generation and accelerator search can evolve independently from
  the guest machine definition.

## Disadvantages

- Every CPU/native execution change must consider two host ISAs from the start.
- CI and benchmark evidence eventually need representative x86-64 and AArch64
  machines plus CUDA and ROCm hardware for backend-specific claims.
- Excluding 32-bit host targets initially narrows legacy-host portability.

## Consequences

- `accelerator/cpu/`, `accelerator/cuda/`, and `accelerator/rocm/` are the first
  adapter scaffold identities.
- CPU reference tests and performance evidence identify whether results came
  from x86-64 or AArch64.
- Native cache identity includes host architecture and cannot reuse x86-64 code
  on AArch64 or vice versa.
- ROCm replaces the vague `AMD` adapter name throughout planning and technical
  documentation.
- Unsupported host or accelerator hardware changes available acceleration, not
  the acceptance semantics of a valid `.malbolge` program.

## Rejected Alternatives

- Supporting x86-64 first and adding AArch64 later was rejected because host ISA
  assumptions would otherwise leak into execution IR, native-cache identity, and
  benchmark infrastructure before portability is exercised.
- Naming an adapter `AMD` was rejected because vendor identity does not specify
  the compiler/runtime interface implemented by the adapter.
- Requiring a GPU was rejected because compiler correctness and VM execution
  must remain available on the CPU baseline.
- Treating CUDA or ROCm as compiler semantics was rejected because emitted
  `.malbolge` artifacts must not depend on the machine that optimized them.

## Evidence

- `accelerator/cpu/`
- `accelerator/cuda/`
- `accelerator/rocm/`
- `docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md`
- `docs/technical/adr/tiered-native-execution.md`
- `docs/bibliography/platforms-and-runtimes/aarch64.md`
- `docs/bibliography/platforms-and-runtimes/x86-64.md`
- `docs/bibliography/platforms-and-runtimes/rocm.md`
