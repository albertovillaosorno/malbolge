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
objects do not leak decoder/type exceptions, and direct JSON parsing requires
an exact string instead of accepting byte/bytearray aliases or leaking decoder
`TypeError`. Oversized JSON integer literals that hit the interpreter conversion
limit remain inside the stable sidecar error boundary, and impossible UTC
calendar timestamps are reported the same way.
`ProgressTimer` validates every phase and monotonic-clock sample before mutating

timing evidence. Non-callable clocks and callback failures remain inside the
stable sidecar error boundary. Snapshotting also revalidates its internal
anchors and accumulated phase partition, so directly constructed or corrupted
timer state cannot be misclassified as verification time. Public path helpers
reject foreign objects instead of stringifying them, and direct reads require a
real `pathlib.Path` before filesystem inspection.

`write_atomic()` also validates every referenced checkpoint and partial payload
before moving the mutable pointer: the files must exist, hashes must match, and
partial byte counts must agree. Direct generation publication requires exact
immutable `bytes`; mutable or foreign aliases fail before hashing or creating a
generation file. Its read-transition-validation-replacement
transaction is serialized by a process-shared sibling `.lock` file so two
writers cannot both validate against one stale predecessor and then race the
mutable pointer backward. A caller therefore cannot publish a syntactically
valid sidecar that points at absent or corrupted generation bytes.

Atomic publication and directory durability confirmation are distinct commit
phases. `ProgressSidecarCommittedError` carries the exact `published_path` when
a failure is reported only after publication crossed its commit point. Its
`ProgressSidecarDurabilityError` subtype means parent-directory synchronization
failed after publication, so durability is unconfirmed rather than rolled back.

A directory-descriptor close failure after successful directory sync reports the
broader committed error because durability is already confirmed. If sync and
close both fail, the sync failure remains primary and close failure is secondary
evidence.

Writer-lock release/close and immutable temporary-file cleanup failure after
durable publication follow the same committed-evidence principle. If a durable
checkpoint member commits before a later partial member fails prepublication,
the failure reports the checkpoint as the exact last committed path. After all
generation members commit, a mutable sidecar prepublication failure likewise
reports the last committed member until the pointer itself crosses commit.

During lock unwinding, a later release or close failure is secondary evidence
when an
acquisition, body, or release failure is already active. Mutable replacement
does not unlink the moved temporary pathname after commit. Before
replacement, mutable temporary-cleanup failure is retained as secondary evidence
and cannot mask the primary publication failure.

Failures before publication retain ordinary `ProgressSidecarError` behavior and
do not gain committed-path evidence. Failed payload-stream ownership transfer
closes the raw temporary descriptor, while cleanup failure remains secondary to
the stream-open failure. Temporary payload-stream teardown likewise keeps an
earlier write, flush, or file-sync failure primary when close also fails.

A crash after writing a later generation but before replacing the sidecar leaves
the previously referenced generation intact and resumable. Unreferenced newer
generations are ignored until a valid sidecar publishes them. `ProgressTimer`
uses an injectable monotonic nanosecond clock and exclusive active, paused,
verification, serialization, and checkpoint phases to construct the exact timing
fields without UTC arithmetic.

`ProgressWriteLimiter` accepts one explicit
positive monotonic interval: routine queued/running updates are suppressed until
that interval passes, while checkpointed and terminal evidence always attempts
publication. Only successful or post-commit-failing writes consume the limiter
window, so a prepublication failure can retry immediately.

`malbolge-checkpoint-v1` now supplies a canonical backend-neutral envelope for
opaque resumable state. The envelope binds the sidecar compatibility
fingerprint, checkpoint sequence, stage, completed-unit count, caller-owned
versioned state codec, payload SHA-256, and canonical base64 payload while
intentionally omitting CPU/CUDA backend identity. Decoding first requires the
envelope bytes to match the sidecar checkpoint digest, then revalidates all of
those fields and rejects malformed, noncanonical, or differently identified
state.
The envelope does not define compiler-stage semantics; concrete compiler/search
state codecs remain owned by their producing subsystems.

The accelerator application now supplies one concrete search codec,
`evaluated-search-prefix-evidence-v1`. It canonically binds the exact
`SearchRequest`, a fingerprint over evaluator identity plus every candidate
identity/payload byte, total candidate count, and an immutable request-order
prefix of completed `CandidateEvidence`. Backend and device identity are
omitted, so byte-identical CPU/CUDA evidence has one durable representation.
Restore requires the current request and batch to match exactly.

`evaluated-search-prefix-resume-v1` now consumes that codec for ordinary
evaluated search. It rebuilds and validates the exact candidate batch, evaluates
only the unfinished request-order suffix through the selected backend, combines
restored and fresh evidence, reruns the ordinary selector, and checks proposal
membership. Fixed-width indexed candidate storage remains packed across suffix
projection. Restored evidence remains untrusted and does not bypass independent
verification.

`prepared-evaluated-search-prefix-resume-v1` applies the same evidence codec to
prepared search without downgrading to ordinary evaluation. Resume reconstructs
the strategy-owned prepared projection, requires the checkpoint to match that
exact evaluation batch, re-prepares only the unfinished projected suffix, and
then reruns prepared proposal selection against the original full candidate
batch. Ordinary batch preparers are reusable for suffix state automatically;
selection-aware strategies must declare an explicit `resume_preparer`. Rotate
and crazy target strategies bind their primitive suffix preparers explicitly.

Rotate-target and crazy-target expose target-owned resume factories that reuse
the exact ordinary strategy definitions rather than reconstructing selection
behavior at the call site.

Focused differential evidence now covers both accelerator-backed search
strategies. Rotate-target and crazy-target each produce byte-identical CPU/CUDA
checkpoint payloads, resume CPU-produced state on CUDA, resume CUDA-produced
state on CPU, and match uninterrupted CPU proposals. Prepared checkpoint resume
additionally proves a CPU-produced projected prefix resumes on live CUDA with
matching proposals. Full bidirectional prepared and later compiler-execution
CPU/CUDA resume equivalence remain open.

Canonical typed-IR durable state is already backend-identity neutral.

The external optimizer runner now accepts `--resume-checkpoint PATH` for
rotate-target and crazy-target evaluated-search checkpoint payloads. It
preserves
configured-versus-actual backend identity, retries accelerator execution failure
through the CPU reference route, rejects unsupported algorithms and incompatible
checkpoint state, and records checkpoint SHA-256 plus
`evaluated-search-prefix-resume-v1` in resumed JSON output. Fresh-search JSON is
unchanged.

The progress-sidecar inspector provides two verified portable-checkpoint views.
`--checkpoint-info PROGRESS.json` validates the mutable sidecar, immutable
generation bytes, outer checkpoint digest, resume identity and position,
canonical envelope, and inner payload digest before reporting only checkpoint
sequence, stage, completed units, state codec, and payload SHA-256.
`--extract-checkpoint STATE_CODEC PROGRESS.json` performs the same durable-state
admission, additionally requires the caller's expected codec, and emits exact
opaque state bytes to binary stdout. Together these provide an operator bridge
from `malbolge-progress-v1` into codec-aware consumers without allowing unknown
checkpoint state to execute automatically.

The optimizer still consumes an explicit extracted file. Typed-IR compiler
composition now has `resume_typed_ir_from_progress()`, a composition bridge that
invokes the verified extractor for `malbolge-typed-ir-v1` and immediately reruns
complete typed-IR checkpoint admission. The product `malbolge` CLI now exposes
both `--checkpoint-info PROGRESS.json` and
`--extract-checkpoint STATE_CODEC PROGRESS.json`. Command-line composition
selects the repository-pinned Python 3.14.6 interpreter plus this trusted
inspector and delegates metadata validation or binary-safe extraction without
parsing sidecar JSON in Rust.

Product compiler resume selection/wiring remains
open because no product compilation command yet consumes restored typed IR.

Compiler integration tests now publish real canonical typed-IR generations
through the production Python sidecar writer, inject process death at every
checkpoint/pointer publication boundary relevant when no partial artifact is
present, and resume through the Rust composition bridge plus production
inspector. Before pointer replacement, resume restores the previous committed
generation; after pointer replacement, it restores the new generation. The
fixture deliberately moves from a CPU sidecar to a CUDA sidecar at generation
two, so the same matrix also exercises backend-neutral compiler-state handoff.

Child-process crash fixtures now terminate after temporary bytes are flushed but
before file synchronization for checkpoint, partial, and sidecar writes;
immediately before or after checkpoint/partial atomic publication; after
checkpoint/partial directory durability confirmation but before immutable
temporary cleanup; after a durable checkpoint; immediately before sidecar
publication; after the mutable sidecar temporary file is durable but before
atomic pointer replacement; after replacement but before directory durability
confirmation; and immediately after sidecar directory durability confirmation.

Canonical typed IR now supplies one concrete compiler-state codec,
`malbolge-typed-ir-v1`: validation-gated canonical bytes can be restored through
`canonical_module()` with exact-tag, bounded-length, UTF-8, trailing-byte, full
IR-validation, and byte-for-byte re-encode checks. The typed-IR stage now has
a single `enter_typed_ir_stage()` handoff that accepts either normalized
frontend evidence or canonical checkpoint bytes and returns the same admitted
module type. Compiler composition can now directly consume a progress-sidecar
path through the explicit verified composition bridge; it still does not
publish
that state itself. Generic checkpoint metadata discovery remains available
through the progress inspector.

Product CLI metadata inspection and explicit-codec binary checkpoint extraction
are now wired through the trusted inspector. Product compiler resume
selection/wiring, later compiler-stage codecs, later-stage and final-artifact
crash injection, and later compiler-execution CPU/CUDA resume equivalence remain
unimplemented.

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

A verified inner checkpoint payload can be extracted without trusting the
mutable pointer or outer envelope directly:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  src/automation/repository/composition/scripts/progress_sidecar.py `
  --extract-checkpoint evaluated-search-prefix-evidence-v1 `
  output.malbolge.progress.json > search.resume.json
```

The output bytes are exact and binary-safe. Extraction emits nothing when the
sidecar, referenced generation, outer digest, resume position, state codec,
canonical encoding, or inner payload digest is invalid.

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
- Publication commit and parent-directory durability confirmation are separate.
  A synchronization failure after atomic replacement or immutable publication
  reports the exact committed path and never claims that the prior state was
  restored.
- The final `.malbolge` path is published atomically only after independent
  verification succeeds.
- Resume compatibility binds source identity, target profile, exact repository
  revision, toolchain fingerprint, algorithm version, seed, and checkpoint
  schema.
  Any mismatch is rejected unless an explicit reviewed migration exists.
- Device-local memory is never the only copy of resumable state. GPU jobs emit a
  backend-neutral durable checkpoint sufficient for CPU inspection and exact
  compatibility checks. `malbolge-checkpoint-v1` carries no backend or device
  identity; backend-specific state must be normalized by the owning state codec
  before publication.
- `active_elapsed_ns` is accumulated from monotonic clock segments. UTC wall
  timestamps provide chronology but never replace monotonic duration
  measurement.
- Paused time, checkpoint overhead, verification, serialization, and active
  compute/search time remain distinguishable for scientific analysis. Their
  exclusive nanosecond counters exactly partition `wall_elapsed_ns`.
- The sidecar is evidence and recovery state, not semantic authority. Source,
  target profile, compiler, verifier, and accepted artifact determine meaning.
- Routine progress writes are rate-limited by an explicit positive monotonic
  interval so checkpointing does not become an unmeasured dominant cost. The
  first routine write is eligible immediately; checkpointed and terminal states
  bypass suppression, and only attempts that cross publication commit start a
  new rate window.

## Failure Behavior

On orderly cancellation or a handled failure, the job writes one final sidecar
state and preserves the most recent valid generation. On abrupt process or host
failure, restart follows only the last atomically committed sidecar pointer.
Later unreferenced generation files cannot invalidate that pointer. Missing,
stale, overwritten, or incompatible generation data is rejected with a stable
diagnostic and never guessed into validity.

Sidecar reads, writer-lock lifecycle, and mutable or immutable pre-publication
failures are likewise translated into the stable sidecar error boundary rather
than leaking host filesystem exceptions. Post-commit failures preserve the
committed path through `ProgressSidecarCommittedError`; directory-sync failures
use its `ProgressSidecarDurabilityError` subtype, while later lock cleanup
failures report that the pointer committed durably before cleanup failed.

If checkpoint persistence fails, the job may continue only when the caller
explicitly accepts non-resumable execution. Public CLI defaults fail closed for
jobs that requested resumability.

## Verification

- Schema tests validate every required field, status transition, and unknown-
  total representation.
- Crash fixtures terminate a child process after temporary bytes are flushed but
  before file synchronization for checkpoint, partial, and sidecar writes;
  immediately before or after checkpoint/partial atomic publication; after
  checkpoint/partial directory sync but before immutable temporary cleanup;
  after a durable checkpoint; immediately before sidecar publication; after the
  mutable sidecar temporary file is durable but before atomic pointer
  replacement; after replacement but before directory durability confirmation;
  and immediately after sidecar directory durability confirmation. Restart
  observes the last pointer
  that actually crossed atomic replacement at each boundary.
- Prepublication durability tests inject temporary-file synchronization failure
  for immutable checkpoint and mutable sidecar writes, prove no canonical path
  crosses commit, clean the temporary pathname, and preserve any prior pointer.
- Durability-failure tests inject parent-directory synchronization failure
  after checkpoint, partial, and mutable sidecar publication and retain the
  exact committed path as evidence.
- Resume tests cover unchanged jobs, monotonic transitions, exact repository
  revision and source/profile/toolchain mismatch, overwritten or missing
  generations, durable cancellation/failure/completion publication, and
  rejected terminal-job reopening. Two-process fixtures prove both lock
  exclusion and
  post-lock revalidation: a stale candidate that
  waited behind a newer commit is rejected before mutable-pointer replacement.
- Portable-checkpoint tests prove that identical opaque state produces
  byte-exact checkpoint envelopes for CPU and CUDA sidecars and that identity,
  position, codec, payload, and canonical-encoding drift fail closed.
- Evaluated-search checkpoint tests cover empty and partial prefixes, packed
  candidate storage, exact request/batch drift, malformed/noncanonical JSON,
  mutable aliases, and explicit absence of backend/device identity.
- Resumed-search tests compare interrupted and uninterrupted execution, preserve
  indexed suffix storage, materialize packed suffix evidence safely, reject
  backend/proposal drift, and exercise CPU-to-CUDA plus CUDA-to-CPU rotate and
  crazy-target resume with byte-identical checkpoints and matching proposals.
- Typed-IR compiler tests round-trip canonical and extended semantic modules,
  reject every truncated canonical prefix, unknown tags, wrong magic/version,
  invalid UTF-8, trailing bytes, and semantically invalid restored modules. They
  also prove fresh normalized frontend entry and resumed canonical entry
  converge on the same admitted typed-IR module while preserving failure
  categories. Progress-adapter tests cover exact codec extraction arguments,
  launch/rejection/diagnostic failures, malformed extracted bytes, and
  successful restoration of the tracked canonical typed-IR golden. A
  cross-language crash matrix additionally publishes real typed-IR generations,
  kills publication at ten checkpoint/pointer boundaries, and proves the Rust
  resume bridge restores exactly the last committed generation.
- Prepared-search resume tests cover partial and completed projected prefixes,
  empty rotate prefixes, exact projected-batch binding, uninterrupted prepared
  equivalence, and CPU-produced checkpoint resume through live CUDA.
- Search CLI tests cover CPU resume, unavailable-CUDA fallback, live CUDA
  resume, unsupported-algorithm rejection, checkpoint file loading,
  malformed-state rejection, resumed JSON checkpoint/executor provenance, and
  the sidecar-extraction-to-optimizer subprocess bridge.
- Progress-sidecar recovery tests inject every publication crash boundary using
  real portable checkpoint envelopes and prove that recovery decodes only the
  last sidecar-committed inner state. The same matrix now carries tracked
  canonical `malbolge-typed-ir-v1` modules before and after each crash, proving
  byte-exact non-search compiler-state recovery at the generic sidecar boundary.
  Operator inspection tests also prove verified typed-IR codec/payload-digest
  discovery and fail-closed outer-digest drift. Extraction tests prove exact
  binary stdout, help discovery, and fail-closed state-codec mismatch handling.
- The tracked canonical `malbolge-typed-ir-v1` fixture produces byte-identical
  envelopes under CPU and CUDA sidecar identities, with identical verified
  metadata and byte-exact decoded compiler state. Backend/device identity is not
  part of portable typed-IR checkpoint compatibility.
- Timing tests use an injected monotonic clock, exercise every exclusive
  phase, reject foreign phases, corrupt direct timer state, boolean/negative/
  backward samples, and prove
  active, paused, wall, verification, serialization, and checkpoint durations
  are not conflated.
- Direct-construction tests mutate resume identity and sidecar fields, reject
  boolean sequence aliases and impossible UTC dates, and prove pointer
  publication validates the referenced checkpoint/partial generation first.
- Final `.malbolge` artifact publication remains an open verification item.
  No current compiler backend emits that artifact, so atomic final publication
  and continuous sidecar inspection are not yet claimed as implemented evidence.

## References

<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
- [Compiler Pipeline And Guest Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
- [Parametric Multi Objective Algorithm Evaluation](../../research/adr/parametric-multi-objective-algorithm-evaluation.md)
