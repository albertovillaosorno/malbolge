# Turnkey C-to-Malbolge toolchain

## Status

Proposed.

## Purpose

Define the final user-facing installation and compilation contract: bootstrap a
clean checkout, then transform one explicit C source file into one verified
`.malbolge` artifact with a single stable command.

## Dependency boundary

The bootstrap provisions or verifies all public, pinned project dependencies
needed by the supported CPU compiler and optional NVIDIA CUDA acceleration. Jig
is maintainer governance tooling and is not installed or required by the public
compiler workflow. Privileged host components, especially GPU kernel drivers,
are detected and diagnosed rather than installed silently.

## Platform contract

- CPU compilation is the correctness baseline and works without a GPU.
- Windows and Linux are supported deployment hosts.
- NVIDIA CUDA is optional on Windows and Linux, including headless Linux servers.
- Accelerator availability changes performance only; deterministic verification
  remains authoritative.
- ROCm retains only a reserved adapter contract until supported hardware and a
  maintainer are available.

## Command contract

After bootstrap, the supported interface accepts an explicitly named `.c` input
and `.malbolge` output, validates the guest-C profile, performs all compiler
stages, verifies the emitted program, and publishes the output atomically. It
must not expose intermediate IR or require users to assemble the pipeline by
hand.

## Failure behavior

Missing dependencies, unsupported C, unavailable CUDA, invalid profiles,
verification disagreement, and output publication failures are exact,
non-destructive diagnostics. CUDA unavailability permits CPU fallback; semantic
or verification failure never does.

## Verification

Completion requires deterministic bootstrap identity, offline reuse after exact
archives are cached, end-to-end CPU fixtures, Linux NVIDIA selection/fallback
evidence, and byte-exact verified `.malbolge` outputs.
