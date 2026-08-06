# Resumable compilation progress sidecars

## Status

Active contract; implementation pending

## Purpose

Preserve objective timing and resumable state for long-running compilation,
layout, block synthesis, optimization, verification, and accelerator jobs. A
power loss, process crash, cancellation, or planned pause must lose at most the
work performed since the last durable checkpoint rather than the whole job.

## Scope

The contract applies to public commands and internal services that can spend
material time converting source files, compiler IR, link plans, or reusable
blocks into verified Malbolge artifacts. It covers CPU and accelerator paths on
Windows and Linux. Short operations may omit checkpoint creation, but any job
that advertises resumability or crosses the configured checkpoint interval must
maintain the sidecar.

For an intended output named `program.malbolge`, the canonical progress path is
`program.malbolge.progress.json`. Optional durable state uses
`program.malbolge.checkpoint` or a versioned directory referenced by the
sidecar. An incomplete executable artifact may use
`program.malbolge.partial`; the final requested path is never replaced until the
artifact is complete and independently verified.

## Current Behavior

The repository now exposes a reference `malbolge-progress-v1` validator and
atomic writer in `scripts/progress_sidecar.py`. It defines canonical paths,
backend-neutral resume identity, exact timing/lifecycle invariants,
duplicate-key rejection, canonical JSON, and atomic sidecar replacement.

Product CLI/compiler integration, portable compiler-state serialization,
crash injection, and CPU/CUDA resume equivalence remain unimplemented. The
reference schema therefore establishes the boundary without claiming complete
resumability.

### Sidecar Schema

The first accepted schema is identified by `malbolge-progress-v1`. The JSON
object must contain at least:

- `schema`, `operation_id`, and `status`;
- requested output path and canonical sidecar/checkpoint paths;
- source path plus cryptographic source identity;
- target profile ID and fingerprint;
- repository revision, toolchain identity, algorithm ID/version, and seed when
  applicable;
- backend kind plus device identity when an accelerator is used;
- current pipeline stage, checkpoint sequence, completed units, and total units
  when the total is knowable;
- UTC `started_at`, `updated_at`, and optional `completed_at` timestamps;
- persisted `active_elapsed_ns`, `wall_elapsed_ns`, verification time,
  serialization time, and checkpoint overhead;
- checkpoint compatibility fingerprint and checkpoint SHA-256;
- partial-output byte count/hash when a partial artifact exists;
- stable diagnostic code and message for failed or cancelled jobs.

Percent completion is emitted only when the denominator is stable and known.
Unknown totals remain `null`; the tool reports counters and stage identity
instead of inventing a percentage.

## Invariants

- Sidecar and checkpoint updates use write-to-temporary, flush, and atomic
  rename within the destination filesystem.
- The final `.malbolge` path is published atomically only after independent
  verification succeeds.
- Resume rejects source, target profile, compiler revision, algorithm version,
  seed, or checkpoint-format mismatches unless an explicit reviewed migration
  exists.
- Device-local memory is never the only copy of resumable state. GPU jobs emit a
  backend-neutral durable checkpoint sufficient for CPU inspection and exact
  compatibility checks.
- `active_elapsed_ns` is accumulated from monotonic clock segments. UTC wall
  timestamps provide chronology but never replace monotonic duration
  measurement.
- Paused time, checkpoint overhead, verification, serialization, and active
  compute/search time remain distinguishable for scientific analysis.
- The sidecar is evidence and recovery state, not semantic authority. Source,
  target profile, compiler, verifier, and accepted artifact determine meaning.
- Progress writes are rate-limited and bounded so checkpointing does not become
  an unmeasured dominant cost.

## Failure Behavior

On orderly cancellation or a handled failure, the job writes one final sidecar
state and preserves the most recent valid checkpoint. On abrupt process or host
failure, restart reads only the last atomically committed sidecar/checkpoint
pair. A torn, missing, stale, or incompatible pair is rejected with a stable
diagnostic and never guessed into validity.

If checkpoint persistence fails, the job may continue only when the caller
explicitly accepts non-resumable execution. Public CLI defaults fail closed for
jobs that requested resumability.

## Verification

- Schema tests validate every required field, status transition, and unknown-
  total representation.
- Crash fixtures terminate jobs between temporary write, flush, rename, and
  checkpoint publication boundaries.
- Resume tests cover unchanged jobs, source/profile/toolchain mismatch,
  corrupted checkpoints, cancellation, and completed-job idempotence.
- CPU and CUDA fixtures resume from a common canonical checkpoint and produce
  the same independently verified final artifact as uninterrupted execution.
- Timing tests use injected monotonic and UTC clocks and prove that active,
  paused, wall, verification, serialization, and checkpoint durations are not
  conflated.
- End-to-end CLI tests prove that the final artifact is atomic while the sidecar
  remains continuously inspectable.

## References

<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
- [Compiler Pipeline And Guest Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
- [Parametric Multi Objective Algorithm Evaluation](../../research/adr/parametric-multi-objective-algorithm-evaluation.md)
