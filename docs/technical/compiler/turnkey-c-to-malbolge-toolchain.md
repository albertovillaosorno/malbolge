# Turnkey C-to-Malbolge toolchain

## Status

Proposed.

## Purpose

Define the final user-facing installation and compilation contract: bootstrap a
clean checkout, then transform one explicit C source file into one verified
`.malbolge` artifact with a single stable command.

## Scope

- Public dependency bootstrap for supported Windows and Linux hosts.
- CPU/reference compilation as the universal correctness baseline.
- Optional NVIDIA CUDA acceleration on Windows and Linux.
- One explicit `.c` input and one atomically published `.malbolge` output.
- Jig excluded from the redistributable end-user dependency contract.

## Current Behavior

### Proposed Model

The repository already has a cross-platform bootstrap foundation and a CLI that
recognizes `.c` and `.malbolge` inputs. The complete C-to-Malbolge lowering path
and single-command user workflow remain unfinished.

### Implementation Status

Not implemented. This contract does not claim that arbitrary supported C already
compiles to `.malbolge`.

## Invariants

- CPU compilation works without a GPU.
- CUDA availability changes performance only, never semantic acceptance.
- Windows and Linux use exact manifest-selected dependencies.
- Privileged host drivers are detected and diagnosed, not installed silently.
- ROCm remains a reserved adapter contract and is not a completion dependency.
- Jig remains maintainer governance tooling outside the public bootstrap.

## Failure Behavior

Missing dependencies, unsupported C, unavailable CUDA, invalid profiles,
verification disagreement, and output publication failure are exact,
non-destructive diagnostics. CUDA unavailability may permit CPU fallback;
semantic or verification failure never does.

## Verification

Completion requires deterministic bootstrap identity, offline reuse after exact
archives are cached, end-to-end CPU fixtures, Linux NVIDIA selection and
fallback evidence, atomic output tests, and byte-exact verified `.malbolge`
artifacts.

## References

- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`
- `docs/todo/open/compiler/turnkey-c-to-malbolge-toolchain.mdc`
