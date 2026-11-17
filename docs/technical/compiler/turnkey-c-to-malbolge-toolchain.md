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

## Bounded Acceptance (2026-11-16)

- The supported Windows/Linux C compiler/bootstrap must run without GPU or
  native JIT; it uses an ordinary interpreter/verifier-backed `.malbolge`
  build. CUDA provisioning, NVIDIA kernel drivers and the six-pair native
  capability-runner matrix are separate integrations, not prerequisites for
  compiling C in the supported CPU path.
- Offline reuse means exact toolchains and public archives are already
  cached for the declared supported host. Uncached content, missing licensed
  components or privileged drivers fail with explicit diagnostics instead of
  a false universal offline-installation promise.

## Invariants

- CPU compilation works without a GPU.
- CUDA availability changes performance only, never semantic acceptance.
- Supported Windows/Linux compiler hosts use exact manifest-selected
  public dependencies with an explicit supported-host matrix. Native runner
  coverage and CUDA device availability are reported separately.
- Privileged host drivers are detected and diagnosed, not installed silently.
- Jig remains maintainer governance tooling outside the public bootstrap.

## Failure Behavior

Missing dependencies, unsupported C, unavailable CUDA, invalid profiles,
verification disagreement, and output publication failure are exact,
non-destructive diagnostics. CUDA unavailability may permit CPU fallback;
semantic or verification failure never does.

## Verification

Completion requires deterministic bootstrap identity, offline reuse after
exact archives are cached, end-to-end CPU fixtures, explicit missing-CUDA
fallback, atomic output tests, and verified `.malbolge` artifacts. Live Linux
NVIDIA selection and throughput are separately reported when hardware exists;
no GPU test is a P7 public-compiler prerequisite.

## References

- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`
- `docs/todo/open/self_hosting/turnkey-c-to-malbolge-toolchain.mdc`
