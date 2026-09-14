# Tiered Execution

## Purpose

Tiered execution cache, orchestration, and native adapters.

## Ownership

This boundary is owned by `function:tiered-execution`.

## Prohibitions

It must not bypass another function or architectural kind boundary.

## Navigation

- `adapter-outbound/`: governed native/cache parts, bounded opaque-blob
  storage, and standard monotonic interval timing.
- `application/`: explicit bounded opaque-blob persistence use cases.
- `composition/`: handoff plus cached/leased retry routing, semantic rebase,
  exact telemetry summaries, latency schema normalization/assessment, policy
  recommendation/request publication, turns, and cycles.
- `port-outbound/`: storage-neutral bounded-blob and monotonic clock contracts.
