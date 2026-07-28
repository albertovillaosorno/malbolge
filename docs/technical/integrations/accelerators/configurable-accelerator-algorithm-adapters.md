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
fail explicitly instead of changing strategy. Synthesis/guided strategies, ROCm
search implementations, richer orchestration, and comparative benchmark evidence
remain open.

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
