# CPU accelerator reference

This directory owns mandatory deterministic CPU execution capacity for
hardware-neutral accelerator contracts.

`CpuExactPrimitiveAdapter` implements classic ten-trit `rotate` and `crazy`
independently from the Rust lookup tables. It is intentionally simple: optional
CUDA/ROCm implementations must preserve the same exact operation semantics before
their throughput is relevant.

`CpuCandidateEvaluationAdapter` and `CpuSearchExecutionAdapter` bind an explicit
evaluator or algorithm identity to a deterministic CPU callback. The callback is
the algorithm, while the adapter is execution capacity; hardware and strategy
identity therefore remain separate. Search output is always an untrusted
`CandidateProposal`. Only a `TrustedCandidateVerifier` can admit a proposal, and
verification-assist backends may supply hints but never an acceptance decision.
