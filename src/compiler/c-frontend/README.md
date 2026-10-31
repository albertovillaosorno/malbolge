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

## Native source acquisition

The standalone frontend reads at most 64 MiB of C source from a regular
file. Input is bounded even when a previously inspected file grows during
acquisition. Linux/Android open source handles nonblocking, preventing a
writerless FIFO (including an alias pointing to one) from stalling the
frontend. On those hosts, the opened descriptor and current path must retain
the same regular inode, size, and nanosecond modification/change times after
reading. Stable regular-file symlinks remain supported. Rejected sources
return `MALBOLGE-FRONTEND-003` without invoking Clang or emitting JSON.
Other hosts use a regular-file precheck, a bounded stream read, and a
post-read pathname check.
