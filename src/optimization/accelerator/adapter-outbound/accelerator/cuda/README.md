# CUDA exact accelerator adapter

This directory owns the optional NVIDIA CUDA implementation behind the shared
accelerator contract. It is not a semantic dependency of the compiler, verifier,
or VM.

The active slices evaluate exact classic `rotate`/`crazy` batches, compact
one-step classic transitions, and complete resident bounded runs with
integer-only
CUDA kernels. The resident kernel is geometry-bound: classic uses 10 trits and
59,049 words, while `malbolge-2026.2` uses 14 trits and 4,782,969 words. One GPU
thread owns one independent complete memory image and performs its whole step
budget without round-tripping guest state through the host between steps. A
narrow
standard-library `ctypes` runtime binds only the reviewed NVRTC and CUDA Driver
API
calls needed by the adapter. Normative Rust execution remains the differential
correctness oracle.

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
idempotent, limits cannot be widened after construction, snapshots are ordered
by
fingerprint, and removal releases exact document and byte budgets. Invalid
fingerprints/documents, budget overflow, collisions, or retained decode failure
fail
closed without partial mutation. The memory adapter performs no filesystem I/O,
automatic loading, summaries, merging, recommendations, or admission changes.
`ticket-admission-telemetry-schema-migration-v1` publishes a fixed lossless
1-to-1, 1-to-2, 2-to-1, and 2-to-2 compatibility matrix. Schema-v2 is canonical
sorted JSON containing the exact canonical schema-v1 bytes as standard Base64,
plus the required schema-v1 document identity and SHA-256 fingerprint. Versioned
decoding defaults to 2 MiB outer bytes, 1 MiB embedded source bytes, and 4,096
observations per FIFO. Upgrade and downgrade are explicit; schema-v1 bytes
remain
unchanged. There is no automatic migration, file loading, snapshot
reinterpretation, merge, recommendation, lineage inference, or policy change.
`offline-ticket-admission-telemetry-summary-v1` validates one explicit document
and groups retained observations by exact backend, device, workload, and ticket
count. It publishes completed/failed integer totals, estimate-comparison counts,
retention ranges, stable failure categories, and sorted selected-evidence
appearances.
`offline-ticket-admission-telemetry-collection-v1` defaults to explicit
4,096-document and 16 MiB canonical-input bounds. It fingerprints canonical
bytes
as `ticket-admission-telemetry-document-v1:sha256:<hex>`, counts byte-identical
occurrences once, publishes input/unique/duplicate byte counts, and orders
unique
entries by fingerprint. Different snapshots remain separate even when their
contexts or sequence ranges overlap; digest collisions fail closed.
`offline-ticket-admission-telemetry-overlap-v1` compares two validated documents
in fingerprint order. For completed and failed FIFOs it publishes capacities,
retained half-open sequence ranges, exact overlap ranges, matching counts, and
conflicting sequence IDs, with explicit empty and no-overlap classifications. An
exact document match is separate from matching retained observations.
`offline-ticket-admission-telemetry-overlap-index-v1` deduplicates one bounded
collection before comparing every unique pair. It defaults to a 65,536-pair
budget, fails before pairwise work when that budget is exceeded, orders reports
by
fingerprint, and publishes completed/failed counts for all four overlap classes.
Exact duplicates remain collection occurrences and never create pairs.
`offline-ticket-admission-telemetry-overlap-components-v1` selects an undirected
edge only when completed and failed FIFOs contain at least one exact matching
observation in total and neither FIFO has a conflicting sequence ID. It retains
isolated unique documents, fingerprints each component, and publishes member,
direct, possible, and missing edge counts plus a clique flag. A bridged
component
may contain member pairs with no direct edge, so connectivity is neither
pairwise
equivalence nor recorder lineage. Component fingerprint collisions fail closed.
`authenticated-ticket-admission-telemetry-lineage-v1` separately binds one exact
document fingerprint to caller-supplied recorder, completed/failed stream,
capture
sequence, key, and optional immediate-predecessor identities. Canonical
HMAC-SHA-256 uses at least 32 caller-owned secret bytes; the secret is never
stored.
Verification requires an explicit trusted key identity and secret. Same-sequence
forks, adjacent predecessor mismatch, nonadjacent direct links, MAC mismatch,
and
fingerprint collisions fail closed. Different recorder or stream identities
remain
separate lineages; ordered gaps are common lineage without a direct link. The
caller owns key legitimacy.
`caller-owned-ticket-admission-telemetry-lineage-trust-v1` builds an explicit
in-memory set of at most 256 unique HMAC keys, sorted by `key_id`. Each key has
an
inclusive first/optional-last capture sequence window; empty sets trust nothing.
Verification selects the exact key identity and window, and independently
verified
items may be compared across a rotation. Duplicate identities, malformed
windows,
unknown keys, out-of-window captures, and incorrect secrets fail closed. Secret
fields are hidden from representations.
`ticket-admission-telemetry-lineage-trust-manifest-v1` canonically persists only
`key_id`, an opaque `key_reference_id`, and inclusive capture windows. It
defaults
to 256 entries and 64 KiB, orders entries by key identity, fingerprints
canonical
bytes, and supports only explicit bounded reads and atomic replacement.
Resolution
requires exact caller-supplied key/reference coverage and produces
manifest-bound
in-memory trust. A resolved secret is not certified until an attestation
verifies.
Duplicate keys/references, malformed or noncanonical JSON, incomplete or
excessive
coverage, reference mismatch, and storage failures fail closed. Secrets never
enter
manifest bytes.
`explicit-ticket-admission-telemetry-lineage-secret-provider-v1` accepts one
caller-supplied synchronous provider. Manifest validation and a default
256-request
budget complete before the first call. Immutable requests follow canonical key
order and carry manifest/provider identity, key/reference identity, capture
window,
and request index. Providers return only typed `resolved`, `unavailable`, or
`failed` results; non-success stops without retry, and each entry is called
exactly
once. Repeated explicit resolutions call the provider again. Secret bytes remain
hidden, and resolution still does not authenticate them before attestation use.
`bounded-in-memory-ticket-admission-telemetry-lineage-secret-provider-v1`
implements one reusable bounded caller-owned synchronous provider over explicit
immutable secret entries. Each hidden key is bound to one canonical manifest
fingerprint, key reference, key identity, and inclusive capture window. The
service
permits 256 entries by default and 4096 at the supported maximum, sorts entries
by
manifest fingerprint and reference, and rejects duplicate manifest/reference
bindings. Construction and every call revalidate the exact service type and
identity, provider identity, configured limit, secret count, entry tuple,
canonical
ordering, shared 32-to-4096-byte key rules, request metadata, and each hidden
key. A
different provider identity returns typed `failed`; an unknown
manifest/reference
returns `unavailable`; a known binding with conflicting key/window metadata
returns
`failed`; and an exact binding returns `resolved` with unchanged hidden bytes.
Request index remains ordering context rather than a secret binding. Repeated
calls
validate and resolve again without mutation or an external cache. The service
reads
no environment, file, network, process credential state, secret store, or hosted
API
and performs no discovery, refresh, retry, persistence, logging, worker
creation,
certificate rule, PKI operation, algorithm choice, or admission-policy
operation.
`explicit-async-ticket-admission-telemetry-lineage-secret-provider-v1`
defines one caller-driven sequential async port over the same manifest-bound
requests and typed outcomes. The synchronous port exposes one immutable
nonsecret
preflight, exact request/result validators, one result materializer, and one
final
trust materializer; both routes share those contracts. Manifest validation,
provider identity, and the request budget complete before the first `await`. The
provider is awaited once per entry in canonical order and never concurrently.
Cancellation propagates directly; ordinary provider exceptions become stable
errors
without vendor text; typed non-success stops the walk without retry. Repeated
explicit resolutions await again. The port creates no event loop, task, thread,
executor, worker, cache, lifecycle, discovery, refresh, persistence,
secret-store
access, certificate rule, PKI operation, algorithm choice, or policy operation.
`bounded-in-memory-async-ticket-admission-telemetry-lineage-secret-provider-v1`
adapts one exact bounded memory secret provider to that async port. Construction
and
every call revalidate the adapter identity, hidden wrapped service, provider
identity, secret count, and entry limit. Each await delegates exactly once to
the
synchronous memory lookup and completes inline without an internal suspension or
hidden task. Repeated calls reuse only explicit immutable caller-owned memory
and
validate it again. The adapter reads no environment, file, network, process
credential state, external secret store, or hosted API and adds no retry, cache,
refresh, persistence, logging, worker, certificate, PKI, algorithm, or policy.
`explicit-file-ticket-admission-telemetry-lineage-secret-provider-v1`
implements one bounded read-only provider over caller-supplied absolute
raw-secret
paths. Every hidden path is bound to an exact manifest fingerprint, key
reference,
key identity, and capture window. Construction and validation perform no file
I/O.
A provider mismatch returns typed `failed`; an unknown manifest/reference
returns
`unavailable`; conflicting key/window metadata returns `failed`; all three
outcomes
occur before any open. An exact match opens the selected path once and reads at
most
`max_secret_bytes + 1` bytes. A missing file returns `unavailable`; other read
errors, oversized files, and bytes outside the shared 32-to-4096-byte key
contract
return `failed` without operating-system text. Exact raw bytes, including
trailing
newlines, are preserved. Repeated calls reopen and reread the file, so rotation
is
caller-controlled and no secret cache exists. The provider does not discover
paths,
write files, scan directories, inspect ownership or permissions, validate
symlinks,
decrypt values, create workers, retry, persist, log paths or secrets, choose
algorithms, or change admission policy.
`offloaded-async-file-ticket-admission-telemetry-lineage-secret-provider-v1`
adapts one exact explicit file provider through a caller-supplied async
offloader.
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
caller-owned public-key bytes, and optional HMAC or signature predecessor.
Signers
return typed `signed`, `unavailable`, or `failed`; verifiers return `verified`,
`invalid`, `unavailable`, or `failed`. Each explicit operation calls its port
once
without retry or cache. Verification checks the exact public-key fingerprint
before
the port call, then reuses the common verified-lineage comparison for public-key
rotation and an explicit HMAC-to-signature transition. No concrete signature
algorithm, key generation, private-key storage, certificate chain, PKI, trust
discovery, provider lifecycle, or security claim is supplied by this boundary.
`caller-owned-ticket-admission-telemetry-lineage-signature-trust-v1` builds
an explicit in-memory set of at most 256 unique `(algorithm_id, public_key_id)`
pairs sorted by that composite identity. Each entry binds exact public-key
bytes,
their required SHA-256 fingerprint, and an inclusive first/optional-last capture
window. Empty sets trust nothing. Verification selects the exact algorithm, key
identity, fingerprint, and capture window before calling the verifier;
independently
verified items preserve same-key, public-key rotation, algorithm rotation,
ordered
gap, and fork checks. Duplicate identities, malformed windows, invalid key
bytes,
fingerprint mismatch, unknown identities, out-of-window captures, and tampered
trust metadata fail closed. Public-key bytes are hidden from representations. No
manifest, provider, certificate, PKI, trust discovery, algorithm selection, or
policy authority is supplied.
`ticket-admission-telemetry-lineage-signature-trust-manifest-v1` persists
algorithm identity, public-key identity, one opaque public-key reference, the
required exact public-key fingerprint, and inclusive capture windows as
canonical
key-free JSON. It defaults to 256 entries and 64 KiB, sorts by composite
identity,
requires globally unique references, publishes a stable SHA-256 fingerprint, and
supports only explicit bounded reads or atomic replacement. Resolution requires
exact caller-supplied algorithm/key/reference coverage and exact public-key
bytes
matching the persisted fingerprint before building manifest-bound in-memory
signature trust. The same public-key ID may exist under distinct algorithms.
Duplicate identities or references, malformed or noncanonical JSON, incomplete
or
excessive coverage, reference or fingerprint mismatch, and storage failures fail
closed. No public-key bytes, provider, certificate, PKI, trust discovery,
algorithm
selection, or policy authority are supplied.
`explicit-ticket-admission-telemetry-lineage-public-key-provider-v1` accepts one
caller-supplied synchronous provider. It validates the signature trust manifest
and
a default 256-request budget before the first call, then emits immutable
requests
in canonical `(algorithm_id, public_key_id)` order. Each request carries only
the
manifest/provider identities, algorithm/key/reference identities, required exact
public-key fingerprint, capture window, and request index. Providers return
typed
`resolved`, `unavailable`, or `failed` results. Each entry is called exactly
once;
non-success stops without retry, while repeated explicit resolution performs a
fresh provider walk. Resolved bytes are hidden from representations and must
match
the manifest fingerprint before in-memory signature trust is constructed. No
provider discovery, built-in key service, retry, cache, persistence, hidden
worker,
certificate validation, PKI, algorithm selection, or policy authority is
supplied.
`explicit-async-ticket-admission-telemetry-lineage-public-key-provider-v1`
accepts one caller-supplied async provider and reuses the synchronous request,
result, and resolved-trust contracts. The caller owns and starts the coroutine
and
event loop. Manifest, provider identity, and the default 256-request budget are
validated before the first provider await. Requests are awaited sequentially in
canonical `(algorithm_id, public_key_id)` order, with no task creation or hidden
parallelism; each entry is awaited exactly once and repeated explicit resolution
performs a fresh walk. Typed non-success stops without retry. Ordinary provider
exceptions become stable boundary errors without vendor text, while cancellation
propagates to the caller. Exact public-key fingerprints are checked before trust
construction. This sequential port creates no event loop, task, provider
session,
concurrency policy, discovery, retry, cache, persistence, certificate
validation,
PKI, algorithm selection, or admission authority.
`explicit-async-batch-ticket-admission-telemetry-lineage-public-key-provider-v1`
accepts one caller-supplied async batch provider. Manifest, provider identity,
and
the default 256-request budget are validated before the first await. Empty
manifests
make no provider call; nonempty manifests produce one immutable batch containing
the
full canonical `(algorithm_id, public_key_id)` request tuple and exactly one
provider
await. The provider owns all scheduling and may resolve the batch sequentially
or
concurrently. The boundary requires one exact positional result tuple with
matching
cardinality, validates every shared typed item result, propagates cancellation,
and
converts ordinary provider exceptions to stable errors without vendor text.
Reversed,
missing, excessive, foreign, nonresolved-with-bytes, or fingerprint-mismatched
results
fail closed before trust is returned. This batch port creates no event loop,
task,
concurrency implementation, provider session, discovery, retry, cache,
persistence,
certificate validation, PKI, algorithm selection, or admission authority.
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
`explicit-async-session-ticket-admission-telemetry-lineage-public-key-provider-v1`
accepts one caller-supplied async lifecycle port around the batch provider.
Manifest,
provider identity, and the default 256-request budget are validated before
opening.
Empty manifests perform no lifecycle calls. Nonempty manifests call `open`
exactly
once with immutable manifest fingerprint, provider identity, and request count;
typed outcomes are `opened`, `unavailable`, or `failed`, and only `opened` may
carry
a hidden callable batch provider. The existing canonical batch boundary then
runs
once. Every opened session receives exactly one `close` request with a stable
`completed`, `failed`, or `cancelled` reason; close outcomes are `closed` or
`failed`. Opening exceptions become stable errors without vendor text and
opening
cancellation propagates without closing. After opening, failure or cancellation
attempts one close. Cancellation propagates only after successful close; close
failure replaces the preceding outcome and fails closed. No built-in service,
event loop, task, discovery, retry, cache, persistence, certificate validation,
PKI, algorithm selection, or admission authority is supplied.
`bounded-in-memory-ticket-admission-telemetry-lineage-public-key-provider-v1`
implements the synchronous provider port with one caller-owned immutable key
tuple.
Construction accepts at most 256 entries, validates canonical provider,
algorithm,
key, and reference identities, validates inclusive capture windows, recomputes
every
exact public-key SHA-256 fingerprint, rejects duplicate composite identities and
references, and sorts entries by reference identity. Key bytes are hidden from
representations. Every explicit lookup revalidates service identity, count,
tuple,
ordering, metadata, and exact key bytes. An absent reference returns typed
`unavailable`; a known reference with different algorithm, key, fingerprint, or
window returns typed `failed`; only an exact request returns `resolved`. Empty
services are valid and resolve nothing. The object is reusable caller-owned
memory,
not an automatic or hidden cache. It performs no file, environment, network,
discovery, mutation, retry, persistence, async adaptation, certificate
validation,
PKI, algorithm selection, or admission-policy operation.
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
`bounded-in-memory-async-ticket-admission-telemetry-lineage-public-key-provider-v1`
adapts one exact bounded memory service to the sequential async provider port.
Construction validates the complete wrapped service and retains only its
provider
identity, key count, stable adapter identity, and a hidden service reference.
Every
await revalidates the adapter binding and the complete memory service before
invoking
the synchronous lookup inline. It returns the same typed `resolved`,
`unavailable`,
or `failed` outcome and introduces no internal suspension point; the
caller-owned
event loop cannot run another task merely because this adapter was awaited. The
existing sequential async boundary still performs manifest preflight, canonical
ordering, fingerprint checks, stable exception wrapping, and trust construction.
Empty manifests perform no lookup, while explicit adapter construction already
validates the service. The adapter creates no event loop, task, sleep,
artificial
yield, batch/session lifecycle, file, environment, network, discovery, retry,
persistence, certificate validation, PKI, algorithm selection, or policy
operation.
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
`bounded-memory-async-batch-ticket-admission-telemetry-lineage-public-key-provider-v1`
adapts one exact bounded memory service to the caller-controlled async batch
port.
Construction validates the complete wrapped service and a positive request limit
of
at most the caller-selected boundary, defaulting to 256. Every await revalidates
the
adapter binding and complete memory service, then validates the exact batch
request,
nonempty manifest/provider identities, immutable request tuple, configured
count,
positional indices, and every item manifest/provider binding. Requests are
resolved
inline in tuple order through the synchronous memory service and returned as one
hidden positional result tuple, preserving typed `resolved`, `unavailable`, and
`failed` outcomes. Direct empty batches are valid. The existing batch trust
boundary
still performs manifest preflight, one nonempty provider await, exact
cardinality and
fingerprint checks, and trust construction; empty manifests make no provider
call.
The adapter creates no event loop, task, concurrency, sleep, artificial yield,
session lifecycle, file, environment, network, discovery, retry, persistence,
certificate validation, PKI, algorithm selection, or policy operation.
`memory-async-session-ticket-admission-telemetry-lineage-public-key-provider-v1`
adapts one exact bounded memory service to the explicit async provider-session
port.
Construction validates the memory service, builds its bounded inline batch
adapter,
and stores only caller-owned serial lifecycle state. `open` and `close` complete
inline without scheduling. One active lifecycle is allowed: an exact nonempty
open
request with matching provider identity and bounded request count returns
`opened`
with the hidden memory batch adapter; a second or mismatched open returns
`failed`
without replacing active state. Close requests require the exact persisted
manifest
fingerprint, provider identity, and request count. A mismatch returns `failed`
and
retains active state; an exact close returns `closed`, clears the active
request,
increments a nonnegative completed-lifecycle count, and permits serial reuse.
The
existing session boundary still preflights manifests and budgets, performs no
lifecycle calls for empty manifests, and closes after success or batch failure.
The
adapter creates no event loop, task, lock, concurrency, sleep, artificial yield,
file, environment, network, discovery, retry, persistence, certificate
validation,
PKI, algorithm selection, or policy operation.
`ticket-admission-telemetry-lineage-public-key-bundle-v1` persists one explicit
bounded public-key service as canonical compact UTF-8 JSON. Unlike the key-free
trust manifest, this separate document intentionally contains public-key bytes
as
lowercase hexadecimal. Construction reuses the memory provider to validate exact
bytes, fingerprints, identities, windows, uniqueness, cardinality, and reference
ordering. Encoding uses sorted keys and one trailing newline; decoding requires
byte
identity with that canonical encoding, rejects duplicate or unknown JSON keys,
and
is bounded by 256 entries and 1 MiB by default. Explicit writes atomically
replace
one caller-selected path. Explicit reads consume at most the configured byte
limit.
Each explicit load rereads the path, fingerprints canonical bytes, and builds a
new
caller-owned memory provider with hidden key material and stable non-key
metadata.
There is no path discovery, automatic loading, watch, retained cache, retry,
network
fetch, session creation, certificate validation, PKI, algorithm selection, or
policy
operation.
`explicit-ticket-admission-telemetry-lineage-public-key-bundle-fetcher-v1`
defines one synchronous transport-neutral fetch boundary. The caller constructs
an
exact immutable request binding source identity, resource identity, provider
identity, expected bundle fingerprint, byte limit, and entry limit. All request
metadata and limits are validated before the first transport call. Each
invocation
makes exactly one caller-supplied fetcher call and accepts only the exact typed
`fetched`, `unavailable`, or `failed` result enum. Nonfetched results cannot
carry
bytes. A fetched result requires exact nonempty bytes within the requested
limit,
canonical bundle decoding, a newly materialized caller-owned memory provider,
and
exact matches for the expected bundle fingerprint and provider identity.
Repeated
explicit invocations call the transport again and retain no cache. The boundary
implements no HTTP, TLS, endpoint discovery, credential handling, redirect,
retry,
watch, persistence, certificate validation, PKI, algorithm selection, or policy
operation.
`explicit-async-ticket-admission-telemetry-lineage-public-key-bundle-fetcher-v1`
defines the caller-driven async form of the same transport-neutral boundary. The
caller owns the coroutine and event loop. The exact shared request is completely
validated before the first await, and each invocation awaits the supplied
fetcher
exactly once. The shared typed result, bounded canonical decode, fingerprint and
provider bindings, and caller-owned memory-provider materialization remain the
single synchronous source of validation truth. Ordinary fetcher exceptions
become
stable async-boundary errors without vendor text, while cancellation propagates
directly. Repeated explicit invocations await the transport again and retain no
cache. The boundary creates no event loop, task, worker, concurrency policy,
endpoint discovery, credential handling, redirect, retry, watch, persistence,
certificate validation, PKI, algorithm selection, or policy operation.
`explicit-https-ticket-admission-telemetry-lineage-public-key-bundle-fetcher-v1`
implements one concrete synchronous stdlib HTTPS GET transport. Its exact
immutable
config binds a canonical lowercase ASCII host, TCP port, origin-form target,
source/resource identities, a positive finite timeout capped at 300 seconds, and
a
caller-owned `SSLContext`. Build and every use require hostname checking,
`CERT_REQUIRED`, and TLS 1.2 or newer; the module never creates or loads trust
roots.
Each invocation revalidates the config and shared fetch request, requires exact
source/resource matches, opens one new `HTTPSConnection` with the same caller
context, sends only `GET` with JSON/identity/close headers and no credentials,
and
closes once. Status 200 may return `fetched`; 404 and 410 return `unavailable`;
all
other statuses, including redirects, return `failed`. Successful responses
require
JSON content type with optional UTF-8 charset, absent or identity content
encoding,
an optional canonical positive content length within the request limit, and an
exact
nonempty bytes body read with a `max_bytes + 1` bound. Connection, request,
response,
body-read, or close failures return typed `failed` without vendor text. There is
no
plaintext HTTP, endpoint discovery, credential handling, redirect following,
retry,
watch, cache, persistence, hosted-service API, certificate/PKI ownership,
algorithm
selection, or policy operation.
`offloaded-async-https-ticket-admission-lineage-public-key-bundle-fetcher-v1`
adapts the exact synchronous HTTPS fetcher to the shared async port through one
caller-supplied offloader. Construction and every call fully revalidate the
wrapped
HTTPS fetcher, stable adapter identity, copied fetcher/source/resource bindings,
and
callable offloader. The shared request is validated before the first await; a
source/resource mismatch returns typed `failed` without calling the offloader. A
matched request awaits the offloader exactly once with the same exact fetcher
and
request. The caller alone decides whether that await runs inline, in a thread,
through an executor, or through another scheduling mechanism. Cancellation
propagates directly. Ordinary offloader exceptions become stable adapter errors
without vendor text. Returned results are revalidated for exact type, enum,
payload
presence, exact bytes, nonempty content, and the request byte limit before they
reach
the outer async materialization boundary. Repeated calls revalidate and offload
again. The adapter creates no event loop, task, thread, executor, worker, retry,
redirect, cache, trust root, credential, hosted-service policy, algorithm
choice, or
admission-policy operation.
`explicit-ticket-admission-lineage-https-authorization-provider-v1`
defines one synchronous caller-owned port for resolving an opaque HTTPS
`Authorization` value. Preflight validates the exact HTTPS fetcher, exact
canonical
bundle-fetch request, source/resource binding, canonical authorization-provider
identity, callable provider, and positive byte limit before the provider is
called.
The default limit is 4096 ASCII bytes and the supported maximum is 16384. One
immutable request carries only the bundle fingerprint and nonsecret provider,
resource, and source identities. Each successful preflight makes exactly one
provider call. Stable `resolved`, `unavailable`, and `failed` outcomes carry no
vendor text; nonresolved outcomes cannot carry credential text. A resolved value
must be exact nonempty ASCII field text containing only spaces and visible
characters, with no edge spaces and no normalization. The value is hidden from
representations and returned only in caller-owned state with its exact byte
count
and the fixed `Authorization` header name. Repeated explicit resolutions call
the
provider again. The port does not choose an authorization scheme, inject a
header,
open a connection, discover credentials, retry, cache, persist, log values,
create
workers, own a hosted-service API, validate certificates, distribute PKI, select
a
signature algorithm, or change admission policy.
`explicit-async-ticket-admission-lineage-https-authorization-provider-v1`
defines one caller-driven async port for resolving the same bounded opaque HTTPS
`Authorization` value. The synchronous port now exposes one immutable nonsecret
preflight plus one exact result materializer, and both sync and async resolution
use
those same validators. Preflight validates the exact HTTPS fetcher, canonical
bundle
request, source/resource binding, authorization-provider identity, and positive
byte
limit before the first `await`; a noncallable provider also fails before
awaiting.
One successful preflight awaits the caller-supplied provider exactly once with
the
same exact immutable request. The provider controls whether that await suspends.
Cancellation propagates directly. Ordinary provider exceptions become stable
async
errors without vendor text. The shared materializer enforces exact result type
and
enum, forbids credential text in nonresolved outcomes, requires bounded nonempty
ASCII field text for `resolved`, and returns the same hidden caller-owned
metadata as
the synchronous path. Repeated explicit resolutions await again with no cache or
refresh. The port creates no event loop, task, thread, executor, worker, retry,
discovery, refresh, header injection, hosted-service policy, certificate rule,
PKI
operation, algorithm choice, or admission-policy operation.
`memory-ticket-admission-lineage-https-authorization-provider-v1`
implements one reusable bounded caller-owned synchronous Authorization provider
over
explicit immutable in-memory entries. Each entry binds one hidden Authorization
value and exact byte count to one canonical bundle fingerprint, fetch-provider
identity, resource identity, and source identity. One service binds all entries
to
one authorization-provider identity, permits at most 64 entries by default and
4096
at the supported maximum, requires canonical deterministic ordering, and rejects
duplicate request bindings. Construction and every call revalidate the exact
service
type and identity, provider identity, limits, entry tuple, shared request
metadata,
shared Authorization text rules, byte counts, ordering, and uniqueness. A
request
with a different authorization-provider identity returns typed `failed`; a valid
unmatched request returns `unavailable`; an exact match returns `resolved` with
the
unchanged hidden caller-owned value. Repeated calls perform the same validation
and
lookup without mutation or an external cache. The provider reads no environment,
file, network, process credential state, secret store, or hosted API and
performs no
discovery, refresh, retry, persistence, logging, task creation, certificate
rule,
PKI operation, algorithm choice, or admission-policy operation.
`offloaded-async-file-ticket-admission-lineage-https-authorization-provider-v1`
adapts one exact explicit file Authorization provider to the shared async port
through one caller-supplied offloader. Construction and every call revalidate
the
adapter identity, hidden wrapped provider, copied authorization count, entry and
byte limits, provider identity, and callable offloader. The shared request is
validated before the first `await`; a provider-identity mismatch returns typed
`failed` without invoking the offloader. A matched provider identity awaits the
offloader exactly once with the same exact provider and immutable request. The
caller alone chooses whether the file read completes inline, suspends, or runs
in
a caller-owned thread or executor. Cancellation propagates directly. Ordinary
offloader exceptions become stable adapter errors without path or vendor text.
Returned results are revalidated after the await, including exact result type
and
enum, nonresolved payload absence, canonical ASCII text, and the wrapped
provider
byte limit for resolved values. Repeated calls offload and reread the file so
rotation and removal remain visible without a cache. The adapter creates no
event
loop, task, thread, executor, worker, discovery, retry, refresh, persistence,
logging, scheme selection, certificate rule, PKI operation, algorithm choice, or
admission-policy operation.
`explicit-file-ticket-admission-lineage-https-authorization-provider-v1`
binds exact nonsecret Authorization requests to caller-selected absolute file
paths. Paths and entries stay hidden from representations. Build and validation
perform no file I/O; every call revalidates the exact service, provider
identity,
copied authorization count, entry and byte limits, canonical ordering, request
metadata, and absolute paths before lookup. A provider-identity mismatch returns
typed `failed` without I/O, while an unmatched request returns `unavailable`.
One exact match opens one path once in binary mode and reads at most the
configured
byte limit plus one. Missing files return `unavailable`; operating-system
errors,
oversized content, non-ASCII bytes, empty or noncanonical text, whitespace,
control
bytes, and NUL return `failed` without path or system text. Valid ASCII text is
revalidated through the shared Authorization materializer without trimming or
normalization. Repeated calls reread the file so rotation and removal remain
visible without a cache. The provider performs no discovery, writes, permission
inspection, retries, persistence, logging, worker creation, scheme selection,
credential refresh, certificate validation, PKI, algorithm choice, or policy.
`explicit-environment-ticket-admission-lineage-https-authorization-provider-v1`
implements one bounded synchronous Authorization provider over explicit
immutable
request-to-variable bindings. Each entry hides one canonical uppercase ASCII
environment name and binds it to one exact bundle fingerprint, fetch-provider
identity, resource identity, and source identity. One service binds all entries
to
one authorization-provider identity, permits at most 64 entries by default and
4096
at the supported maximum, limits resolved values to 4096 bytes by default and
16384
at the supported maximum, canonicalizes ordering, and rejects duplicate request
bindings. Construction and validation read no environment state. A
provider-identity
mismatch returns typed `failed`; a valid unmatched request returns
`unavailable`;
only an exact match performs one lookup of the caller-named variable. A missing
variable returns `unavailable`; an operating-system or Unicode lookup failure,
an
invalid nonempty-ASCII Authorization value, or an oversized value returns
`failed`
without variable names, values, or operating-system text. An exact valid value
returns `resolved` unchanged. Repeated calls reread the environment, so
caller-owned
rotation and removal are visible without a cache. The provider never enumerates
or
mutates environment state, discovers names, reads files, network, external
stores,
or hosted APIs, retries, persists, logs names or values, creates workers,
chooses an
Authorization scheme, refreshes credentials, validates certificates, distributes
PKI, selects algorithms, or changes admission policy.
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
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
rotation and removal remain visible without a cache. The adapter creates no
event
loop, task, thread, executor, worker, discovery, refresh, retry, persistence,
logging, hosted-service policy, certificate rule, PKI operation, algorithm
choice, or admission-policy operation.
`memory-async-ticket-admission-lineage-https-authorization-provider-v1`
adapts one exact bounded memory Authorization provider to the shared async
provider
port without introducing a scheduling point. Construction and every call
revalidate
the exact adapter type and identity, wrapped memory service, copied entry count,
entry limit, and authorization-provider identity. A direct await delegates once
to
the same synchronous memory lookup and returns the same typed `resolved`,
`unavailable`, or `failed` result before any other caller task can run. The
shared
async Authorization boundary can therefore materialize the exact hidden value
and
metadata while preserving its own preflight and result validation. Repeated
awaits
reuse only the explicit immutable memory state and perform validation again. The
adapter creates no event loop, task, thread, executor, worker, scheduling point,
environment or file read, network access, secret-store call, discovery, refresh,
retry, external cache, persistence, logging, hosted-service policy, certificate
rule, PKI operation, algorithm choice, or admission-policy operation.
`authorized-https-ticket-admission-lineage-public-key-bundle-fetcher-v1`
binds one exact synchronous HTTPS fetcher to one exact caller-owned resolved
Authorization value. Construction and every call revalidate the wrapped HTTPS
fetcher, resolved Authorization value, stable adapter identity, copied byte
count,
authorization-provider identity, bundle fingerprint, fetch-provider identity,
and
source/resource bindings. A request must exactly match the bound bundle
fingerprint,
fetch provider, source, and resource; any mismatch returns typed `failed` before
a
connection is opened. A matched call opens one connection, sends one `GET` with
the
base JSON/identity/close headers plus exactly one unchanged `Authorization`
header,
reuses the base response/status/body validation, and closes once. The explicit
adapter may be reused with the same caller-owned authorization object, but it
never
calls a credential provider, refreshes credentials, retries, redirects, caches
hidden state, normalizes or selects a scheme, logs credential text, discovers an
endpoint, creates workers, owns a hosted-service API, validates certificates,
distributes PKI, selects a signature algorithm, or changes admission policy.
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
`offloaded-async-authorized-https-ticket-admission-lineage-key-bundle-fetcher-v1`
adapts one exact authorized synchronous HTTPS fetcher to the shared async fetch
port
through one caller-supplied offloader. Construction and every call fully
revalidate
the wrapped authorized fetcher, stable adapter identity, copied authorization
byte
count, authorization-provider identity, bundle fingerprint, fetch-provider
identity,
and source/resource bindings. The shared request is validated before the first
`await`; any fingerprint/provider/source/resource mismatch returns typed
`failed`
without invoking the offloader. A matched request awaits the offloader exactly
once
with the same exact authorized fetcher and request, then revalidates the exact
typed
result and request byte limit. The caller alone decides whether blocking work
runs
inline, in a thread, through an executor, or by another scheduling mechanism.
Cancellation propagates directly. Ordinary offloader exceptions become stable
adapter errors without vendor text. Repeated calls offload again but never
resolve or
refresh credentials. The adapter creates no event loop, task, thread, executor,
worker, retry, redirect, cache, trust root, credential provider, hosted-service
policy, certificate rule, PKI operation, algorithm choice, or admission-policy
operation.
The built-in HMAC-secret implementations are the bounded caller-owned memory
service, its inline sequential async adapter, the explicit read-only file
provider, and its caller-offloaded async adapter. The built-in public-key
implementations are the bounded caller-owned
memory service, its inline sequential and batch async adapters, its serial
session
adapter, explicit canonical file bundles, synchronous plus async
transport-neutral fetch ports, a concrete synchronous HTTPS GET adapter,
a caller-offloaded async HTTPS adapter, explicit synchronous and async
Authorization-provider ports, a bounded caller-owned memory Authorization
provider with an inline async adapter, an explicit file Authorization provider
with a caller-offloaded async adapter,
an explicit environment Authorization provider with a caller-offloaded async
adapter,
an explicit authorized HTTPS adapter,
and a caller-offloaded async authorized HTTPS adapter.
There is no built-in external secret-store integration,
hosted credential provider, native async file-secret or file-Authorization I/O,
native async
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
runtime drifts, multi-profile selection, invalid/unknown workloads, ambiguity,
and
three live CUDA routes. The seven route records and exact
provenance now live in schema-v4
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
`src/optimization/accelerator/adapter-outbound/accelerator/cuda/ticket_admission_profiles.json`,
not Python source.
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
`src/performance/benchmarking/composition/benchmarks/accelerator/ticket_admission_profile_manifest.py`
reconstructs those
canonical bytes from retained JSON/TOML, source commit, exact
raw/structured-output
hashes, the tracked CUDA toolchain manifest, retained driver build, and retained
host/Python context. Twelve manifest tests require byte equality and reject
duplicate or unknown keys, unsupported schema, duplicate routes, malformed
display
versions, invalid host fields, exact runtime-context duplicates, and direct
capability/runtime mismatch; distinct runtime variants may coexist for one
capability/workload. Runtime loading reads only the tracked product manifest and
never opens benchmark evidence. `resolve_cuda_ticket_admission_profile` selects
at
most one exact workload/capability/runtime record; invalid or ambiguous requests
fail closed, while retained wrappers delegate through the stable workload
identity. At adapter
startup, `cuda-runtime-toolchain-identity-v1` requires Driver API 13030 or
newer,
exact NVRTC 13.3, the tracked toolchain SHA-256, and NVML display build
`610.88`;
`cuda-host-runtime-identity-v1` measures Windows 11 Professional build
`10.0.26200`, `x86_64`, and CPython `3.14.6`. Missing or failed optional NVML or
host measurement leaves ordinary CUDA available but this evidence-bound profile
unmatched. Fourteen runtime-identity tests cover required query/hash failures,
NVML lifetimes, host validation, exact live host measurement, and one live CUDA
route. Other hosts, Python versions, driver builds, devices, and workloads
remain
open. The global synchronous default does not change.

The repository pins CUDA 13.3 Update 1 for Windows x86-64 through
`toolchain.json`. Binary redistributables live under ignored
`.dependencies/cuda/13.3.1/`, and every downloaded archive is checked against
the recorded NVIDIA SHA-256. The active adapter requires no third-party Python
packages beyond the repository's pinned Python runtime.

The runtime is now platform-selected. Windows retains `ctypes.WinDLL`,
`nvcuda.dll`, and its reviewed NVRTC DLL identity; Linux uses `ctypes.CDLL`,
`libcuda.so.1`, repository-local NVRTC/builtins ELF libraries, and the separate
Linux manifest. The completed [CUDA Linux runtime and hermetic toolchain
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
contract](../../../../../../docs/technical/integrations/accelerators/cuda-linux-runtime-and-toolchain.md)
also binds the Linux LLVM development kit, clang-tidy module, and normalized C
frontend without changing CPU/verifier authority.

Development evidence on an NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB) runs
NVRTC-generated PTX through the Driver API and matches the CPU reference for
boundary-heavy plus deterministic `rotate`/`crazy` batches. Rust integration
also
sends fourteen compact transition fixtures through an external CUDA worker and
requires exact equality with normative `Machine::step_traced()` across all seven
instructions, no-op, EOF, non-graphical termination, rejected jump atomicity,
pointer wrap, data/encryption aliasing, and already-terminated state. A second
Rust integration sends nine complete classic resident states through a binary
worker and compares all 59,049 memory words plus registers, I/O, termination,
step counts, and atomic rejection. A scalable integration separately supplies
canonical geometry from Rust `current_profile()` and compares eight complete
`malbolge-2026.2` outcomes across all 4,782,969 final memory words, including
real
I/O, EOF, non-graphical termination, rejected jump atomicity, maximum-pointer
wrap, bounded budget exhaustion, live checkpoint resumption, and
already-terminated execution. This is correctness evidence, not a
speedup claim.

The classic resident path now measures free/total device memory with
`cuMemGetInfo_v2` and SM/thread capacity with `cuDeviceGetAttribute`, then
applies
the hardware-neutral resource planner before allocation. There is no fixed
RTX-specific batch ceiling. Classic launches also split before their 32-bit
memory-index product can
overflow. Very large VRAM therefore expands total capacity without requiring one
unsafe monolithic launch. Scalable profile execution uses the same live resource
planner and compact contiguous 32-bit host memory representation. Rust product
batch ports now route both classic and current-profile requests through the real
CUDA workers while retaining safe-Rust fallback. The original current-profile
RTX 4060 baseline remains under
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
`benchmarks/accelerator/evidence/2026-07-27-current-profile-throughput-rtx4060/`.
Post-optimization evidence under
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
`benchmarks/accelerator/evidence/2026-07-27-current-profile-resident-session-rtx4060/`
uses device-to-device replication for shared initial memory: complete-snapshot
batch 32 reaches about 51.67 VMs/s, about 1.289x the retained baseline, and
median upload time falls about 6.93x. Persistent profile sessions separately
reach about 2.00 million 64-step VM segments/s at batch 128 when setup, compact
observation, and snapshots are outside the timed `advance()` region. Validated
`ProfileMemoryImage` inputs now reuse their geometry/domain proof across calls;
retained complete-snapshot batch 32 reaches about 93.68 VMs/s and median
validation/planning is about 0.23 ms. Complete-snapshot materialization,
asynchronous transfer/stream tuning, broader hardware evidence, and CUDA
superoptimization remain open.

Direct current-profile snapshot evidence is retained under
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
`benchmarks/accelerator/evidence/2026-07-27-current-profile-direct-snapshot-rtx4060/`.
The adapter downloads complete memory directly into each final `array('I')`;
batch 32 reaches about 93.68 VMs/s and batch 1 about 60.43 VMs/s on the
retained RTX 4060 workload. This removes redundant packed host staging/copying;
it does not remove the requested full-state transfer.

