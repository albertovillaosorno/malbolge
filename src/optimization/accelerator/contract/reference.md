# Replaceable accelerator boundary

`accelerator/` owns optional execution capacity behind hardware-neutral exact
contracts. Accelerator results never become semantic authority merely because a
GPU produced them.

The first implemented port is `ExactPrimitiveAdapter`, which batches classic
Malbolge `rotate` and `crazy` over the exact 59,049-word domain.
`ClassicStepRequest`/`ClassicStepResult` represents one specification-mode classic
VM transition over at most four explicitly declared memory cells.
`ClassicRunRequest`/`ClassicRunResult` carries one complete 59,049-word classic
state through bounded resident execution. `ProfileRunGeometry` plus
`ProfileRunRequest`/`ProfileRunResult` extends that boundary to validated
single-word-modular ternary profiles without embedding CUDA identity. The current
14-trit/4,782,969-word profile now executes through the same geometry-bound CUDA
kernel model. `accelerator/cpu/` remains the mandatory scalar primitive reference;
CUDA results are checked against normative Rust execution. Compiler and verifier
code do not import CUDA APIs.

Missing accelerator hardware changes availability/performance only. Malformed
requests fail in the shared contract before backend execution; accelerator
runtime failures are explicit and never silently change acceptance rules.
`resource_budget.py` additionally owns hardware-neutral measured resource
snapshots and deterministic resident chunk planning; it does not know CUDA APIs.

Rust product batches now route through hardware-neutral optional backends with
safe-Rust fallback. RTX 4060 current-profile evidence now includes device-side
shared-state replication and persistent scalable sessions. Complete-snapshot
batch 32 reaches about 51.67 VMs/s, while resident batch 128 reaches about
2.00 million 64-step segments/s when setup and snapshots are outside the timed
region. `ProfileMemoryImage` now carries reusable geometry-bound validation proof;
retained batch-32 complete-snapshot throughput reaches about 93.68 VMs/s and
validation/planning falls to about 0.23 ms. Direct complete-snapshot materialization now downloads into final result
arrays without redundant packed host staging. `CudaProfileRunSession.profile_snapshot()`
adds a diagnostic-only decomposition of fresh host-array allocation,
state/memory/output D-to-H, decode, and inclusive total while ordinary `snapshot()`
remains unchanged. Retained RTX 4060 evidence records 3.1616/65.7829/271.1391 ms
for batches 1/8/32. Batch 1 is 96.489% memory transfer; batches 8/32 are about
62--64% fresh arrays and 36--37% memory transfer. Ordinary resident snapshots now always own fresh independent mutable
`array('I')` memories. The explicit
`caller-owned-independent-u32-arrays-v1` workspace allocates those arrays once and
advertises that later calls overwrite earlier aliased results. Retained RTX 4060
batches 1/8/32 improve by 2.586x/2.667x/2.712x with median-derived crossover
1/2/2 snapshots. Batch-one advantage is marginal; repeated batches 8/32 recover
allocation on the second snapshot. Explicit
`bounded-all-or-pageable-u32-arrays-v1` host registration now page-locks all
workspace arrays only within a caller-supplied byte budget. Retained RTX 4060
batches 1/8 improve 1.079x/1.108x with crossover 2/3; a 256 MiB budget forces
batch 32 to `budget-exceeded` pageable fallback. Ordinary snapshots and default
workspaces remain pageable. The explicit `caller-owned-windowed-u32-arrays-v1`
stream workspace now reuses a fixed host-memory window across ordered callbacks.
Retained batch-32 windows 1/8 reduce host memory 96.875%/75.000% and improve
1.023x/1.036x versus the full pageable window. Evidence is retained under
`benchmarks/accelerator/evidence/2026-07-29-current-profile-snapshot-stream-window-tradeoff-rtx4060/`.
Callback-scoped aliases must be copied before the next window when durable ownership
is required. CUDA runtime identity `cuda-ordered-registered-dtoh-stream-v1` now binds
ordered D-to-H submission with default-stream dependencies to same-context registered buffers. Pending
copies retain host registration until `wait()` or teardown, and runtime close drains
streams before unregistering host memory. The explicit
`caller-owned-double-window-overlap-u32-arrays-v1` workspace now retains two equal
registered banks and submits the next D-to-H window while the current callback
validates or consumes its aliases. One-bank budgets and registration disable,
budget, or Driver rejection preserve exact synchronous fallback. Retained evidence
under `benchmarks/accelerator/evidence/2026-07-29-current-profile-snapshot-double-buffer-overlap-rtx4060/` records matched window-1/8
speedups of 1.003x/1.012x with 14/15 and 15/15 paired wins, while retained memory
and setup roughly double. It is therefore opt-in; no kernel overlap or semantic
authority changes. `work_ports.py` now defines hardware-neutral candidate evaluation, search
execution, verification-assist, and trusted-admission boundaries. CPU callback
adapters provide mandatory candidate/search execution capacity while search
proposals and verification hints remain untrusted. `submission.py` adds
`validated-candidate-submission-v1`: an exact candidate batch is bound to one
optional ticket and a deferred CPU reference route. Results remain unpublished
until `wait()` validates capability, evaluator identity, count, and request order.
Pending tickets must close before fallback; malformed tickets and cleanup failure
fail closed. State and actual/fallback route are observable, repeated successful
wait is idempotent, and close-before-wait prevents execution. The contract creates
no hidden threads. CUDA now implements this port for exact classic crazy/rotate
candidates. Runtime identity `cuda-independent-stream-kernel-launch-v1` gives every
one-shot ticket one nonblocking Driver stream, exact parameter/buffer ownership,
stream-specific synchronization, and deterministic destruction. Launch rejection
cleans the new stream; synchronization failure still attempts destruction; runtime
close drains all outstanding ticket streams. Five deterministic tests cover both
stable launch identities, distinct handles, selected-stream wait, launch cleanup,
and synchronization-failure cleanup. Seven live RTX 4060 routes cover rotate,
crazy, empty/idempotent, close-before-wait, adapter-teardown fallback, and reverse
waiting of two tickets; that route passes 50/50 stress. Existing synchronous
primitive calls retain `cuda-default-stream-kernel-launch-v1`. Retained evidence
under `benchmarks/accelerator/evidence/2026-07-29-independent-ticket-stream-throughput-rtx4060/` records sequential/grouped medians for groups 2/4/8 of
2.1745/1.5970, 3.6403/3.0304, and 7.5313/5.6971 ms, improvements of
1.362x/1.201x/1.322x with 15/15 paired wins each. The opt-in
`cuda-independent-stream-kernel-timeline-v1` path adds a synchronized origin and
start/end events around each exact launch while ordinary tickets remain event-free.
Three deterministic timeline tests cover ordering, active lifetime, overlap, and
failure cleanup; one live test preserves exact output. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-29-independent-ticket-event-timeline-rtx4060/` uses the same workload SHA: groups 2/4/8 overlap in 2/15, 8/15, and
15/15 samples, with median overlap 0/0.006144/0.015360 ms, concurrency
1.000x/1.072x/1.091x, and maximum peaks 2/3/5. This is positive origin-relative
event-interval attribution, not pure kernel duration, SM occupancy, or
kernel-transfer overlap.
Opt-in `cuda-independent-stream-ticket-transfer-v1` now registers exact
input/output host buffers and enqueues H-to-D, kernel, and D-to-H work on the
ticket's same nonblocking stream. Five deterministic runtime tests cover
ordering, leases, and partial-failure cleanup; four live candidate routes cover
no synchronous-copy use, crazy exactness, reverse waiting, and teardown
fallback. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-29-independent-ticket-transfer-throughput-rtx4060/`
records 210 chronological samples over 14 routes. The group-eight hypothesis
fails: streamed grouped is 12.0138 ms versus 5.9408 ms synchronous grouped, a
0.494x ratio and 0/15 paired wins, despite improving 1.118x over streamed
sequential with 14/15 wins. Synchronous copies therefore remain the default and
streaming remains an exact explicit experiment. Wall time alone does not
attribute physical transfer/kernel overlap.
Opt-in `cuda-independent-stream-ticket-transfer-timeline-v1` now records four
contiguous CUDA events around upload, exact kernel, and download on each
streamed ticket. Three deterministic tests cover phase order, active lifetime,
and failed-kernel cleanup; one live RTX 4060 test preserves CPU-equal output and
monotonic phases. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-29-independent-ticket-transfer-event-timeline-rtx4060/`
contains 45 grouped observations and 210 ticket phase rows. Groups 2/4/8 record
0.000000 ms median transfer/kernel overlap and 0/15 significant samples each, so
the group-eight hypothesis fails. Group-eight upload/kernel/download sums are
0.956352/0.340768/0.588512 ms versus 12.9495 ms wall time; only about 14.6% of
the instrumented wall interval is represented by those summed device phases.
This closes phase attribution for the retained workload, not a universal claim
that CUDA hardware can never overlap transfers and kernels.
Hardware-neutral `evidence-bound-ticket-route-admission-v1` now gives ticket
grouping an explicit evidence gate. It validates exact backend, device, and
workload identity plus exact output, lower candidate median, and a strict
paired-win majority; malformed or duplicate route records fail closed. Plans
preserve input order, minimize chunk count, then measured median cost, and
prefer synchronous ties. Opt-in
`evidence-bound-ticket-route-admission-report-v1` publishes one immutable
assessment per retained route in input order. It distinguishes context
mismatch, inexact results, no median improvement, no paired majority, and a
group larger than the pending queue. Eligible but unused routes remain visible
with zero selected counts; the report also records selected chunks/tickets,
fallback tickets, synchronous/streamed totals, and the unchanged plan. It reads
no additional evidence, performs no online learning, and changes no default.
`bounded-ticket-admission-telemetry-v1` retains completed reports in a
caller-owned positive-capacity FIFO.
`bounded-ticket-admission-failure-telemetry-v1` independently retains failed
accelerator attempts as unavailable, invalid-input, execution, or other stable
categories without exception text. Both immutable snapshots expose monotonic
sequence IDs, eviction counts, measured/estimated duration delta, and exact
selected-route usage. Malformed reports, timings, or foreign failures fail
before mutation. `TicketAdmissionAttemptTelemetry` pairs the two FIFOs, and a
separate retained CUDA attempt executor records exactly one outcome before
returning or re-raising the same accelerator error. The ordinary and existing
completion-only executors remain unchanged.
`ticket-admission-telemetry-document-v1` captures both snapshots as compact,
sorted-key schema-v1 JSON. Decoding defaults to a 1 MiB byte limit and 4,096
observations per FIFO, rejects duplicate, unknown, oversized, and noncanonical
input, and restores exact sequence and eviction state. File reads and writes are
explicit; writes use a same-directory temporary file and atomic replacement.
`caller-owned-ticket-admission-telemetry-store-v1` defines an explicit
put/get/remove/snapshot port and a bounded caller-owned memory adapter.
Defaults are 4,096 unique documents, 4,096 observations per FIFO, and 16 MiB
of exact schema-v1 canonical bytes. Fingerprints
reuse `ticket-admission-telemetry-document-v1:sha256:<hex>`; duplicate puts are
idempotent, limits cannot be widened after construction, snapshots are ordered by
fingerprint, and removal releases exact document and byte budgets. Invalid
fingerprints/documents, budget overflow, collisions, or retained decode failure fail
closed without partial mutation. The memory adapter performs no filesystem I/O,
automatic loading, summaries, merging, recommendations, or admission changes.
`ticket-admission-telemetry-schema-migration-v1` publishes a fixed lossless
1-to-1, 1-to-2, 2-to-1, and 2-to-2 compatibility matrix. Schema-v2 is canonical
sorted JSON containing the exact canonical schema-v1 bytes as standard Base64,
plus the required schema-v1 document identity and SHA-256 fingerprint. Versioned
decoding defaults to 2 MiB outer bytes, 1 MiB embedded source bytes, and 4,096
observations per FIFO. Upgrade and downgrade are explicit; schema-v1 bytes remain
unchanged. There is no automatic migration, file loading, snapshot
reinterpretation, merge, recommendation, lineage inference, or policy change.
`offline-ticket-admission-telemetry-summary-v1` validates one explicit document
and groups retained observations by exact backend, device, workload, and ticket
count. It publishes completed/failed integer totals, estimate-comparison counts,
retention ranges, stable failure categories, and sorted selected-evidence
appearances.
`offline-ticket-admission-telemetry-collection-v1` defaults to explicit
4,096-document and 16 MiB canonical-input bounds. It fingerprints canonical bytes
as `ticket-admission-telemetry-document-v1:sha256:<hex>`, counts byte-identical
occurrences once, publishes input/unique/duplicate byte counts, and orders unique
entries by fingerprint. Different snapshots remain separate even when their
contexts or sequence ranges overlap; digest collisions fail closed.
`offline-ticket-admission-telemetry-overlap-v1` compares two validated documents
in fingerprint order. For completed and failed FIFOs it publishes capacities,
retained half-open sequence ranges, exact overlap ranges, matching counts, and
conflicting sequence IDs, with explicit empty and no-overlap classifications. An
exact document match is separate from matching retained observations.
`offline-ticket-admission-telemetry-overlap-index-v1` deduplicates one bounded
collection before comparing every unique pair. It defaults to a 65,536-pair
budget, fails before pairwise work when that budget is exceeded, orders reports by
fingerprint, and publishes completed/failed counts for all four overlap classes.
Exact duplicates remain collection occurrences and never create pairs.
`offline-ticket-admission-telemetry-overlap-components-v1` selects an undirected
edge only when completed and failed FIFOs contain at least one exact matching
observation in total and neither FIFO has a conflicting sequence ID. It retains
isolated unique documents, fingerprints each component, and publishes member,
direct, possible, and missing edge counts plus a clique flag. A bridged component
may contain member pairs with no direct edge, so connectivity is neither pairwise
equivalence nor recorder lineage. Component fingerprint collisions fail closed.
`authenticated-ticket-admission-telemetry-lineage-v1` separately binds one exact
document fingerprint to caller-supplied recorder, completed/failed stream, capture
sequence, key, and optional immediate-predecessor identities. Canonical
HMAC-SHA-256 uses at least 32 caller-owned secret bytes; the secret is never stored.
Verification requires an explicit trusted key identity and secret. Same-sequence
forks, adjacent predecessor mismatch, nonadjacent direct links, MAC mismatch, and
fingerprint collisions fail closed. Different recorder or stream identities remain
separate lineages; ordered gaps are common lineage without a direct link. The
caller owns key legitimacy.
`caller-owned-ticket-admission-telemetry-lineage-trust-v1` builds an explicit
in-memory set of at most 256 unique HMAC keys, sorted by `key_id`. Each key has an
inclusive first/optional-last capture sequence window; empty sets trust nothing.
Verification selects the exact key identity and window, and independently verified
items may be compared across a rotation. Duplicate identities, malformed windows,
unknown keys, out-of-window captures, and incorrect secrets fail closed. Secret
fields are hidden from representations.
`ticket-admission-telemetry-lineage-trust-manifest-v1` canonically persists only
`key_id`, an opaque `key_reference_id`, and inclusive capture windows. It defaults
to 256 entries and 64 KiB, orders entries by key identity, fingerprints canonical
bytes, and supports only explicit bounded reads and atomic replacement. Resolution
requires exact caller-supplied key/reference coverage and produces manifest-bound
in-memory trust. A resolved secret is not certified until an attestation verifies.
Duplicate keys/references, malformed or noncanonical JSON, incomplete or excessive
coverage, reference mismatch, and storage failures fail closed. Secrets never enter
manifest bytes.
`explicit-ticket-admission-telemetry-lineage-secret-provider-v1` accepts one
caller-supplied synchronous provider. Manifest validation and a default 256-request
budget complete before the first call. Immutable requests follow canonical key
order and carry manifest/provider identity, key/reference identity, capture window,
and request index. Providers return only typed `resolved`, `unavailable`, or
`failed` results; non-success stops without retry, and each entry is called exactly
once. Repeated explicit resolutions call the provider again. Secret bytes remain
hidden, and resolution still does not authenticate them before attestation use.
`bounded-in-memory-ticket-admission-telemetry-lineage-secret-provider-v1`
implements one reusable bounded caller-owned synchronous provider over explicit
immutable secret entries. Each hidden key is bound to one canonical manifest
fingerprint, key reference, key identity, and inclusive capture window. The service
permits 256 entries by default and 4096 at the supported maximum, sorts entries by
manifest fingerprint and reference, and rejects duplicate manifest/reference
bindings. Construction and every call revalidate the exact service type and
identity, provider identity, configured limit, secret count, entry tuple, canonical
ordering, shared 32-to-4096-byte key rules, request metadata, and each hidden key. A
different provider identity returns typed `failed`; an unknown manifest/reference
returns `unavailable`; a known binding with conflicting key/window metadata returns
`failed`; and an exact binding returns `resolved` with unchanged hidden bytes.
Request index remains ordering context rather than a secret binding. Repeated calls
validate and resolve again without mutation or an external cache. The service reads
no environment, file, network, process credential state, secret store, or hosted API
and performs no discovery, refresh, retry, persistence, logging, worker creation,
certificate rule, PKI operation, algorithm choice, or admission-policy operation.
`explicit-async-ticket-admission-telemetry-lineage-secret-provider-v1`
defines one caller-driven sequential async port over the same manifest-bound
requests and typed outcomes. The synchronous port exposes one immutable nonsecret
preflight, exact request/result validators, one result materializer, and one final
trust materializer; both routes share those contracts. Manifest validation,
provider identity, and the request budget complete before the first `await`. The
provider is awaited once per entry in canonical order and never concurrently.
Cancellation propagates directly; ordinary provider exceptions become stable errors
without vendor text; typed non-success stops the walk without retry. Repeated
explicit resolutions await again. The port creates no event loop, task, thread,
executor, worker, cache, lifecycle, discovery, refresh, persistence, secret-store
access, certificate rule, PKI operation, algorithm choice, or policy operation.
`bounded-in-memory-async-ticket-admission-telemetry-lineage-secret-provider-v1`
adapts one exact bounded memory secret provider to that async port. Construction and
every call revalidate the adapter identity, hidden wrapped service, provider
identity, secret count, and entry limit. Each await delegates exactly once to the
synchronous memory lookup and completes inline without an internal suspension or
hidden task. Repeated calls reuse only explicit immutable caller-owned memory and
validate it again. The adapter reads no environment, file, network, process
credential state, external secret store, or hosted API and adds no retry, cache,
refresh, persistence, logging, worker, certificate, PKI, algorithm, or policy.
`explicit-file-ticket-admission-telemetry-lineage-secret-provider-v1`
implements one bounded read-only provider over caller-supplied absolute raw-secret
paths. Every hidden path is bound to an exact manifest fingerprint, key reference,
key identity, and capture window. Construction and validation perform no file I/O.
A provider mismatch returns typed `failed`; an unknown manifest/reference returns
`unavailable`; conflicting key/window metadata returns `failed`; all three outcomes
occur before any open. An exact match opens the selected path once and reads at most
`max_secret_bytes + 1` bytes. A missing file returns `unavailable`; other read
errors, oversized files, and bytes outside the shared 32-to-4096-byte key contract
return `failed` without operating-system text. Exact raw bytes, including trailing
newlines, are preserved. Repeated calls reopen and reread the file, so rotation is
caller-controlled and no secret cache exists. The provider does not discover paths,
write files, scan directories, inspect ownership or permissions, validate symlinks,
decrypt values, create workers, retry, persist, log paths or secrets, choose
algorithms, or change admission policy.
`offloaded-async-file-ticket-admission-telemetry-lineage-secret-provider-v1`
adapts one exact explicit file provider through a caller-supplied async offloader.
Construction and every call revalidate the adapter identity, hidden wrapped
provider, copied provider identity, secret count, entry and byte limits, and
callable offloader. Each request is fully validated before the first await; a
provider-identity mismatch returns typed `failed` without awaiting. An exact
request awaits the offloader once with the same immutable provider and request.
The caller alone chooses whether that await completes inline, uses a thread or
executor, or suspends by another mechanism. Cancellation propagates directly;
ordinary offloader exceptions become stable adapter errors without vendor text.
Returned results reuse the shared exact type and enum validation; nonresolved
results cannot carry secret bytes, while resolved bytes must use the exact bytes
type and remain within the wrapped provider's 32-to-4096-byte bound. Repeated
calls offload and reread again. The adapter creates no event loop, task, thread,
executor, worker, path discovery, retry, cache, persistence, environment access,
external-store integration, secret logging, algorithm choice, or policy action.
`caller-owned-ticket-admission-telemetry-lineage-signature-v1` defines
algorithm-neutral synchronous detached signer and verifier ports. Canonical
attestations bind the exact schema-v1 document fingerprint, algorithm, recorder,
completed/failed streams, capture sequence, public-key ID, SHA-256 of the exact
caller-owned public-key bytes, and optional HMAC or signature predecessor. Signers
return typed `signed`, `unavailable`, or `failed`; verifiers return `verified`,
`invalid`, `unavailable`, or `failed`. Each explicit operation calls its port once
without retry or cache. Verification checks the exact public-key fingerprint before
the port call, then reuses the common verified-lineage comparison for public-key
rotation and an explicit HMAC-to-signature transition. No concrete signature
algorithm, key generation, private-key storage, certificate chain, PKI, trust
discovery, provider lifecycle, or security claim is supplied by this boundary.
`caller-owned-ticket-admission-telemetry-lineage-signature-trust-v1` builds
an explicit in-memory set of at most 256 unique `(algorithm_id, public_key_id)`
pairs sorted by that composite identity. Each entry binds exact public-key bytes,
their required SHA-256 fingerprint, and an inclusive first/optional-last capture
window. Empty sets trust nothing. Verification selects the exact algorithm, key
identity, fingerprint, and capture window before calling the verifier; independently
verified items preserve same-key, public-key rotation, algorithm rotation, ordered
gap, and fork checks. Duplicate identities, malformed windows, invalid key bytes,
fingerprint mismatch, unknown identities, out-of-window captures, and tampered
trust metadata fail closed. Public-key bytes are hidden from representations. No
manifest, provider, certificate, PKI, trust discovery, algorithm selection, or
policy authority is supplied.
`ticket-admission-telemetry-lineage-signature-trust-manifest-v1` persists
algorithm identity, public-key identity, one opaque public-key reference, the
required exact public-key fingerprint, and inclusive capture windows as canonical
key-free JSON. It defaults to 256 entries and 64 KiB, sorts by composite identity,
requires globally unique references, publishes a stable SHA-256 fingerprint, and
supports only explicit bounded reads or atomic replacement. Resolution requires
exact caller-supplied algorithm/key/reference coverage and exact public-key bytes
matching the persisted fingerprint before building manifest-bound in-memory
signature trust. The same public-key ID may exist under distinct algorithms.
Duplicate identities or references, malformed or noncanonical JSON, incomplete or
excessive coverage, reference or fingerprint mismatch, and storage failures fail
closed. No public-key bytes, provider, certificate, PKI, trust discovery, algorithm
selection, or policy authority are supplied.
`explicit-ticket-admission-telemetry-lineage-public-key-provider-v1` accepts one
caller-supplied synchronous provider. It validates the signature trust manifest and
a default 256-request budget before the first call, then emits immutable requests
in canonical `(algorithm_id, public_key_id)` order. Each request carries only the
manifest/provider identities, algorithm/key/reference identities, required exact
public-key fingerprint, capture window, and request index. Providers return typed
`resolved`, `unavailable`, or `failed` results. Each entry is called exactly once;
non-success stops without retry, while repeated explicit resolution performs a
fresh provider walk. Resolved bytes are hidden from representations and must match
the manifest fingerprint before in-memory signature trust is constructed. No
provider discovery, built-in key service, retry, cache, persistence, hidden worker,
certificate validation, PKI, algorithm selection, or policy authority is supplied.
`explicit-async-ticket-admission-telemetry-lineage-public-key-provider-v1`
accepts one caller-supplied async provider and reuses the synchronous request,
result, and resolved-trust contracts. The caller owns and starts the coroutine and
event loop. Manifest, provider identity, and the default 256-request budget are
validated before the first provider await. Requests are awaited sequentially in
canonical `(algorithm_id, public_key_id)` order, with no task creation or hidden
parallelism; each entry is awaited exactly once and repeated explicit resolution
performs a fresh walk. Typed non-success stops without retry. Ordinary provider
exceptions become stable boundary errors without vendor text, while cancellation
propagates to the caller. Exact public-key fingerprints are checked before trust
construction. This sequential port creates no event loop, task, provider session,
concurrency policy, discovery, retry, cache, persistence, certificate validation,
PKI, algorithm selection, or admission authority.
`explicit-async-batch-ticket-admission-telemetry-lineage-public-key-provider-v1`
accepts one caller-supplied async batch provider. Manifest, provider identity, and
the default 256-request budget are validated before the first await. Empty manifests
make no provider call; nonempty manifests produce one immutable batch containing the
full canonical `(algorithm_id, public_key_id)` request tuple and exactly one provider
await. The provider owns all scheduling and may resolve the batch sequentially or
concurrently. The boundary requires one exact positional result tuple with matching
cardinality, validates every shared typed item result, propagates cancellation, and
converts ordinary provider exceptions to stable errors without vendor text. Reversed,
missing, excessive, foreign, nonresolved-with-bytes, or fingerprint-mismatched results
fail closed before trust is returned. This batch port creates no event loop, task,
concurrency implementation, provider session, discovery, retry, cache, persistence,
certificate validation, PKI, algorithm selection, or admission authority.
`explicit-async-session-ticket-admission-telemetry-lineage-public-key-provider-v1`
accepts one caller-supplied async lifecycle port around the batch provider. Manifest,
provider identity, and the default 256-request budget are validated before opening.
Empty manifests perform no lifecycle calls. Nonempty manifests call `open` exactly
once with immutable manifest fingerprint, provider identity, and request count;
typed outcomes are `opened`, `unavailable`, or `failed`, and only `opened` may carry
a hidden callable batch provider. The existing canonical batch boundary then runs
once. Every opened session receives exactly one `close` request with a stable
`completed`, `failed`, or `cancelled` reason; close outcomes are `closed` or
`failed`. Opening exceptions become stable errors without vendor text and opening
cancellation propagates without closing. After opening, failure or cancellation
attempts one close. Cancellation propagates only after successful close; close
failure replaces the preceding outcome and fails closed. No built-in service,
event loop, task, discovery, retry, cache, persistence, certificate validation,
PKI, algorithm selection, or admission authority is supplied.
`bounded-in-memory-ticket-admission-telemetry-lineage-public-key-provider-v1`
implements the synchronous provider port with one caller-owned immutable key tuple.
Construction accepts at most 256 entries, validates canonical provider, algorithm,
key, and reference identities, validates inclusive capture windows, recomputes every
exact public-key SHA-256 fingerprint, rejects duplicate composite identities and
references, and sorts entries by reference identity. Key bytes are hidden from
representations. Every explicit lookup revalidates service identity, count, tuple,
ordering, metadata, and exact key bytes. An absent reference returns typed
`unavailable`; a known reference with different algorithm, key, fingerprint, or
window returns typed `failed`; only an exact request returns `resolved`. Empty
services are valid and resolve nothing. The object is reusable caller-owned memory,
not an automatic or hidden cache. It performs no file, environment, network,
discovery, mutation, retry, persistence, async adaptation, certificate validation,
PKI, algorithm selection, or admission-policy operation.
`bounded-in-memory-async-ticket-admission-telemetry-lineage-public-key-provider-v1`
adapts one exact bounded memory service to the sequential async provider port.
Construction validates the complete wrapped service and retains only its provider
identity, key count, stable adapter identity, and a hidden service reference. Every
await revalidates the adapter binding and the complete memory service before invoking
the synchronous lookup inline. It returns the same typed `resolved`, `unavailable`,
or `failed` outcome and introduces no internal suspension point; the caller-owned
event loop cannot run another task merely because this adapter was awaited. The
existing sequential async boundary still performs manifest preflight, canonical
ordering, fingerprint checks, stable exception wrapping, and trust construction.
Empty manifests perform no lookup, while explicit adapter construction already
validates the service. The adapter creates no event loop, task, sleep, artificial
yield, batch/session lifecycle, file, environment, network, discovery, retry,
persistence, certificate validation, PKI, algorithm selection, or policy operation.
`bounded-memory-async-batch-ticket-admission-telemetry-lineage-public-key-provider-v1`
adapts one exact bounded memory service to the caller-controlled async batch port.
Construction validates the complete wrapped service and a positive request limit of
at most the caller-selected boundary, defaulting to 256. Every await revalidates the
adapter binding and complete memory service, then validates the exact batch request,
nonempty manifest/provider identities, immutable request tuple, configured count,
positional indices, and every item manifest/provider binding. Requests are resolved
inline in tuple order through the synchronous memory service and returned as one
hidden positional result tuple, preserving typed `resolved`, `unavailable`, and
`failed` outcomes. Direct empty batches are valid. The existing batch trust boundary
still performs manifest preflight, one nonempty provider await, exact cardinality and
fingerprint checks, and trust construction; empty manifests make no provider call.
The adapter creates no event loop, task, concurrency, sleep, artificial yield,
session lifecycle, file, environment, network, discovery, retry, persistence,
certificate validation, PKI, algorithm selection, or policy operation.
`memory-async-session-ticket-admission-telemetry-lineage-public-key-provider-v1`
adapts one exact bounded memory service to the explicit async provider-session port.
Construction validates the memory service, builds its bounded inline batch adapter,
and stores only caller-owned serial lifecycle state. `open` and `close` complete
inline without scheduling. One active lifecycle is allowed: an exact nonempty open
request with matching provider identity and bounded request count returns `opened`
with the hidden memory batch adapter; a second or mismatched open returns `failed`
without replacing active state. Close requests require the exact persisted manifest
fingerprint, provider identity, and request count. A mismatch returns `failed` and
retains active state; an exact close returns `closed`, clears the active request,
increments a nonnegative completed-lifecycle count, and permits serial reuse. The
existing session boundary still preflights manifests and budgets, performs no
lifecycle calls for empty manifests, and closes after success or batch failure. The
adapter creates no event loop, task, lock, concurrency, sleep, artificial yield,
file, environment, network, discovery, retry, persistence, certificate validation,
PKI, algorithm selection, or policy operation.
`ticket-admission-telemetry-lineage-public-key-bundle-v1` persists one explicit
bounded public-key service as canonical compact UTF-8 JSON. Unlike the key-free
trust manifest, this separate document intentionally contains public-key bytes as
lowercase hexadecimal. Construction reuses the memory provider to validate exact
bytes, fingerprints, identities, windows, uniqueness, cardinality, and reference
ordering. Encoding uses sorted keys and one trailing newline; decoding requires byte
identity with that canonical encoding, rejects duplicate or unknown JSON keys, and
is bounded by 256 entries and 1 MiB by default. Explicit writes atomically replace
one caller-selected path. Explicit reads consume at most the configured byte limit.
Each explicit load rereads the path, fingerprints canonical bytes, and builds a new
caller-owned memory provider with hidden key material and stable non-key metadata.
There is no path discovery, automatic loading, watch, retained cache, retry, network
fetch, session creation, certificate validation, PKI, algorithm selection, or policy
operation.
`explicit-ticket-admission-telemetry-lineage-public-key-bundle-fetcher-v1`
defines one synchronous transport-neutral fetch boundary. The caller constructs an
exact immutable request binding source identity, resource identity, provider
identity, expected bundle fingerprint, byte limit, and entry limit. All request
metadata and limits are validated before the first transport call. Each invocation
makes exactly one caller-supplied fetcher call and accepts only the exact typed
`fetched`, `unavailable`, or `failed` result enum. Nonfetched results cannot carry
bytes. A fetched result requires exact nonempty bytes within the requested limit,
canonical bundle decoding, a newly materialized caller-owned memory provider, and
exact matches for the expected bundle fingerprint and provider identity. Repeated
explicit invocations call the transport again and retain no cache. The boundary
implements no HTTP, TLS, endpoint discovery, credential handling, redirect, retry,
watch, persistence, certificate validation, PKI, algorithm selection, or policy
operation.
`explicit-async-ticket-admission-telemetry-lineage-public-key-bundle-fetcher-v1`
defines the caller-driven async form of the same transport-neutral boundary. The
caller owns the coroutine and event loop. The exact shared request is completely
validated before the first await, and each invocation awaits the supplied fetcher
exactly once. The shared typed result, bounded canonical decode, fingerprint and
provider bindings, and caller-owned memory-provider materialization remain the
single synchronous source of validation truth. Ordinary fetcher exceptions become
stable async-boundary errors without vendor text, while cancellation propagates
directly. Repeated explicit invocations await the transport again and retain no
cache. The boundary creates no event loop, task, worker, concurrency policy,
endpoint discovery, credential handling, redirect, retry, watch, persistence,
certificate validation, PKI, algorithm selection, or policy operation.
`explicit-https-ticket-admission-telemetry-lineage-public-key-bundle-fetcher-v1`
implements one concrete synchronous stdlib HTTPS GET transport. Its exact immutable
config binds a canonical lowercase ASCII host, TCP port, origin-form target,
source/resource identities, a positive finite timeout capped at 300 seconds, and a
caller-owned `SSLContext`. Build and every use require hostname checking,
`CERT_REQUIRED`, and TLS 1.2 or newer; the module never creates or loads trust roots.
Each invocation revalidates the config and shared fetch request, requires exact
source/resource matches, opens one new `HTTPSConnection` with the same caller
context, sends only `GET` with JSON/identity/close headers and no credentials, and
closes once. Status 200 may return `fetched`; 404 and 410 return `unavailable`; all
other statuses, including redirects, return `failed`. Successful responses require
JSON content type with optional UTF-8 charset, absent or identity content encoding,
an optional canonical positive content length within the request limit, and an exact
nonempty bytes body read with a `max_bytes + 1` bound. Connection, request, response,
body-read, or close failures return typed `failed` without vendor text. There is no
plaintext HTTP, endpoint discovery, credential handling, redirect following, retry,
watch, cache, persistence, hosted-service API, certificate/PKI ownership, algorithm
selection, or policy operation.
`offloaded-async-https-ticket-admission-lineage-public-key-bundle-fetcher-v1`
adapts the exact synchronous HTTPS fetcher to the shared async port through one
caller-supplied offloader. Construction and every call fully revalidate the wrapped
HTTPS fetcher, stable adapter identity, copied fetcher/source/resource bindings, and
callable offloader. The shared request is validated before the first await; a
source/resource mismatch returns typed `failed` without calling the offloader. A
matched request awaits the offloader exactly once with the same exact fetcher and
request. The caller alone decides whether that await runs inline, in a thread,
through an executor, or through another scheduling mechanism. Cancellation
propagates directly. Ordinary offloader exceptions become stable adapter errors
without vendor text. Returned results are revalidated for exact type, enum, payload
presence, exact bytes, nonempty content, and the request byte limit before they reach
the outer async materialization boundary. Repeated calls revalidate and offload
again. The adapter creates no event loop, task, thread, executor, worker, retry,
redirect, cache, trust root, credential, hosted-service policy, algorithm choice, or
admission-policy operation.
`explicit-ticket-admission-lineage-https-authorization-provider-v1`
defines one synchronous caller-owned port for resolving an opaque HTTPS
`Authorization` value. Preflight validates the exact HTTPS fetcher, exact canonical
bundle-fetch request, source/resource binding, canonical authorization-provider
identity, callable provider, and positive byte limit before the provider is called.
The default limit is 4096 ASCII bytes and the supported maximum is 16384. One
immutable request carries only the bundle fingerprint and nonsecret provider,
resource, and source identities. Each successful preflight makes exactly one
provider call. Stable `resolved`, `unavailable`, and `failed` outcomes carry no
vendor text; nonresolved outcomes cannot carry credential text. A resolved value
must be exact nonempty ASCII field text containing only spaces and visible
characters, with no edge spaces and no normalization. The value is hidden from
representations and returned only in caller-owned state with its exact byte count
and the fixed `Authorization` header name. Repeated explicit resolutions call the
provider again. The port does not choose an authorization scheme, inject a header,
open a connection, discover credentials, retry, cache, persist, log values, create
workers, own a hosted-service API, validate certificates, distribute PKI, select a
signature algorithm, or change admission policy.
`explicit-async-ticket-admission-lineage-https-authorization-provider-v1`
defines one caller-driven async port for resolving the same bounded opaque HTTPS
`Authorization` value. The synchronous port now exposes one immutable nonsecret
preflight plus one exact result materializer, and both sync and async resolution use
those same validators. Preflight validates the exact HTTPS fetcher, canonical bundle
request, source/resource binding, authorization-provider identity, and positive byte
limit before the first `await`; a noncallable provider also fails before awaiting.
One successful preflight awaits the caller-supplied provider exactly once with the
same exact immutable request. The provider controls whether that await suspends.
Cancellation propagates directly. Ordinary provider exceptions become stable async
errors without vendor text. The shared materializer enforces exact result type and
enum, forbids credential text in nonresolved outcomes, requires bounded nonempty
ASCII field text for `resolved`, and returns the same hidden caller-owned metadata as
the synchronous path. Repeated explicit resolutions await again with no cache or
refresh. The port creates no event loop, task, thread, executor, worker, retry,
discovery, refresh, header injection, hosted-service policy, certificate rule, PKI
operation, algorithm choice, or admission-policy operation.
`memory-ticket-admission-lineage-https-authorization-provider-v1`
implements one reusable bounded caller-owned synchronous Authorization provider over
explicit immutable in-memory entries. Each entry binds one hidden Authorization
value and exact byte count to one canonical bundle fingerprint, fetch-provider
identity, resource identity, and source identity. One service binds all entries to
one authorization-provider identity, permits at most 64 entries by default and 4096
at the supported maximum, requires canonical deterministic ordering, and rejects
duplicate request bindings. Construction and every call revalidate the exact service
type and identity, provider identity, limits, entry tuple, shared request metadata,
shared Authorization text rules, byte counts, ordering, and uniqueness. A request
with a different authorization-provider identity returns typed `failed`; a valid
unmatched request returns `unavailable`; an exact match returns `resolved` with the
unchanged hidden caller-owned value. Repeated calls perform the same validation and
lookup without mutation or an external cache. The provider reads no environment,
file, network, process credential state, secret store, or hosted API and performs no
discovery, refresh, retry, persistence, logging, task creation, certificate rule,
PKI operation, algorithm choice, or admission-policy operation.
`offloaded-async-file-ticket-admission-lineage-https-authorization-provider-v1`
adapts one exact explicit file Authorization provider to the shared async port
through one caller-supplied offloader. Construction and every call revalidate the
adapter identity, hidden wrapped provider, copied authorization count, entry and
byte limits, provider identity, and callable offloader. The shared request is
validated before the first `await`; a provider-identity mismatch returns typed
`failed` without invoking the offloader. A matched provider identity awaits the
offloader exactly once with the same exact provider and immutable request. The
caller alone chooses whether the file read completes inline, suspends, or runs in
a caller-owned thread or executor. Cancellation propagates directly. Ordinary
offloader exceptions become stable adapter errors without path or vendor text.
Returned results are revalidated after the await, including exact result type and
enum, nonresolved payload absence, canonical ASCII text, and the wrapped provider
byte limit for resolved values. Repeated calls offload and reread the file so
rotation and removal remain visible without a cache. The adapter creates no event
loop, task, thread, executor, worker, discovery, retry, refresh, persistence,
logging, scheme selection, certificate rule, PKI operation, algorithm choice, or
admission-policy operation.
`explicit-file-ticket-admission-lineage-https-authorization-provider-v1`
binds exact nonsecret Authorization requests to caller-selected absolute file
paths. Paths and entries stay hidden from representations. Build and validation
perform no file I/O; every call revalidates the exact service, provider identity,
copied authorization count, entry and byte limits, canonical ordering, request
metadata, and absolute paths before lookup. A provider-identity mismatch returns
typed `failed` without I/O, while an unmatched request returns `unavailable`.
One exact match opens one path once in binary mode and reads at most the configured
byte limit plus one. Missing files return `unavailable`; operating-system errors,
oversized content, non-ASCII bytes, empty or noncanonical text, whitespace, control
bytes, and NUL return `failed` without path or system text. Valid ASCII text is
revalidated through the shared Authorization materializer without trimming or
normalization. Repeated calls reread the file so rotation and removal remain
visible without a cache. The provider performs no discovery, writes, permission
inspection, retries, persistence, logging, worker creation, scheme selection,
credential refresh, certificate validation, PKI, algorithm choice, or policy.
`explicit-environment-ticket-admission-lineage-https-authorization-provider-v1`
implements one bounded synchronous Authorization provider over explicit immutable
request-to-variable bindings. Each entry hides one canonical uppercase ASCII
environment name and binds it to one exact bundle fingerprint, fetch-provider
identity, resource identity, and source identity. One service binds all entries to
one authorization-provider identity, permits at most 64 entries by default and 4096
at the supported maximum, limits resolved values to 4096 bytes by default and 16384
at the supported maximum, canonicalizes ordering, and rejects duplicate request
bindings. Construction and validation read no environment state. A provider-identity
mismatch returns typed `failed`; a valid unmatched request returns `unavailable`;
only an exact match performs one lookup of the caller-named variable. A missing
variable returns `unavailable`; an operating-system or Unicode lookup failure, an
invalid nonempty-ASCII Authorization value, or an oversized value returns `failed`
without variable names, values, or operating-system text. An exact valid value
returns `resolved` unchanged. Repeated calls reread the environment, so caller-owned
rotation and removal are visible without a cache. The provider never enumerates or
mutates environment state, discovers names, reads files, network, external stores,
or hosted APIs, retries, persists, logs names or values, creates workers, chooses an
Authorization scheme, refreshes credentials, validates certificates, distributes
PKI, selects algorithms, or changes admission policy.
`offloaded-async-environment-ticket-admission-lineage-https-authorization-provider-v1`
adapts one exact explicit environment Authorization provider to the shared async
port through one caller-supplied offloader. Construction and every call fully
revalidate the adapter identity, hidden wrapped provider, copied binding count,
entry and byte limits, provider identity, and callable offloader. The shared
request is validated before the first `await`; a provider-identity mismatch
returns typed `failed` without invoking the offloader. A matched request awaits
the offloader exactly once with the same exact provider and immutable request.
The caller alone chooses whether the environment read completes inline, runs in
a thread or executor, or suspends by another mechanism. Cancellation propagates
directly. Ordinary offloader exceptions become stable adapter errors without
vendor text. Returned typed results are revalidated after the await, including
exact enum and type, nonresolved payload absence, and bounded canonical ASCII
text for resolved values. Repeated calls offload and reread the environment, so
rotation and removal remain visible without a cache. The adapter creates no event
loop, task, thread, executor, worker, discovery, refresh, retry, persistence,
logging, hosted-service policy, certificate rule, PKI operation, algorithm
choice, or admission-policy operation.
`memory-async-ticket-admission-lineage-https-authorization-provider-v1`
adapts one exact bounded memory Authorization provider to the shared async provider
port without introducing a scheduling point. Construction and every call revalidate
the exact adapter type and identity, wrapped memory service, copied entry count,
entry limit, and authorization-provider identity. A direct await delegates once to
the same synchronous memory lookup and returns the same typed `resolved`,
`unavailable`, or `failed` result before any other caller task can run. The shared
async Authorization boundary can therefore materialize the exact hidden value and
metadata while preserving its own preflight and result validation. Repeated awaits
reuse only the explicit immutable memory state and perform validation again. The
adapter creates no event loop, task, thread, executor, worker, scheduling point,
environment or file read, network access, secret-store call, discovery, refresh,
retry, external cache, persistence, logging, hosted-service policy, certificate
rule, PKI operation, algorithm choice, or admission-policy operation.
`authorized-https-ticket-admission-lineage-public-key-bundle-fetcher-v1`
binds one exact synchronous HTTPS fetcher to one exact caller-owned resolved
Authorization value. Construction and every call revalidate the wrapped HTTPS
fetcher, resolved Authorization value, stable adapter identity, copied byte count,
authorization-provider identity, bundle fingerprint, fetch-provider identity, and
source/resource bindings. A request must exactly match the bound bundle fingerprint,
fetch provider, source, and resource; any mismatch returns typed `failed` before a
connection is opened. A matched call opens one connection, sends one `GET` with the
base JSON/identity/close headers plus exactly one unchanged `Authorization` header,
reuses the base response/status/body validation, and closes once. The explicit
adapter may be reused with the same caller-owned authorization object, but it never
calls a credential provider, refreshes credentials, retries, redirects, caches
hidden state, normalizes or selects a scheme, logs credential text, discovers an
endpoint, creates workers, owns a hosted-service API, validates certificates,
distributes PKI, selects a signature algorithm, or changes admission policy.
`offloaded-async-authorized-https-ticket-admission-lineage-key-bundle-fetcher-v1`
adapts one exact authorized synchronous HTTPS fetcher to the shared async fetch port
through one caller-supplied offloader. Construction and every call fully revalidate
the wrapped authorized fetcher, stable adapter identity, copied authorization byte
count, authorization-provider identity, bundle fingerprint, fetch-provider identity,
and source/resource bindings. The shared request is validated before the first
`await`; any fingerprint/provider/source/resource mismatch returns typed `failed`
without invoking the offloader. A matched request awaits the offloader exactly once
with the same exact authorized fetcher and request, then revalidates the exact typed
result and request byte limit. The caller alone decides whether blocking work runs
inline, in a thread, through an executor, or by another scheduling mechanism.
Cancellation propagates directly. Ordinary offloader exceptions become stable
adapter errors without vendor text. Repeated calls offload again but never resolve or
refresh credentials. The adapter creates no event loop, task, thread, executor,
worker, retry, redirect, cache, trust root, credential provider, hosted-service
policy, certificate rule, PKI operation, algorithm choice, or admission-policy
operation.
The built-in HMAC-secret implementations are the bounded caller-owned memory
service, its inline sequential async adapter, the explicit read-only file
provider, and its caller-offloaded async adapter. The built-in public-key
implementations are the bounded caller-owned
memory service, its inline sequential and batch async adapters, its serial session
adapter, explicit canonical file bundles, synchronous plus async
transport-neutral fetch ports, a concrete synchronous HTTPS GET adapter,
a caller-offloaded async HTTPS adapter, explicit synchronous and async
Authorization-provider ports, a bounded caller-owned memory Authorization
provider with an inline async adapter, an explicit file Authorization provider with a caller-offloaded async adapter,
an explicit environment Authorization provider with a caller-offloaded async adapter,
an explicit authorized HTTPS adapter,
and a caller-offloaded async authorized HTTPS adapter.
There is no built-in external secret-store integration,
hosted credential provider, native async file-secret or file-Authorization I/O, native async
environment access, native nonblocking HTTPS
client, automatic
credential refresh, or hosted key service.
No bundle or session is loaded automatically;
there is no discovery, retry,
retained cache, persistence, automatic trust
loading, snapshot merge, route recommendation, or policy authority. There is no
hidden worker or
automatic promotion. The retained
`rtx4060-full-domain-crazy-ticket-admission-2026-07-29-v1` profile binds the RTX
4060 `sm_89` capability and full-domain CRAZY workload to source commit
`431f542ab6321eeb12b7bcb9195318f25cf376a5`. It admits synchronous groups 2/4/8
and rejects streamed routes 1/2/4/8; a ten-ticket queue therefore selects groups
2+8 at a 7.3271 ms estimated median. The opt-in executor validates the packed
workload SHA-256, reverse-waits each group, restores input order, and closes
every ticket. One thousand seven hundred eighty-nine
admission/telemetry/persistence/store/migration/summary/collection/overlap/
index/components/lineage/trust/manifest/provider/memory-secret-provider/
async-secret-provider/memory-async-secret-provider/file-secret-provider/
file-async-secret-provider/
signature/signature-trust/
signature-manifest/public-key-bundle/public-key-bundle-fetcher/
async-public-key-bundle-fetcher/https-public-key-bundle-fetcher/
async-https-public-key-bundle-fetcher/https-authorization-provider/
async-https-authorization-provider/
memory-https-authorization-provider/
file-https-authorization-provider/
file-async-https-authorization-provider/
environment-https-authorization-provider/
environment-async-https-authorization-provider/
memory-async-https-authorization-provider/
authorized-https-public-key-bundle-fetcher/
async-authorized-https-public-key-bundle-fetcher/
public-key-provider/async-public-key-provider/
async-batch-public-key-provider/provider-session/
memory-public-key-provider/memory-async-public-key-provider/
memory-batch-public-key-provider/
memory-session-public-key-provider tests cover fallback,
positive/negative
evidence, duplicate/malformed records, exact profile matching, seven isolated
runtime drifts, multi-profile selection, invalid/unknown workloads, ambiguity, and
three live CUDA routes. The seven route records and exact
provenance now live in schema-v4
`src/optimization/accelerator/adapter-outbound/accelerator/cuda/ticket_admission_profiles.json`, not Python source.
`src/performance/benchmarking/composition/benchmarks/accelerator/ticket_admission_profile_manifest.py` reconstructs those
canonical bytes from retained JSON/TOML, source commit, exact raw/structured-output
hashes, the tracked CUDA toolchain manifest, retained driver build, and retained
host/Python context. Twelve manifest tests require byte equality and reject
duplicate or unknown keys, unsupported schema, duplicate routes, malformed display
versions, invalid host fields, exact runtime-context duplicates, and direct
capability/runtime mismatch; distinct runtime variants may coexist for one
capability/workload. Runtime loading reads only the tracked product manifest and
never opens benchmark evidence. `resolve_cuda_ticket_admission_profile` selects at
most one exact workload/capability/runtime record; invalid or ambiguous requests
fail closed, while retained wrappers delegate through the stable workload identity. At adapter
startup, `cuda-runtime-toolchain-identity-v1` requires Driver API 13030 or newer,
exact NVRTC 13.3, the tracked toolchain SHA-256, and NVML display build `610.88`;
`cuda-host-runtime-identity-v1` measures Windows 11 Professional build
`10.0.26200`, `x86_64`, and CPython `3.14.6`. Missing or failed optional NVML or
host measurement leaves ordinary CUDA available but this evidence-bound profile
unmatched. Fourteen runtime-identity tests cover required query/hash failures,
NVML lifetimes, host validation, exact live host measurement, and one live CUDA
route. Other hosts, Python versions, driver builds, devices, and workloads remain
open. The global synchronous default does not change.
`search_submission.py` adds
`validated-search-submission-v1`: one exact algorithm/problem/seed/budget request
binds an optional ticket and deferred CPU search. Proposal publication waits for
capability/algorithm/seed/budget validation; cleanup must succeed before fallback.
Malformed tickets fail closed, successful wait is idempotent, mandatory failure is
cached, and close-before-wait prevents execution. Ten tests cover the complete
neutral lifetime. Proposals remain untrusted and require `admit_search_result` for
independent acceptance. `classic-rotate-target-search-submission-v1` is the first
concrete composition: it retains full-batch selector state, submits only the exact
zero-or-one preimage projection through a candidate ticket, and publishes against
the full batch after candidate validation. Eight tests cover identity, projected
and empty CPU routes, malformed nested evidence/ticket behavior, and three live
RTX 4060 routes: exact one-position publication, empty projection, and adapter-
teardown CPU fallback. This is lifetime/exactness evidence, not measured speedup or
independent-stream overlap. Other strategies and ROCm search tickets remain open.
`verification_submission.py` adds
`validated-verification-assist-submission-v1`. Optional assistance remains pending
until `wait()`; no backend, typed submit/wait failure, or malformed result completes
with no hints only after any known ticket closes. Malformed tickets and cleanup
failure fail closed, successful waits are idempotent, and close-before-wait blocks
publication. Nine tests cover the neutral state/outcome lifetime.
`candidate-evidence-verification-submission-v1` composes exact candidate tickets
into ordered optional hints while retaining evaluator/verifier identity. Seven tests
cover CPU evidence, malformed nested evidence/ticket, verifier mismatch, and two
live RTX 4060 routes: exact CUDA hints and teardown-driven empty completion. Hints
remain untrusted; only `TrustedCandidateVerifier` may accept a proposal. No hint-
ticket speedup or independent-stream claim is made.
`search_selection.py` independently resolves algorithm and backend bindings,
requires a CPU reference, supports explicit overrides, and records configured
versus actual backend identity after fallback. `search_config.py` adds versioned
TOML base selection with fail-closed schema/identity validation and durable source
identity; explicit overrides produce a new effective selection without mutating
the loaded configuration. `primitive_candidates.py` binds
classic crazy/rotate candidate payloads to any exact primitive adapter; the same
bridge is differentially exercised through CPU and live CUDA backends.
`evidence_verification.py` reuses candidate evidence as optional verification
hints without introducing backend acceptance authority, and live CUDA hints match
the CPU reference over a deterministic 257-item corpus. `evaluated_search.py`
adds a bounded map/select search adapter that only proposes members of the exact
evaluated batch. `classic-rotate-target-search-v1` uses a zero-or-one inverse
projection. `classic-crazy-target-search-v1` proves the general multiposition case
without heuristic filtering: neutral `CRAZY_TRIT_TABLE` semantics derive exact
fixed-accumulator preimage positions, full-batch membership remains authoritative,
and only the projected subset reaches CPU/CUDA evaluation. The canonical complete
59,049-word domain retains exactly 1,024 positions for accumulator zero and target
29,524. Fourteen strategy tests include a live RTX 4060 prepared CUDA result equal
to CPU with resident cardinality 1,024; three CLI tests cover CPU, CUDA, and setup
fallback. Trusted CPU admission remains separate. This is correctness evidence,
not a speedup or independent-stream claim.
`python -m optimizer.cli` is the first external search runner: it reads Search
Configuration v1 plus canonical problem bytes, accepts explicit algorithm/backend
overrides, and emits deterministic JSON containing problem SHA-256,
configured-versus-actual backend identity, device metadata, seed/budget, and only
untrusted proposals. Supported CUDA setup failure preserves configured CUDA intent
while safely falling back to CPU; unsupported algorithm/backend pairs fail
explicitly. The retained full-domain comparison at
`benchmarks/accelerator/evidence/2026-07-27-rotate-target-search-rtx4060/`
contains 15 samples per backend under Benchmark Protocol v1. CPU median is
401.185 ms and CUDA median is 412.570 ms over all 59,049 classic words, yielding a
0.972x CUDA/CPU ratio and rejecting the speedup hypothesis for this complete
host-heavy route. Proposals remain identical and independently admitted. This
negative result motivates larger or resident search designs rather than hidden
benchmark filtering. The retained phase profile at
`benchmarks/accelerator/evidence/2026-07-27-rotate-target-search-phase-profile-rtx4060/`
shows 97.5% CPU and 99.5% CUDA named-phase coverage. CUDA host-side phases account
for about 57.0% of median total time, backend evaluation about 42.5%, and batch
construction plus proposal selection about 173.081 ms.
`PreparedEvaluatedSearch` now carries immutable validated request/batch state bound
to exact algorithm, batch-builder, and selector identity. It can be prepared once
through CPU and reused unchanged through matching CPU or CUDA adapters; forged or
mismatched strategy state fails closed. Prepared execution and diagnostics avoid
repeated batch construction/validation, while rotate-target selection decodes only
the validated header target instead of rebuilding the complete corpus. The
ordinary-versus-prepared evidence is retained under
`benchmarks/accelerator/evidence/2026-07-28-prepared-search-rtx4060/`. CPU median
falls from 293.564 to 148.590 ms (1.976x), and CUDA median falls from 306.872 to
162.693 ms (1.886x). Prepared CUDA remains about 9.5% slower than prepared CPU
(0.913x CPU-prepared/CUDA-prepared). These are amortized repeated-search results;
preparation is outside the timed interval. The retained prepared phase profile at
`benchmarks/accelerator/evidence/2026-07-28-prepared-search-phase-profile-rtx4060/`
shows backend evaluation consuming 79.9% of CPU and 81.2% of CUDA median total
time; proposal selection consumes 19.6% and 18.7%. Proof/result validation is
negligible. `PackedCandidateEvidence` now implements that boundary with one
fixed-width opaque payload buffer whose logical identities are inherited from the
validated batch order. Generic item results remain compatible; width, size, and
mixed-form drift fail closed. Primitive search iterates packed u32 values without
per-candidate bytes/objects, while verification-assist materializes only at the hint
boundary. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-packed-search-rtx4060/` lowers CPU
ordinary/prepared medians to 211.693/77.309 ms and CUDA medians to
230.144/91.199 ms, improvements of 1.387x/1.922x and 1.333x/1.784x over the
pre-packed routes. The sibling packed phase profile lowers backend evaluation to
53.907 ms CPU and 67.202 ms CUDA. Packed CUDA prepared remains about 18.0% slower
than packed CPU prepared. `PreparedCandidateExecution` now lets a strategy attach
hardware-neutral decoded candidate state to the existing proof. Rotate search
prepares one validated `PrimitiveBatch`; matching CPU/CUDA adapters consume it
without repeated candidate batch validation or payload decode. The preparer is
part of strategy identity, and forged type/kind/evaluator state fails closed.
Ordinary one-shot search still prepares locally. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-prepared-primitive-search-rtx4060/`
records 43.129 ms CPU and 57.296 ms CUDA prepared medians, 1.792x/1.592x faster
than the packed baseline. Ordinary routes regress 6.6%/3.7%, and prepared CUDA
remains 32.8% slower than prepared CPU. The phase bundle lowers backend evaluation
2.801x CPU and 2.083x CUDA. `PreparedPrimitiveBatch` now carries reusable exact
validation proof. CPU consumes it directly; CUDA prepared execution keeps one
proof-bound input/output allocation resident and rebuilds only when proof identity
changes. Ordinary CUDA stays one-shot. `CudaPreparedPrimitiveStats` and the prepared
benchmarks require one build, 16 evaluations, 15 reuses, and 59,049 resident rotate
words. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-resident-primitive-search-rtx4060/`
records 34.132 ms CUDA prepared versus 46.232 ms CPU prepared: a 1.355x same-run
CUDA advantage and 1.679x CUDA improvement over the pre-resident baseline. The
phase sibling lowers CUDA backend evaluation 3.252x to 9.922 ms, but complete phase
total stays at 55.910 ms because selection rises to 46.331 ms. Proposal
selection/membership validation selected the next boundary.
`PreparedEvaluatedSearch` now stores a `frozenset` of exact `(logical_id, payload)`
pairs built after batch validation. Prepared CPU/CUDA validation reuses it; ordinary
search remains one-shot, and forged payloads fail closed. Both prepared benchmarks
require exactly 59,049 indexed members. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-indexed-membership-search-rtx4060/`
records 26.797 ms CPU prepared and 17.970 ms CUDA prepared, 1.725x/1.899x faster
than the resident baseline. CUDA prepared is 1.491x faster than same-run CPU. The
phase sibling lowers proposal selection 3.519x CPU and 3.939x CUDA to
11.801/11.761 ms. Improved controls bound total attribution.
`PreparedProposalSelection` now binds strategy-specific selector state into the
prepared proof. Rotate target preparation computes the unique classic rotate
preimage after pruning/seed/budget and retains its evaluated positions. Prepared
selection validates only those packed evidence words; ordinary search keeps the
full scan. Missing/excluded positions, forged state, and nonmatching evidence fail
closed, and benchmarks require one prepared position. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-direct-rotate-selection-rtx4060/`
records 15.266 ms CPU prepared and 6.182 ms CUDA prepared, improvements of
1.755x/2.907x over indexed membership. CUDA is 2.470x faster in the same run. The
phase sibling lowers selection to 13.2/12.4 us (894.008x/948.452x), while backend
phases change only 1.034x/1.035x. Primitive result validation now checks exact
minimum/maximum tuple bounds rather than a Python per-value loop, preserving
negative/overflow rejection before packing. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-extrema-validation-search-rtx4060/`
records 14.058 ms CPU prepared and 4.929 ms CUDA prepared, improvements of
1.086x/1.254x over direct selection. Backend phases improve 1.091x/1.330x while
ordinary controls remain nearly flat. Prepared CPU rotate now reuses a cached
59,049-entry table generated from the scalar reference formula. Ordinary CPU stays
scalar, the exhaustive test compares every classic word, and benchmarks require
16 prepared evaluations plus the full table cardinality. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-cpu-rotate-table-search-rtx4060/`
records 3.313 ms CPU prepared, 4.243x faster than extrema validation and 1.440x
faster than same-run CUDA. The phase sibling lowers CPU backend evaluation 4.540x
to 2.906 ms while CUDA changes only 1.018x. `PackedPrimitiveResult` now carries
canonical little-endian u32 words alongside tuple results. Prepared CUDA returns the
resident host buffer as bytes after D-to-H transfer; the candidate bridge validates
capability, exact byte count, and every classic-domain word before forwarding those
same bytes. Ordinary CUDA and CPU tuple routes remain unchanged. Benchmarks require
`packed_evaluations=16` with the existing proofs. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-packed-cuda-primitive-search-rtx4060/`
records 2.036 ms CUDA prepared, 2.343x faster than the CPU-table baseline and
1.621x faster than same-run CPU. The phase sibling lowers CUDA backend evaluation
2.147x to 1.802 ms while CPU changes only about 0.5%. Packed-domain validation
now uses `u32le-broadword-domain-v1`: repeated high-bit masks plus an independent
per-lane threshold addition validate all u32le words in big-integer operations.
Invalid first/last threshold or high-bit lanes retain descriptive fail-closed
fallback. Benchmarks require the validator identity. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-broadword-packed-validation-search-rtx4060/`
records 1.175 ms CUDA prepared, 1.733x faster than scalar packed validation and
2.706x faster than same-run CPU. The phase sibling lowers CUDA backend evaluation
2.095x to 0.860 ms and CUDA total 2.057x to 0.886 ms; CPU phase regressions remain
controls. `CudaPreparedPrimitivePhaseProfile` now records resident launch/sync,
D-to-H, immutable bytes, and total time. `PackedPrimitiveEncodingPhaseProfile`
records the historical broadword contract, masks, integer decode, checks,
diagnostics, result build, and total. Prepared candidate state now additionally
retains immutable CPU truth under `cpu-reference-packed-equality-v1`; ordinary
results continue to use `u32le-broadword-domain-v1`. Prepared CPU/CUDA output must
match all retained bytes after capability, representation, and exact-count checks,
so incorrect in-domain first or final words fail closed. The generic search adapter
exposes proof-bound candidate-state cardinality, and full-domain benchmarks require
59,049 reference words plus all existing table/session/membership/selector proofs.
The prepared profiler now records contract, exact compare, result build, visible
layer residuals, CUDA phases, and end-to-end total. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-prepared-reference-search-rtx4060/`
records 0.488 ms CUDA prepared, 2.407x better than broadword and 6.786x faster than
same-run CPU. The search-phase sibling records 0.215 ms CUDA backend evaluation
(3.999x) and 0.238 ms total (3.729x). The primitive profile records 0.0278 ms exact
validation (23.590x better), 0.0180 ms byte comparison, and 0.1935 ms end-to-end
(4.488x). Reference construction is untimed and the full-domain image consumes
236,196 bytes. `search_preparation_crossover.py` now measures cold/warm preparation,
incremental Python allocation, fresh resident build, steady reuse, and strict
ordinary/prepared crossover at 1/64/1,024/59,049 candidates. It preserves both
validator IDs, exact proposals/admission, state cardinalities, and CUDA session
proofs. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-prepared-search-crossover-rtx4060/`
records warm crossover 6/3/2/1 and cold crossover 106/38/5/2. Full-domain warm
preparation plus first search is 212.140 ms versus 222.842 ms ordinary; cold crosses
on run two. Incremental Python state retains/peaks at 16.063/19.040 MiB versus
0.901 MiB exact reference/device/host buffers. Component tracing selected the historical membership frozenset as the first safe
compaction target. Prepared search now uses
`identity-sorted-candidate-reference-binary-search-v1`: an immutable, proof-bound,
identity-sorted tuple of references to the original batch items. Membership uses
binary search by logical ID followed by byte-exact payload equality; forged indexes,
cross-batch reuse, missing IDs, and payload substitution fail closed. Retained
version-2 evidence under
`benchmarks/accelerator/evidence/2026-07-28-compact-membership-crossover-rtx4060/`
records 473,352 bytes retained for the compact component versus 5,876,552 bytes for
the copied set at full domain (91.945% lower), with 15.851/18.027 ms preparation
(1.137x compact advantage). Complete prepared state falls from 16.063 to 10.910 MiB
retained and from 19.040 to 14.080 MiB peak. Exact hit/miss lookup regresses
9.898x/13.856x, so the index is promoted for scale memory/preparation rather than
lookup speed. Warm/cold crossover is 7/3/2/1 and 108/38/5/1. The trusted verifier
remains the sole proposal-admission authority. This is the retained version-2
baseline.
Retained version-3 evidence under
`benchmarks/accelerator/evidence/2026-07-28-indexed-candidate-batch-crossover-rtx4060/`
promotes proof-carrying fixed-width candidate storage for large deterministic
batches. At 59,049 candidates, complete prepared state falls from 10.910 to 2.923
MiB retained (73.211%) and from 14.080 to 8.395 MiB peak (40.378%). Warm/cold
preparation improves from 194.917/207.761 ms to 117.753/132.553 ms
(1.655x/1.567x), while ordinary CUDA search improves from 222.518 to 152.998 ms
(1.454x). Warm/cold preparation plus first resident search is 129.508/144.308 ms,
so both retain one-run crossover with 23.490/8.691 ms observed margins. The
rotation-backed membership component retains 528 bytes versus 473,352 bytes in
version 2 and 11,180,412 bytes for the same-run copied set; its preparation is
0.0177 ms versus 15.8507/155.4303 ms. Exact hit lookup is the retained cost:
17.755 microseconds versus 2.625 microseconds in version 2 and 0.266 microseconds
copied (6.763x/66.844x slower). Exact miss lookup improves to 0.636 microseconds
from 2.785 microseconds in version 2, but remains 3.094x slower than copied-set
miss lookup. The promotion is not universal: one-candidate memory grows slightly,
and 64-candidate cold/warm crossover moves from 38/3 to 45/4. Duplicate or
out-of-domain indexes, malformed widths/sizes, incorrect pivots, forged or
cross-batch proofs, and payload substitution still fail closed. Retained version-4 evidence under
`benchmarks/accelerator/evidence/2026-07-28-packed-prepared-primitive-crossover-rtx4060/`
promotes `proof-bound-u32le-primitive-input-v1`. At 59,049 candidates,
incremental retained prepared state falls from 3,064,623 to 713,791 bytes, a
76.709% reduction and 12.088 bytes per candidate. Peak allocation remains exactly
8,802,328 bytes (8.395 MiB): preparation still builds a temporary CPU
reference/decode tuple, so the result removes retained ownership rather than the
transient peak. Full-domain cold/warm crossover remains 1/1. Against the immediate
clean `81d82cf` baseline, CPU ordinary/prepared improve from 139.517/3.316 ms to
132.848/3.261 ms (1.050x/1.017x), while CUDA ordinary/prepared improve from
152.055/0.449 ms to 144.440/0.429 ms (1.053x/1.047x). Phase totals are 2.9664 ms
CPU (1.006x) and 0.2654 ms CUDA (1.099x). CPU and CUDA both prove one session
build, 16 evaluations, 15 reuses, rotate kind, and 59,049 resident words; CUDA
also proves 16 packed evaluations and CPU proves the full rotate table. The packed
representation is promoted because no clean route regresses. Retained version-5 evidence under
`benchmarks/accelerator/evidence/2026-07-28-packed-rotate-batch-builder-crossover-rtx4060/`
promotes `classic-u32le-bitset-first-representatives-v1` with independent
`cpu-scalar-packed-equality-v2`. At 59,049 candidates, cold/warm preparation falls
from 122.990/109.027 ms to 76.130/76.584 ms (1.616x/1.424x), retained state falls
slightly from 713,791 to 710,647 bytes, and peak Python allocation falls from
8,802,328 to 1,183,023 bytes (86.560%). Full-domain crossover remains 1/1. CPU
ordinary/prepared improve from 132.848/3.261 ms to 90.869/3.108 ms
(1.462x/1.049x), while CUDA ordinary improves from 144.440 to 103.562 ms
(1.395x). CUDA prepared throughput is the retained contextual negative at
0.479 versus 0.429 ms (0.896x); the separate prepared CUDA phase total changes
only from 0.2654 to 0.2676 ms (0.992x), so no prepared-execution effect is
attributed to the builder. The fixed bitset raises one-candidate peak from 2,664
to 8,391 bytes and 64-candidate warm crossover from 3 to 4 runs; promotion is for
large deterministic batches, not universal small-batch memory. All builder,
storage, validator, membership, proposal, admission, cardinality, and CPU/CUDA
session proofs pass. Component attribution now places the remaining peak in the
batch builder: it reaches about 1,183,087 bytes while retaining 473,546 bytes as
representative, selected-index, and payload arrays coexist. Retained version-6 evidence under
`benchmarks/accelerator/evidence/2026-07-28-inplace-packed-batch-builder-crossover-rtx4060/`
promotes `classic-u32le-bitset-inplace-first-representatives-v2`. At 59,049
candidates, cold/warm preparation falls from 76.130/76.584 to 64.606/65.101 ms
(1.178x/1.176x), peak Python allocation falls from 1,183,023 to 962,052 bytes
(18.679%), retained state remains 710,647 bytes, and full-domain crossover remains
1/1. CPU/CUDA ordinary routes improve from 90.869/103.562 to 79.943/92.133 ms
(1.137x/1.124x). Prepared controls move in opposite directions: CPU throughput is
3.267 versus 3.108 ms (0.952x), CUDA throughput is 0.385 versus 0.479 ms
(1.245x), and separate CPU/CUDA phase totals are 2.9659/0.2723 ms versus
2.9535/0.2676 ms (0.996x/0.983x). No prepared-execution effect is attributed to
the builder. One-candidate peak stays 8,391 bytes; at 64 candidates peak falls
8,788 to 8,635 bytes while sub-millisecond ordinary timing varies upward; at 1,024
candidates peak falls 22,155 to 19,116 bytes and ordinary CUDA improves. All
builder, storage, validator, membership, proposal, admission, cardinality, and
CPU/CUDA session proofs pass. Component attribution now places the builder phase
near 710,190 bytes peak while retaining 473,546 bytes. The overall ~962 KiB peak
occurs when that retained batch coexists with candidate-state creation (~237 KiB
incremental) or selector creation (~253 KiB incremental). Reducing this post-builder
coexistence without weakening exact reference, selection, membership, or admission
proofs is the next measured boundary.
Retained version-7 evidence under
`benchmarks/accelerator/evidence/2026-07-28-native-view-selector-crossover-rtx4060/`
promotes `classic-u32le-native-view-preimage-v2`. The same-run component
comparison preserves the one exact preimage at all four scales. At 59,049
candidates, selector peak falls from 252,597 to 1,885 bytes (99.254%), while
selector preparation changes from 3.7642 to 3.9644 ms, a retained 5.318%
regression. Complete preparation peak falls from 962,052 to 946,675 bytes
(1.598%); retained state remains 710,647 bytes. Cold/warm preparation changes
from 64.606/65.101 to 64.465/64.780 ms and full-domain crossover remains 1/1.
At one candidate, the native selector retains 56 bytes more and peaks 240 bytes
higher; total one- and 64-candidate peaks are unchanged. CUDA ordinary, fresh
build, and reuse timings remain contextual controls because selector preparation
is outside execution intervals. Candidate-state creation, approximately 237 KiB
incremental beside the retained batch, is the next measured preparation-memory
boundary; exact reference, selection, membership, proposal, and admission proofs
remain mandatory.
Retained version-8 evidence under
`benchmarks/accelerator/evidence/2026-07-28-projected-prepared-rotate-crossover-rtx4060/`
promotes selection-aware exact projection under
`classic-rotate-preimage-projection-v1`. Generic evaluated search prepares the
selector proof first, requires the projected sub-batch to preserve evaluator
identity and exact full-batch membership, binds projection callbacks into strategy
identity, and validates backend evidence against only that sub-batch. Proposal
membership and trusted admission still use all 59,049 evaluated candidates. The
classic rotate inverse has zero or one exact preimage, so the canonical full-domain
prepared state retains one reference word, one selected position, and one resident
CPU/CUDA word while full membership remains 59,049. Empty projections skip backend
execution; wrong evaluator, fabricated member, oversized projection, forged proof,
wrong evidence, and fabricated proposal still fail closed. Against the immediate
clean version-7 baseline, cold/warm preparation improves from 64.4648/64.7804 ms to
46.2706/46.6161 ms (1.393x/1.390x), retained state falls from 710,647 to 475,010
bytes (33.158%), peak allocation falls from 946,675 to 710,126 bytes (24.987%),
and crossover remains 1/1. CPU prepared throughput improves from 3.2402 to 0.0787
ms (41.172x), while CUDA prepared improves from 0.5116 to 0.2743 ms (1.865x).
Prepared backend-phase speedups are 218.4x CPU and 2.366x CUDA; total prepared-phase
speedups are 52.8x and 1.914x. Ordinary CPU/CUDA changes are contextual controls and
are not attributed to projection. Projection is not universal tiny-batch policy: at
one candidate retained state rises from 1,863 to 2,349 bytes and cold/warm crossover
moves from 6/6 to 8/7. The required architectural boundary was an exact projected-subset contract for
strategies without a unique algebraic inverse. The promoted proof retains subset
identity, full membership, exact evidence, proposal validation, and independent
trusted admission rather than introducing heuristic filtering.
Retained version-9 evidence under
`benchmarks/accelerator/evidence/2026-07-28-exact-candidate-subset-crossover-rtx4060/`
promotes neutral `request-order-position-subset-v1` and rotate projection
`classic-rotate-preimage-position-subset-v2`. The proof binds immutable, strictly
increasing request-order positions to the exact full-batch object; empty, one-item,
and multi-item subsets are supported. Mutable, duplicate, reordered, out-of-range,
forged, wrong-type, and cross-batch state fail closed. Generic preparation validates
and unwraps the projection once, stores primitive state directly on the repeated hot
path, and retains the exact projected batch beside full membership authority. Formal
`candidate-subset-proof-tradeoff-v1` medians over 59,049 full-batch items compare
legacy membership revalidation with the proof route: 2.3/4.3 microseconds for empty
(0.535x), 20.0/7.5 microseconds for one item (2.667x), 1.0356/0.1581 ms for
64 items (6.550x), and 16.8647/2.5298 ms for 1,024 items (6.666x). The empty
proof adds 144 retained and 64 peak bytes; from one item upward retained memory is
slightly lower and peak memory is equal. Against the immediate clean version-8
baseline, full-domain cold/warm preparation improves from 46.2706/46.6161 ms to
45.7698/46.2938 ms, retained state falls by 32 bytes to 474,978 bytes, peak stays
710,126 bytes, and crossover remains 1/1. One-candidate crossover improves from
8/7 to 7/6, while 1,024 improves from 2/1 to 1/1. CPU prepared isolated throughput
regresses 2.8% (0.0787 to 0.0809 ms) and remains an explicit tradeoff; CPU prepared
phase total is exactly unchanged at 56.4 microseconds. CUDA prepared throughput
improves 0.5% and phase total improves from 141.4 to 141.1 microseconds. The proof
is promoted for exact authority and multi-item scaling, not as an empty-subset
optimization. That production boundary is now implemented by
`classic-crazy-target-search-v1`: exact digitwise preparation projects the full
59,049-member accumulator-zero/target-29,524 case to 1,024 positions before
replaceable CPU/CUDA evaluation. The full membership and independent admission
proofs remain unchanged. `classic-crazy-target-search-submission-v1` now carries
that full selector/projection proof across a deferred 1,024-item candidate ticket.
Seven tests cover full-domain/empty CPU routes, malformed nested protocol, live CUDA
publication, and teardown fallback. Retained evidence under `benchmarks/accelerator/evidence/2026-07-29-crazy-target-performance-matrix-rtx4060/`
records CPU ordinary/prepared medians of 368.3588/22.4264 ms (16.425x), CUDA
ordinary/prepared medians of 235.8490/20.3304 ms (11.601x), and a 185.7629 ms
one-shot CUDA ticket (1.270x over ordinary); every same-baseline comparison wins
15/15 retained pairs. CUDA prepared is 1.103x faster than CPU prepared and 9.137x
faster than the one-shot ticket. Prepared setup is untimed while ticket setup and
cleanup are timed. No cross-device, compiler, synthesis, kernel-overlap, or
independent-stream claim is made.
Synthesis/guided search, ROCm work ports and VM execution, broader hardware
evidence, richer orchestration, and additional representative comparisons remain
follow-on work. `src/optimization/optimizer/application/optimizer/enumerative.py` supplies the first concrete CPU-only
search strategy: deterministic finite-corpus enumeration with canonical replay
identity and independent trusted verification.
