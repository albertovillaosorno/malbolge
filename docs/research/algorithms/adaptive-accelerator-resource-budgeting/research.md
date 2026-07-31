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
facade resolves the same exact profile before reporting. Three hundred fifty-three
admission/telemetry/persistence/store/migration/summary/collection/overlap/
index/components/lineage/trust/manifest/provider/signature,
twelve manifest, and fourteen runtime-identity tests prevent silent drift,
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
There is no built-in secret provider, discovery, retry, retained cache,
persistence, asynchronous provider lifecycle, automatic trust loading, snapshot
merge, route recommendation, evidence promotion, or policy update.
The registry now selects at most one
exact workload/capability/runtime record, permits distinct runtime variants, and
rejects invalid or ambiguous selection. This closes exact queue-size,
generated-profile, runtime, display-driver, host/Python identity,
registry-resolution, and offline admission-explanation slices; evidence for other
hosts, Python versions, drivers, devices, workloads, concrete public-key
signature algorithms and PKI/trust distribution, and automatic adaptive
queue/resource feedback remain open.

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

