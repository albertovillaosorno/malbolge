# Tiered-execution filesystem blob adapter

## Purpose

Bind the storage-neutral tiered-execution blob port to one explicit host
filesystem path without granting the adapter application, retry-policy, or
codec authority.

## Owns

- bounded file reads from one caller-configured destination;
- same-directory collision-resistant staging files;
- complete staging writes and file-content synchronization before publication;
- atomic `rename` publication when the host filesystem supports replacement;
- best-effort cleanup of adapter-owned staging files after rejected writes,
  synchronization, or publication.

## Does Not Own

- telemetry framing, validation, assessment, or policy selection;
- byte-limit selection;
- directory creation or destination discovery;
- removal of a previously published destination before replacement;
- directory-entry synchronization after successful publication;
- cross-process locking, compare-and-swap, or multi-blob transactions.

## Failure semantics

A missing destination loads as absent. Reads probe one byte beyond the admitted
bound and reject oversized blobs without returning partial bytes. Publication
uses a new same-directory staging file, writes and synchronizes all bytes,
closes the staging handle, then renames it onto the destination. If staging,
writing,
synchronization, or rename fails, the adapter never removes the previously
published destination and returns exact filesystem error-category evidence.

On hosts where standard-library `rename` does not replace an existing file
atomically, an overwrite may fail safely instead of deleting the destination.
The current port requires any returned failure to leave the prior publication
authoritative, so a remove-then-rename fallback is intentionally prohibited.

Directory fsync is exposed through a separate durability-confirmation port
capability rather than hidden inside `replace`. Application orchestration first
commits publication, then confirms the destination directory; sync failure is
returned as committed `Published` evidence, never as rollback. The ordinary
replacement API keeps its original prepublication failure contract.
