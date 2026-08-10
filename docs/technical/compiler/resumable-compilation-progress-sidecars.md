# Resumable compilation progress sidecars

## Status

Active contract and durable generation reference

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
`program.malbolge.progress.json`. Durable generations use immutable paths such
as `program.malbolge.checkpoint.00000000000000000001` and
`program.malbolge.partial.00000000000000000001`. The sidecar is the only mutable
pointer to the latest committed generation. A persistent
`program.malbolge.progress.json.lock` file coordinates sidecar writers; its
contents carry no recovery semantics and the operating-system lock is released
when the owning process exits. The final requested path is never replaced until
the artifact is complete and independently verified.

## Current Behavior

The repository now exposes a reference `malbolge-progress-v1` validator and
durable generation writer in `scripts/progress_sidecar.py`. It defines canonical
sequence-addressed paths, backend-neutral resume identity, exact timing and
lifecycle invariants, monotonic transition validation, duplicate-key rejection,
canonical JSON, immutable checkpoint/partial persistence, and atomic sidecar
replacement after generation payloads are durable. Mutable pointer updates are
serialized across processes from prior-sidecar validation through replacement,
so a stale writer cannot overwrite a generation committed concurrently.

Direct API admission is fail-closed as well as JSON admission. Runtime callers
must supply exact sidecar/resume-identity enums, strings, integers, and
immutable records. Booleans cannot alias counters or sequence numbers, foreign
objects do not leak decoder/type exceptions, oversized JSON integer literals
that hit the interpreter conversion limit remain inside the stable sidecar error
boundary, and impossible UTC calendar timestamps are reported the same way.
`ProgressTimer` validates every phase and monotonic-clock sample before mutating
timing evidence.

`write_atomic()` also validates every referenced checkpoint and partial payload
before moving the mutable pointer: the files must exist, hashes must match, and
partial byte counts must agree. Its read-transition-validation-replacement
transaction is serialized by a process-shared sibling `.lock` file so two
writers cannot both validate against one stale predecessor and then race the
mutable pointer backward. A caller therefore cannot publish a syntactically
valid sidecar that points at absent or corrupted generation bytes.

A crash after writing a later generation but before replacing the sidecar leaves
the previously referenced generation intact and resumable. Unreferenced newer
generations are ignored until a valid sidecar publishes them. `ProgressTimer`
uses an injectable monotonic nanosecond clock and exclusive active, paused,
verification, serialization, and checkpoint phases to construct the exact timing
fields without UTC arithmetic. Child-process crash fixtures now terminate
publication after the checkpoint and immediately before the sidecar commit.
Product CLI/compiler integration, portable compiler-state serialization, broader
power-loss injection, and CPU/CUDA resume equivalence remain unimplemented.

### Sidecar Schema

The first accepted schema is identified by `malbolge-progress-v1`. The JSON
object must contain at least:

- `schema`, `operation_id`, and `status`;
- requested output path and canonical sidecar/checkpoint paths;
- source path plus cryptographic source identity;
- target profile ID and fingerprint;
- exact lowercase 40-hex Git `repository_revision`, toolchain fingerprint,
  algorithm ID/version, and seed when applicable;
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

### Operator inspection

The reference inspector prints one exact key/value summary without rounding
scientific timing:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  src/automation/repository/composition/scripts/progress_sidecar.py `
  output.malbolge.progress.json
```

The summary includes status, stage, completed/total units, active/wall/paused
nanoseconds, verification/serialization/checkpoint nanoseconds, and canonical
progress/checkpoint/partial paths. The JSON sidecar remains the machine-readable
authority; this line is an operator view over the same validated record. Invalid
UTF-8 is converted to the same stable inspection failure as malformed schema or
missing storage rather than escaping as a decoder exception.

## Invariants

- Checkpoint and partial generations are immutable and sequence-addressed.
- Generation payloads use write-to-temporary, flush, and atomic no-replace
  publication before the canonical sidecar pointer is replaced. Windows uses a
  same-directory no-replace rename instead of requiring hard-link support;
  POSIX uses a same-filesystem hard link. A collided destination is re-read to
  prove byte identity; if that destination disappears or becomes unreadable
  during the collision check, publication fails with the stable sidecar error
  rather than leaking a raw filesystem exception. Canonical sidecar,
  writer-lock, checkpoint, and partial-generation paths reject symlink or
  junction components
  from the leaf through the ancestor chain; a byte-identical redirected target
  is not accepted as mutable or immutable state.
- A rejected transition, malformed direct API value, missing generation, or
  payload/hash/length mismatch never replaces the last valid sidecar. Concurrent
  writers serialize transition validation and pointer replacement through the
  same persistent sibling lock path.
- The final `.malbolge` path is published atomically only after independent
  verification succeeds.
- Resume compatibility binds source identity, target profile, exact repository
  revision, toolchain fingerprint, algorithm version, seed, and checkpoint
  schema.
  Any mismatch is rejected unless an explicit reviewed migration exists.
- Device-local memory is never the only copy of resumable state. GPU jobs emit a
  backend-neutral durable checkpoint sufficient for CPU inspection and exact
  compatibility checks.
- `active_elapsed_ns` is accumulated from monotonic clock segments. UTC wall
  timestamps provide chronology but never replace monotonic duration
  measurement.
- Paused time, checkpoint overhead, verification, serialization, and active
  compute/search time remain distinguishable for scientific analysis. Their
  exclusive nanosecond counters exactly partition `wall_elapsed_ns`.
- The sidecar is evidence and recovery state, not semantic authority. Source,
  target profile, compiler, verifier, and accepted artifact determine meaning.
- Progress writes are rate-limited and bounded so checkpointing does not become
  an unmeasured dominant cost.

## Failure Behavior

On orderly cancellation or a handled failure, the job writes one final sidecar
state and preserves the most recent valid generation. On abrupt process or host
failure, restart follows only the last atomically committed sidecar pointer.
Later unreferenced generation files cannot invalidate that pointer. Missing,
stale, overwritten, or incompatible generation data is rejected with a stable
diagnostic and never guessed into validity. Sidecar reads, writer-lock
lifecycle, and mutable or immutable publication failures are likewise translated
into the
stable sidecar error boundary rather than leaking host filesystem exceptions.

If checkpoint persistence fails, the job may continue only when the caller
explicitly accepts non-resumable execution. Public CLI defaults fail closed for
jobs that requested resumability.

## Verification

- Schema tests validate every required field, status transition, and unknown-
  total representation.
- Crash fixtures terminate a child process after checkpoint publication and
  immediately before sidecar replacement, proving the previous pointer remains
  readable and resumable across torn next-generation state.
- Resume tests cover unchanged jobs, monotonic transitions, exact repository
  revision and source/profile/toolchain mismatch, overwritten or missing
  generations, cancellation, and terminal-job reopening. Two-process fixtures
  prove both lock exclusion and post-lock revalidation: a stale candidate that
  waited behind a newer commit is rejected before mutable-pointer replacement.
- CPU and CUDA fixtures resume from a common canonical checkpoint and produce
  the same independently verified final artifact as uninterrupted execution.
- Timing tests use an injected monotonic clock, exercise every exclusive
  phase, reject foreign phases plus boolean/negative/backward samples, and prove
  active, paused, wall, verification, serialization, and checkpoint durations
  are not conflated.
- Direct-construction tests mutate resume identity and sidecar fields, reject
  boolean sequence aliases and impossible UTC dates, and prove pointer
  publication validates the referenced checkpoint/partial generation first.
- End-to-end CLI tests prove that the final artifact is atomic while the sidecar
  remains continuously inspectable.

## References

<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
- [Compiler Pipeline And Guest Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
- [Parametric Multi Objective Algorithm Evaluation](../../research/adr/parametric-multi-objective-algorithm-evaluation.md)
