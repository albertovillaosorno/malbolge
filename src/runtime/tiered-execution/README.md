# Tiered Execution

## Purpose

Tiered execution cache, orchestration, and native adapters.

## Ownership

This boundary is owned by `function:tiered-execution`.

## Prohibitions

It must not bypass another function or architectural kind boundary.

## Navigation

- `adapter-outbound/`: governed native/cache parts, bounded opaque-blob
  storage with cooperative conditional publication, and standard monotonic
  interval timing.
- `application/`: explicit bounded opaque-blob persistence and conditional
  publication use cases.
- `composition/`: handoff plus cached/leased retry routing, semantic rebase,
  exact telemetry summaries, latency normalization/refinement/durable merge,
  assessment, policy snapshot/codec/persistence, durable revisioned state,
  ownership, recommendation/request publication, turns, and cycles.
- `port-outbound/`: storage-neutral bounded/conditional blob and monotonic
  clock contracts.
