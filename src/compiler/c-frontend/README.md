# C Frontend

## Purpose

Normalize pinned-Clang C semantics into a deterministic repository-owned form.

## Ownership

This boundary is owned by `function:c-frontend`.

## Prohibitions

It must not expose Clang AST addresses, native paths, or downstream IR policy.

## Navigation

- `adapter-inbound/`: pinned Clang AST adapter.
- `contract/`: normalized frontend artifact contract.
- `composition/`: exact native build and executable entrypoint.
