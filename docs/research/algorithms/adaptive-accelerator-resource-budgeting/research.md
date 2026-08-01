# Adaptive accelerator resource budgeting

## Status

Active

## Research Question

Does `adaptive-accelerator-resource-budgeting` provide a reproducible verified
benefit over its declared baseline for the Malbolge compiler or execution
problem without weakening semantic correctness?

## Background

Discover available memory and compute resources at runtime and choose batch
size, state layout, caches, and search breadth accordingly. Tiny devices around
Small-memory devices must remain usable while additional addressable
resources on arbitrarily larger devices must increase available work rather than
hitting a fixed artificial VRAM ceiling. The 128 MiB and 80 GiB values are only
example probe points, not supported-range endpoints.

- Status: Active
- Research ID: `adaptive-accelerator-resource-budgeting`
- Last reviewed: 2026-07-30

## Prior Work

- `../../../bibliography/platforms-and-runtimes/accelerators/nvidia-cuda.md`

## Hypothesis

- Baseline: one fixed resident batch ceiling chosen for a development GPU. Such
  a ceiling either wastes larger devices or fails when a smaller device cannot
  admit the configured state set.
- H1: measuring free/total memory and coarse compute capacity at runtime, then
  greedily partitioning exact per-item byte requirements below an explicit
  reserve, admits the same workload across wider device sizes without changing
  semantic acceptance.
- H0/rejection condition: reject the planner if one admitted chunk exceeds its
  measured usable bytes, if an item that cannot fit alone is admitted, if input
  order changes, or if increasing otherwise-equivalent usable memory reduces
  resident breadth. Performance benefit remains unproven until raw throughput
  samples exist.

## Method

The research identity and configuration live at
`algorithms/adaptive-accelerator-resource-budgeting/`. Product planners live in
`accelerator/resource_budget.py` and `accelerator/ticket_admission.py`; exact CUDA
route evidence is bound by `accelerator/cuda/ticket_admission.py`. The reproducible
resource measurement entry point is
`benchmarks/accelerator/resource_budget_measure.py`. Experiments deliberately
separate synthetic capacity scenarios, live CUDA resource evidence, and retained
route comparisons. Raw regenerable output stays outside correctness authority.

## Evidence

Candidate generation, heuristics, models, and accelerators are untrusted. A
research result can compare quality or cost only after the trusted semantic
verifier accepts the candidate under the declared target profile.

- The scheduler runs within measured memory limits from approximately 128 MiB
  through large-memory accelerators and converts additional resources into
  measured throughput/search breadth without fixed-size assumptions.
- A CPU/reference path remains sufficient for correctness, and accelerator
  failure/unavailability changes performance rather than semantic acceptance.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.
- Performance conclusions use equivalent workloads and report raw-sample
  provenance, resource budgets, dispersion/uncertainty, and failure/success
  behavior rather than only a best-case number.

## Results

The first correctness slice is active. `AcceleratorResources` validates measured
free/total memory, maximum threads per block, and multiprocessor count.
`plan_resident_batches` reserves the larger of 8 MiB or one sixteenth of total
memory, then constructs maximal contiguous input-order chunks whose exact
resident byte requirement fits the remaining free-memory budget. An item that
cannot fit alone is rejected before backend allocation.

The classic resident CUDA adapter now uses this plan before allocation. CUDA
resource evidence comes from `cuMemGetInfo_v2` plus
`cuDeviceGetAttribute`; no GPU model name selects a batch limit. Synthetic
boundary tests model a 19,131,940-byte current-profile state and admit six such
states in the first chunk of a 128 MiB device model versus 4,209 in an 80 GiB
model under the same reserve rule. These are capacity-model results, **not**
claims that either hardware class was physically benchmarked.

Existing RTX 4060 classic resident differential tests continue to pass after the
planner is inserted into the real allocation path. Post-commit resource evidence
at `benchmarks/accelerator/evidence/2026-07-27-resource-budget-windows-x86_64/`
records commit/toolchain/device identity plus the raw planning JSON. The live
snapshot reports 8,585,084,928 total bytes, 7,451,181,056 free bytes, 24 SMs,
and 1,024 maximum threads/block; the modeled current state admits 361 items in
the first chunk. This remains capacity evidence, not throughput. Post-commit
no-ceiling evidence under
`benchmarks/accelerator/evidence/2026-07-27-unbounded-vram-windows-x86_64/`
adds a 100,000 GiB synthetic scenario with 100,000 classic items. The complete
workload is admitted as 72,736 + 27,264 items because classic CUDA splits at its
32-bit per-launch memory-index boundary rather than imposing a VRAM maximum.

The first retained throughput matrix at
`benchmarks/accelerator/evidence/2026-07-27-classic-throughput-rtx4060/` is a
negative scaling result. For an exact 64-step classic no-op workload, median
end-to-end throughput is 29.127 VMs/s at batch 1, 28.136 at batch 8, 27.922 at
batch 32, and 27.751 at batch 128. Batch 128 is about 4.73% slower than batch 1.
Therefore larger resident batches are not yet converting capacity into measured
throughput. The evidence does not assign causality; phase-separated timing is the
next experiment.

Phase-separated post-commit evidence under
`benchmarks/accelerator/evidence/2026-07-27-classic-phase-profile-rtx4060/`
locates that failure. At batch 128, median kernel+sync time is 458,100 ns out of
4,698,614,500 ns total (about 0.0097%). Validation/planning, host-buffer
construction, and result decode account for about 97.75% combined. The evidence
therefore rejects CUDA-kernel tuning as the next bottleneck-directed action and
selects host representation/validation work for optimization first.

The first bottleneck-directed optimization is retained under
`benchmarks/accelerator/evidence/2026-07-27-classic-phase-profile-array-rtx4060/`.
Removing duplicate request validation and replacing tuple/ctypes flattening with
contiguous unsigned-word buffers reduces batch-8 median wall time from
287,277,100 ns to 66,098,600 ns (4.35x) and batch-128 time from 4,698,614,500 ns
to 1,162,925,900 ns (4.04x). Batch-128 throughput rises from about 27.24 to
110.07 VMs/s. Validation/planning is now the dominant measured phase, so the next
candidate is safe reuse of validation for immutable requests.

A second host-side optimization is retained under
`benchmarks/accelerator/evidence/2026-07-27-classic-phase-profile-minmax-rtx4060/`.
Aggregate `min`/`max` validation reduces batch-8 median wall time again from
66,098,600 ns to 36,729,100 ns and batch-128 to 636,002,300 ns. Relative to the
original phase baseline, batch 128 is now 7.39x faster and reaches about
201.26 VMs/s. Host-buffer construction is again the dominant measured phase;
shared immutable memory identity inside a batch is the next candidate.

Batch-local shared-memory reuse is retained under
`benchmarks/accelerator/evidence/2026-07-27-classic-phase-profile-shared-memory-rtx4060/`.
The batch-128 median falls again from 636,002,300 ns to 118,917,500 ns and reaches
about 1,076.38 VMs/s, roughly 39.5x lower wall time than the original phase
baseline. Complete result decode is now the dominant phase (~75.1%), while the
kernel remains ~0.10%. This selects an actually resident continuation/snapshot
boundary: continue VM state on device and materialize all 59,049 words only when
a host snapshot is explicitly requested.

Ticket queue admission now extends the budgeting work without introducing online
learning. `accelerator/ticket_admission.py` accepts only exact, same-context
route evidence with lower median and a strict paired-win majority, fails closed
for malformed or duplicate records, and chooses a deterministic input-order
partition. The first retained CUDA profile is limited to the RTX 4060 `sm_89`
full-domain CRAZY evidence from 2026-07-29. It admits synchronous groups 2/4/8,
rejects every measured streamed route, and leaves the ordinary synchronous path
as the global default. The schema-v4 product registry at
`accelerator/cuda/ticket_admission_profiles.json` is generated canonically from
retained evidence and the tracked CUDA toolchain manifest by
`benchmarks/accelerator/ticket_admission_profile_manifest.py`; runtime loading
never reads benchmark files. Profile use measures
`cuda-runtime-toolchain-identity-v1` and `cuda-host-runtime-identity-v1` at adapter
startup and requires Driver API 13030 or newer, NVRTC 13.3, the tracked toolchain
SHA-256, NVML display build `610.88`, Windows 11 Professional build `10.0.26200`,
`x86_64`, and CPython `3.14.6`. Missing optional identity leaves ordinary CUDA
available while this profile remains unmatched. Opt-in
`evidence-bound-ticket-route-admission-report-v1` publishes immutable input-order
route assessments for context mismatch, inexact output, absent median improvement,
absent paired majority, and groups larger than the queue. Eligible but unused
routes retain zero selected counts; the report embeds the unchanged plan and
records fallback plus synchronous/streamed selected totals. The retained CUDA
facade resolves the same exact profile before reporting. One thousand one
hundred ninety-three
admission/telemetry/persistence/store/migration/summary/collection/overlap/
index/components/lineage/trust/manifest/provider/signature/signature-trust/
signature-manifest/public-key-bundle/public-key-bundle-fetcher/
async-public-key-bundle-fetcher/https-public-key-bundle-fetcher/
async-https-public-key-bundle-fetcher/https-authorization-provider/
async-https-authorization-provider/
authorized-https-public-key-bundle-fetcher/
async-authorized-https-public-key-bundle-fetcher/
public-key-provider/async-public-key-provider/
async-batch-public-key-provider/provider-session/
memory-public-key-provider,
twelve profile-manifest, and fourteen
runtime-identity
tests prevent silent drift,
direct-plan bypass, or report-only policy changes. The report reads no benchmark
evidence and performs no online learning. The caller-owned
`bounded-ticket-admission-telemetry-v1` recorder retains completed reports;
`bounded-ticket-admission-failure-telemetry-v1` independently retains stable
accelerator-failure categories without exception text. Both bounded FIFOs expose
monotonic sequence/eviction state and measured-versus-estimated duration.
Malformed reports, timings, or foreign failures fail before mutation.
`TicketAdmissionAttemptTelemetry` pairs the FIFOs, and the separate CUDA attempt
executor records exactly one outcome before returning or re-raising the same
accelerator error. Existing ordinary and completion-only executors remain
unchanged. `ticket-admission-telemetry-document-v1` captures both snapshots as
compact sorted-key schema-v1 JSON. Bounded decoding rejects duplicate, unknown,
oversized, noncanonical, and inconsistent state; explicit writes use atomic
replacement, and restoration preserves exact sequence and eviction state.
`caller-owned-ticket-admission-telemetry-store-v1` defines a minimal
put/get/remove/snapshot port and one bounded in-memory adapter. Construction fixes
positive unique-document, per-FIFO observation, and canonical-byte limits.
Defaults are 4,096 documents, 4,096 observations per FIFO, and 16 MiB.
Puts validate schema-v1 canonical bytes before mutation, reuse the established
fingerprint, and treat exact duplicates as idempotent. Snapshots publish only sorted
fingerprints, byte counts, and immutable limits; removal releases exact budgets.
Invalid fingerprints/documents, capacity overflow, collisions, or retained decode
failure fail closed. There is no filesystem access, automatic loading, summary,
merge, recommendation, lineage inference, or policy update.
`ticket-admission-telemetry-schema-migration-v1` publishes an explicit lossless
1-to-1, 1-to-2, 2-to-1, and 2-to-2 compatibility matrix. Schema-v2 is canonical
sorted JSON wrapping the exact canonical schema-v1 bytes as standard Base64 plus
the required schema-v1 identity and SHA-256 fingerprint. Versioned decoding
defaults to 2 MiB outer bytes, 1 MiB embedded source bytes, and 4,096 observations
per FIFO. Upgrade and downgrade are caller-invoked; schema-v1 bytes remain
unchanged. Schema-v2 adds no telemetry semantics. There is no automatic migration,
file loading, snapshot reinterpretation, merge, recommendation, lineage inference,
or policy change.
`offline-ticket-admission-telemetry-summary-v1` validates one explicit document
and groups exact backend/device/workload/ticket-count contexts into integer
completed/failed totals, estimate comparisons, retention ranges, failure-category
counts, and sorted evidence appearances.
`offline-ticket-admission-telemetry-collection-v1` fingerprints canonical documents
as `ticket-admission-telemetry-document-v1:sha256:<hex>`. Configurable limits
default to 4,096 documents and 16 MiB of canonical input. Exact-byte duplicates
share one entry with occurrence and input/unique/duplicate byte counts; unique
entries remain fingerprint-ordered with one summary per distinct document.
Nonidentical snapshots are never merged even when contexts or sequence ranges
overlap; digest collisions fail closed.
`offline-ticket-admission-telemetry-overlap-v1` compares two validated canonical
documents in fingerprint order. Each FIFO reports capacities, retained half-open
sequence ranges, exact overlap bounds, matching observation counts, and conflicting
sequence IDs, including empty and no-overlap classifications. Exact document
equality is distinct from retained-data compatibility.
`offline-ticket-admission-telemetry-overlap-index-v1` first deduplicates the
bounded canonical collection, then compares every unique fingerprint-ordered pair
within a configurable budget that defaults to 65,536 pairs. The pair budget is
checked before comparison. Completed and failed classification summaries count
conflicting, matching, no-overlap, and empty pairs independently. Exact duplicates
remain collection occurrences and do not create pair reports.
`offline-ticket-admission-telemetry-overlap-components-v1` selects an undirected
compatibility edge only when completed and failed FIFOs contain at least one exact
matching observation in total and neither FIFO has conflicting sequence IDs.
Isolated unique documents remain singleton components. Each component publishes a
stable SHA-256 identity over sorted members and direct edges, direct/possible/missing
edge counts, and a clique flag. A transitive bridge may connect documents that have
no direct edge, so connectivity is not pairwise equivalence or recorder lineage.
Matching observations may be coincidental; pairwise, indexed, and component review
never attributes lineage.
`authenticated-ticket-admission-telemetry-lineage-v1` separately binds the exact
canonical document fingerprint to caller-supplied recorder, completed/failed stream,
capture sequence, key, and optional immediate-predecessor identities. Canonical
HMAC-SHA-256 uses a caller-owned secret of at least 32 bytes and stores only the
key identity and MAC. Explicit verification reselects the trusted key identity and
secret. Same-sequence forks, adjacent predecessor mismatch, nonadjacent direct
links, MAC mismatch, document mismatch, and hash collisions fail closed. Different
recorder or stream identities are not common lineage; ordered gaps retain common
lineage without a direct link. Key legitimacy remains caller-owned.
`caller-owned-ticket-admission-telemetry-lineage-trust-v1` creates an explicit
in-memory set of at most 256 unique HMAC keys sorted by identity. Each entry owns
an inclusive first/optional-last capture sequence window; empty sets trust nothing.
Exact key identity and window selection precede MAC verification. Independently
verified canonical materials preserve cross-key direct-successor, ordered-gap,
fork, and collision checks. Duplicate identities, malformed windows, unknown keys,
out-of-window captures, and incorrect secrets fail closed. Secret fields are hidden
from representations.
`ticket-admission-telemetry-lineage-trust-manifest-v1` canonically stores only key
identity, opaque key-reference identity, and inclusive capture windows. Its explicit
read/write boundary defaults to 256 entries and 64 KiB, assigns a SHA-256 identity
to canonical bytes, and resolves only from exact caller-supplied secret coverage.
Resolution binds in-memory trust to the manifest identity but does not certify a
secret until an attestation verifies. Duplicate keys/references, malformed or
noncanonical JSON, incomplete or excessive coverage, reference mismatch, and
storage failures fail closed.
`explicit-ticket-admission-telemetry-lineage-secret-provider-v1` accepts exactly one
caller-supplied synchronous port. Manifest validation and the configurable request
budget, default 256, complete before provider work. Requests are immutable and
canonical-key ordered; each reference is called once. Typed `unavailable` or
`failed` results stop without retry, and no vendor text enters the contract.
Repeated explicit resolution performs a new provider walk. Resolved bytes remain
unverified until attestation authentication.
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
The built-in public-key implementations are the bounded caller-owned memory
service, its inline sequential and batch async adapters, its serial session
adapter, explicit canonical file bundles, synchronous plus async
transport-neutral fetch ports, a concrete synchronous HTTPS GET adapter,
a caller-offloaded async HTTPS adapter, explicit synchronous and async
Authorization-provider ports, an explicit authorized HTTPS adapter, and a
caller-offloaded async
authorized HTTPS adapter. There is no built-in secret provider implementation,
native nonblocking HTTPS client, concrete credential provider, automatic
credential refresh, or hosted key service.
No bundle or session is loaded automatically;
there is no discovery, retry,
retained cache, persistence, automatic trust
loading, snapshot merge, route recommendation, evidence promotion, or policy
update. The registry now selects at most one
exact workload/capability/runtime record, permits distinct runtime variants, and
rejects invalid or ambiguous selection. This closes exact queue-size,
generated-profile, runtime, display-driver, host/Python identity,
registry-resolution, and offline admission-explanation slices; evidence for other
hosts, Python versions, drivers, devices, workloads, concrete public-key
signature algorithms, native async HTTPS public-key transports,
synchronous or async concrete
Authorization providers, hosted-service integrations,
certificates, PKI/trust distribution, and automatic adaptive queue/resource
feedback remain open.

## Threats to Validity

Initial threats include challenge-family bias, hardware/toolchain sensitivity,
search-seed variance, verifier bounds, and overfitting to small Malbolge blocks.
Each experiment must narrow these threats before drawing a conclusion.

## Conclusion

Accept the measured-memory planner as a correctness-preserving allocation guard
for resident classic and current-profile CUDA execution. The first retained RTX
4060 current-profile matrix reached about 40.08 VMs/s at batch 32 and showed that
state movement dominated its 64-step complete-snapshot workload. Device-side
replication now raises the retained batch-32 result to about 51.67 VMs/s and cuts
median upload time about 6.93x. Persistent scalable sessions separately reach
about 2.00 million 64-step VM segments/s at batch 128 when complete state remains
resident and setup/observation/snapshots are outside the timed region. This
confirms transfer avoidance as a high-leverage continuation boundary. A later
`ProfileMemoryImage` experiment validates and owns one geometry-bound input once;
on the same RTX 4060 matrix, median validation/planning falls from about 62.40 ms
to 0.23 ms at batch 32 and complete throughput reaches about 93.68 VMs/s. The
remaining measured complete-run host boundary is snapshot construction/download
and final `array('I')` materialization. None of these values is a CPU-relative or
cross-device speedup claim; broader hardware evidence remains open.

## References

- [Replaceable Accelerator And Algorithm
  Ports](../../../technical/adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust
  Boundary](../../../technical/adr/verification-trust-boundary.md)
- [Research Evidence And Algorithm
  Mirror](../../adr/research-evidence-and-algorithm-mirror.md)

A subsequent direct-snapshot experiment removes the packed intermediate host
memory buffer and downloads each VM directly into its final compact result
array. On the same 14-trit/64-step RTX 4060 workload, retained batch-32
throughput reaches about 93.68 VMs/s. Median batch-32 host construction is
about 13.39 ms and result decode/materialization about 163.34 ms; the
remaining roughly 97.97 ms D-to-H phase is the requested complete snapshot
transfer itself rather than a redundant second copy.

