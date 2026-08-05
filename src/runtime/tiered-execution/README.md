# Tiered Execution

## Purpose

Tiered execution cache, orchestration, and native adapters.

## Ownership

This boundary is owned by `function:tiered-execution`.

## Prohibitions

It must not bypass another function or architectural kind boundary.

## Navigation

- `adapter-outbound/`: governed native/cache parts with isolated limit and
  reclamation transactions.
- `application/`: handoff plus cached/leased retry routing, semantic rebase,
  exact telemetry summaries, FIFO snapshots/assessment, turns, and cycles.
- `domain/`: governed `domain` parts.
