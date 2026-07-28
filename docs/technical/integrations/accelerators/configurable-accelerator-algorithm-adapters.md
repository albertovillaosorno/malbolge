# Configurable accelerator algorithm adapters

## Status

Active implementation

## Purpose

Separate optimization/search strategy from accelerator hardware. Define common
algorithm ports for enumerative, stochastic, Monte Carlo, evolutionary, learned,
hybrid, pruning, and future strategies, and let CPU, CUDA, ROCm, or later
hardware adapters provide execution capacity for those strategies. Select
algorithms and hardware through deterministic configuration with optional CLI
overrides, record the exact combination in benchmark evidence, and permit side-
by-side comparison without recompiling or modifying compiler semantics.

## Scope

This document governs the following declared TODO scope:

- `accelerator/`
- `algorithms/`
- `optimizer/`
- `benchmarks/accelerator/`
- `tests/optimizer/`

## Current Behavior

### Active Model

`SearchRequest` binds an algorithm ID, deterministic seed, evaluation budget, and
opaque problem bytes independently from backend capability.
`SearchExecutionAdapter` supplies execution capacity only; returned
`CandidateProposal` values are untrusted until `TrustedCandidateVerifier` admits
them. `CpuSearchExecutionAdapter` supplies the mandatory portable callback path.
The same boundary separates candidate-evaluation evidence and optional
verification hints from candidate acceptance.

### Implementation Status

The selection-independent contract is active. Algorithm ID is request identity
while `AcceleratorCapability` is backend identity, so the two dimensions are
recorded independently. `SearchSelection` plus `SearchAdapterBinding` resolve one
mandatory `cpu-reference` implementation and an optional preferred backend.
Algorithm/backend overrides are explicit and unsupported combinations fail
before search starts. `SearchRunIdentity` records both configured and actual
backend IDs, so a CPU fallback cannot be mislabeled as accelerated evidence.
`accelerator/search_config.py` adds versioned `schema_version = 1` TOML selection
with independent `algorithm_id`/`backend_id`, fail-closed unknown keys, durable
configuration-source identity, and explicit caller overrides that never mutate
the loaded base configuration. The first concrete strategy is
`deterministic-corpus-enumeration-v1`, bound to the mandatory CPU reference
through the same registry. Candidate evidence can independently feed optional
verification-assist hints through CPU or CUDA without granting either backend
acceptance authority. `EvaluatedSearchExecutionAdapter` now binds deterministic
batch construction and proposal selection to a replaceable candidate evaluator;
selected proposals must be byte-identical members of the evaluated batch and the
evaluation count cannot exceed the search budget. The concrete
`classic-rotate-target-search-v1` strategy runs unchanged through CPU or live CUDA
evaluation. CUDA and CPU produce identical proposals over a deterministic
257-candidate corpus, `SearchRunIdentity` records CUDA as actual execution, and a
separate CPU verifier recomputes acceptance. `optimizer/cli.py` now exposes the
same registry externally through `python -m optimizer.cli`. It reads versioned
TOML configuration plus canonical binary problem bytes, accepts explicit
algorithm/backend overrides, and emits deterministic JSON with configuration
source, problem SHA-256, configured and actual backend IDs, device metadata,
seed/budget, and hex-encoded proposals marked `untrusted`. A supported CUDA route
that cannot initialize is represented as optional unavailable capacity and falls
back through the normal CPU reference path while retaining configured CUDA
identity. Unsupported pairs such as deterministic corpus enumeration plus CUDA
fail explicitly instead of changing strategy. The first retained side-by-side
performance record uses the complete 59,049-word classic domain with 15 retained
samples per backend, one warmup, fixed CPU-then-CUDA interleaving, retain-all
outlier policy, exact proposal equality, and independent CPU admission. On the
RTX 4060, CPU median is 401.185 ms and CUDA median is 412.570 ms, producing a
0.972x CUDA/CPU ratio. The preregistered speedup hypothesis is therefore rejected
for this host-heavy route; no CUDA performance benefit is claimed. A separate
phase profile retains 15 profiles per backend and explains 97.5% of CPU and 99.5%
of CUDA median total time through named phases. For CUDA, host-side phases account
for about 57.0% of median total time while backend evaluation accounts for about
42.5%; batch construction plus proposal selection consume about 173.081 ms.
`PreparedEvaluatedSearch` now implements the target: `prepare()` validates request
and batch exactly once and emits immutable state bound to algorithm ID plus the
concrete batch-builder/selector identities. Matching CPU and CUDA adapters may
reuse that proof; forged or different strategy bindings fail closed.
`search_prepared()` and `profile_prepared_search()` preserve untrusted proposal
and result validation while removing repeated batch construction and validation
from the amortized path. Rotate-target selection additionally decodes only the
validated target/header. The retained four-route comparison records CPU
ordinary/prepared medians of 293.564/148.590 ms (1.976x) and CUDA
ordinary/prepared medians of 306.872/162.693 ms (1.886x). Prepared CUDA remains
about 9.5% slower than prepared CPU, so reusable state is beneficial without
establishing a CUDA advantage. Preparation is outside timed intervals. The
prepared-path profile attributes 79.9% of CPU and 81.2% of CUDA median total time
to backend evaluation, with proposal selection at 19.6% and 18.7%. Strategy-proof
and result validation are negligible. `PackedCandidateEvidence` now implements the
next neutral boundary: fixed-width opaque payloads share one byte buffer and inherit
logical identity from validated request order. Existing item-based results remain
valid; packed width/size/mixed representation failures are rejected. Primitive
selectors iterate packed u32 evidence without materializing per-item bytes, while
verification-assist materializes only when producing explicit hint objects.
Retained packed evidence lowers CPU ordinary/prepared medians to
211.693/77.309 ms and CUDA medians to 230.144/91.199 ms. Relative to pre-packed
routes, the improvements are 1.387x/1.922x for CPU and 1.333x/1.784x for CUDA.
Packed backend evaluation falls to 53.907 ms CPU and 67.202 ms CUDA; selection
falls to 22.502/22.288 ms. Packed CUDA prepared remains about 18.0% slower than
packed CPU prepared. `PreparedCandidateExecution` now extends strategy identity
with an optional candidate-state preparer and backend-specific prepared evaluator.
Rotate preparation validates and decodes one hardware-neutral `PrimitiveBatch`
once; matching CPU/CUDA strategies reuse it, while forged type/kind/evaluator
state or a distinct preparer fails closed. Generic strategies without candidate
state retain their previous behavior. Retained prepared medians are 43.129 ms CPU
and 57.296 ms CUDA, 1.792x/1.592x faster than the packed prepared baseline.
Ordinary routes regress 6.6%/3.7%, and prepared CUDA remains 32.8% slower than CPU.
Backend evaluation falls 2.801x/2.083x while selection is unchanged.
`PreparedPrimitiveBatch` now adds repository-sealed validation proof below the
candidate strategy. CPU prepared evaluation consumes it directly; CUDA keeps one
proof-bound input/output allocation resident and rebuilds only for a different
proof object. Ordinary execution remains one-shot. Session statistics and benchmark
assertions expose actual build/reuse counts rather than inferring residence from
timing. Retained resident evidence records 34.132 ms CUDA prepared versus
46.232 ms CPU prepared (1.355x CUDA/CPU) and a 1.679x improvement over the prior
CUDA prepared baseline. CUDA backend evaluation improves 3.252x to 9.922 ms, but
complete phase total stays flat/slightly worse because proposal selection rises to
46.331 ms. `PreparedEvaluatedSearch` now builds an immutable exact membership
index from the validated candidate `(logical_id, payload)` pairs. Prepared CPU/CUDA
proposal validation reuses the index, while ordinary execution retains the one-shot
dictionary path. Fabricated payloads still fail closed, and benchmarks require
59,049 indexed members. Retained prepared medians are 26.797 ms CPU and 17.970 ms
CUDA, improvements of 1.725x/1.899x over the resident baseline; CUDA is 1.491x
faster in the same run. Selection improves 3.519x/3.939x to 11.801/11.761 ms.
Ordinary/backend controls also improve, so the direct phase change bounds causal
attribution. `PreparedProposalSelection` now adds strategy-owned preparation,
selection, and state-count callbacks to the strategy identity. Rotate target state
uses the exact inverse of the classic rotate bijection and records only preimage
positions that survive pruning, seed order, and budget. Prepared selection reads
and validates packed evidence only at those positions; ordinary search retains the
full scan. Missing/excluded positions, forged state, and nonmatching evidence remain
fail-closed. Benchmarks require one canonical position. Retained prepared medians
are 15.266 ms CPU and 6.182 ms CUDA, improvements of 1.755x/2.907x over indexed
membership; CUDA is 2.470x faster in the same run. Selection improves
894.008x/948.452x to 13.2/12.4 us. Ordinary controls improve only 1.022x/1.015x and
backend phases only 1.034x/1.035x, strongly bounding attribution. Primitive backend
execution selected the next neutral boundary. Primitive result validation now uses
exact tuple minimum/maximum bounds rather than an interpreted per-value loop. Both negative and above-domain evidence still fail before packing. Retained
prepared medians improve 1.086x CPU and 1.254x CUDA; backend evaluation improves
1.091x/1.330x while ordinary controls remain nearly flat. Prepared CPU rotate now
uses a cached 59,049-entry table generated exclusively from the scalar reference.
Ordinary CPU evaluation remains scalar. An exhaustive classic-domain test and
benchmark diagnostics require exact equality, 16 prepared evaluations, and full
table cardinality. Retained CPU prepared median falls from 14.058 to 3.313 ms
(4.243x), and CPU backend evaluation from 13.190 to 2.906 ms (4.540x). CPU ordinary
is effectively unchanged; same-run CPU prepared is 1.440x faster than CUDA prepared.
`PackedPrimitiveResult` now extends the neutral result contract with canonical
little-endian u32 bytes while preserving tuple compatibility. Prepared CUDA exposes
the resident host output without tuple materialization or repacking. The bridge
still validates capability identity, exact result count, and every word's classic
bound before candidate evidence acceptance. Ordinary CUDA and CPU paths remain
tuple-based. Benchmarks require 16 packed CUDA evaluations plus all prior proofs.
Retained CUDA prepared median falls from 4.769 to 2.036 ms (2.343x), and CUDA
backend evaluation from 3.868 to 1.802 ms (2.147x). CPU prepared/backend change only
1.004x/1.005x, and ordinary controls remain effectively flat. CUDA prepared is
1.621x faster than same-run CPU. Packed validation now has stable identity
`u32le-broadword-domain-v1`. A repeated high-word mask establishes unsigned 16-bit
lanes; adding `0xffff - 59048` independently in each 32-bit lane sets bit 16 exactly
when a word exceeds the classic maximum. Failure falls back to scalar decoding only
for diagnostics. First/last-lane threshold and high-bit adversaries fail closed, and
benchmarks require the identity. Retained CUDA prepared median falls from 2.036
to 1.175 ms (1.733x), CUDA backend evaluation from 1.802 to 0.860 ms (2.095x), and
CUDA total from 1.824 to 0.886 ms (2.057x). CUDA is 2.706x faster than same-run CPU.
CPU phase regressions remain contextual controls. Public diagnostic records now
cover resident CUDA launch/sync, transfer, immutable-byte materialization, and total
plus neutral packed contract, masks, integer decode, high-mask, threshold,
diagnostic, result construction, and total. The dedicated full-domain profiler
historically requires exact CPU packed equality around broadword validation. The
active prepared strategy now retains immutable CPU-reference bytes once during
preparation and validates every prepared backend result with
`cpu-reference-packed-equality-v1`. Ordinary routes continue to use
`u32le-broadword-domain-v1`. Capability, immutable representation, and exact count
precede equality; first/final in-domain drift fails closed with a precise mismatch.
A generic proof-bound candidate-state count exposes all 59,049 reference words.
Benchmarks require both IDs and all existing CPU-table, CUDA-session, membership,
and selector proofs. Retained CUDA prepared search is 0.488 ms, 2.407x better than
broadword validation and 6.786x faster than same-run CPU. CUDA backend/total improve
3.999x/3.729x to 0.215/0.238 ms. Exact prepared validation improves 23.590x to
0.0278 ms, including 0.0180 ms equality; primitive end-to-end improves 4.488x to
0.1935 ms. The 236,196-byte reference and its construction are preparation costs,
not timed execution. The active crossover benchmark measures fresh-process and
warm-process preparation, incremental Python memory, first resident execution,
steady reuse, and strict amortization at four corpus sizes. Validator identities,
exact proposal/admission, reference/membership/selector counts, and CUDA counters
remain required. Retained warm crossover is 6/3/2/1 and cold crossover is
106/38/5/2. Full-domain warm preparation plus first search is 212.140 ms versus
222.842 ms ordinary; cold crosses on run two. Incremental Python state
retains/peaks at 16.063/19.040 MiB versus 0.901 MiB exact buffers. Component tracing selected the duplicate membership frozenset for the first safe
compaction. Prepared membership now uses
`identity-sorted-candidate-reference-binary-search-v1`, a proof-bound sorted tuple of
references to the original immutable batch items. Binary search locates logical IDs
and exact payload equality preserves anti-fabrication semantics. Forged/cross-batch
indexes fail closed. Retained version-2 evidence under
`benchmarks/accelerator/evidence/2026-07-28-compact-membership-crossover-rtx4060/`
shows 91.945% lower full-domain component retention and 1.137x faster component
preparation. Complete prepared retention/peak fall 32.083%/26.051%. Binary hit/miss
lookup regresses 9.898x/13.856x versus the copied set, so promotion is explicitly for
scale memory/preparation. Warm/cold crossover is 7/3/2/1 and 108/38/5/1. This is
the retained version-2 baseline.
The next slice is now active. Rotate-target batch construction uses proof-carrying
`IndexedCandidateWorkItems` under
`u32-index-fixed-width-payloads-rotation-v1`: original u32 logical indexes and
fixed-width payloads remain in immutable bytes, while IDs and item objects
materialize only at consumer boundaries. Exact duplicate pruning now admits generic
hashable exact equality, so injective u32 encoding does not create temporary payload
objects before pruning. A validated rotation pivot lets
`u32-rotation-or-pair-or-reference-binary-search-v1` search two ordered regions
without retaining a sorted reference or pair array; arbitrary indexed batches and
ordinary tuple batches retain exact pair/reference fallbacks. Ordinary indexed
proposal admission also uses the direct proof-bound lookup instead of materializing
a one-shot identity/payload dictionary. Duplicate or
out-of-domain indexes, malformed widths/sizes, incorrect pivots, forged/cross-batch
proofs, and payload substitution fail closed. Crossover protocol v3 records both
storage identities. Clean post-commit memory, preparation, lookup, and crossover
evidence is pending; the retained prepared primitive integer tuple is the next
candidate only after this result is measured.
Resident or fused
evaluation-selection remains a later
option only if exact equivalence stays explicit. Synthesis and guided strategies,
ROCm search implementations, richer
orchestration, and broader representative benchmark evidence remain open.

## Invariants

- Hardware backend and search/optimization strategy are independently selected;
  unsupported combinations fail explicitly and benchmark identity records both
  dimensions.
- A CPU/reference path remains sufficient for correctness, and accelerator
  failure/unavailability changes performance rather than semantic acceptance.

## Failure Behavior

Missing hardware, resource exhaustion, or accelerator disagreement falls back or
fails explicitly without changing correctness rules.

## Verification

- Expected durable artifact surface: `accelerator/`, `algorithms/`,
  `optimizer/`, `benchmarks/accelerator/`, `tests/optimizer/`.
- Required evidence: CPU/reference differential results, device/resource
  metadata, failure/fallback tests, and benchmark samples for claimed speedups.
- `tests/optimizer/test_search_config.py` verifies schema versioning, independent
  algorithm/backend fields, explicit overrides, unknown-key rejection, mandatory
  nonempty identities, and durable file-source identity.
- `tests/optimizer/test_search_cli.py` verifies CPU execution evidence, explicit
  overrides, unsupported-pair rejection, CUDA-unavailable CPU fallback with
  configured identity preserved, file-backed JSON output, and a live CUDA route
  that records CUDA as actual execution.
- `benchmarks/accelerator/evidence/2026-07-27-rotate-target-search-rtx4060/`
  retains Benchmark Protocol v1 metadata, an Experiment Manifest v1 run, 30 raw
  samples, structured output, exact source commit, workload SHA-256, device and
  toolchain identity, proposal-equality checks, and the negative 0.972x median
  CUDA/CPU result.
- `benchmarks/accelerator/evidence/2026-07-27-rotate-target-search-phase-profile-rtx4060/`
  retains Benchmark Protocol v1 phase attribution with 210 raw phase samples,
  exact source/workload identity, proposal equality, independent CPU admission,
  97.5% CPU named-phase coverage, 99.5% CUDA named-phase coverage, and the
  host-versus-backend split motivating prepared search state.
- `benchmarks/accelerator/evidence/2026-07-28-prepared-search-rtx4060/`
  retains Benchmark Protocol v1 metadata, 60 raw interleaved samples, exact
  source/workload identity, proposal/admission checks, 1.976x CPU and 1.886x CUDA
  same-backend prepared improvements, and the negative 0.913x prepared CUDA/CPU
  comparison boundary.
- `benchmarks/accelerator/evidence/2026-07-28-prepared-search-phase-profile-rtx4060/`
  retains 150 raw prepared-path phase samples. Backend evaluation accounts for
  79.9% of CPU and 81.2% of CUDA median total time; proposal selection accounts
  for 19.6% and 18.7%, selecting result representation/transport as the next
  measured boundary.
- `benchmarks/accelerator/evidence/2026-07-28-packed-search-rtx4060/` and
  `2026-07-28-packed-search-phase-profile-rtx4060/` retain 60 throughput samples
  plus 150 phase samples. All four route medians improve; backend evaluation falls
  2.326x on CPU and 2.058x on CUDA, while exact proposals/admission remain stable.
- `benchmarks/accelerator/evidence/2026-07-28-prepared-primitive-search-rtx4060/`
  and its phase-profile sibling retain 60 throughput plus 150 phase samples.
  Prepared medians improve 1.792x CPU and 1.592x CUDA; ordinary-route regressions
  and the remaining 32.8% CUDA disadvantage are retained explicitly.
- `benchmarks/accelerator/evidence/2026-07-28-resident-primitive-search-rtx4060/`
  and its phase sibling retain 60 throughput plus 150 phase samples and explicit
  session counters. CUDA prepared reaches 34.132 ms, 1.355x faster than same-run
  CPU; CUDA backend evaluation improves 3.252x, while total phase time does not.
- `benchmarks/accelerator/evidence/2026-07-28-indexed-membership-search-rtx4060/`
  and its phase sibling retain full index/session identity. Prepared medians improve
  1.725x CPU and 1.899x CUDA; proposal selection improves 3.519x/3.939x.
- `benchmarks/accelerator/evidence/2026-07-28-direct-rotate-selection-rtx4060/`
  and its phase sibling retain selector/index/session proof identity. Prepared
  medians improve 1.755x CPU and 2.907x CUDA; selection improves
  894.008x/948.452x to microsecond scale.
- `benchmarks/accelerator/evidence/2026-07-28-extrema-validation-search-rtx4060/`
  and its phase sibling retain negative/overflow failure plus all prepared proofs.
  Prepared medians improve 1.086x CPU and 1.254x CUDA; backend phases improve
  1.091x/1.330x while ordinary controls remain effectively unchanged.
- Prerequisite completion evidence: `replaceable-accelerator-boundary`,
  `algorithm-research-mirror-and-local-output-contract`.
## References

### Host Architecture Baseline

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`

- [Replaceable Accelerator And Algorithm
  Ports](../../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md`
- `docs/technical/adr/verification-trust-boundary.md`
