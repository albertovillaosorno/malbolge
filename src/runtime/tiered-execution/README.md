# Tiered Execution

## Purpose

Tiered execution cache, orchestration, and native adapters.

## Ownership

This boundary is owned by `function:tiered-execution`.

## Prohibitions

It must not bypass another function or architectural kind boundary.

## Navigation

- `adapter-outbound/`: governed native/cache parts, bounded opaque-blob
  storage with cooperative conditional publication, atomic filesystem blob-pair
  generations, and standard monotonic interval timing.
- `application/`: explicit bounded opaque-blob and atomic pair persistence plus
  conditional publication use cases.
- `composition/`: handoff plus cached/leased retry routing, semantic rebase,
  exact telemetry summaries, caller-ordered count retention, typed atomic-pair
  CAS plus ordered count/latency persistence and reconciliation, latency
  normalization/refinement, durable merge, assessment, policy
  codec/persistence, ownership, recommendation/request publication, turns,
  cycles, exact interpreter-relative JIT promotion gating, lazy AOT-first JIT
  rescue eligibility, explicit pre-compilation resource/time scheduling, and
  bounded JIT compilation fallback orchestration.
- `port-outbound/`: storage-neutral bounded/conditional blob, atomic blob-pair,
  monotonic clock, and budget-enforcing JIT compiler contracts.
