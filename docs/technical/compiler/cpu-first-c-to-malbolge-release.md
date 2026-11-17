# CPU-first C-to-Malbolge release

## Status

Proposed P5 delivery contract. This is an intermediate, independently usable
release gate, not the completed multi-platform turnkey toolchain.

## Purpose

Make the first genuinely useful, reproducible C-to-Malbolge compiler available
before native execution tiers, CUDA, DOOM, self-hosting or publication. The
supported deterministic-C subset must be explicit and tested end to end.

## Scope

- An unaccelerated reference compiler on one declared supported Linux host.
- An ordinary single-command source-C-to-verified-`.malbolge` workflow.
- Documented deterministic C support for mutable locals, control flow,
  arithmetic, finite byte I/O and EOF behavior as actually implemented.
- Reproducible installation, diagnostics and safe output publication.

## Invariants

- The executable Malbolge guest, not a host helper, performs every claimed
  runtime C computation and guest I/O effect.
- The supported source language is the proven subset, never "arbitrary C".
- CPU-only operation must not require a GPU, native JIT/AOT or a resident
  compiler service.
- The release has explicit target-profile identity and bounded execution
  controls; verifier disagreement never publishes an artifact.
- The same source/profile/inputs reproduce observable output, halting and
  declared failure behavior.

## Acceptance evidence

1. Starting from a clean checkout with the documented pinned bootstrap, a
   developer compiles an ordinary supported C source file through one command.
   No manually fabricated JSON/IR, phase-specific fixture selection or
   pre-generated guest artifact may be required.
2. A source-controlled **compound program** combines mutable local state,
   arithmetic, an input-dependent branch and an EOF-driven loop. The compiled
   Malbolge runs on the normative profile VM and matches an independently
   justified native C23 oracle for empty, short, NUL, high-bit and mixed inputs.
   A second distinct program demonstrates bounded binary stream transformation.
3. Real guest observations include output bytes, termination/EOF handling,
   failure diagnostics and finite step/resource limits. Pinned C23 optimized
   and unoptimized native controls, defined-behavior checks, negative source
   mutations and independent VM replay must agree.
4. Unsupported C, wrong profile, failed verification and output collisions
   return explicit errors without leaving or clobbering a final artifact.
   Successful source/profile identity is retained for reproducibility.
5. The declared CPU-only installation/CLI test suite and the repository-owned
   relevant validation gates pass, or any unrelated baseline failure is
   documented with an exact reproducible diagnostic.

## Non-goals

Cross-platform packaging, native x86-64/AArch64 backends, CUDA,
accelerated compilation, DOOM playability, arbitrary C, self-hosting and
paper-grade adversarial matrices are later, separately owned work. The
existing [turnkey toolchain contract](turnkey-c-to-malbolge-toolchain.md)
continues to own the eventual wider user-facing release.

## Related authority

- [Live guest byte-stream contract](parametric-guest-byte-stream-emission.md)
- [Ternary machine lowering](ternary-machine-lowering.md)
- [Malbolge layout and encoding](malbolge-layout-and-encoding-backend.md)
- [Translation validation](../verification/translation-validation.md)
- [Compiler pipeline ADR](../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification trust ADR](../adr/verification-trust-boundary.md)
