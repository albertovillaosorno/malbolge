# Tiered Execution

## Purpose

Tiered execution IR, cache, and native adapters.

## Ownership

This boundary is owned by `function:tiered-execution`.

## Prohibitions

It must not bypass another function or architectural kind boundary.

## Navigation

- `adapter-outbound/`: governed `adapter-outbound` parts.
- `application/`: handoff, scheduling, bounded retry routing, and rebase.
- `domain/`: governed `domain` parts.
