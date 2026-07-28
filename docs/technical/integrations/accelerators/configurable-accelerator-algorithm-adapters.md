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
and result validation are negligible. Candidate-evaluation result representation
and transport are therefore the next neutral optimization boundary. Resident or
fused evaluation-selection remains a later
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
